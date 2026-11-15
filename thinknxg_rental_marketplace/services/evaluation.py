"""Customer-side offer comparison, transparent scoring, shortlist/reject, clarifications & negotiation."""
import frappe
from frappe.utils import cint, date_diff, flt, getdate, now_datetime

from thinknxg_rental_marketplace.services import audit, notifications, tender as tender_service
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid

LIVE = tender_service.OFFER_LIVE
TECH_POINTS = {"Full": 100, "Partial": 60, "Alternative": 50}


def score_offers(offers, criteria, today=None):
	"""Pure. offers: dicts(name, comparable_total, delivery_date, rating, technical_compliance, manual_score);
	criteria: dicts(basis, weight, criterion). Lower price/earlier delivery score higher. Returns {name: (total, [rows])}."""
	today = getdate(today) if today else getdate()
	prices = [flt(o["comparable_total"]) for o in offers if flt(o["comparable_total"]) > 0]
	lead = {o["name"]: max(date_diff(o["delivery_date"], today), 0) if o.get("delivery_date") else None for o in offers}
	lead_values = [v for v in lead.values() if v is not None]
	total_weight = sum(flt(c["weight"]) for c in criteria) or 1
	out = {}
	for o in offers:
		rows, total = [], 0.0
		for c in criteria:
			b = c["basis"]
			if b == "Price":
				s = (min(prices) / flt(o["comparable_total"]) * 100) if prices and flt(o["comparable_total"]) > 0 else 0
			elif b == "Delivery":
				l = lead[o["name"]]
				s = 0 if l is None else (100 if not lead_values or max(lead_values) == min(lead_values) else (max(lead_values) - l) / (max(lead_values) - min(lead_values)) * 100)
			elif b == "Rating":
				s = flt(o.get("rating")) / 5 * 100
			elif b == "Technical":
				s = TECH_POINTS.get(o.get("technical_compliance") or "Full", 0)
			else:
				s = flt(o.get("manual_score"))
			w = flt(c["weight"]) / total_weight * 100
			rows.append({"criterion": c.get("criterion"), "basis": b, "weight": round(w, 2), "score": round(s, 2), "weighted_score": round(s * w / 100, 2)})
			total += s * w / 100
		out[o["name"]] = (round(total, 2), rows)
	return out


def _customer_tender(ctx, name):
	t = frappe.get_doc("Marketplace Tender", name)
	if t.customer != ctx.customer:
		forbid()
	return t


def offers_visible_to_customer(t):
	"""Sealed/Rank Only tenders open offers to the customer only once bidding has closed."""
	return t.confidentiality == "Open" or t.status not in ("Bidding Open", "Draft", "Submitted", "Published", "Supplier Matching", "Invitation Sent")


def compare(ctx, name):
	t = _customer_tender(ctx, name)
	base = {"tender": {k: t.get(k) for k in ("name", "title", "status", "transaction_type", "submission_deadline", "currency", "evaluation_method",
		"confidentiality", "offers_count", "invited_count", "duration_days", "contract_months", "required_from", "required_to", "tender_type")},
		"items": [{"name": i.name, "equipment_name": i.equipment_name, "qty": i.qty, "uom": i.uom, "specifications": i.specifications} for i in t.items]}
	if not offers_visible_to_customer(t):
		base["sealed"] = True
		base["offers"] = []
		return base
	statuses = list(LIVE) + ["Accepted", "Technically Rejected", "Rejected"]
	offers = frappe.get_all("Supplier Offer", filters={"tender": t.name, "status": ["in", statuses]}, fields=["*"], order_by="comparable_total asc")
	rows = []
	for o in offers:
		v = frappe.db.get_value("Marketplace Vendor", o.vendor, ["business_name", "verified", "rating", "review_count", "city", "country", "logo", "route"], as_dict=True)
		items = frappe.get_all("Supplier Offer Item", filters={"parent": o.name, "parenttype": "Supplier Offer"},
			fields=["tender_item", "equipment_name", "listing", "is_alternative", "alternative_details", "qty", "uom", "rate_basis", "unit_rate", "periods", "amount", "compliance", "remarks"], order_by="idx")
		missing = [label for f, label in (("delivery_date", "delivery date"), ("payment_terms", "payment terms"), ("valid_until", "validity")) if not o.get(f)]
		covered = {i.tender_item for i in items}
		missing += [frappe._("no line for {0}").format(ti.equipment_name) for ti in t.items if ti.name not in covered]
		short = [frappe._("{0}: offered {1} of {2}").format(ti.equipment_name, sum(flt(i.qty) for i in items if i.tender_item == ti.name), ti.qty)
			for ti in t.items if ti.name in covered and sum(flt(i.qty) for i in items if i.tender_item == ti.name) < flt(ti.qty)]
		rows.append({**{k: o.get(k) for k in ("name", "status", "revision_no", "currency", "rate_basis", "delivery_date", "valid_until", "payment_terms",
			"technical_compliance", "compliance_notes", "commercial_conditions", "security_deposit", "transport_charges", "loading_charges",
			"installation_charges", "mobilization_charges", "demobilization_charges", "tax_percent", "subtotal", "charges_total", "tax_amount",
			"grand_total", "comparable_total", "shortlisted", "total_score", "technical_score", "rental_period_days", "contract_months", "availability_confirmed")},
			"vendor": {"business_name": v.business_name, "verified": v.verified, "rating": v.rating, "review_count": v.review_count,
				"city": v.city, "country": v.country, "logo": v.logo, "route": v.route},
			"items": items, "missing": missing + short})
	live = [r for r in rows if r["status"] in LIVE]
	if live:
		lowest = min(live, key=lambda r: flt(r["comparable_total"]))
		lowest["flags"] = ["Lowest comparable price"]
		dated = [r for r in live if r["delivery_date"]]
		if dated:
			early = min(dated, key=lambda r: getdate(r["delivery_date"]))
			early.setdefault("flags", []).append("Earliest delivery")
		tech = sorted(live, key=lambda r: (-(TECH_POINTS.get(r["technical_compliance"] or "Full", 0)), len(r["missing"]), -flt(r["vendor"]["rating"])))
		tech[0].setdefault("flags", []).append("Best technical match")
	if t.evaluation_method == "Weighted Score" and live:
		crit = [{"criterion": c.criterion, "basis": c.basis or frappe.db.get_value("Offer Evaluation Criterion", c.criterion, "basis"), "weight": c.weight} for c in t.criteria]
		if crit:
			scores = score_offers([{"name": r["name"], "comparable_total": r["comparable_total"], "delivery_date": r["delivery_date"],
				"rating": r["vendor"]["rating"], "technical_compliance": r["technical_compliance"], "manual_score": r.get("technical_score")} for r in live], crit)
			for r in live:
				r["score"], r["score_breakdown"] = scores[r["name"]]
			base["criteria"] = crit
	base["offers"] = rows
	base["clarifications"] = frappe.get_all("Tender Clarification", filters={"tender": t.name},
		fields=["name", "offer", "subject", "message", "response", "status", "clarification_type", "raised_by_party", "counter_amount", "creation"], order_by="creation desc")
	return base


def _offer_for_customer(ctx, offer_name):
	o = frappe.get_doc("Supplier Offer", offer_name)
	t = _customer_tender(ctx, o.tender)
	if not offers_visible_to_customer(t):
		fail("OFFERS_SEALED", "Offers open after the submission deadline.", Conflict)
	return o, t


def shortlist(ctx, offer_name, value=1):
	o, t = _offer_for_customer(ctx, offer_name)
	if o.status not in LIVE:
		fail("OFFER_STATE", "Only active offers can be shortlisted.", Conflict)
	o.db_set("shortlisted", cint(value))
	audit.log("offer.shortlisted" if value else "offer.unshortlisted", o.doctype, o.name)
	if value and t.disclosure_stage == "On Shortlist":
		notifications.to_vendor(o.vendor, frappe._("Your offer was shortlisted: {0}").format(t.title), "", link=f"/marketplace/vendor/tenders/{t.name}", category="Offer", ref=t)
	return o


def reject(ctx, offer_name, reason):
	o, t = _offer_for_customer(ctx, offer_name)
	if o.status not in LIVE:
		fail("OFFER_STATE", "Only active offers can be rejected.", Conflict)
	prev = o.status
	o.db_set({"status": "Rejected", "rejection_reason": reason})
	audit.log("offer.rejected", o.doctype, o.name, prev, "Rejected", reason=reason)
	notifications.to_vendor(o.vendor, frappe._("Offer not selected: {0}").format(t.title), reason or "", link=f"/marketplace/vendor/tenders/{t.name}", category="Offer", ref=t)
	tender_service.refresh_counts(t)
	return o


def operator_evaluate(offer_name, technical_result=None, commercial_result=None, manual_score=None, remarks=None):
	o = frappe.get_doc("Supplier Offer", offer_name)
	ev = frappe.get_doc({"doctype": "Offer Evaluation", "tender": o.tender, "offer": o.name, "evaluator": frappe.session.user,
		"evaluation_type": "Operator", "technical_result": technical_result or "Pending", "commercial_result": commercial_result or "Pending",
		"total_score": flt(manual_score), "remarks": remarks})
	ev.flags.ignore_permissions = True
	ev.insert()
	prev, new = o.status, o.status
	if technical_result == "Rejected":
		new = "Technically Rejected"
	elif technical_result == "Accepted":
		new = "Commercially Accepted" if commercial_result == "Accepted" else "Technically Accepted"
	updates = {"status": new}
	if manual_score is not None:
		updates["technical_score"] = flt(manual_score)
	if o.status in LIVE:
		o.db_set(updates)
	audit.log("offer.evaluated", o.doctype, o.name, prev, new, technical=technical_result, commercial=commercial_result)
	return ev


# ------------------------------------------------------------------ clarifications
def raise_clarification(party, tender_name, subject, message, vendor=None, offer=None, ctype="Clarification", counter_amount=None, user_ctx=None):
	t = frappe.get_doc("Marketplace Tender", tender_name)
	if t.status in ("Cancelled", "Expired", "Awarded"):
		fail("TENDER_STATE", "Clarifications are closed for this tender.", Conflict)
	if party == "Supplier" and ctype not in ("Clarification", "Technical", "Commercial"):
		fail("CLARIFICATION_TYPE", "Suppliers can raise clarification, technical or commercial questions.")
	if ctype in ("Counteroffer", "Revision Request") and not offer:
		fail("CLARIFICATION_OFFER", "Choose the offer to negotiate.")
	if offer:
		ov = frappe.db.get_value("Supplier Offer", offer, ["tender", "vendor", "status"], as_dict=True)
		if not ov or ov.tender != t.name:
			forbid()
		vendor = ov.vendor
	c = frappe.get_doc({"doctype": "Tender Clarification", "tender": t.name, "offer": offer, "vendor": vendor,
		"raised_by_party": party, "clarification_type": ctype, "status": "Open", "raised_by": frappe.session.user,
		"subject": subject[:140], "message": message, "counter_amount": counter_amount})
	c.flags.ignore_permissions = True
	c.insert()
	audit.log("clarification.raised", c.doctype, c.name, party=party, type=ctype)
	if party == "Customer":
		targets = [vendor] if vendor else frappe.get_all("Tender Invitation", filters={"tender": t.name, "status": ["!=", "Excluded"]}, pluck="vendor")
		for v in targets:
			notifications.to_vendor(v, frappe._("{0} on {1}").format(frappe._(ctype), t.title), subject, link=f"/marketplace/vendor/tenders/{t.name}", category="Clarification", ref=t)
	else:
		notifications.to_customer(t.customer, frappe._("Supplier question on {0}").format(t.title), subject, link=f"/marketplace/account/tenders/{t.name}/compare", category="Clarification", ref=t)
	return c


def respond_clarification(party, name, response, share_with_all=0, ctx=None):
	c = frappe.get_doc("Tender Clarification", name)
	if c.status != "Open":
		fail("CLARIFICATION_STATE", "This clarification is already answered.", Conflict)
	if party == c.raised_by_party:
		fail("CLARIFICATION_PARTY", "The other party answers this clarification.")
	c.response = response
	c.status = "Answered"
	c.responded_by = frappe.session.user
	c.responded_on = now_datetime()
	c.share_with_all = cint(share_with_all) if party == "Customer" else 0
	c.flags.ignore_permissions = True
	c.save()
	audit.log("clarification.answered", c.doctype, c.name, "Open", "Answered")
	t = frappe.db.get_value("Marketplace Tender", c.tender, ["customer", "title"], as_dict=True)
	if party == "Customer":
		targets = frappe.get_all("Tender Invitation", filters={"tender": c.tender, "status": ["!=", "Excluded"]}, pluck="vendor") if c.share_with_all else [c.vendor]
		for v in targets:
			if v:
				notifications.to_vendor(v, frappe._("Clarification answered: {0}").format(t.title), c.subject, link=f"/marketplace/vendor/tenders/{c.tender}", category="Clarification", ref=c)
	else:
		notifications.to_customer(t.customer, frappe._("Supplier replied: {0}").format(c.subject), "", link=f"/marketplace/account/tenders/{c.tender}/compare", category="Clarification", ref=c)
	return c

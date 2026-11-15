"""Supplier offers: drafts, server-side pricing, submission with immutable revisions, withdrawal,
and the confidentiality-aware tender view suppliers get."""
import json

import frappe
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, nowdate

from thinknxg_rental_marketplace.services import audit, notifications, pricing, subscriptions, tender as tender_service
from thinknxg_rental_marketplace.services.context import settings
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid
from thinknxg_rental_marketplace.services.money import D, to_float

HEADER = ("rate_basis", "delivery_date", "availability_confirmed", "valid_until", "payment_terms", "technical_compliance",
	"compliance_notes", "commercial_conditions", "security_deposit", "transport_charges", "loading_charges",
	"installation_charges", "mobilization_charges", "demobilization_charges", "tax_percent")
ITEM = ("tender_item", "equipment_name", "listing", "is_alternative", "alternative_details", "qty", "uom", "rate_basis",
	"unit_rate", "compliance", "remarks")
LIVE = tender_service.OFFER_LIVE
EDITABLE = ("Draft", "Withdrawn") + LIVE
SNAPSHOT_SKIP = {"modified", "modified_by", "owner", "creation", "docstatus", "idx", "_user_tags", "_comments", "_assign", "_liked_by", "_seen"}


# ------------------------------------------------------------------ supplier's view of a tender
def disclosed_to(t, vendor):
	stage = t.disclosure_stage
	if stage == "Always":
		return True
	offer = frappe.db.get_value("Supplier Offer", {"tender": t.name, "vendor": vendor}, ["status", "shortlisted"], as_dict=True)
	if stage == "On Shortlist" and offer and (offer.shortlisted or offer.status == "Accepted"):
		return True
	return bool(offer and offer.status == "Accepted")


def tender_for_vendor(t, vendor):
	disclosed = disclosed_to(t, vendor)
	req = frappe.db.get_value("Rental Request", t.rental_request, ["project_name", "site_address", "site_contact", "site_phone",
		"site_access", "special_requirements", "delivery_required", "transport_required", "installation_required",
		"technical_support", "payment_terms_pref", "delivery_terms", "extension_possible", "other_conditions", "project_requirements",
		"expected_monthly_qty"], as_dict=True)
	out = {
		"name": t.name, "title": t.title, "status": t.status, "transaction_type": t.transaction_type, "category": t.category,
		"tender_type": t.tender_type, "confidentiality": t.confidentiality, "submission_deadline": t.submission_deadline,
		"required_from": t.required_from, "required_to": t.required_to, "duration_days": t.duration_days,
		"contract_start": t.contract_start, "contract_months": t.contract_months, "expected_delivery_date": t.expected_delivery_date,
		"city": t.city, "state": t.state, "country": t.country, "currency": t.currency, "terms": t.terms,
		"required_qualifications": t.required_qualifications, "allow_alternatives": t.allow_alternatives,
		"allow_revisions": t.allow_revisions, "max_revisions": t.max_revisions, "budget_max": t.budget_max if t.show_budget else None,
		"reserve_price": t.reserve_price if t.tender_type == "Reverse Auction" else None,
		"items": [{"name": i.name, "equipment_name": i.equipment_name, "category": i.category, "qty": i.qty, "uom": i.uom,
			"specifications": i.specifications, "condition_required": i.condition_required, "brand_preference": i.brand_preference,
			"accept_alternatives": i.accept_alternatives, "certifications_required": i.certifications_required} for i in t.items],
		"requirements": {k: req.get(k) for k in ("special_requirements", "delivery_required", "transport_required", "installation_required",
			"technical_support", "payment_terms_pref", "delivery_terms", "extension_possible", "other_conditions", "project_requirements", "expected_monthly_qty")},
		"customer_disclosed": disclosed,
		"attachments": [{"title": a.title or a.document_type, "document_type": a.document_type, "file": a.file}
			for a in frappe.get_all("Request Attachment", filters={"parent": t.rental_request, "parenttype": "Rental Request", "share_with_suppliers": 1},
			fields=["title", "document_type", "file"])],
		"clarifications": [c for c in frappe.get_all("Tender Clarification", filters={"tender": t.name, "share_with_all": 1, "status": "Answered"},
			fields=["subject", "message", "response", "responded_on"])],
	}
	if disclosed:
		cust = frappe.db.get_value("Marketplace Customer", t.customer, ["customer_name", "company_name", "email", "phone"], as_dict=True)
		out["customer"] = cust
		out["site"] = {k: req.get(k) for k in ("project_name", "site_address", "site_contact", "site_phone", "site_access")}
	else:
		out["customer"] = {"customer_name": frappe._("Verified marketplace customer")}
		out["site"] = {"project_name": None, "site_address": frappe._("{0}, {1} (full address after award)").format(t.city or "", t.country or "")}
	if t.tender_type == "Reverse Auction" and t.status == "Bidding Open":
		lowest = frappe.db.sql("select min(grand_total) from `tabSupplier Offer` where tender=%s and status in %s", (t.name, LIVE))[0][0]
		out["current_lowest"] = lowest
	return out


def mark_viewed(t, vendor):
	inv = tender_service.require_vendor_access(t, vendor)
	if inv.status == "Invited":
		frappe.db.set_value("Tender Invitation", inv.name, {"status": "Viewed", "viewed_on": now_datetime()})
	return inv


def respond_invitation(t, vendor, response, reason=None):
	inv = tender_service.require_vendor_access(t, vendor)
	if inv.status == "Offer Submitted":
		fail("INVITE_STATE", "You have already submitted an offer.", Conflict)
	status = {"interested": "Interested", "decline": "Declined"}.get(response)
	if not status:
		fail("INVITE_RESPONSE", "Unknown response.")
	frappe.db.set_value("Tender Invitation", inv.name, {"status": status, "declined_reason": reason if status == "Declined" else None})
	audit.log("invitation." + status.lower(), "Tender Invitation", inv.name, inv.status, status)


# ------------------------------------------------------------------ offer drafting
def get_offer(t, vendor, create=False):
	name = frappe.db.get_value("Supplier Offer", {"tender": t.name, "vendor": vendor}, "name")
	if name:
		return frappe.get_doc("Supplier Offer", name)
	if not create:
		return None
	s = settings()
	doc = frappe.new_doc("Supplier Offer")
	doc.update({"tender": t.name, "vendor": vendor, "status": "Draft", "rental_request": t.rental_request, "customer": t.customer,
		"transaction_type": t.transaction_type, "currency": t.currency, "revision_no": 0,
		"rate_basis": "Unit" if t.transaction_type == "Sale" else "Monthly",
		"valid_until": add_days(max(getdate(t.submission_deadline), getdate()), cint(s.default_offer_validity_days) or 14),
		"delivery_date": t.required_from or t.contract_start or t.expected_delivery_date})
	return doc


def apply_pricing(doc, t):
	"""Recompute every amount on the server."""
	days = cint(t.duration_days) if t.transaction_type == "Hire" else 0
	months = cint(t.contract_months) if t.transaction_type == "Contract" else 0
	doc.rental_period_days, doc.contract_months = days or None, months or None
	try:
		res = pricing.compute(t.transaction_type, [{"qty": i.qty, "unit_rate": i.unit_rate, "rate_basis": i.rate_basis or doc.rate_basis} for i in doc.items],
			charges={f: doc.get(f) for f in pricing.CHARGE_FIELDS}, tax_percent=doc.tax_percent or 0, days=days, months=months,
			currency=t.currency, security_deposit=doc.security_deposit)
	except pricing.PricingError as e:
		fail("OFFER_PRICING", str(e))
	for row, line in zip(doc.items, res["lines"]):
		row.rate_basis, row.periods, row.amount = line["rate_basis"], float(line["periods"]), to_float(line["amount"], t.currency)
	for f, v in res["charges"].items():
		doc.set(f, to_float(v, t.currency))
	for f in ("subtotal", "charges_total", "tax_amount", "grand_total", "comparable_total", "security_deposit"):
		doc.set(f, to_float(res[f], t.currency))
	return res


def _validate_lines(doc, t, vendor):
	tender_items = {i.name: i for i in t.items}
	if not doc.items:
		fail("OFFER_ITEMS", "Add at least one offer line.")
	for row in doc.items:
		ti = tender_items.get(row.tender_item)
		if not ti:
			fail("OFFER_TENDER_ITEM", "Row {idx}: link each line to a tender requirement line.", idx=row.idx)
		if row.is_alternative and not (t.allow_alternatives and ti.accept_alternatives):
			fail("OFFER_ALTERNATIVE", "Row {idx}: alternatives are not accepted for {item}.", idx=row.idx, item=ti.equipment_name)
		row.uom = row.uom or ti.uom
		row.equipment_name = row.equipment_name or ti.equipment_name
		if row.listing:
			l = frappe.db.get_value("Marketplace Listing", row.listing, ["vendor", "status", "allow_hire", "allow_sale", "allow_contract"], as_dict=True)
			if not l or l.vendor != vendor:
				forbid("LISTING_FORBIDDEN", "Offer lines can only use your own listings.")
			if l.status != "Published":
				fail("LISTING_UNPUBLISHED", "Row {idx}: listing {l} is not published.", idx=row.idx, l=row.listing)
			if not l.get("allow_" + t.transaction_type.lower()):
				fail("LISTING_MODE", "Row {idx}: listing {l} is not offered for {tx}.", idx=row.idx, l=row.listing, tx=t.transaction_type)


def save_draft(vctx, tender_name, data):
	t = frappe.get_doc("Marketplace Tender", tender_name)
	tender_service.require_vendor_access(t, vctx.vendor)
	doc = get_offer(t, vctx.vendor, create=True)
	if not can_edit(t, None if doc.is_new() else doc):
		fail("TENDER_CLOSED", "This tender is not accepting offers.", Conflict)
	if doc.status not in EDITABLE:
		fail("OFFER_STATE", "This offer can no longer be edited.", Conflict)
	for k in HEADER:
		if k in data:
			doc.set(k, data.get(k))
	if "items" in data:
		doc.set("items", [])
		for it in data.get("items") or []:
			doc.append("items", {k: it.get(k) for k in ITEM if k in it})
	_validate_lines(doc, t, vctx.vendor)
	apply_pricing(doc, t)
	if doc.valid_until and getdate(doc.valid_until) < getdate():
		fail("OFFER_VALIDITY", "Offer validity cannot be in the past.")
	if doc.status == "Withdrawn":
		doc.status = "Draft"
	doc.flags.ignore_permissions = True
	doc.save()
	return doc


def can_edit(t, offer):
	"""Before the deadline while bidding is open; afterwards only in negotiated tenders when the customer asked for a revision."""
	if t.status == "Bidding Open" and get_datetime(t.submission_deadline) > now_datetime():
		return True
	if offer and t.status == "Evaluation" and t.tender_type == "Negotiated":
		return bool(frappe.db.exists("Tender Clarification", {"tender": t.name, "offer": offer.name, "status": "Open",
			"clarification_type": ["in", ["Revision Request", "Counteroffer"]], "raised_by_party": "Customer"}))
	return False


def snapshot(doc):
	data = doc.as_dict(no_default_fields=False)
	for k in list(data):
		if k in SNAPSHOT_SKIP:
			data.pop(k)
	data["items"] = [{k: v for k, v in r.items() if k not in SNAPSHOT_SKIP | {"parent", "parenttype", "parentfield", "doctype"}} for r in data.get("items", [])]
	data.pop("attachments", None)
	return json.loads(json.dumps(data, default=str))


def submit(vctx, offer_name, reason=None, idempotency_key=None):
	doc = frappe.get_doc("Supplier Offer", offer_name)
	if doc.vendor != vctx.vendor:
		forbid()
	t = tender_service.lock(doc.tender)  # serialises submissions against close/award
	frappe.db.sql("select name from `tabSupplier Offer` where name=%s for update", doc.name)
	doc.reload()
	if idempotency_key and doc.idempotency_key == idempotency_key and doc.status in LIVE:
		return doc
	tender_service.require_vendor_access(t, vctx.vendor)
	if not can_edit(t, doc):
		fail("TENDER_CLOSED", "The submission deadline has passed or the tender is not open.", Conflict)
	if doc.status not in EDITABLE:
		fail("OFFER_STATE", "This offer cannot be submitted in its current state.", Conflict)
	first = cint(doc.revision_no) == 0
	if not first and not t.allow_revisions:
		fail("REVISIONS_DISABLED", "This tender does not allow revised offers.", Conflict)
	if not first and cint(t.max_revisions) and cint(doc.revision_no) >= cint(t.max_revisions) + 1:
		fail("REVISION_LIMIT", "Maximum number of revisions reached.", Conflict)
	subscriptions.check_offer_limit(vctx.vendor, first_submission=first)
	if not doc.availability_confirmed:
		fail("AVAILABILITY_UNCONFIRMED", "Confirm that the offered equipment is available for the requested period.")
	if not doc.delivery_date:
		fail("OFFER_DELIVERY", "Delivery date is required.")
	_validate_lines(doc, t, vctx.vendor)
	apply_pricing(doc, t)
	if t.tender_type == "Reverse Auction":
		if flt(t.reserve_price) and flt(doc.grand_total) > flt(t.reserve_price):
			fail("ABOVE_RESERVE", "Offer exceeds the reverse auction ceiling.", Conflict)
		lowest = frappe.db.sql("select min(grand_total) from `tabSupplier Offer` where tender=%s and status in %s and name!=%s",
			(t.name, LIVE, doc.name))[0][0]
		if lowest and flt(doc.grand_total) > flt(lowest) * (1 - flt(t.min_decrement_percent) / 100.0):
			fail("BID_DECREMENT", "Bids must beat the current lowest by at least {p}%.", Conflict, p=t.min_decrement_percent)
	prev = doc.status
	doc.revision_no = cint(doc.revision_no) + 1
	doc.status = "Under Review" if t.status == "Evaluation" else "Submitted"
	doc.submitted_on = now_datetime()
	doc.idempotency_key = idempotency_key
	doc.flags.ignore_permissions = True
	doc.save()
	rev = frappe.get_doc({"doctype": "Offer Revision", "offer": doc.name, "tender": t.name, "vendor": doc.vendor,
		"revision_no": doc.revision_no, "grand_total": doc.grand_total, "submitted_on": doc.submitted_on,
		"submitted_by": frappe.session.user, "reason": reason, "snapshot": json.dumps(snapshot(doc))})
	rev.flags.ignore_permissions = True
	rev.insert()
	# close any revision request this answered
	for c in frappe.get_all("Tender Clarification", filters={"tender": t.name, "offer": doc.name, "status": "Open",
		"clarification_type": ["in", ["Revision Request", "Counteroffer"]]}, pluck="name"):
		frappe.db.set_value("Tender Clarification", c, {"status": "Answered", "response": frappe._("Revised offer submitted (revision {0})").format(doc.revision_no),
			"responded_by": frappe.session.user, "responded_on": now_datetime()})
	inv = frappe.db.get_value("Tender Invitation", {"tender": t.name, "vendor": doc.vendor}, "name")
	if inv:
		frappe.db.set_value("Tender Invitation", inv, "status", "Offer Submitted")
	if first:
		frappe.db.sql("update `tabMarketplace Vendor` set offers_submitted=ifnull(offers_submitted,0)+1 where name=%s", doc.vendor)
	tender_service.refresh_counts(t)
	audit.log("offer.submitted", doc.doctype, doc.name, prev, doc.status, revision=doc.revision_no, grand_total=doc.grand_total)
	label = frappe._("New offer") if first else frappe._("Revised offer")
	notifications.to_customer(t.customer, frappe._("{0} on {1}").format(label, t.title),
		frappe._("You now have {0} offers.").format(t.offers_count), link=f"/marketplace/account/tenders/{t.name}/compare", category="Offer", ref=t)
	return doc


def withdraw(vctx, offer_name, reason=None):
	doc = frappe.get_doc("Supplier Offer", offer_name)
	if doc.vendor != vctx.vendor:
		forbid()
	tender_service.lock(doc.tender)
	doc.reload()
	if doc.status not in LIVE + ("Draft",):
		fail("OFFER_STATE", "This offer cannot be withdrawn.", Conflict)
	prev = doc.status
	doc.db_set("status", "Withdrawn")
	t = frappe.get_doc("Marketplace Tender", doc.tender)
	tender_service.refresh_counts(t)
	audit.log("offer.withdrawn", doc.doctype, doc.name, prev, "Withdrawn", reason=reason)
	if prev != "Draft":
		notifications.to_customer(t.customer, frappe._("An offer was withdrawn on {0}").format(t.title), reason or "", link=f"/marketplace/account/tenders/{t.name}/compare", ref=t)
	return doc


def vendor_offer_view(doc, t):
	out = {k: doc.get(k) for k in ("name", "status", "revision_no", "submitted_on", "currency", "rate_basis", "rental_period_days",
		"contract_months") + HEADER + ("subtotal", "charges_total", "tax_amount", "grand_total", "rejection_reason", "shortlisted")}
	out["items"] = [{k: r.get(k) for k in ITEM + ("periods", "amount")} for r in doc.items]
	out["revisions"] = frappe.get_all("Offer Revision", filters={"offer": doc.name}, fields=["revision_no", "grand_total", "submitted_on", "reason"], order_by="revision_no desc")
	out["can_edit"] = can_edit(t, doc) and doc.status in EDITABLE
	if t.confidentiality in ("Rank Only", "Open") and doc.status in LIVE:
		totals = [r[0] for r in frappe.db.sql("select comparable_total from `tabSupplier Offer` where tender=%s and status in %s order by comparable_total", (t.name, LIVE))]
		out["rank"] = (totals.index(doc.comparable_total) + 1) if doc.comparable_total in totals else None
		out["rank_of"] = len(totals) if t.confidentiality == "Open" else None
	return out

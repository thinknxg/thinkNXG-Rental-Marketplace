"""Platform operator console API (Marketplace Admin / Moderator / Finance)."""
import frappe
from frappe.utils import add_days, cint, flt, getdate

from thinknxg_rental_marketplace.api.utils import mark_read, notifications_for, paged, parse
from thinknxg_rental_marketplace.services import (
	audit, booking as booking_service, evaluation, fulfilment, matching, payments, settlement, tender as tender_service, trust, vendors,
)
from thinknxg_rental_marketplace.services.context import is_operator, require_operator
from thinknxg_rental_marketplace.services.errors import fail


def has_app_permission():
	return is_operator()


@frappe.whitelist()
def dashboard():
	require_operator()
	since = add_days(getdate(), -30)
	tx = frappe.db.sql("""select transaction_type, count(*) n, sum(grand_total) value, sum(commission_amount) commission
		from `tabMarketplace Booking` where status not in ('Cancelled') group by transaction_type""", as_dict=True)
	reqs = frappe.db.count("Rental Request", {"status": ["!=", "Draft"]})
	booked = frappe.db.count("Rental Request", {"status": ["in", ["Booked", "Closed"]], "booking": ["is", "set"]})
	return {
		"counts": {
			"vendors_pending": frappe.db.count("Marketplace Vendor", {"status": ["in", ["Submitted", "Documents Pending", "Under Review"]]}),
			"vendors_active": frappe.db.count("Marketplace Vendor", {"status": "Approved"}),
			"customers": frappe.db.count("Marketplace Customer"),
			"requests_total": reqs,
			"tenders_active": frappe.db.count("Marketplace Tender", {"status": ["in", ["Bidding Open", "Invitation Sent", "Evaluation", "Bidding Closed"]]}),
			"tenders_moderation": frappe.db.count("Marketplace Tender", {"status": ["in", ["Submitted", "Suspended"]]}),
			"offers_30d": frappe.db.count("Supplier Offer", {"submitted_on": [">=", since]}),
			"bookings_active": frappe.db.count("Marketplace Booking", {"status": ["not in", ["Completed", "Cancelled"]]}),
			"payments_to_confirm": frappe.db.count("Marketplace Payment", {"status": "Pending", "gateway": "Manual"}),
			"disputes_open": frappe.db.count("Marketplace Dispute", {"status": ["in", ["Open", "Under Review", "Escalated"]]}),
			"reviews_pending": frappe.db.count("Marketplace Review", {"status": "Pending Moderation"}),
		},
		"conversion": round(booked / reqs * 100, 1) if reqs else 0,
		"avg_offers_per_tender": flt(frappe.db.sql("select avg(offers_count) from `tabMarketplace Tender` where status not in ('Draft','Submitted')")[0][0], 2),
		"avg_suppliers_per_tender": flt(frappe.db.sql("select avg(invited_count) from `tabMarketplace Tender` where status not in ('Draft','Submitted')")[0][0], 2),
		"by_transaction": tx,
		"by_category": frappe.db.sql("""select t.category, count(distinct t.name) tenders, count(b.name) bookings, sum(b.grand_total) value
			from `tabMarketplace Tender` t left join `tabMarketplace Booking` b on b.tender=t.name and b.status!='Cancelled'
			group by t.category order by tenders desc limit 12""", as_dict=True),
		"by_country": frappe.db.sql("""select t.country, count(distinct t.name) tenders, count(b.name) bookings, sum(b.grand_total) value
			from `tabMarketplace Tender` t left join `tabMarketplace Booking` b on b.tender=t.name and b.status!='Cancelled'
			group by t.country order by tenders desc limit 12""", as_dict=True),
		"revenue": {
			"subscriptions": flt(frappe.db.sql("select sum(amount) from `tabMarketplace Payment` where payment_type='Subscription' and status='Succeeded'")[0][0]),
			"commission_earned": flt(frappe.db.sql("select sum(commission_amount) from `tabMarketplace Commission` where status in ('Earned','Settled')")[0][0]),
			"commission_accrued": flt(frappe.db.sql("select sum(commission_amount) from `tabMarketplace Commission` where status='Accrued'")[0][0]),
			"promotions": flt(frappe.db.sql("select sum(amount) from `tabMarketplace Payment` where payment_type in ('Featured Fee','Listing Fee') and status='Succeeded'")[0][0]),
		},
		"notifications": notifications_for(frappe.session.user, 8),
	}


# ------------------------------------------------------------------ vendors & customers
@frappe.whitelist()
def vendors_list(status=None, q=None, page=1):
	require_operator()
	filters = {}
	if status:
		filters["status"] = ["in", status.split(",")]
	if q:
		filters["business_name"] = ["like", f"%{q[:80]}%"]
	return paged("Marketplace Vendor", filters, ["name", "business_name", "business_type", "status", "verified", "city", "country", "rating",
		"review_count", "offers_submitted", "offers_won", "submitted_on", "erp_company"], "modified desc", page)


@frappe.whitelist()
def vendor_get(name):
	require_operator()
	v = frappe.get_doc("Marketplace Vendor", name)
	out = v.as_dict()
	if not is_operator("finance"):
		for f in vendors.BANK_FIELDS:
			out.pop(f, None)
	out["documents"] = frappe.get_all("Vendor Verification", filters={"vendor": name}, fields=["name", "document_type", "status", "attachment", "document_number", "expiry_date", "remarks"])
	out["users"] = frappe.get_all("Vendor User", filters={"vendor": name}, fields=["user", "full_name", "vendor_role", "enabled"])
	out["subscriptions"] = frappe.get_all("Vendor Subscription", filters={"vendor": name}, fields=["name", "plan", "status", "start_date", "end_date"], order_by="creation desc")
	out["listings"] = frappe.db.count("Marketplace Listing", {"vendor": name})
	out["history"] = audit.history("Marketplace Vendor", name)
	out["transitions"] = sorted(vendors.VENDOR_TRANSITIONS.get(v.status, set()))
	return out


@frappe.whitelist(methods=["POST"])
def vendor_set_status(name, status, reason=None):
	require_operator("moderator")
	return vendors.set_status(name, status, reason).status


@frappe.whitelist(methods=["POST"])
def vendor_document_review(name, status, remarks=None):
	require_operator("moderator")
	return vendors.review_document(name, status, remarks).status


@frappe.whitelist(methods=["POST"])
def vendor_erp_link(name, erp_company=None, erp_supplier=None):
	require_operator("admin")
	frappe.db.set_value("Marketplace Vendor", name, {"erp_company": erp_company or None, "erp_supplier": erp_supplier or None})
	audit.log("vendor.erp_linked", "Marketplace Vendor", name, company=erp_company)
	return True


@frappe.whitelist()
def customers_list(status=None, q=None, page=1):
	require_operator()
	filters = {}
	if status:
		filters["status"] = status
	if q:
		filters["customer_name"] = ["like", f"%{q[:80]}%"]
	return paged("Marketplace Customer", filters, ["name", "customer_name", "customer_type", "company_name", "status", "verified", "email", "city", "country", "creation"], "creation desc", page)


@frappe.whitelist(methods=["POST"])
def customer_set_status(name, status=None, verified=None, reason=None):
	require_operator("moderator")
	updates = {}
	if status in ("Active", "Restricted", "Suspended"):
		updates.update(status=status, restriction_reason=reason)
	if verified is not None:
		updates["verified"] = cint(verified)
	frappe.db.set_value("Marketplace Customer", name, updates)
	audit.log("customer.updated", "Marketplace Customer", name, **{k: str(v) for k, v in updates.items()})
	return True


# ------------------------------------------------------------------ tenders & offers
@frappe.whitelist()
def tenders_list(status=None, q=None, page=1):
	require_operator()
	filters = {}
	if status:
		filters["status"] = ["in", status.split(",")]
	if q:
		filters["title"] = ["like", f"%{q[:80]}%"]
	return paged("Marketplace Tender", filters, ["name", "title", "status", "transaction_type", "category", "customer", "city", "country",
		"submission_deadline", "invited_count", "offers_count", "tender_type", "visibility", "awarded_vendor", "booking"], "modified desc", page)


@frappe.whitelist()
def tender_get(name):
	require_operator()
	t = frappe.get_doc("Marketplace Tender", name)
	out = t.as_dict()
	out["invitations"] = frappe.get_all("Tender Invitation", filters={"tender": name}, fields=["name", "vendor", "status", "source", "match_score", "match_reasons", "invited_on", "viewed_on"], order_by="match_score desc")
	for i in out["invitations"]:
		i["vendor_name"] = frappe.db.get_value("Marketplace Vendor", i.vendor, "business_name")
	out["offers"] = frappe.get_all("Supplier Offer", filters={"tender": name}, fields=["name", "vendor", "status", "revision_no", "grand_total", "currency",
		"delivery_date", "valid_until", "technical_compliance", "technical_score", "shortlisted", "submitted_on"], order_by="grand_total asc")
	for o in out["offers"]:
		o["vendor_name"] = frappe.db.get_value("Marketplace Vendor", o.vendor, "business_name")
		o["revisions"] = frappe.get_all("Offer Revision", filters={"offer": o.name}, fields=["name", "revision_no", "grand_total", "submitted_on", "reason"], order_by="revision_no desc")
	out["clarifications"] = frappe.get_all("Tender Clarification", filters={"tender": name}, fields=["name", "vendor", "subject", "message", "response", "status", "raised_by_party", "clarification_type", "creation"], order_by="creation desc")
	out["history"] = audit.history("Marketplace Tender", name)
	out["customer_name"] = frappe.db.get_value("Marketplace Customer", t.customer, "customer_name")
	return out


@frappe.whitelist()
def tender_candidates(name):
	require_operator("moderator")
	t = frappe.get_doc("Marketplace Tender", name)
	rows = matching.candidates(t)
	for r in rows:
		r["vendor_name"] = frappe.db.get_value("Marketplace Vendor", r.vendor, "business_name")
		r["invited"] = bool(frappe.db.exists("Tender Invitation", {"tender": name, "vendor": r.vendor}))
	return rows


@frappe.whitelist(methods=["POST"])
def tender_action(name, action, data=None):
	require_operator("moderator")
	data = parse(data)
	if action == "publish":
		tender_service.publish(name, actor="operator")
	elif action == "suspend":
		tender_service.suspend(name, data.get("reason") or "")
	elif action == "resume":
		tender_service.resume(name)
	elif action == "cancel":
		tender_service.cancel(name, data.get("reason") or "Cancelled by marketplace")
	elif action == "extend":
		tender_service.extend(name, data.get("deadline"), data.get("reason"))
	elif action == "close":
		tender_service.close_bidding(name)
	elif action == "invite":
		t = frappe.get_doc("Marketplace Tender", name)
		tender_service.invite(t, data.get("vendors") or [], source="Admin Override")
	elif action == "exclude":
		inv = data.get("invitation")
		if frappe.db.get_value("Tender Invitation", inv, "tender") != name:
			fail("INVITATION", "Invitation does not belong to this tender.")
		frappe.db.set_value("Tender Invitation", inv, "status", "Excluded")
		audit.log("invitation.excluded", "Tender Invitation", inv)
		tender_service.refresh_counts(frappe.get_doc("Marketplace Tender", name))
	elif action == "settings":
		t = tender_service.lock(name)
		if t.status not in ("Draft", "Submitted", "Suspended", "Bidding Open"):
			fail("TENDER_STATE", "Rules can change before evaluation only.")
		for f in ("tender_type", "visibility", "confidentiality", "disclosure_stage", "evaluation_method", "require_verified", "min_vendor_rating",
			"allow_revisions", "max_revisions", "allow_alternatives", "reserve_price", "min_decrement_percent", "show_budget", "terms", "required_qualifications", "featured"):
			if f in data:
				t.set(f, data[f])
		t.flags.ignore_permissions = True
		t.save()
		audit.log("tender.rules_changed", t.doctype, t.name, **{k: str(v) for k, v in data.items()})
	else:
		fail("ACTION", "Unknown action.")
	return tender_get(name)


@frappe.whitelist(methods=["POST"])
def offer_evaluate(offer, technical_result=None, commercial_result=None, manual_score=None, remarks=None):
	require_operator("moderator")
	evaluation.operator_evaluate(offer, technical_result, commercial_result, flt(manual_score) if manual_score not in (None, "") else None, remarks)
	return True


@frappe.whitelist()
def offer_revision(name):
	require_operator("moderator")
	return frappe.get_doc("Offer Revision", name).as_dict()


# ------------------------------------------------------------------ bookings & money
@frappe.whitelist()
def bookings_list(status=None, page=1):
	require_operator()
	filters = {"status": ["in", status.split(",")]} if status else {}
	return paged("Marketplace Booking", filters, ["name", "status", "transaction_type", "customer", "vendor", "grand_total", "amount_paid",
		"balance_due", "commission_amount", "currency", "start_date", "end_date", "creation"], "creation desc", page)


@frappe.whitelist()
def booking_get(name):
	require_operator()
	b = frappe.get_doc("Marketplace Booking", name)
	out = b.as_dict()
	out["payments"] = frappe.get_all("Marketplace Payment", filters={"booking": name}, fields=["name", "payment_type", "status", "amount", "currency", "gateway", "payer_reference", "refund_of", "creation"])
	out["commission"] = frappe.get_all("Marketplace Commission", filters={"booking": name}, fields=["name", "status", "commission_amount", "basis", "rate"])
	out["vendor_order_doc"] = frappe.get_doc("Vendor Order", b.vendor_order).as_dict() if b.vendor_order else None
	out["history"] = audit.history("Marketplace Booking", name)
	out["next_actions"] = fulfilment.allowed_next(b)
	return out


@frappe.whitelist(methods=["POST"])
def booking_action(name, action, data=None):
	require_operator("moderator")
	data = parse(data)
	if action == "cancel":
		booking_service.cancel(name, "Operator", data.get("reason") or "Cancelled by marketplace")
	elif action in fulfilment.ACTORS:
		fulfilment.transition(name, action, "Operator", data)
	else:
		fail("ACTION", "Unknown action.")
	return booking_get(name)


@frappe.whitelist()
def payments_list(status=None, payment_type=None, page=1):
	require_operator("finance")
	filters = {}
	if status:
		filters["status"] = ["in", status.split(",")]
	if payment_type:
		filters["payment_type"] = payment_type
	return paged("Marketplace Payment", filters, ["name", "payment_type", "status", "amount", "refunded_amount", "currency", "booking", "customer",
		"vendor", "subscription", "gateway", "payer_reference", "refund_of", "confirmed_on", "creation"], "creation desc", page)


@frappe.whitelist(methods=["POST"])
def payment_confirm(name, reference=None):
	"""Finance confirms a manual payment (bank transfer received) or a pending manual refund (money sent)."""
	require_operator("finance")
	p = frappe.get_doc("Marketplace Payment", name)
	if p.gateway != "Manual":
		fail("GATEWAY_CONFIRMS", "Gateway payments are confirmed by the provider's webhook only.")
	if p.payment_type == "Refund":
		payments.confirm_refund(name, reference)
	else:
		payments.mark_succeeded(name, reference, source="finance", payer_reference=reference)
	return True


@frappe.whitelist(methods=["POST"])
def payment_fail(name, reason):
	require_operator("finance")
	payments.mark_failed(name, reason)
	return True


@frappe.whitelist(methods=["POST"])
def payment_refund(name, amount, reason=None):
	require_operator("finance")
	return payments.refund(name, amount, reason).name


@frappe.whitelist()
def commissions_list(status=None, page=1):
	require_operator("finance")
	return paged("Marketplace Commission", {"status": status} if status else {}, ["name", "booking", "vendor", "status", "basis", "rate", "base_amount", "commission_amount", "currency", "settlement"], "creation desc", page)


@frappe.whitelist()
def settlements_list(status=None, page=1):
	require_operator("finance")
	return paged("Marketplace Settlement", {"status": status} if status else {}, ["name", "vendor", "status", "period_from", "period_to", "gross_amount", "commission_amount", "refund_amount", "net_payable", "currency", "payout_reference"], "creation desc", page)


@frappe.whitelist(methods=["POST"])
def settlement_action(action, name=None, vendor=None, period_from=None, period_to=None, payout_reference=None):
	require_operator("finance")
	if action == "build":
		return settlement.build(vendor, period_from, period_to).name
	if action == "approve":
		return settlement.approve(name).status
	if action == "paid":
		return settlement.mark_paid(name, payout_reference).status
	if action == "cancel":
		return settlement.cancel(name).status
	fail("ACTION", "Unknown action.")


@frappe.whitelist()
def subscriptions_list(status=None, page=1):
	require_operator("finance")
	return paged("Vendor Subscription", {"status": status} if status else {}, ["name", "vendor", "plan", "status", "change_type", "start_date", "end_date", "amount", "currency"], "creation desc", page)


# ------------------------------------------------------------------ catalogue, trust
@frappe.whitelist()
def listings_list(status=None, q=None, page=1):
	require_operator()
	filters = {}
	if status:
		filters["status"] = status
	if q:
		filters["title"] = ["like", f"%{q[:80]}%"]
	return paged("Marketplace Listing", filters, ["name", "title", "vendor", "category", "status", "featured", "total_qty", "currency", "monthly_rate", "sale_price", "route"], "modified desc", page)


@frappe.whitelist(methods=["POST"])
def listing_moderate(name, action, reason=None, until=None):
	require_operator("moderator")
	if action == "suspend":
		frappe.db.set_value("Marketplace Listing", name, "status", "Suspended")
	elif action == "restore":
		frappe.db.set_value("Marketplace Listing", name, "status", "Paused")
	elif action == "feature":
		frappe.db.set_value("Marketplace Listing", name, {"featured": 1, "featured_until": until or add_days(getdate(), 30)})
	elif action == "unfeature":
		frappe.db.set_value("Marketplace Listing", name, {"featured": 0, "featured_until": None})
	else:
		fail("ACTION", "Unknown action.")
	audit.log("listing.moderated", "Marketplace Listing", name, action=action, reason=reason)
	return True


@frappe.whitelist()
def reviews_list(status="Pending Moderation", page=1):
	require_operator("moderator")
	return paged("Marketplace Review", {"status": status} if status else {}, ["name", "booking", "vendor", "customer", "status", "rating", "title", "comment", "creation"], "creation desc", page)


@frappe.whitelist(methods=["POST"])
def review_moderate(name, status):
	require_operator("moderator")
	trust.moderate_review(name, status)
	return True


@frappe.whitelist()
def disputes_list(status=None, page=1):
	require_operator("moderator")
	return paged("Marketplace Dispute", {"status": ["in", status.split(",")]} if status else {}, ["name", "booking", "raised_by_party", "dispute_type", "status", "claimed_amount", "refund_amount", "creation"], "creation desc", page)


@frappe.whitelist()
def dispute_get(name):
	require_operator("moderator")
	d = frappe.get_doc("Marketplace Dispute", name).as_dict()
	d["booking_info"] = frappe.db.get_value("Marketplace Booking", d.booking, ["status", "customer", "vendor", "grand_total", "amount_paid", "currency"], as_dict=True)
	return d


@frappe.whitelist(methods=["POST"])
def dispute_resolve(name, status, resolution, refund_amount=0):
	require_operator("moderator")
	if flt(refund_amount) and not is_operator("finance"):
		fail("FINANCE_ONLY", "Refunds need a Finance user.")
	trust.resolve_dispute(name, status, resolution, refund_amount)
	return True


@frappe.whitelist()
def enquiries(page=1):
	require_operator()
	return paged("Marketplace Enquiry", {}, ["name", "full_name", "email", "company", "enquiry_type", "status", "message", "creation"], "creation desc", page)


@frappe.whitelist()
def audit_trail(doctype=None, name=None, page=1):
	require_operator()
	filters = {}
	if doctype:
		filters["reference_doctype"] = doctype
	if name:
		filters["reference_name"] = name
	return paged("Marketplace Audit Event", filters, ["event", "reference_doctype", "reference_name", "actor", "from_state", "to_state", "creation", "data"], "creation desc", page, 50)


@frappe.whitelist()
def notifications():
	require_operator()
	return notifications_for(frappe.session.user)


@frappe.whitelist(methods=["POST"])
def notifications_read(names=None):
	require_operator()
	return mark_read(frappe.session.user, names)

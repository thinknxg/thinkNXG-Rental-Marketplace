"""Supplier portal API. Tenant isolation: every query is filtered by the vendor resolved from the session."""
import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, getdate, add_days

from thinknxg_rental_marketplace.api.utils import mark_read, notifications_for, paged, parse
from thinknxg_rental_marketplace.services import (
	audit, availability, booking as booking_service, evaluation, fulfilment, offers, payments, subscriptions,
	tender as tender_service, trust, vendors,
)
from thinknxg_rental_marketplace.services.context import require_vendor
from thinknxg_rental_marketplace.services.errors import fail, forbid

LISTING_LIST = ["name", "title", "category", "status", "route", "cover_image", "allow_hire", "allow_sale", "allow_contract", "total_qty",
	"available_today", "currency", "daily_rate", "weekly_rate", "monthly_rate", "sale_price", "contract_monthly_rate", "featured", "modified"]
BOOKING_LIST = ["name", "status", "transaction_type", "tender", "start_date", "end_date", "delivery_date", "currency", "grand_total",
	"amount_paid", "balance_due", "commission_amount", "city", "project_name", "creation", "vendor_order"]


def _own(doctype, name, ctx=None, field="vendor"):
	ctx = ctx or require_vendor()
	doc = frappe.get_doc(doctype, name)
	if doc.get(field) != ctx.vendor:
		forbid()
	return ctx, doc


@frappe.whitelist()
def dashboard():
	ctx = require_vendor()
	v = ctx.vendor
	invited = frappe.get_all("Tender Invitation", filters={"vendor": v, "status": ["in", ["Invited", "Viewed", "Interested"]]}, pluck="tender")
	return {
		"vendor": frappe.db.get_value("Marketplace Vendor", v, ["name", "business_name", "status", "verified", "rating", "review_count",
			"offers_submitted", "offers_won", "logo", "route", "status_reason"], as_dict=True),
		"role": ctx.role,
		"entitlements": subscriptions.entitlements(v),
		"counts": {
			"invited_open": frappe.db.count("Marketplace Tender", {"name": ["in", invited or ["-"]], "status": "Bidding Open"}),
			"submitted": frappe.db.count("Supplier Offer", {"vendor": v, "status": ["in", list(tender_service.OFFER_LIVE)]}),
			"won": frappe.db.count("Supplier Offer", {"vendor": v, "status": "Accepted"}),
			"open_clarifications": frappe.db.count("Tender Clarification", {"vendor": v, "status": "Open", "raised_by_party": "Customer"}),
			"active_bookings": frappe.db.count("Marketplace Booking", {"vendor": v, "status": ["not in", ["Completed", "Cancelled", "Pending Payment"]]}),
			"at_site": frappe.db.count("Marketplace Booking", {"vendor": v, "status": ["in", ["On Hire", "Off-Hire Requested", "Active", "Mobilized"]]}),
			"returns_due": frappe.db.count("Marketplace Booking", {"vendor": v, "status": ["in", ["On Hire", "Off-Hire Requested"]], "end_date": ["<=", add_days(getdate(), 7)]}),
			"sale_orders": frappe.db.count("Marketplace Booking", {"vendor": v, "transaction_type": "Sale", "status": ["not in", ["Completed", "Cancelled"]]}),
			"contracts": frappe.db.count("Marketplace Booking", {"vendor": v, "transaction_type": "Contract", "status": ["not in", ["Completed", "Cancelled"]]}),
			"listings": frappe.db.count("Marketplace Listing", {"vendor": v, "status": "Published"}),
		},
		"revenue": frappe.db.sql("""select currency, sum(grand_total) total, sum(commission_amount) commission from `tabMarketplace Booking`
			where vendor=%s and status not in ('Cancelled','Pending Payment') group by currency""", v, as_dict=True),
		"notifications": notifications_for(frappe.session.user, 8),
	}


# ------------------------------------------------------------------ profile, documents, staff
@frappe.whitelist()
def profile():
	ctx = require_vendor()
	d = frappe.get_doc("Marketplace Vendor", ctx.vendor)
	out = {f: d.get(f) for f in vendors.PROFILE_FIELDS + ("name", "status", "verified", "route", "rating", "review_count", "status_reason", "erp_company")}
	if ctx.role == "Owner":
		out.update({f: d.get(f) for f in vendors.BANK_FIELDS})
	out["categories"] = [c.category for c in d.categories]
	out["locations"] = [{k: l.get(k) for k in ("location_name", "city", "state", "country", "delivery_radius_km", "is_head_office")} for l in d.locations]
	out["documents"] = frappe.get_all("Vendor Verification", filters={"vendor": ctx.vendor}, fields=["name", "document_type", "status", "document_number", "expiry_date", "remarks", "creation"])
	out["staff"] = frappe.get_all("Vendor User", filters={"vendor": ctx.vendor}, fields=["name", "user", "full_name", "vendor_role", "enabled"])
	out["role"] = ctx.role
	return out


@frappe.whitelist(methods=["POST"])
def profile_update(data):
	ctx = require_vendor("Manager", active=False)
	vendors.update_profile(ctx, parse(data))
	return profile()


@frappe.whitelist(methods=["POST"])
def submit_for_review():
	ctx = require_vendor("Owner", active=False)
	return vendors.submit_for_review(ctx).status


@frappe.whitelist(methods=["POST"])
def document_add(document_type, file_url, document_number=None, expiry_date=None):
	ctx = require_vendor("Manager", active=False)
	return vendors.add_verification_document(ctx, document_type, file_url, document_number, expiry_date).name


@frappe.whitelist(methods=["POST"])
def staff_add(email, full_name=None, vendor_role="Staff"):
	ctx = require_vendor("Manager")
	vendors.add_staff(ctx, email, full_name, vendor_role)
	return profile()["staff"]


@frappe.whitelist(methods=["POST"])
def staff_toggle(name, enabled):
	ctx, vu = _own("Vendor User", name, require_vendor("Manager"))
	if vu.vendor_role == "Owner" and not cint(enabled):
		fail("OWNER_REQUIRED", "The owner cannot be disabled.")
	if cint(enabled):
		subscriptions.check_staff_limit(ctx.vendor)
	vu.db_set("enabled", cint(enabled))
	return True


# ------------------------------------------------------------------ catalogue
@frappe.whitelist()
def listings_list(status=None, q=None, page=1):
	ctx = require_vendor()
	filters = {"vendor": ctx.vendor}
	if status:
		filters["status"] = status
	if q:
		filters["title"] = ["like", f"%{q[:80]}%"]
	return paged("Marketplace Listing", filters, LISTING_LIST, "modified desc", page)


@frappe.whitelist()
def listing_get(name):
	ctx, d = _own("Marketplace Listing", name)
	out = {f: d.get(f) for f in vendors.LISTING_FIELDS + ("name", "status", "route", "featured", "featured_until", "available_today", "item")}
	out["specifications"] = [{"attribute": s.attribute, "value": s.value, "unit": s.unit} for s in d.specifications]
	out["images"] = [{"image": i.image, "caption": i.caption} for i in d.images]
	out["availability"] = frappe.get_all("Listing Availability", filters={"listing": name, "status": "Active"},
		fields=["name", "entry_type", "from_date", "to_date", "qty", "booking", "remarks"], order_by="from_date asc")
	return out


@frappe.whitelist(methods=["POST"])
def listing_save(data, name=None):
	ctx = require_vendor("Staff", approved=False)
	d = vendors.save_listing(ctx, parse(data), name)
	return d.name


@frappe.whitelist(methods=["POST"])
def listing_status(name, status):
	ctx = require_vendor("Manager")
	return vendors.set_listing_status(ctx, name, status).status


@frappe.whitelist()
def availability_check(listing, from_date, to_date):
	ctx, d = _own("Marketplace Listing", listing)
	return {"free": availability.available_qty(listing, from_date, to_date), "total": d.total_qty}


@frappe.whitelist(methods=["POST"])
def availability_block(listing, from_date, to_date, qty, entry_type="Blocked", remarks=None):
	ctx = require_vendor("Staff")
	return vendors.block_availability(ctx, listing, from_date, to_date, qty, entry_type, remarks)


@frappe.whitelist(methods=["POST"])
def availability_release(name):
	ctx = require_vendor("Staff")
	vendors.release_block(ctx, name)
	return True


# ------------------------------------------------------------------ tenders & offers
@frappe.whitelist()
def tenders_list(scope="invited", page=1):
	ctx = require_vendor()
	v = ctx.vendor
	if scope == "open":
		# open marketplace tenders the vendor is eligible for but not yet invited to
		rows = []
		invited = set(frappe.get_all("Tender Invitation", filters={"vendor": v}, pluck="tender"))
		for t in frappe.get_all("Marketplace Tender", filters={"status": "Bidding Open", "tender_type": "Open",
			"visibility": ["in", list(tender_service.OPEN_TYPES_VISIBLE)]}, fields=["name"], order_by="submission_deadline asc", limit=100):
			if t.name in invited:
				continue
			doc = frappe.get_doc("Marketplace Tender", t.name)
			if tender_service.vendor_access(doc, v, create=False) is None:
				from thinknxg_rental_marketplace.services import matching

				if not matching.is_eligible(doc, v):
					continue
			rows.append(_tender_row(doc, None, v))
		return {"rows": rows, "total": len(rows)}
	inv_filters = {"vendor": v, "status": ["!=", "Excluded"]}
	invs = {i.tender: i for i in frappe.get_all("Tender Invitation", filters=inv_filters, fields=["tender", "status", "match_score", "invited_on"])}
	tfilters = {"name": ["in", list(invs) or ["-"]]}
	if scope == "invited":
		tfilters["status"] = ["in", ["Bidding Open", "Invitation Sent"]]
	elif scope == "submitted":
		tfilters["name"] = ["in", frappe.get_all("Supplier Offer", filters={"vendor": v, "status": ["not in", ["Draft"]]}, pluck="tender") or ["-"]]
	elif scope == "won":
		tfilters["name"] = ["in", frappe.get_all("Supplier Offer", filters={"vendor": v, "status": "Accepted"}, pluck="tender") or ["-"]]
	res = paged("Marketplace Tender", tfilters, ["name"], "submission_deadline desc", page)
	res["rows"] = [_tender_row(frappe.get_doc("Marketplace Tender", r.name), invs.get(r.name), v) for r in res["rows"]]
	return res


def _tender_row(t, inv, vendor):
	offer = frappe.db.get_value("Supplier Offer", {"tender": t.name, "vendor": vendor}, ["name", "status", "grand_total", "revision_no"], as_dict=True)
	return {"name": t.name, "title": t.title, "transaction_type": t.transaction_type, "category": t.category, "status": t.status,
		"submission_deadline": t.submission_deadline, "city": t.city, "country": t.country, "currency": t.currency, "lines": len(t.items),
		"invitation_status": inv.status if inv else None, "match_score": inv.match_score if inv else None, "offer": offer,
		"required_from": t.required_from, "required_to": t.required_to, "tender_type": t.tender_type}


@frappe.whitelist()
def tender_get(name):
	ctx = require_vendor()
	t = frappe.get_doc("Marketplace Tender", name)
	inv = offers.mark_viewed(t, ctx.vendor)
	out = offers.tender_for_vendor(t, ctx.vendor)
	out["invitation_status"] = frappe.db.get_value("Tender Invitation", inv.name, "status")
	o = offers.get_offer(t, ctx.vendor)
	out["offer"] = offers.vendor_offer_view(o, t) if o else None
	out["can_offer"] = offers.can_edit(t, o) and (not o or o.status in offers.EDITABLE)
	out["my_listings"] = frappe.get_all("Marketplace Listing", filters={"vendor": ctx.vendor, "status": "Published",
		"allow_" + t.transaction_type.lower(): 1}, fields=["name", "title", "category", "uom", "total_qty", "daily_rate", "weekly_rate", "monthly_rate",
		"sale_price", "contract_monthly_rate", "security_deposit_rate", "currency"])
	start, end = availability.window(t.transaction_type, t.required_from or t.contract_start or t.expected_delivery_date or getdate(),
		t.required_to or (frappe.utils.add_months(t.contract_start, cint(t.contract_months) or 1) if t.contract_start else None))
	for l in out["my_listings"]:
		l["free_for_window"] = availability.available_qty(l.name, start, end)
	out["my_clarifications"] = frappe.get_all("Tender Clarification", filters={"tender": name, "vendor": ctx.vendor},
		fields=["name", "subject", "message", "response", "status", "clarification_type", "raised_by_party", "counter_amount", "creation"], order_by="creation desc")
	out["entitlements"] = subscriptions.entitlements(ctx.vendor)
	return out


@frappe.whitelist(methods=["POST"])
def tender_respond(name, response, reason=None):
	ctx = require_vendor("Staff", approved=True)
	offers.respond_invitation(frappe.get_doc("Marketplace Tender", name), ctx.vendor, response, reason)
	return True


@frappe.whitelist(methods=["POST"])
def offer_save(tender, data):
	ctx = require_vendor("Staff", approved=True)
	o = offers.save_draft(ctx, tender, parse(data))
	return offers.vendor_offer_view(o, frappe.get_doc("Marketplace Tender", tender))


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=60, seconds=3600)
def offer_submit(offer, reason=None, idempotency_key=None):
	ctx = require_vendor("Manager", approved=True)
	o = offers.submit(ctx, offer, reason, idempotency_key)
	return offers.vendor_offer_view(o, frappe.get_doc("Marketplace Tender", o.tender))


@frappe.whitelist(methods=["POST"])
def offer_withdraw(offer, reason=None):
	ctx = require_vendor("Manager", approved=True)
	offers.withdraw(ctx, offer, reason)
	return True


@frappe.whitelist(methods=["POST"])
def clarification_raise(tender, subject, message, clarification_type="Clarification"):
	ctx = require_vendor("Staff", approved=True)
	t = frappe.get_doc("Marketplace Tender", tender)
	tender_service.require_vendor_access(t, ctx.vendor)
	return evaluation.raise_clarification("Supplier", tender, subject, message, vendor=ctx.vendor, ctype=clarification_type).name


@frappe.whitelist(methods=["POST"])
def clarification_respond(name, response):
	ctx = require_vendor("Staff", approved=True)
	c = frappe.get_doc("Tender Clarification", name)
	if c.vendor != ctx.vendor:
		forbid()
	evaluation.respond_clarification("Supplier", name, response)
	return True


# ------------------------------------------------------------------ bookings / fulfilment
@frappe.whitelist()
def bookings_list(status=None, transaction_type=None, page=1):
	ctx = require_vendor()
	filters = {"vendor": ctx.vendor}
	if status:
		filters["status"] = status
	if transaction_type:
		filters["transaction_type"] = transaction_type
	return paged("Marketplace Booking", filters, BOOKING_LIST, "creation desc", page)


@frappe.whitelist()
def booking_get(name):
	ctx, b = _own("Marketplace Booking", name)
	out = {k: b.get(k) for k in BOOKING_LIST + ["subtotal", "charges_total", "tax_amount", "security_deposit", "deposit_required", "additional_charges",
		"commission_rate", "commission_basis", "accepted_on", "extension_days", "returned_on", "completed_on", "cancel_reason", "erp_reference_doctype", "erp_reference", "site_address", "country"]}
	confirmed = b.status not in ("Pending Payment", "Cancelled")
	cust = frappe.db.get_value("Marketplace Customer", b.customer, ["customer_name", "company_name"], as_dict=True)
	if confirmed:
		cust.update(frappe.db.get_value("Marketplace Customer", b.customer, ["email", "phone"], as_dict=True))
		req = frappe.db.get_value("Rental Request", b.rental_request, ["site_contact", "site_phone", "site_access", "special_requirements"], as_dict=True)
		out["site"] = req
	else:
		out["site_address"] = f"{b.city or ''}, {b.country or ''}"
	out["customer_info"] = cust
	out["items"] = [{k: i.get(k) for k in ("name", "equipment_name", "listing", "qty", "uom", "rate_basis", "unit_rate", "periods", "amount", "returned_qty", "damaged_qty", "lost_qty")} for i in b.items]
	out["schedule"] = [{k: s.get(k) for k in ("line_type", "due_date", "amount", "status")} for s in b.schedule]
	out["vendor_order"] = frappe.db.get_value("Vendor Order", b.vendor_order, ["name", "status", "fulfilment_mode", "erp_reference_doctype", "erp_reference",
		"erp_status", "dispatched_on", "delivered_on", "return_due", "returned_on", "vehicle_details", "driver_contact", "notes"], as_dict=True) if b.vendor_order else None
	out["next_actions"] = [a for a in fulfilment.allowed_next(b) if "Vendor" in fulfilment.ACTORS.get(a, set())]
	out["can_cancel"] = b.status in booking_service.PRE_FULFILMENT
	out["extension_requests"] = frappe.get_all("Tender Clarification", filters={"offer": b.offer, "status": "Open", "subject": ["like", f"Extension request {b.name}%"]}, fields=["name", "subject", "creation"])
	out["history"] = audit.history("Marketplace Booking", b.name, 50)
	return out


@frappe.whitelist(methods=["POST"])
def booking_action(name, action, data=None):
	ctx, b = _own("Marketplace Booking", name, require_vendor("Staff"))
	data = parse(data)
	if action == "cancel":
		require_vendor("Manager")
		booking_service.cancel(name, "Vendor", data.get("reason") or "Cancelled by supplier")
	elif action == "approve_extension":
		require_vendor("Manager")
		fulfilment.approve_extension(name, data.get("new_end"), ctx)
	elif action in fulfilment.ACTORS:
		fulfilment.transition(name, action, "Vendor", data)
	else:
		fail("ACTION", "Unknown action.")
	return booking_get(name)


@frappe.whitelist(methods=["POST"])
def booking_dispute(booking, data):
	ctx = require_vendor("Manager")
	return trust.raise_dispute("Vendor", booking, parse(data), ctx).name


# ------------------------------------------------------------------ finance & subscription
@frappe.whitelist()
def finance():
	ctx = require_vendor("Manager")
	v = ctx.vendor
	return {
		"payments": frappe.get_all("Marketplace Payment", filters={"vendor": v, "payment_type": ["not in", ["Subscription", "Featured Fee", "Listing Fee"]]},
			fields=["name", "booking", "payment_type", "status", "amount", "currency", "confirmed_on"], order_by="creation desc", limit=100),
		"commissions": frappe.get_all("Marketplace Commission", filters={"vendor": v}, fields=["name", "booking", "status", "basis", "rate", "base_amount", "commission_amount", "currency", "settlement"], order_by="creation desc", limit=100),
		"settlements": frappe.get_all("Marketplace Settlement", filters={"vendor": v}, fields=["name", "status", "period_from", "period_to", "gross_amount", "commission_amount", "refund_amount", "net_payable", "currency", "payout_reference", "payout_confirmed_on"], order_by="creation desc"),
	}


@frappe.whitelist()
def subscription():
	ctx = require_vendor(active=False)
	return {
		"entitlements": subscriptions.entitlements(ctx.vendor),
		"usage": {"listings": frappe.db.count("Marketplace Listing", {"vendor": ctx.vendor, "status": "Published"}),
			"offers_this_month": subscriptions.offers_this_month(ctx.vendor), "staff": frappe.db.count("Vendor User", {"vendor": ctx.vendor, "enabled": 1})},
		"plans": frappe.get_all("Marketplace Subscription Plan", filters={"enabled": 1}, fields=["name", "plan_name", "currency", "price_monthly", "price_yearly",
			"max_listings", "max_tender_responses", "max_staff_users", "advanced_reports", "api_access", "priority_support", "featured_listings", "description"], order_by="sort_order asc"),
		"history": frappe.get_all("Vendor Subscription", filters={"vendor": ctx.vendor}, fields=["name", "plan", "status", "change_type", "start_date", "end_date", "amount", "currency", "payment"], order_by="creation desc"),
	}


@frappe.whitelist(methods=["POST"])
def subscribe(plan, cycle="Monthly"):
	ctx = require_vendor("Owner", active=False)
	if ctx.status not in ("Approved", "Under Review", "Documents Pending", "Submitted"):
		fail("VENDOR_STATE", "Subscriptions are available once your application is submitted.")
	sub = subscriptions.subscribe(ctx.vendor, plan, "Yearly" if cycle == "Yearly" else "Monthly")
	pay = payments.create_subscription_payment(sub.name) if sub.status == "Pending Payment" else None
	return {"subscription": sub.name, "status": sub.status, "payment": pay.name if pay else None, "checkout_url": pay.checkout_url if pay else None}


@frappe.whitelist(methods=["POST"])
def promote(promotion_type, days=7, listing=None):
	ctx = require_vendor("Manager")
	p = trust.request_promotion(ctx, promotion_type, days, listing)
	pay = frappe.db.get_value("Marketplace Payment", p.payment, ["name", "checkout_url"], as_dict=True)
	return {"promotion": p.name, "payment": pay}


@frappe.whitelist()
def reviews():
	ctx = require_vendor()
	return frappe.get_all("Marketplace Review", filters={"vendor": ctx.vendor, "status": "Published"},
		fields=["name", "booking", "rating", "quality_rating", "delivery_rating", "communication_rating", "title", "comment", "vendor_response", "reviewer_display_name", "creation"], order_by="creation desc")


@frappe.whitelist(methods=["POST"])
def review_respond(name, response):
	ctx = require_vendor("Manager")
	trust.vendor_respond(ctx, name, response)
	return True


@frappe.whitelist()
def notifications():
	require_vendor(active=False)
	return notifications_for(frappe.session.user)


@frappe.whitelist(methods=["POST"])
def notifications_read(names=None):
	require_vendor(active=False)
	return mark_read(frappe.session.user, names)

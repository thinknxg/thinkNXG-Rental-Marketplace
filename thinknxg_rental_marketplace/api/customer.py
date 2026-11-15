"""Customer portal API. Every call resolves the customer from the session; nothing is trusted from the browser."""
import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from thinknxg_rental_marketplace.api.utils import mark_read, notifications_for, paged, parse
from thinknxg_rental_marketplace.services import (
	audit, booking as booking_service, evaluation, fulfilment, payments, requests, tender as tender_service, trust,
)
from thinknxg_rental_marketplace.services.context import require_customer
from thinknxg_rental_marketplace.services.errors import fail, forbid

REQ_LIST = ["name", "title", "transaction_type", "category", "status", "city", "country", "required_from", "required_to",
	"expected_delivery_date", "contract_start", "contract_months", "tender", "booking", "submitted_on", "creation"]
BOOKING_LIST = ["name", "status", "transaction_type", "vendor", "tender", "start_date", "end_date", "delivery_date", "currency",
	"grand_total", "amount_paid", "balance_due", "deposit_required", "payment_due_by", "project_name", "creation"]


def _own(doctype, name, field="customer"):
	ctx = require_customer()
	doc = frappe.get_doc(doctype, name)
	if doc.get(field) != ctx.customer:
		forbid()
	return ctx, doc


@frappe.whitelist()
def dashboard():
	ctx = require_customer()
	c = ctx.customer
	return {
		"customer": frappe.db.get_value("Marketplace Customer", c, ["name", "customer_name", "company_name", "status", "verified", "city", "country"], as_dict=True),
		"role": ctx.role,
		"counts": {
			"open_requests": frappe.db.count("Rental Request", {"customer": c, "status": ["in", ["Draft", "Submitted", "Tendered", "Offers Received"]]}),
			"live_tenders": frappe.db.count("Marketplace Tender", {"customer": c, "status": ["in", ["Bidding Open", "Invitation Sent"]]}),
			"to_evaluate": frappe.db.count("Marketplace Tender", {"customer": c, "status": "Evaluation"}),
			"active_bookings": frappe.db.count("Marketplace Booking", {"customer": c, "status": ["not in", ["Completed", "Cancelled"]]}),
			"pending_payment": frappe.db.count("Marketplace Booking", {"customer": c, "status": "Pending Payment"}),
		},
		"recent_requests": frappe.get_all("Rental Request", filters={"customer": c}, fields=REQ_LIST, order_by="creation desc", limit=5),
		"recent_bookings": frappe.get_all("Marketplace Booking", filters={"customer": c}, fields=BOOKING_LIST, order_by="creation desc", limit=5),
		"notifications": notifications_for(frappe.session.user, 8),
	}


@frappe.whitelist()
def profile():
	ctx = require_customer()
	d = frappe.get_doc("Marketplace Customer", ctx.customer)
	return {**{f: d.get(f) for f in ("name", "customer_name", "customer_type", "company_name", "industry", "status", "verified", "email", "phone", "country", "city", "tax_id")},
		"members": [{"user": m.user, "member_role": m.member_role, "enabled": m.enabled} for m in d.members], "owner_user": d.owner_user, "role": ctx.role}


@frappe.whitelist(methods=["POST"])
def profile_update(data):
	ctx = require_customer("Owner")
	data = parse(data)
	d = frappe.get_doc("Marketplace Customer", ctx.customer)
	for f in ("customer_name", "customer_type", "company_name", "industry", "phone", "country", "city", "tax_id"):
		if f in data:
			d.set(f, data[f])
	d.flags.ignore_permissions = True
	d.save()
	return profile()


@frappe.whitelist(methods=["POST"])
def member_add(email, full_name=None, member_role="Buyer"):
	ctx = require_customer("Owner")
	if member_role not in ("Buyer", "Viewer"):
		fail("ROLE", "Members can be Buyer or Viewer.")
	from thinknxg_rental_marketplace.services.context import customer_membership
	from thinknxg_rental_marketplace.services.registration import ensure_user

	u = ensure_user(email, full_name, "Marketplace Customer")
	if customer_membership(u):
		fail("USER_LINKED", "This user already belongs to a customer account.")
	d = frappe.get_doc("Marketplace Customer", ctx.customer)
	d.append("members", {"user": u, "member_role": member_role, "enabled": 1})
	d.flags.ignore_permissions = True
	d.save()
	audit.log("customer.member_added", d.doctype, d.name, user=u)
	return profile()


# ------------------------------------------------------------------ project sites
@frappe.whitelist()
def sites():
	ctx = require_customer()
	return frappe.get_all("Customer Project Site", filters={"customer": ctx.customer}, fields=["name", "project_name", "site_address", "city", "state", "country", "site_contact", "site_phone", "site_access"], order_by="modified desc")


@frappe.whitelist(methods=["POST"])
def site_save(data, name=None):
	ctx = require_customer("Buyer")
	data = parse(data)
	if name:
		_c, doc = _own("Customer Project Site", name)
	else:
		doc = frappe.new_doc("Customer Project Site")
		doc.customer = ctx.customer
	for f in ("project_name", "site_address", "city", "state", "country", "site_contact", "site_phone", "site_access", "latitude", "longitude"):
		if f in data:
			doc.set(f, data[f])
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	return doc.name


# ------------------------------------------------------------------ requests
@frappe.whitelist()
def requests_list(status=None, page=1):
	ctx = require_customer()
	filters = {"customer": ctx.customer}
	if status:
		filters["status"] = status
	return paged("Rental Request", filters, REQ_LIST, "creation desc", page)


@frappe.whitelist()
def request_get(name):
	ctx, doc = _own("Rental Request", name)
	out = doc.as_dict()
	for k in ("idempotency_key", "owner", "modified_by", "docstatus", "doctype"):
		out.pop(k, None)
	if doc.tender:
		t = frappe.db.get_value("Marketplace Tender", doc.tender, ["name", "status", "submission_deadline", "invited_count", "offers_count",
			"tender_type", "confidentiality", "evaluation_method", "extension_count", "awarded_offer", "booking"], as_dict=True)
		out["tender_info"] = t
	out["history"] = audit.history("Rental Request", name, 30)
	return out


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=3600)
def request_save(data, name=None, submit=0):
	ctx = require_customer("Buyer")
	doc = requests.save(ctx, parse(data), name)
	if cint(submit):
		doc = requests.submit(ctx, doc.name)
	return {"name": doc.name, "status": doc.status, "tender": doc.tender}


@frappe.whitelist(methods=["POST"])
def request_submit(name):
	ctx = require_customer("Buyer")
	doc = requests.submit(ctx, name)
	return {"name": doc.name, "status": doc.status, "tender": doc.tender}


@frappe.whitelist(methods=["POST"])
def request_cancel(name, reason=None):
	ctx = require_customer("Buyer")
	requests.cancel(ctx, name, reason)
	return True


# ------------------------------------------------------------------ tenders & offers
@frappe.whitelist()
def compare(tender):
	ctx = require_customer()
	return evaluation.compare(ctx, tender)


@frappe.whitelist(methods=["POST"])
def tender_extend(tender, deadline, reason=None):
	ctx = require_customer("Buyer")
	if frappe.db.get_value("Marketplace Tender", tender, "customer") != ctx.customer:
		forbid()
	t = tender_service.extend(tender, deadline, reason)
	return {"status": t.status, "submission_deadline": t.submission_deadline}


@frappe.whitelist(methods=["POST"])
def tender_close_early(tender):
	ctx = require_customer("Buyer")
	if frappe.db.get_value("Marketplace Tender", tender, "customer") != ctx.customer:
		forbid()
	t = tender_service.close_bidding(tender, early=True)
	return {"status": t.status}


@frappe.whitelist(methods=["POST"])
def offer_shortlist(offer, value=1):
	ctx = require_customer("Buyer")
	evaluation.shortlist(ctx, offer, cint(value))
	return True


@frappe.whitelist(methods=["POST"])
def offer_reject(offer, reason=None):
	ctx = require_customer("Buyer")
	evaluation.reject(ctx, offer, reason)
	return True


@frappe.whitelist(methods=["POST"])
def clarification_raise(tender, subject, message, offer=None, clarification_type="Clarification", counter_amount=None):
	ctx = require_customer("Buyer")
	if frappe.db.get_value("Marketplace Tender", tender, "customer") != ctx.customer:
		forbid()
	c = evaluation.raise_clarification("Customer", tender, subject, message, offer=offer, ctype=clarification_type, counter_amount=counter_amount)
	return c.name


@frappe.whitelist(methods=["POST"])
def clarification_respond(name, response, share_with_all=0):
	ctx = require_customer("Buyer")
	tender = frappe.db.get_value("Tender Clarification", name, "tender")
	if frappe.db.get_value("Marketplace Tender", tender, "customer") != ctx.customer:
		forbid()
	evaluation.respond_clarification("Customer", name, response, share_with_all)
	return True


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=600)
def accept_offer(offer, idempotency_key=None):
	ctx = require_customer("Buyer")
	b = booking_service.accept_offer(ctx, offer, idempotency_key)
	pay = frappe.db.get_value("Marketplace Payment", {"booking": b.name, "status": ["in", ["Pending", "Initiated"]]}, ["name", "checkout_url", "amount"], as_dict=True)
	return {"booking": b.name, "status": b.status, "payment": pay}


# ------------------------------------------------------------------ bookings
@frappe.whitelist()
def bookings_list(status=None, page=1):
	ctx = require_customer()
	filters = {"customer": ctx.customer}
	if status:
		filters["status"] = status
	res = paged("Marketplace Booking", filters, BOOKING_LIST, "creation desc", page)
	for r in res["rows"]:
		r["vendor_name"] = frappe.db.get_value("Marketplace Vendor", r.vendor, "business_name")
	return res


@frappe.whitelist()
def booking_get(name):
	ctx, b = _own("Marketplace Booking", name)
	out = {k: b.get(k) for k in BOOKING_LIST + ["subtotal", "charges_total", "tax_amount", "security_deposit", "amount_refunded", "additional_charges",
		"site_address", "city", "country", "accepted_on", "extension_days", "returned_on", "completed_on", "cancel_reason", "offer", "offer_revision", "rental_request"]}
	out["items"] = [{k: i.get(k) for k in ("name", "equipment_name", "qty", "uom", "rate_basis", "unit_rate", "periods", "amount", "returned_qty", "damaged_qty", "lost_qty")} for i in b.items]
	out["schedule"] = [{k: s.get(k) for k in ("name", "line_type", "due_date", "period_from", "period_to", "amount", "status", "payment")} for s in b.schedule]
	out["payments"] = frappe.get_all("Marketplace Payment", filters={"booking": b.name}, fields=["name", "payment_type", "status", "amount", "currency", "checkout_url", "gateway", "creation"], order_by="creation desc")
	v = frappe.db.get_value("Marketplace Vendor", b.vendor, ["business_name", "route", "verified", "rating", "city", "country"], as_dict=True)
	if b.status not in ("Pending Payment", "Cancelled"):
		v.update(frappe.db.get_value("Marketplace Vendor", b.vendor, ["contact_person", "email", "phone"], as_dict=True))
	out["vendor_info"] = v
	vo = frappe.db.get_value("Vendor Order", b.vendor_order, ["status", "dispatched_on", "delivered_on", "return_due", "returned_on", "vehicle_details", "driver_contact"], as_dict=True) if b.vendor_order else None
	out["vendor_order"] = vo
	out["next_actions"] = [a for a in fulfilment.allowed_next(b) if "Customer" in fulfilment.ACTORS.get(a, set())]
	out["can_cancel"] = b.status in booking_service.PRE_FULFILMENT
	out["can_review"] = b.status == "Completed" and not frappe.db.exists("Marketplace Review", {"booking": b.name})
	out["disputes"] = frappe.get_all("Marketplace Dispute", filters={"booking": b.name}, fields=["name", "dispute_type", "status", "resolution", "creation"])
	out["history"] = audit.history("Marketplace Booking", b.name, 50)
	return out


@frappe.whitelist(methods=["POST"])
def booking_action(name, action, data=None):
	ctx, b = _own("Marketplace Booking", name)
	require_customer("Buyer")
	data = parse(data)
	if action == "cancel":
		booking_service.cancel(name, "Customer", data.get("reason") or "Cancelled by customer")
	elif action == "extension":
		fulfilment.request_extension(name, data.get("new_end"), ctx)
	elif action in ("On Hire", "Delivered", "Active", "Off-Hire Requested"):
		fulfilment.transition(name, action, "Customer", data)
	else:
		fail("ACTION", "Unknown action.")
	return booking_get(name)


@frappe.whitelist(methods=["POST"])
def pay(booking, lines=None):
	ctx, b = _own("Marketplace Booking", booking)
	require_customer("Buyer")
	lines = parse(lines) or [r.name for r in b.schedule if r.status == "Pending"][:1]
	p = payments.request_lines(b, lines)
	return {"payment": p.name, "checkout_url": p.checkout_url, "status": p.status}


@frappe.whitelist()
def payment_get(name):
	ctx, p = _own("Marketplace Payment", name)
	s = frappe.get_cached_doc("Marketplace Settings")
	return {**{k: p.get(k) for k in ("name", "payment_type", "status", "amount", "currency", "booking", "gateway", "checkout_url", "payer_reference", "confirmed_on")},
		"instructions": frappe._("Transfer the amount quoting {0} and enter your bank reference below. Our finance team confirms receipt.").format(p.name) if p.gateway == "Manual" else None,
		"support_email": s.support_email}


@frappe.whitelist(methods=["POST"])
def payment_reference(name, reference):
	ctx, p = _own("Marketplace Payment", name)
	if p.gateway != "Manual" or p.status not in ("Pending", "Initiated"):
		fail("PAYMENT_STATE", "This payment does not take a manual reference.")
	p.db_set("payer_reference", (reference or "")[:140])
	audit.log("payment.reference_submitted", p.doctype, p.name, reference=reference)
	from thinknxg_rental_marketplace.services import notifications

	notifications.to_operators(frappe._("Payment reference submitted for {0}").format(p.name), reference, link=f"/marketplace/operator/payments", category="Payment", ref=p, kind="finance")
	return True


@frappe.whitelist(methods=["POST"])
def review_submit(booking, data):
	ctx = require_customer("Buyer")
	return trust.submit_review(ctx, booking, parse(data)).name


@frappe.whitelist(methods=["POST"])
def dispute_raise(booking, data):
	ctx = require_customer("Buyer")
	return trust.raise_dispute("Customer", booking, parse(data), ctx).name


@frappe.whitelist()
def notifications():
	require_customer()
	return notifications_for(frappe.session.user)


@frappe.whitelist(methods=["POST"])
def notifications_read(names=None):
	require_customer()
	return mark_read(frappe.session.user, names)

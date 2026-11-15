"""Payment service: requesting, confirming (webhook / Finance), refunding, and applying effects.

Effects of a succeeded payment:
  booking      → schedule lines Paid, amount_paid/balance updated, booking Confirmed once on-accept lines are paid
  subscription → Vendor Subscription activated
  promotion    → Marketplace Promotion activated
"""
import frappe
from frappe.utils import add_days, flt, getdate, now_datetime

from thinknxg_rental_marketplace.services import audit, notifications
from thinknxg_rental_marketplace.services.errors import Conflict, fail
from thinknxg_rental_marketplace.services.money import D, to_float
from thinknxg_rental_marketplace.services.payments.gateways import GatewayError, get_gateway


def _new_payment(**kw):
	s = frappe.get_cached_doc("Marketplace Settings")
	doc = frappe.get_doc({"doctype": "Marketplace Payment", "status": "Initiated", "gateway": kw.pop("gateway", None) or s.payment_gateway or "Manual", **kw})
	doc.flags.ignore_permissions = True
	doc.insert()
	try:
		res = get_gateway(doc.gateway).create_checkout(doc)
		doc.db_set({"gateway_reference": res.get("reference"), "checkout_url": res.get("checkout_url"), "status": "Pending"})
	except GatewayError as e:
		doc.db_set({"status": "Failed", "failure_reason": str(e)[:500]})
	audit.log("payment.requested", doc.doctype, doc.name, None, doc.status, amount=doc.amount, type=doc.payment_type)
	return doc


def request_lines(booking, line_names, payment_type="Balance"):
	"""One payment covering the given booking schedule lines."""
	b = booking if not isinstance(booking, str) else frappe.get_doc("Marketplace Booking", booking)
	lines = [r for r in b.schedule if r.name in line_names and r.status in ("Pending",)]
	if not lines:
		fail("NOTHING_DUE", "These schedule lines are not payable.", Conflict)
	amount = sum(D(r.amount) for r in lines)
	ptype = payment_type
	if all(r.line_type == "Deposit" for r in lines):
		ptype = "Security Deposit"
	elif any(r.line_type == "Additional Charge" or r.line_type == "Final Settlement" for r in lines):
		ptype = "Additional Charge"
	elif any(r.line_type in ("Rental Period", "Contract Period") for r in lines):
		ptype = "Rental"
	pay = _new_payment(payment_type=ptype, booking=b.name, customer=b.customer, vendor=b.vendor, currency=b.currency,
		amount=to_float(amount, b.currency), schedule_line=",".join(r.name for r in lines))
	for r in lines:
		frappe.db.set_value("Booking Schedule Line", r.name, {"status": "Requested", "payment": pay.name})
	return pay


def create_subscription_payment(subscription):
	sub = frappe.get_doc("Vendor Subscription", subscription)
	existing = frappe.db.get_value("Marketplace Payment", {"subscription": sub.name, "status": ["in", ["Initiated", "Pending", "Succeeded"]]}, "name")
	if existing:
		return frappe.get_doc("Marketplace Payment", existing)
	pay = _new_payment(payment_type="Subscription", subscription=sub.name, vendor=sub.vendor, currency=sub.currency, amount=sub.amount)
	sub.db_set("payment", pay.name)
	return pay


def create_promotion_payment(promotion):
	p = frappe.get_doc("Marketplace Promotion", promotion)
	currency = frappe.get_cached_doc("Marketplace Settings").default_currency
	pay = _new_payment(payment_type="Featured Fee" if p.promotion_type != "Premium Visibility" else "Listing Fee", promotion=p.name,
		vendor=p.vendor, currency=currency, amount=p.fee)
	p.db_set("payment", pay.name)
	return pay


def mark_succeeded(payment_name, reference=None, source="webhook", payer_reference=None):
	frappe.db.sql("select name from `tabMarketplace Payment` where name=%s for update", payment_name)
	pay = frappe.get_doc("Marketplace Payment", payment_name)
	if pay.status == "Succeeded":
		return pay  # idempotent
	if pay.status not in ("Initiated", "Pending", "Failed"):
		fail("PAYMENT_STATE", "Payment is {s}.", Conflict, s=pay.status)
	prev = pay.status
	pay.db_set({"status": "Succeeded", "confirmed_on": now_datetime(), "confirmed_by": frappe.session.user,
		"gateway_reference": reference or pay.gateway_reference, "payer_reference": payer_reference or pay.payer_reference})
	audit.log("payment.succeeded", pay.doctype, pay.name, prev, "Succeeded", source=source, reference=reference)
	apply_effects(pay)
	return pay


def mark_failed(payment_name, reason):
	pay = frappe.get_doc("Marketplace Payment", payment_name)
	if pay.status in ("Succeeded", "Refunded"):
		return pay
	pay.db_set({"status": "Failed", "failure_reason": (reason or "")[:500]})
	audit.log("payment.failed", pay.doctype, pay.name, None, "Failed", reason=reason)
	for line in (pay.schedule_line or "").split(","):
		if line:
			frappe.db.set_value("Booking Schedule Line", line, {"status": "Pending", "payment": None})
	return pay


def apply_effects(pay):
	if pay.payment_type == "Refund":
		return
	if pay.booking:
		from thinknxg_rental_marketplace.services import booking as booking_service

		b = booking_service.lock_booking(pay.booking)
		for line in (pay.schedule_line or "").split(","):
			if line:
				frappe.db.set_value("Booking Schedule Line", line, "status", "Paid")
		b.reload()
		booking_service.recalc_paid(b)
		on_accept_open = [r for r in b.schedule if r.line_type in ("Advance", "Deposit") and r.status not in ("Paid", "Waived")]
		if b.status == "Pending Payment" and not on_accept_open:
			booking_service.confirm(b.name)
		notifications.to_vendor(b.vendor, frappe._("Payment received for {0}").format(b.name), f"{pay.currency} {pay.amount}", link=f"/marketplace/vendor/bookings/{b.name}", category="Payment", ref=pay)
	if pay.subscription:
		from thinknxg_rental_marketplace.services import subscriptions

		subscriptions.activate(pay.subscription)
	if pay.promotion:
		from thinknxg_rental_marketplace.services import trust

		trust.activate_promotion(pay.promotion)


def refund(payment_name, amount, reason=None):
	"""Creates a Refund payment against an original succeeded payment and asks the gateway for it.
	The refund only counts as Succeeded once the gateway (or Finance, for manual) confirms it."""
	orig = frappe.get_doc("Marketplace Payment", payment_name)
	amount = D(amount)
	if orig.status not in ("Succeeded", "Partially Refunded"):
		fail("REFUND_STATE", "Only received payments can be refunded.", Conflict)
	if amount <= 0 or amount > D(orig.amount) - D(orig.refunded_amount) + D("0.0001"):
		fail("REFUND_AMOUNT", "Refund exceeds the refundable amount.", Conflict)
	r = frappe.get_doc({"doctype": "Marketplace Payment", "payment_type": "Refund", "status": "Initiated", "booking": orig.booking,
		"customer": orig.customer, "vendor": orig.vendor, "currency": orig.currency, "amount": to_float(amount, orig.currency),
		"gateway": orig.gateway, "refund_of": orig.name, "failure_reason": None})
	r.flags.ignore_permissions = True
	r.insert()
	try:
		res = get_gateway(orig.gateway).refund(orig, amount)
		r.db_set({"gateway_reference": res.get("reference"), "status": "Pending"})
		if res.get("status") == "Succeeded":
			confirm_refund(r.name)
	except GatewayError as e:
		r.db_set({"status": "Failed", "failure_reason": str(e)[:500]})
	audit.log("refund.requested", r.doctype, r.name, None, r.status, of=orig.name, reason=reason)
	return r


def confirm_refund(refund_name, reference=None):
	r = frappe.get_doc("Marketplace Payment", refund_name)
	if r.payment_type != "Refund" or r.status == "Succeeded":
		return r
	r.db_set({"status": "Succeeded", "confirmed_on": now_datetime(), "confirmed_by": frappe.session.user, "gateway_reference": reference or r.gateway_reference})
	orig = frappe.get_doc("Marketplace Payment", r.refund_of)
	refunded = D(orig.refunded_amount) + D(r.amount)
	orig.db_set({"refunded_amount": to_float(refunded, orig.currency), "status": "Refunded" if refunded >= D(orig.amount) else "Partially Refunded"})
	audit.log("refund.succeeded", r.doctype, r.name, "Pending", "Succeeded")
	if r.booking:
		from thinknxg_rental_marketplace.services import booking as booking_service

		booking_service.recalc_paid(frappe.get_doc("Marketplace Booking", r.booking))
	return r


def record_retained_fee(b, fee):
	"""Cancellation fee kept from money already received (no new charge). Recorded for settlement."""
	doc = frappe.get_doc({"doctype": "Marketplace Payment", "payment_type": "Cancellation Fee", "status": "Succeeded", "booking": b.name,
		"customer": b.customer, "vendor": b.vendor, "currency": b.currency, "amount": to_float(fee, b.currency), "gateway": "Manual",
		"confirmed_on": now_datetime(), "gateway_reference": "retained-from-booking-payments"})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def process_webhook(gateway_name, headers, body):
	gw = get_gateway(gateway_name)
	ev = gw.parse_webhook(headers, body)  # raises GatewayError on bad signature
	if frappe.db.exists("Marketplace Webhook Event", {"event_id": ev["event_id"]}):
		return {"duplicate": True}
	log = frappe.get_doc({"doctype": "Marketplace Webhook Event", "gateway": gw.name, "event_id": ev["event_id"], "event_type": ev["event_type"],
		"payment": ev.get("payment") if ev.get("payment") and frappe.db.exists("Marketplace Payment", ev.get("payment")) else None,
		"payload": body.decode()[:60000] if isinstance(body, bytes) else str(body)[:60000]})
	log.flags.ignore_permissions = True
	log.insert()
	try:
		if log.payment:
			pay = frappe.get_doc("Marketplace Payment", log.payment)
			if ev["status"] == "succeeded":
				if ev.get("amount_minor") is not None and int(ev["amount_minor"]) < gw.minor_units(pay.amount, pay.currency):
					raise GatewayError("Paid amount lower than requested")
				mark_succeeded(pay.name, ev.get("reference"), source=f"{gw.name} webhook")
			elif ev["status"] == "failed":
				mark_failed(pay.name, ev["event_type"])
		elif ev["status"] == "refunded" and ev.get("reference"):
			name = frappe.db.get_value("Marketplace Payment", {"payment_type": "Refund", "gateway_reference": ev["reference"]}, "name")
			if name:
				confirm_refund(name)
		log.db_set("processed", 1)
	except Exception as e:
		log.db_set("error", str(e)[:500])
		raise
	return {"processed": True}

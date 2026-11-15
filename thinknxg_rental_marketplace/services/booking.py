"""Offer acceptance → Marketplace Booking, under row locks, plus confirmation, expiry and cancellation.

accept_offer() lock order (always the same, so concurrent accepts cannot deadlock):
  Marketplace Tender row → Supplier Offer row → Marketplace Listing rows (sorted by name)
"""
import json

import frappe
from frappe.utils import add_days, add_months, add_to_date, cint, flt, get_datetime, getdate, now_datetime, nowdate

from thinknxg_rental_marketplace.services import (
	audit, availability, commission, notifications, pricing, tender as tender_service,
)
from thinknxg_rental_marketplace.services.context import settings
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid
from thinknxg_rental_marketplace.services.money import D, pct, q, to_float

ACCEPTABLE_OFFER = ("Submitted", "Under Review", "Technically Accepted", "Commercially Accepted")
PRE_FULFILMENT = ("Pending Payment", "Confirmed")


def booking_window(t, offer_snapshot):
	if t.transaction_type == "Hire":
		return getdate(t.required_from), getdate(t.required_to)
	if t.transaction_type == "Contract":
		start = getdate(t.contract_start)
		return start, add_days(add_months(start, cint(t.contract_months) or 1), -1)
	start = getdate(offer_snapshot.get("delivery_date") or t.expected_delivery_date)
	return start, availability.FAR_FUTURE


def accept_offer(ctx, offer_name, idempotency_key=None):
	if idempotency_key:
		existing = frappe.db.get_value("Marketplace Booking", {"idempotency_key": idempotency_key}, ["name", "customer"], as_dict=True)
		if existing:
			if existing.customer != ctx.customer:
				forbid()
			return frappe.get_doc("Marketplace Booking", existing.name)
	tender_name = frappe.db.get_value("Supplier Offer", offer_name, "tender")
	if not tender_name:
		fail("NOT_FOUND", "Offer not found.")
	t = tender_service.lock(tender_name)
	if t.customer != ctx.customer:
		forbid()
	frappe.db.sql("select name from `tabSupplier Offer` where name=%s for update", offer_name)
	o = frappe.get_doc("Supplier Offer", offer_name)
	if t.status == "Bidding Open":
		fail("BIDDING_OPEN", "Offers can be accepted once bidding has closed.", Conflict)
	if t.status not in tender_service.ACCEPTANCE_STATES:
		fail("TENDER_STATE", "This tender is {s}; no offer can be accepted.", Conflict, s=t.status)
	if t.booking and frappe.db.get_value("Marketplace Booking", t.booking, "status") != "Cancelled":
		fail("ALREADY_AWARDED", "An offer has already been accepted for this tender.", Conflict)
	if o.status not in ACCEPTABLE_OFFER:
		fail("OFFER_STATE", "This offer is {s} and cannot be accepted.", Conflict, s=o.status)
	if getdate(o.valid_until) < getdate():
		fail("OFFER_EXPIRED", "This offer's validity has expired.", Conflict)
	vstatus = frappe.db.get_value("Marketplace Vendor", o.vendor, "status")
	if vstatus != "Approved":
		fail("VENDOR_INACTIVE", "The supplier is not currently active on the marketplace.", Conflict)
	rev = frappe.get_all("Offer Revision", filters={"offer": o.name, "revision_no": o.revision_no}, fields=["name", "snapshot"], limit=1)
	if not rev:
		fail("REVISION_MISSING", "The offer has no submitted revision.", Conflict)
	snap = json.loads(rev[0].snapshot) if isinstance(rev[0].snapshot, str) else rev[0].snapshot
	# re-price from the immutable snapshot (never from the live document or the browser)
	res = pricing.compute(t.transaction_type, [{"qty": i["qty"], "unit_rate": i["unit_rate"], "rate_basis": i.get("rate_basis")} for i in snap["items"]],
		charges={f: snap.get(f) for f in pricing.CHARGE_FIELDS}, tax_percent=snap.get("tax_percent") or 0,
		days=cint(t.duration_days), months=cint(t.contract_months), currency=t.currency, security_deposit=snap.get("security_deposit"))
	start, end = booking_window(t, snap)
	need = {}
	for i in snap["items"]:
		if not i.get("listing"):
			if t.transaction_type != "Sale":
				fail("LISTING_REQUIRED", "Every hire/contract line must reference a supplier listing so units can be reserved.", Conflict)
			continue
		need[i["listing"]] = need.get(i["listing"], 0) + flt(i["qty"])
	for listing in sorted(need):
		free = availability.available_qty(listing, start, end, for_update=True)
		if need[listing] > free + 1e-9:
			fail("INSUFFICIENT_AVAILABILITY", "The supplier no longer has enough free units of {l} ({free} free).", Conflict, l=listing, free=free)
	s = settings()
	com = commission.resolve(o.vendor, t.category, t.transaction_type, res["grand_total"], t.currency)
	schedule = pricing.booking_schedule(t.transaction_type, res["grand_total"], res["security_deposit"], s.default_deposit_percent or 0,
		start, cint(t.contract_months), t.currency)
	req = frappe.db.get_value("Rental Request", t.rental_request, ["project_name", "site_address", "city", "country"], as_dict=True)
	b = frappe.new_doc("Marketplace Booking")
	b.update({
		"tender": t.name, "offer": o.name, "offer_revision": rev[0].name, "rental_request": t.rental_request, "status": "Pending Payment",
		"customer": t.customer, "vendor": o.vendor, "transaction_type": t.transaction_type, "accepted_by": frappe.session.user,
		"accepted_on": now_datetime(), "start_date": start, "end_date": None if t.transaction_type == "Sale" else end,
		"delivery_date": snap.get("delivery_date"), "project_name": req.project_name, "site_address": req.site_address,
		"city": req.city, "country": req.country, "currency": t.currency,
		"subtotal": to_float(res["subtotal"], t.currency), "charges_total": to_float(res["charges_total"], t.currency),
		"tax_amount": to_float(res["tax_amount"], t.currency), "grand_total": to_float(res["grand_total"], t.currency),
		"security_deposit": to_float(res["security_deposit"], t.currency),
		"commission_rule": com.rule, "commission_basis": com.basis, "commission_rate": com.rate, "commission_amount": float(com.amount),
		"snapshot": json.dumps({"offer": snap, "tender": {"name": t.name, "duration_days": t.duration_days, "contract_months": t.contract_months},
			"commission_rule": com.rule, "deposit_percent": s.default_deposit_percent}),
		"idempotency_key": idempotency_key,
	})
	for i, line in zip(snap["items"], res["lines"]):
		b.append("items", {"equipment_name": i.get("equipment_name"), "listing": i.get("listing"),
			"item_code": frappe.db.get_value("Marketplace Listing", i["listing"], "item") if i.get("listing") else None,
			"qty": i["qty"], "uom": i.get("uom"), "rate_basis": line["rate_basis"], "unit_rate": i["unit_rate"],
			"periods": float(line["periods"]), "amount": to_float(line["amount"], t.currency)})
	deposit_required = D(0)
	for idx, line in enumerate(schedule):
		due = getdate()
		if line["due"] == "on_start":
			due = start
		elif line["due"].startswith("month_"):
			due = add_months(start, int(line["due"].split("_")[1]))
		b.append("schedule", {"line_type": line["line_type"], "due_date": due, "amount": to_float(line["amount"], t.currency), "status": "Pending"})
		if line["due"] == "on_accept":
			deposit_required += line["amount"]
	b.deposit_required = to_float(deposit_required, t.currency)
	b.balance_due = to_float(sum(D(r.amount) for r in b.schedule), t.currency)
	b.payment_due_by = add_to_date(now_datetime(), hours=cint(s.payment_hold_hours) or 48)
	b.flags.ignore_permissions = True
	b.insert()
	for listing in sorted(need):
		availability.allocate(listing, o.vendor, need[listing], start, end, b.name)
	vo = frappe.get_doc({"doctype": "Vendor Order", "booking": b.name, "vendor": o.vendor, "transaction_type": t.transaction_type,
		"status": "New", "delivery_date": snap.get("delivery_date"), "return_due": None if t.transaction_type == "Sale" else end})
	vo.flags.ignore_permissions = True
	vo.insert()
	b.db_set("vendor_order", vo.name)
	cm = frappe.get_doc({"doctype": "Marketplace Commission", "booking": b.name, "vendor": o.vendor, "status": "Accrued",
		"commission_rule": com.rule, "currency": t.currency, "basis": com.basis, "rate": com.rate,
		"base_amount": b.grand_total, "commission_amount": float(com.amount)})
	cm.flags.ignore_permissions = True
	cm.insert()
	# tender / offers / request
	t.awarded_offer, t.awarded_vendor, t.booking = o.name, o.vendor, b.name
	tender_service.set_status(t, "Awarded")
	prev_offer = o.status
	o.db_set("status", "Accepted")
	audit.log("offer.accepted", o.doctype, o.name, prev_offer, "Accepted", booking=b.name)
	for other in frappe.get_all("Supplier Offer", filters={"tender": t.name, "name": ["!=", o.name], "status": ["in", list(ACCEPTABLE_OFFER)]}, fields=["name", "vendor"]):
		frappe.db.set_value("Supplier Offer", other.name, "status", "Not Awarded")
		notifications.to_vendor(other.vendor, frappe._("Tender awarded to another supplier: {0}").format(t.title), "", link=f"/marketplace/vendor/tenders/{t.name}", category="Offer", ref=t)
	frappe.db.sql("update `tabMarketplace Vendor` set offers_won=ifnull(offers_won,0)+1 where name=%s", o.vendor)
	frappe.db.set_value("Rental Request", t.rental_request, {"status": "Awarded", "booking": b.name})
	audit.log("booking.created", b.doctype, b.name, None, "Pending Payment", offer=o.name, revision=rev[0].name, grand_total=b.grand_total)
	notifications.to_vendor(o.vendor, frappe._("You won {0}").format(t.title), frappe._("Booking {0} awaits the customer's deposit.").format(b.name),
		link=f"/marketplace/vendor/bookings/{b.name}", category="Booking", ref=b)
	from thinknxg_rental_marketplace.services import payments

	if deposit_required > 0:
		payments.request_lines(b, [r.name for r in b.schedule if r.line_type in ("Advance", "Deposit")], "Advance")
	else:
		confirm(b.name)
	return frappe.get_doc("Marketplace Booking", b.name)


def lock_booking(name):
	frappe.db.sql("select name from `tabMarketplace Booking` where name=%s for update", name)
	return frappe.get_doc("Marketplace Booking", name)


def recalc_paid(b):
	paid = sum(flt(p.amount) for p in frappe.get_all("Marketplace Payment", filters={"booking": b.name, "status": ["in", ["Succeeded", "Partially Refunded", "Refunded"]], "payment_type": ["not in", ["Refund", "Cancellation Fee"]]}, fields=["amount"]))
	refunded = sum(flt(p.amount) for p in frappe.get_all("Marketplace Payment", filters={"booking": b.name, "status": "Succeeded", "payment_type": "Refund"}, fields=["amount"]))
	due = sum(flt(r.amount) for r in b.schedule if r.status in ("Pending", "Requested"))
	b.db_set({"amount_paid": paid, "amount_refunded": refunded, "balance_due": due})


def confirm(name):
	b = lock_booking(name)
	if b.status != "Pending Payment":
		return b
	b.db_set({"status": "Confirmed"})
	audit.log("booking.status", b.doctype, b.name, "Pending Payment", "Confirmed")
	frappe.db.set_value("Rental Request", b.rental_request, "status", "Booked")
	frappe.db.set_value("Vendor Order", b.vendor_order, "status", "New")
	notifications.to_vendor(b.vendor, frappe._("Booking confirmed: {0}").format(b.name), frappe._("Prepare fulfilment for {0}.").format(b.project_name or ""),
		link=f"/marketplace/vendor/bookings/{b.name}", category="Booking", ref=b)
	notifications.to_customer(b.customer, frappe._("Booking confirmed: {0}").format(b.name), "", link=f"/marketplace/account/bookings/{b.name}", category="Booking", ref=b)
	try:
		from thinknxg_rental_marketplace.services import rental_bridge

		rental_bridge.on_booking_confirmed(b.name)
	except Exception:
		frappe.log_error(title=f"Rental bridge failed for {b.name}")
	return b


def _reopen_tender(b, offer_status):
	t = tender_service.lock(b.tender)
	if t.status == "Awarded" and t.booking == b.name:
		t.awarded_offer = t.awarded_vendor = t.booking = None
		tender_service.set_status(t, "Evaluation")
		frappe.db.set_value("Supplier Offer", b.offer, "status", offer_status)
		# offers that lost only because this one was accepted become available again (if still valid)
		for other in frappe.get_all("Supplier Offer", filters={"tender": t.name, "status": "Not Awarded", "valid_until": [">=", getdate()]}, pluck="name"):
			frappe.db.set_value("Supplier Offer", other, "status", "Under Review")
		frappe.db.set_value("Rental Request", b.rental_request, {"status": "Offers Received", "booking": None})


def cancel(name, party, reason, actor_ctx=None):
	"""party: Customer | Vendor | Operator | System."""
	b = lock_booking(name)
	if b.status in ("Completed", "Cancelled"):
		fail("BOOKING_STATE", "This booking is already {s}.", Conflict, s=b.status)
	if party in ("Customer", "Vendor") and b.status not in PRE_FULFILMENT:
		fail("BOOKING_IN_FULFILMENT", "Fulfilment has started; raise a dispute or contact the marketplace.", Conflict)
	s = settings()
	prev = b.status
	from thinknxg_rental_marketplace.services import payments

	paid = [p for p in frappe.get_all("Marketplace Payment", filters={"booking": b.name, "status": "Succeeded", "payment_type": ["not in", ["Refund"]]}, fields=["name", "amount", "payment_type", "refunded_amount"])]
	fee_base = sum(flt(p.amount) - flt(p.refunded_amount) for p in paid if p.payment_type != "Security Deposit")
	free_until = add_to_date(get_datetime(b.accepted_on), hours=cint(s.free_cancellation_hours))
	fee = D(0)
	if party == "Customer" and now_datetime() > free_until:
		fee = pct(fee_base, s.cancellation_fee_percent or 0, b.currency)
	remaining_fee = fee
	for p in paid:
		refundable = D(p.amount) - D(p.refunded_amount)
		keep = min(remaining_fee, refundable) if p.payment_type != "Security Deposit" else D(0)
		remaining_fee -= keep
		if refundable - keep > 0:
			payments.refund(p.name, refundable - keep, reason=f"Booking {b.name} cancelled ({party})")
	if fee > 0:
		payments.record_retained_fee(b, fee)
	availability.release(b.name)
	for r in b.schedule:
		if r.status in ("Pending", "Requested"):
			frappe.db.set_value("Booking Schedule Line", r.name, "status", "Cancelled")
	for pay in frappe.get_all("Marketplace Payment", filters={"booking": b.name, "status": ["in", ["Initiated", "Pending"]],
		"payment_type": ["!=", "Refund"]}, pluck="name"):  # never void the refunds created above
		frappe.db.set_value("Marketplace Payment", pay, "status", "Cancelled")
	b.db_set({"status": "Cancelled", "cancelled_on": now_datetime(), "cancel_reason": f"{party}: {reason}"})
	frappe.db.set_value("Vendor Order", b.vendor_order, "status", "Cancelled")
	frappe.db.sql("update `tabMarketplace Commission` set status='Reversed' where booking=%s and status in ('Accrued','Earned')", b.name)
	_reopen_tender(b, "Withdrawn" if party == "Vendor" else ("Expired" if party == "System" else "Rejected"))
	b.reload()
	recalc_paid(b)
	audit.log("booking.cancelled", b.doctype, b.name, prev, "Cancelled", party=party, reason=reason, fee=str(fee))
	notifications.to_vendor(b.vendor, frappe._("Booking cancelled: {0}").format(b.name), reason or "", link=f"/marketplace/vendor/bookings/{b.name}", category="Booking", ref=b)
	notifications.to_customer(b.customer, frappe._("Booking cancelled: {0}").format(b.name), reason or "", link=f"/marketplace/account/bookings/{b.name}", category="Booking", ref=b)
	return b


def expire_unpaid():
	"""Scheduler: release bookings whose deposit was not paid in time."""
	for name in frappe.get_all("Marketplace Booking", filters={"status": "Pending Payment", "payment_due_by": ["<", now_datetime()]}, pluck="name"):
		try:
			cancel(name, "System", "Deposit not received in time")
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Unpaid booking expiry failed {name}")

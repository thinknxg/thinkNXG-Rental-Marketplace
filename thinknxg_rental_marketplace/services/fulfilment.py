"""Post-booking fulfilment per commercial model, extensions, returns, completion.

Hire     Confirmed → Dispatched → On Hire → (Off-Hire Requested) → Returned → Completed
Sale     Confirmed → Dispatched → Delivered → Completed
Contract Confirmed → Mobilized → Active → Demobilized → Completed
"""
import frappe
from frappe.utils import add_days, cint, date_diff, flt, getdate, now_datetime

from thinknxg_rental_marketplace.services import audit, availability, notifications, pricing
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid
from thinknxg_rental_marketplace.services.money import D, q, to_float

FLOWS = {
	"Hire": {"Confirmed": {"Dispatched"}, "Dispatched": {"On Hire"}, "On Hire": {"Off-Hire Requested", "Returned"},
		"Off-Hire Requested": {"Returned"}, "Returned": {"Completed"}},
	"Sale": {"Confirmed": {"Dispatched"}, "Dispatched": {"Delivered"}, "Delivered": {"Completed"}},
	"Contract": {"Confirmed": {"Mobilized"}, "Mobilized": {"Active"}, "Active": {"Demobilized"}, "Demobilized": {"Completed"}},
}
# who may trigger each target status
ACTORS = {"Dispatched": {"Vendor", "Operator"}, "On Hire": {"Vendor", "Customer", "Operator"}, "Delivered": {"Vendor", "Customer", "Operator"},
	"Off-Hire Requested": {"Customer", "Operator"}, "Returned": {"Vendor", "Operator"}, "Mobilized": {"Vendor", "Operator"},
	"Active": {"Vendor", "Customer", "Operator"}, "Demobilized": {"Vendor", "Operator"}, "Completed": {"Vendor", "Operator"}}
VO_STATUS = {"Dispatched": "Dispatched", "On Hire": "On Hire", "Delivered": "Delivered", "Off-Hire Requested": "Return Due",
	"Returned": "Returned", "Mobilized": "Mobilized", "Active": "Active", "Demobilized": "Demobilized", "Completed": "Completed"}


def allowed_next(b):
	return sorted(FLOWS[b.transaction_type].get(b.status, set()))


def transition(booking_name, to, party, data=None):
	from thinknxg_rental_marketplace.services.booking import lock_booking, recalc_paid

	data = data or {}
	b = lock_booking(booking_name)
	if to not in FLOWS[b.transaction_type].get(b.status, set()):
		fail("BOOKING_STATE", "Booking cannot move from {frm} to {to}.", Conflict, frm=b.status, to=to)
	if party not in ACTORS.get(to, set()):
		forbid("BOOKING_ACTOR", "This step is performed by the other party.")
	vo_updates = {"status": VO_STATUS[to]}
	now = now_datetime()
	if to == "Dispatched":
		vo_updates.update(dispatched_on=now, vehicle_details=data.get("vehicle_details"), driver_contact=data.get("driver_contact"))
	elif to in ("On Hire", "Delivered", "Mobilized"):
		vo_updates["delivered_on"] = now
	elif to == "Off-Hire Requested":
		ret = getdate(data.get("return_date") or getdate())
		if b.end_date and ret > getdate(b.end_date):
			fail("RETURN_AFTER_END", "Request an extension to keep equipment beyond the end date.")
		vo_updates["return_due"] = ret
	elif to == "Returned":
		_record_return(b, data)
		vo_updates["returned_on"] = now
	elif to == "Completed":
		recalc_paid(b)
		b.reload()
		if flt(b.balance_due) > 0.0001:
			fail("BALANCE_DUE", "The customer still owes {c} {amt}; collect it before completing.", Conflict, c=b.currency, amt=b.balance_due)
		_complete(b)
	prev = b.status
	b.db_set("status", to)
	if b.vendor_order:
		frappe.db.set_value("Vendor Order", b.vendor_order, {k: v for k, v in vo_updates.items() if v is not None})
	audit.log("booking.status", b.doctype, b.name, prev, to, party=party)
	link_c, link_v = f"/marketplace/account/bookings/{b.name}", f"/marketplace/vendor/bookings/{b.name}"
	if party == "Customer":
		notifications.to_vendor(b.vendor, frappe._("{0}: {1}").format(b.name, to), "", link=link_v, category="Booking", ref=b)
	else:
		notifications.to_customer(b.customer, frappe._("{0}: {1}").format(b.name, to), "", link=link_c, category="Booking", ref=b)
	return frappe.get_doc("Marketplace Booking", b.name)


def _record_return(b, data):
	"""data: lines=[{name, returned_qty, damaged_qty, lost_qty}], additional_charges, charge_notes."""
	by_name = {l.get("name"): l for l in data.get("lines") or []}
	for it in b.items:
		l = by_name.get(it.name, {})
		ret, dmg, lost = flt(l.get("returned_qty", it.qty)), flt(l.get("damaged_qty")), flt(l.get("lost_qty"))
		if ret + lost > flt(it.qty) + 1e-9 or dmg > ret + 1e-9 or min(ret, dmg, lost) < 0:
			fail("RETURN_QTY", "Row {idx}: returned + lost cannot exceed hired quantity; damaged is part of returned.", idx=it.idx)
		frappe.db.set_value("Booking Item", it.name, {"returned_qty": ret, "damaged_qty": dmg, "lost_qty": lost})
	extra = q(D(data.get("additional_charges")), b.currency)
	if extra < 0:
		fail("CHARGE_NEGATIVE", "Additional charges cannot be negative; use a dispute for credits.")
	if extra > 0:
		_add_schedule_line(b, "Final Settlement", extra)
		frappe.db.set_value("Marketplace Booking", b.name, "additional_charges", to_float(D(b.additional_charges) + extra, b.currency))
	frappe.db.set_value("Marketplace Booking", b.name, "returned_on", getdate())
	availability.release(b.name)


def _add_schedule_line(b, line_type, amount, period_from=None, period_to=None):
	row = frappe.get_doc({"doctype": "Booking Schedule Line", "parent": b.name, "parenttype": "Marketplace Booking", "parentfield": "schedule",
		"idx": len(b.schedule) + 1, "line_type": line_type, "due_date": getdate(), "period_from": period_from, "period_to": period_to,
		"amount": to_float(amount, b.currency), "status": "Pending"})
	row.db_insert()
	from thinknxg_rental_marketplace.services.booking import recalc_paid

	recalc_paid(frappe.get_doc("Marketplace Booking", b.name))
	return row


def _complete(b):
	availability.release(b.name)
	if b.transaction_type == "Sale":
		for it in b.items:
			if it.listing:
				frappe.db.sql("update `tabMarketplace Listing` set total_qty=greatest(total_qty-%s,0) where name=%s", (it.qty, it.listing))
	for it in b.items:
		if it.listing and flt(it.lost_qty):
			frappe.db.sql("update `tabMarketplace Listing` set total_qty=greatest(total_qty-%s,0) where name=%s", (it.lost_qty, it.listing))
	frappe.db.sql("update `tabMarketplace Commission` set status='Earned' where booking=%s and status='Accrued'", b.name)
	frappe.db.set_value("Marketplace Booking", b.name, "completed_on", now_datetime())
	frappe.db.set_value("Rental Request", b.rental_request, "status", "Closed")
	for it in b.items:
		if it.listing:
			availability.refresh_available_today(it.listing)


def request_extension(booking_name, new_end, ctx):
	b = frappe.get_doc("Marketplace Booking", booking_name)
	if b.customer != ctx.customer:
		forbid()
	if b.transaction_type == "Sale" or b.status not in ("Confirmed", "Dispatched", "On Hire", "Mobilized", "Active"):
		fail("EXTENSION_STATE", "Extensions are available for active hires and contracts.", Conflict)
	if getdate(new_end) <= getdate(b.end_date):
		fail("EXTENSION_DATE", "The new end date must be after the current end date.")
	c = frappe.get_doc({"doctype": "Tender Clarification", "tender": b.tender, "offer": b.offer, "vendor": b.vendor, "raised_by_party": "Customer",
		"clarification_type": "Commercial", "status": "Open", "raised_by": frappe.session.user,
		"subject": f"Extension request {b.name} → {new_end}", "message": f"Please extend booking {b.name} until {new_end}."})
	c.flags.ignore_permissions = True
	c.insert()
	audit.log("booking.extension_requested", b.doctype, b.name, new_end=str(new_end))
	notifications.to_vendor(b.vendor, frappe._("Extension requested: {0}").format(b.name), str(new_end), link=f"/marketplace/vendor/bookings/{b.name}", category="Booking", ref=b)
	return c


def approve_extension(booking_name, new_end, vctx):
	from thinknxg_rental_marketplace.services.booking import lock_booking

	b = lock_booking(booking_name)
	if b.vendor != vctx.vendor:
		forbid()
	if b.transaction_type == "Sale" or b.status in ("Returned", "Completed", "Cancelled", "Demobilized"):
		fail("EXTENSION_STATE", "This booking cannot be extended.", Conflict)
	old_end, new_end = getdate(b.end_date), getdate(new_end)
	if new_end <= old_end:
		fail("EXTENSION_DATE", "The new end date must be after the current end date.")
	availability.extend(b.name, new_end)
	extra_days = date_diff(new_end, old_end)
	months = extra_days / 30.0
	total = D(0)
	for it in b.items:
		basis = it.rate_basis or "Monthly"
		periods = pricing.periods_for("Hire", basis, days=extra_days) if b.transaction_type == "Hire" else D(str(round(months, 4)))
		total += D(it.qty) * D(it.unit_rate) * periods
	tax_pct = (frappe.parse_json(b.snapshot) or {}).get("offer", {}).get("tax_percent") or 0
	total = q(total * (1 + D(tax_pct) / 100), b.currency)
	_add_schedule_line(b, "Rental Period" if b.transaction_type == "Hire" else "Contract Period", total, add_days(old_end, 1), new_end)
	frappe.db.set_value("Marketplace Booking", b.name, {"end_date": new_end, "extension_days": cint(b.extension_days) + extra_days,
		"grand_total": to_float(D(b.grand_total) + total, b.currency)})
	if b.vendor_order:
		frappe.db.set_value("Vendor Order", b.vendor_order, "return_due", new_end)
	for c in frappe.get_all("Tender Clarification", filters={"offer": b.offer, "status": "Open", "subject": ["like", f"Extension request {b.name}%"]}, pluck="name"):
		frappe.db.set_value("Tender Clarification", c, {"status": "Answered", "response": f"Extended to {new_end}", "responded_by": frappe.session.user, "responded_on": now_datetime()})
	audit.log("booking.extended", b.doctype, b.name, str(old_end), str(new_end), amount=str(total))
	notifications.to_customer(b.customer, frappe._("Extension approved: {0}").format(b.name), frappe._("New end date {0}; {1} {2} added.").format(new_end, b.currency, total),
		link=f"/marketplace/account/bookings/{b.name}", category="Booking", ref=b)
	return frappe.get_doc("Marketplace Booking", b.name)

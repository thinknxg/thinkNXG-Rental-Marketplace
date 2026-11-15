"""Listing availability ledger.

A listing's free quantity over a window = total_qty − peak concurrent quantity of active
``Listing Availability`` rows (Allocated / Blocked / Maintenance) overlapping that window.
Allocation is done under a row lock on the listing (SELECT … FOR UPDATE) so two bookings can never
take the same units. Category matching is never treated as proof of availability.
"""
from datetime import date, timedelta

import frappe
from frappe.utils import flt, getdate

from thinknxg_rental_marketplace.services.errors import Conflict, fail

FAR_FUTURE = date(2099, 12, 31)


def peak_usage(intervals, start, end):
	"""Pure. intervals: [(from_date, to_date, qty)] inclusive dates. Returns max concurrent qty within [start, end]."""
	start, end = getdate(start), getdate(end)
	events = []
	for f, t, qty in intervals:
		f, t = max(getdate(f), start), min(getdate(t), end)
		if f > t:
			continue
		events.append((f, 0, flt(qty)))  # ends (-1) sort before starts (0) on the same day: units freed first
		events.append((t + timedelta(days=1), -1, -flt(qty)))
	events.sort(key=lambda e: (e[0], e[1]))
	cur = peak = 0.0
	for _d, _k, delta in events:
		cur += delta
		peak = max(peak, cur)
	return peak


def _rows(listing, start, end, exclude_booking=None):
	filters = {"listing": listing, "status": "Active", "from_date": ["<=", end], "to_date": [">=", start]}
	if exclude_booking:
		filters["booking"] = ["!=", exclude_booking]
	rows = frappe.get_all("Listing Availability", filters=filters, fields=["from_date", "to_date", "qty", "booking"])
	if exclude_booking:
		rows = [r for r in rows if r.booking != exclude_booking]
	return [(r.from_date, r.to_date, r.qty) for r in rows]


def window(transaction_type, start, end):
	start = getdate(start)
	if transaction_type == "Sale":
		return start, FAR_FUTURE
	return start, getdate(end or start)


def available_qty(listing, start, end, for_update=False, exclude_booking=None):
	if for_update:
		row = frappe.db.sql("select total_qty, status from `tabMarketplace Listing` where name=%s for update", listing, as_dict=True)
	else:
		row = frappe.db.get_all("Marketplace Listing", filters={"name": listing}, fields=["total_qty", "status"])
	if not row:
		return 0.0
	total = flt(row[0].total_qty)
	return max(total - peak_usage(_rows(listing, getdate(start), getdate(end), exclude_booking), start, end), 0.0)


def allocate(listing, vendor, qty, start, end, booking, entry_type="Allocated"):
	"""Caller must hold the transaction; this locks the listing row and checks again."""
	free = available_qty(listing, start, end, for_update=True)
	if flt(qty) > free + 1e-9:
		fail("INSUFFICIENT_AVAILABILITY", "Only {free} units of {listing} are free for the selected dates.", Conflict, free=free, listing=listing)
	doc = frappe.get_doc(
		{
			"doctype": "Listing Availability",
			"listing": listing,
			"vendor": vendor,
			"entry_type": entry_type,
			"status": "Active",
			"from_date": getdate(start),
			"to_date": getdate(end),
			"qty": flt(qty),
			"booking": booking,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def release(booking):
	names = frappe.get_all("Listing Availability", filters={"booking": booking, "status": "Active"}, pluck="name")
	for n in names:
		frappe.db.set_value("Listing Availability", n, "status", "Released")
	return len(names)


def extend(booking, new_end):
	"""Extend every active allocation of a booking to new_end, re-checking the extra window."""
	for row in frappe.get_all("Listing Availability", filters={"booking": booking, "status": "Active"}, fields=["name", "listing", "to_date", "qty"]):
		extra_from = getdate(row.to_date) + timedelta(days=1)
		if extra_from > getdate(new_end):
			continue
		free = available_qty(row.listing, extra_from, new_end, for_update=True, exclude_booking=booking)
		if flt(row.qty) > free + 1e-9:
			fail("EXTENSION_UNAVAILABLE", "{listing} is not free for the extension period.", Conflict, listing=row.listing)
		frappe.db.set_value("Listing Availability", row.name, "to_date", getdate(new_end))


def refresh_available_today(listing):
	today = getdate()
	frappe.db.set_value("Marketplace Listing", listing, "available_today", available_qty(listing, today, today), update_modified=False)

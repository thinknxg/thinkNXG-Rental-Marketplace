"""Vendor settlements from succeeded payments of completed bookings.

net = Σ received booking payments (excl. refundable security deposits, retained-fee records)
      − Σ succeeded refunds on those bookings − Σ earned commission
A settlement is only marked Paid with a payout reference supplied by Finance (or a provider confirmation);
the platform never claims funds were paid out on its own.
"""
import frappe
from frappe.utils import getdate, now_datetime

from thinknxg_rental_marketplace.services import audit, notifications
from thinknxg_rental_marketplace.services.errors import Conflict, fail
from thinknxg_rental_marketplace.services.money import D, to_float

REVENUE_TYPES = ("Advance", "Balance", "Rental", "Additional Charge", "Deposit")


def build(vendor, period_from, period_to):
	active_settled = set(frappe.db.sql_list("""select sl.booking from `tabSettlement Line` sl
		join `tabMarketplace Settlement` s on s.name = sl.parent where s.status != 'Cancelled' and s.vendor = %s""", vendor))
	bookings = frappe.get_all("Marketplace Booking", filters={"vendor": vendor, "status": "Completed",
		"completed_on": ["between", [getdate(period_from), str(getdate(period_to)) + " 23:59:59"]]}, fields=["name", "currency"])
	cancelled_with_fee = frappe.get_all("Marketplace Booking", filters={"vendor": vendor, "status": "Cancelled",
		"cancelled_on": ["between", [getdate(period_from), str(getdate(period_to)) + " 23:59:59"]]}, fields=["name", "currency"])
	doc = frappe.get_doc({"doctype": "Marketplace Settlement", "vendor": vendor, "status": "Draft", "period_from": period_from, "period_to": period_to})
	gross = commission = refunds = D(0)
	currency = None
	for b in bookings + cancelled_with_fee:
		if b.name in active_settled:
			continue
		currency = currency or b.currency
		pays = frappe.get_all("Marketplace Payment", filters={"booking": b.name, "status": ["in", ["Succeeded", "Partially Refunded", "Refunded"]],
			"payment_type": ["in", list(REVENUE_TYPES)]}, fields=["name", "amount", "payment_type"])
		refs = frappe.get_all("Marketplace Payment", filters={"booking": b.name, "status": "Succeeded", "payment_type": "Refund"}, fields=["name", "amount", "refund_of"])
		deposit_pays = {p.name for p in frappe.get_all("Marketplace Payment", filters={"booking": b.name, "payment_type": "Security Deposit"}, pluck="name")}
		bgross = sum(D(p.amount) for p in pays)
		brefund = sum(D(r.amount) for r in refs if r.refund_of not in deposit_pays)
		bcom = sum(D(c.commission_amount) for c in frappe.get_all("Marketplace Commission", filters={"booking": b.name, "status": "Earned", "settlement": ["is", "not set"]}, fields=["commission_amount"]))
		if not bgross and not bcom:
			continue
		doc.append("lines", {"booking": b.name, "payment_type": "Booking", "gross_amount": to_float(bgross - brefund, b.currency),
			"commission_amount": to_float(bcom, b.currency), "net_amount": to_float(bgross - brefund - bcom, b.currency)})
		gross += bgross
		refunds += brefund
		commission += bcom
	if not doc.lines:
		fail("NOTHING_TO_SETTLE", "No completed, unsettled bookings in this period.", Conflict)
	doc.currency = currency
	doc.gross_amount, doc.refund_amount, doc.commission_amount = to_float(gross, currency), to_float(refunds, currency), to_float(commission, currency)
	doc.net_payable = to_float(gross - refunds - commission, currency)
	doc.flags.ignore_permissions = True
	doc.insert()
	for line in doc.lines:
		frappe.db.sql("update `tabMarketplace Commission` set settlement=%s where booking=%s and status='Earned' and ifnull(settlement,'')=''", (doc.name, line.booking))
	audit.log("settlement.created", doc.doctype, doc.name, None, "Draft", net=doc.net_payable)
	return doc


def approve(name):
	doc = frappe.get_doc("Marketplace Settlement", name)
	if doc.status != "Draft":
		fail("SETTLEMENT_STATE", "Only draft settlements can be approved.", Conflict)
	doc.db_set({"status": "Approved", "approved_by": frappe.session.user, "approved_on": now_datetime()})
	audit.log("settlement.approved", doc.doctype, doc.name, "Draft", "Approved")
	return doc


def mark_paid(name, payout_reference):
	doc = frappe.get_doc("Marketplace Settlement", name)
	if doc.status not in ("Approved", "Payout Initiated"):
		fail("SETTLEMENT_STATE", "Approve the settlement before recording the payout.", Conflict)
	if not (payout_reference or "").strip():
		fail("PAYOUT_REFERENCE", "A bank or provider payout reference is required to mark a settlement as paid.")
	doc.db_set({"status": "Paid", "payout_reference": payout_reference.strip(), "payout_confirmed_on": now_datetime()})
	frappe.db.sql("update `tabMarketplace Commission` set status='Settled' where settlement=%s", doc.name)
	audit.log("settlement.paid", doc.doctype, doc.name, "Approved", "Paid", reference=payout_reference)
	notifications.to_vendor(doc.vendor, frappe._("Settlement {0} paid").format(doc.name), f"{doc.currency} {doc.net_payable} · ref {payout_reference}",
		link="/marketplace/vendor/finance", category="Payment", ref=doc, min_role="Manager")
	return doc


def cancel(name):
	doc = frappe.get_doc("Marketplace Settlement", name)
	if doc.status == "Paid":
		fail("SETTLEMENT_STATE", "Paid settlements cannot be cancelled.", Conflict)
	doc.db_set("status", "Cancelled")
	frappe.db.sql("update `tabMarketplace Commission` set settlement=null where settlement=%s", doc.name)
	audit.log("settlement.cancelled", doc.doctype, doc.name, None, "Cancelled")
	return doc

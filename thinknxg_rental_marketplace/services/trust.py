"""Reviews, disputes and paid promotions."""
import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

from thinknxg_rental_marketplace.services import audit, notifications
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid
from thinknxg_rental_marketplace.services.money import D


# ------------------------------------------------------------------ reviews
def submit_review(ctx, booking, data):
	b = frappe.get_doc("Marketplace Booking", booking)
	if b.customer != ctx.customer:
		forbid()
	if b.status != "Completed":
		fail("REVIEW_STATE", "Reviews open once the booking is completed.", Conflict)
	if frappe.db.exists("Marketplace Review", {"booking": booking}):
		fail("REVIEW_EXISTS", "You already reviewed this booking.", Conflict)
	def stars(k):
		v = flt(data.get(k))
		v = v / 5.0 if v > 1 else v  # accept 1–5 or 0–1
		return max(0.0, min(v, 1.0))
	if not stars("rating"):
		fail("REVIEW_RATING", "Choose a star rating.")
	name = frappe.db.get_value("Marketplace Customer", b.customer, "customer_name") or ""
	r = frappe.get_doc({"doctype": "Marketplace Review", "booking": booking, "vendor": b.vendor, "customer": b.customer,
		"status": "Pending Moderation", "rating": stars("rating"), "quality_rating": stars("quality_rating"),
		"delivery_rating": stars("delivery_rating"), "communication_rating": stars("communication_rating"),
		"title": (data.get("title") or "")[:140], "comment": data.get("comment"),
		"reviewer_display_name": (name.split(" ")[0] + " " + (name.split(" ")[1][:1] + "." if len(name.split(" ")) > 1 else "")).strip()})
	r.flags.ignore_permissions = True
	r.insert()
	audit.log("review.submitted", r.doctype, r.name)
	notifications.to_operators(frappe._("Review awaiting moderation"), b.name, link=f"/marketplace/operator/reviews", category="Review", ref=r)
	return r


def moderate_review(name, status):
	if status not in ("Published", "Hidden"):
		fail("REVIEW_STATUS", "Publish or hide.")
	r = frappe.get_doc("Marketplace Review", name)
	r.db_set("status", status)
	recompute_rating(r.vendor)
	audit.log("review.moderated", r.doctype, r.name, None, status)
	return r


def recompute_rating(vendor):
	row = frappe.db.sql("select avg(rating), count(*) from `tabMarketplace Review` where vendor=%s and status='Published'", vendor)[0]
	frappe.db.set_value("Marketplace Vendor", vendor, {"rating": round(flt(row[0]) * 5, 2), "review_count": row[1] or 0}, update_modified=False)


def vendor_respond(vctx, name, response):
	r = frappe.get_doc("Marketplace Review", name)
	if r.vendor != vctx.vendor:
		forbid()
	r.db_set("vendor_response", response)
	return r


# ------------------------------------------------------------------ disputes
def raise_dispute(party, booking, data, ctx):
	b = frappe.get_doc("Marketplace Booking", booking)
	if (party == "Customer" and b.customer != ctx.customer) or (party == "Vendor" and b.vendor != ctx.vendor):
		forbid()
	if b.status in ("Pending Payment",):
		fail("DISPUTE_STATE", "Cancel the booking instead.", Conflict)
	d = frappe.get_doc({"doctype": "Marketplace Dispute", "booking": booking, "raised_by": frappe.session.user, "raised_by_party": party,
		"dispute_type": data.get("dispute_type") or "Other", "status": "Open", "claimed_amount": flt(data.get("claimed_amount")),
		"description": data.get("description") or "", "evidence": data.get("evidence")})
	d.flags.ignore_permissions = True
	d.insert()
	audit.log("dispute.raised", d.doctype, d.name, party=party)
	notifications.to_operators(frappe._("Dispute raised on {0}").format(booking), d.dispute_type, link=f"/marketplace/operator/disputes/{d.name}", category="Booking", ref=d)
	other = notifications.to_vendor if party == "Customer" else notifications.to_customer
	other(b.vendor if party == "Customer" else b.customer, frappe._("Dispute raised on {0}").format(booking), d.dispute_type, link=None, category="Booking", ref=d)
	return d


def resolve_dispute(name, status, resolution, refund_amount=0):
	d = frappe.get_doc("Marketplace Dispute", name)
	if d.status in ("Resolved", "Rejected"):
		fail("DISPUTE_STATE", "Dispute already closed.", Conflict)
	refund_amount = D(refund_amount)
	if refund_amount > 0:
		from thinknxg_rental_marketplace.services import payments

		remaining = refund_amount
		for p in frappe.get_all("Marketplace Payment", filters={"booking": d.booking, "status": ["in", ["Succeeded", "Partially Refunded"]],
			"payment_type": ["not in", ["Refund", "Cancellation Fee"]]}, fields=["name", "amount", "refunded_amount"], order_by="creation desc"):
			if remaining <= 0:
				break
			avail = D(p.amount) - D(p.refunded_amount)
			take = min(avail, remaining)
			if take > 0:
				payments.refund(p.name, take, reason=f"Dispute {d.name}")
				remaining -= take
		if remaining > 0:
			fail("REFUND_EXCEEDS", "Refund exceeds what was paid on this booking.", Conflict)
	d.db_set({"status": status, "resolution": resolution, "refund_amount": float(refund_amount), "resolved_by": frappe.session.user, "resolved_on": now_datetime()})
	audit.log("dispute.resolved", d.doctype, d.name, None, status, refund=str(refund_amount))
	return d


# ------------------------------------------------------------------ promotions
FEES = {"Featured Listing": 10, "Featured Supplier": 25, "Featured Tender": 5, "Premium Visibility": 15}  # per 7 days, settings currency


def request_promotion(vctx, promotion_type, days=7, listing=None):
	if promotion_type not in FEES or promotion_type == "Featured Tender":
		fail("PROMOTION_TYPE", "Unknown promotion.")
	if listing and frappe.db.get_value("Marketplace Listing", listing, "vendor") != vctx.vendor:
		forbid()
	days = max(int(days or 7), 7)
	p = frappe.get_doc({"doctype": "Marketplace Promotion", "promotion_type": promotion_type, "vendor": vctx.vendor, "listing": listing,
		"status": "Pending Payment", "from_date": nowdate(), "to_date": frappe.utils.add_days(nowdate(), days - 1), "fee": FEES[promotion_type] * days / 7})
	p.flags.ignore_permissions = True
	p.insert()
	from thinknxg_rental_marketplace.services import payments

	payments.create_promotion_payment(p.name)
	return p


def activate_promotion(name):
	p = frappe.get_doc("Marketplace Promotion", name)
	p.db_set("status", "Active")
	if p.promotion_type == "Featured Listing" and p.listing:
		frappe.db.set_value("Marketplace Listing", p.listing, {"featured": 1, "featured_until": p.to_date})
	elif p.promotion_type == "Featured Supplier":
		frappe.db.set_value("Marketplace Vendor", p.vendor, "featured_until", p.to_date)
	audit.log("promotion.activated", p.doctype, p.name, "Pending Payment", "Active")


def expire_promotions():
	today = getdate()
	for p in frappe.get_all("Marketplace Promotion", filters={"status": "Active", "to_date": ["<", today]}, fields=["name", "listing", "promotion_type"]):
		frappe.db.set_value("Marketplace Promotion", p.name, "status", "Expired")
		if p.listing:
			frappe.db.set_value("Marketplace Listing", p.listing, "featured", 0)
	frappe.db.commit()

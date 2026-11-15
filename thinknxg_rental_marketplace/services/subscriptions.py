"""Vendor SaaS subscriptions and backend-enforced entitlements."""
import frappe
from frappe.utils import add_days, add_months, add_years, get_first_day, getdate, nowdate, now_datetime

from thinknxg_rental_marketplace.services import audit
from thinknxg_rental_marketplace.services.errors import LimitReached, fail

LIVE = ("Trial", "Active", "Grace")


def active_subscription(vendor):
	rows = frappe.get_all("Vendor Subscription", filters={"vendor": vendor, "status": ["in", LIVE]},
		fields=["name", "plan", "status", "start_date", "end_date", "grace_end"], order_by="end_date desc", limit=1)
	return rows[0] if rows else None


def entitlements(vendor):
	s = frappe.get_cached_doc("Marketplace Settings")
	sub = active_subscription(vendor)
	if not sub:
		return frappe._dict(active=not s.subscription_required, plan=None, status=None, max_listings=0, max_tender_responses=0,
			max_staff_users=0, advanced_reports=0, api_access=0, unlimited=not s.subscription_required)
	p = frappe.get_cached_doc("Marketplace Subscription Plan", sub.plan)
	return frappe._dict(active=True, plan=sub.plan, plan_name=p.plan_name, status=sub.status, end_date=sub.end_date,
		max_listings=p.max_listings, max_tender_responses=p.max_tender_responses, max_staff_users=p.max_staff_users,
		advanced_reports=p.advanced_reports, api_access=p.api_access, featured_listings=p.featured_listings, unlimited=False)


def _require_active(ent):
	if not ent.active:
		fail("SUBSCRIPTION_REQUIRED", "An active subscription is required. Choose a plan in Subscription.", LimitReached)


def check_listing_limit(vendor, exclude=None):
	ent = entitlements(vendor)
	_require_active(ent)
	if ent.unlimited or not ent.max_listings:
		return ent
	filters = {"vendor": vendor, "status": "Published"}
	if exclude:
		filters["name"] = ["!=", exclude]
	if frappe.db.count("Marketplace Listing", filters) >= ent.max_listings:
		fail("LISTING_LIMIT", "Your plan allows {n} published listings. Upgrade to publish more.", LimitReached, n=ent.max_listings)
	return ent


def offers_this_month(vendor):
	first = get_first_day(nowdate())
	return frappe.db.count("Offer Revision", {"vendor": vendor, "revision_no": 1, "submitted_on": [">=", first]})


def check_offer_limit(vendor, first_submission=True):
	ent = entitlements(vendor)
	_require_active(ent)
	if ent.unlimited or not ent.max_tender_responses or not first_submission:
		return ent
	if offers_this_month(vendor) >= ent.max_tender_responses:
		fail("OFFER_LIMIT", "Your plan allows {n} tender responses per month.", LimitReached, n=ent.max_tender_responses)
	return ent


def check_staff_limit(vendor):
	ent = entitlements(vendor)
	_require_active(ent)
	if ent.unlimited or not ent.max_staff_users:
		return ent
	if frappe.db.count("Vendor User", {"vendor": vendor, "enabled": 1}) >= ent.max_staff_users:
		fail("STAFF_LIMIT", "Your plan allows {n} users.", LimitReached, n=ent.max_staff_users)
	return ent


def _new(vendor, plan, status, start, end, change_type, cycle="Monthly", amount=0, previous=None, grace_end=None):
	p = frappe.get_cached_doc("Marketplace Subscription Plan", plan)
	doc = frappe.get_doc({"doctype": "Vendor Subscription", "vendor": vendor, "plan": plan, "status": status,
		"change_type": change_type, "billing_cycle": cycle, "start_date": start, "end_date": end, "grace_end": grace_end,
		"currency": p.currency, "amount": amount, "previous_subscription": previous})
	doc.flags.ignore_permissions = True
	doc.insert()
	audit.log("subscription.created", "Vendor Subscription", doc.name, None, status, plan=plan, change_type=change_type)
	return doc


def start_trial(vendor):
	if frappe.db.exists("Vendor Subscription", {"vendor": vendor}):
		return None
	s = frappe.get_cached_doc("Marketplace Settings")
	plan = s.default_trial_plan or frappe.db.get_value("Marketplace Subscription Plan", {"enabled": 1}, "name", order_by="sort_order asc")
	if not plan:
		return None
	days = frappe.db.get_value("Marketplace Subscription Plan", plan, "trial_days") or s.trial_days or 30
	return _new(vendor, plan, "Trial", nowdate(), add_days(nowdate(), int(days) - 1), "Trial")


def subscribe(vendor, plan, cycle="Monthly"):
	"""Create a subscription for a plan change/renewal. Paid plans start as Pending Payment."""
	p = frappe.get_cached_doc("Marketplace Subscription Plan", plan)
	if not p.enabled:
		fail("PLAN_DISABLED", "This plan is not available.")
	current = active_subscription(vendor)
	price = p.price_yearly if cycle == "Yearly" else p.price_monthly
	change = "New"
	if current:
		cur_price = frappe.db.get_value("Marketplace Subscription Plan", current.plan, "price_monthly") or 0
		change = "Renewal" if current.plan == plan else ("Upgrade" if (p.price_monthly or 0) > cur_price else "Downgrade")
	start = nowdate()
	end = add_days(add_years(start, 1) if cycle == "Yearly" else add_months(start, 1), -1)
	status = "Pending Payment" if price else "Active"
	doc = _new(vendor, plan, status, start, end, change, cycle, price, current.name if current else None)
	if status == "Active":
		activate(doc.name)
	return doc


def activate(subscription):
	doc = frappe.get_doc("Vendor Subscription", subscription)
	if doc.status == "Active" and not doc.previous_subscription:
		pass
	if doc.previous_subscription:
		prev = frappe.db.get_value("Vendor Subscription", doc.previous_subscription, ["status", "end_date"], as_dict=True)
		if prev and prev.status in LIVE:
			frappe.db.set_value("Vendor Subscription", doc.previous_subscription, "status", "Superseded")
			if doc.change_type == "Renewal" and getdate(prev.end_date) >= getdate():
				doc.start_date = add_days(prev.end_date, 1)
				doc.end_date = add_days(add_years(doc.start_date, 1) if doc.billing_cycle == "Yearly" else add_months(doc.start_date, 1), -1)
	for other in frappe.get_all("Vendor Subscription", filters={"vendor": doc.vendor, "status": ["in", LIVE], "name": ["!=", doc.name]}, pluck="name"):
		frappe.db.set_value("Vendor Subscription", other, "status", "Superseded")
	old = doc.status
	doc.status = "Active"
	doc.flags.ignore_permissions = True
	doc.save()
	audit.log("subscription.activated", "Vendor Subscription", doc.name, old, "Active")
	return doc


def daily_lifecycle():
	"""Scheduler: Active → Grace → Expired, Trial → Expired; renewal invoices for auto-renew."""
	s = frappe.get_cached_doc("Marketplace Settings")
	today = getdate()
	for sub in frappe.get_all("Vendor Subscription", filters={"status": ["in", ["Active", "Trial"]], "end_date": ["<", today]}, fields=["name", "vendor", "plan", "status", "auto_renew", "billing_cycle"]):
		if sub.status == "Trial":
			frappe.db.set_value("Vendor Subscription", sub.name, "status", "Expired")
			audit.log("subscription.expired", "Vendor Subscription", sub.name, "Trial", "Expired")
			continue
		frappe.db.set_value("Vendor Subscription", sub.name, {"status": "Grace", "grace_end": add_days(today, int(s.grace_days or 7))})
		audit.log("subscription.grace", "Vendor Subscription", sub.name, "Active", "Grace")
		if sub.auto_renew and not frappe.db.exists("Vendor Subscription", {"previous_subscription": sub.name}):
			from thinknxg_rental_marketplace.services import payments

			renewal = subscribe(sub.vendor, sub.plan, sub.billing_cycle)
			if renewal.status == "Pending Payment":
				payments.create_subscription_payment(renewal.name)
	for sub in frappe.get_all("Vendor Subscription", filters={"status": "Grace", "grace_end": ["<", today]}, pluck="name"):
		frappe.db.set_value("Vendor Subscription", sub, "status", "Expired")
		audit.log("subscription.expired", "Vendor Subscription", sub, "Grace", "Expired")
	frappe.db.commit()

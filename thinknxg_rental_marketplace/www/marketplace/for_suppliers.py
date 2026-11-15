import frappe

from thinknxg_rental_marketplace.website import base


def get_context(context):
	base(context, "For Suppliers", "for-suppliers")
	context.plans = frappe.get_all("Marketplace Subscription Plan", filters={"enabled": 1}, fields=["plan_name", "currency", "price_monthly", "price_yearly",
		"max_listings", "max_tender_responses", "max_staff_users", "advanced_reports", "api_access", "priority_support", "featured_listings", "trial_days", "description"], order_by="sort_order asc")
	context.business_types = frappe.get_meta("Marketplace Vendor").get_field("business_type").options.split("\n")
	context.countries = frappe.get_all("Country", pluck="name", order_by="name asc")
	return context

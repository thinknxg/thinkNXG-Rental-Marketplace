import json

import frappe

from thinknxg_rental_marketplace.website import base


def get_context(context):
	base(context, "Post Your Requirement", None)
	sites = []
	if context.mp_customer:
		sites = frappe.get_all("Customer Project Site", filters={"customer": context.mp_customer.customer},
			fields=["name", "project_name", "site_address", "city", "state", "country", "site_contact", "site_phone", "site_access"])
	fd = frappe.form_dict
	prefill = {"transaction_type": fd.get("type") if fd.get("type") in ("Hire", "Sale", "Contract") else None,
		"category": fd.get("category") if fd.get("category") and frappe.db.exists("Marketplace Category", fd.get("category")) else None,
		"q": (fd.get("q") or "")[:140], "city": (fd.get("city") or "")[:80],
		"listing": fd.get("listing") if fd.get("listing") and frappe.db.exists("Marketplace Listing", {"name": fd.get("listing"), "status": "Published"}) else None}
	context.boot = json.dumps({
		"categories": [{k: c.get(k) for k in ("name", "category_name", "parent", "is_group", "icon", "allow_hire", "allow_sale", "allow_contract", "listing_count")} for c in context.mp_categories],
		"uoms": frappe.get_all("UOM", filters={"enabled": 1}, pluck="name", order_by="name asc", limit=200),
		"countries": frappe.get_all("Country", pluck="name", order_by="name asc"),
		"currency": context.mp_settings.default_currency, "default_country": context.mp_settings.default_country,
		"user": context.mp_user, "customer": context.mp_customer.customer if context.mp_customer else None,
		"customer_role": context.mp_customer.role if context.mp_customer else None, "sites": sites, "prefill": prefill,
	}, default=str).replace("</", "<\\/")
	return context

import frappe
from frappe.utils import cint

from thinknxg_rental_marketplace.api import public
from thinknxg_rental_marketplace.website import base


def get_context(context):
	fd = frappe.form_dict
	category = fd.get("category")
	cat = None
	if category:
		cat = frappe.db.get_value("Marketplace Category", {"route": category}, ["name", "category_name", "description", "parent_marketplace_category"], as_dict=True) \
			or frappe.db.get_value("Marketplace Category", category, ["name", "category_name", "description", "parent_marketplace_category"], as_dict=True)
	base(context, cat.category_name if cat else "Browse Equipment", "categories" if cat else "equipment")
	context.cat = cat
	context.q, context.mode, context.country, context.city, context.sort = fd.get("q") or "", fd.get("mode") or "", fd.get("country") or "", fd.get("city") or "", fd.get("sort") or ""
	context.page = max(cint(fd.get("page")) or 1, 1)
	res = public.listing_query(context.q, cat.name if cat else None, context.mode, context.country, context.city, None, context.sort, context.page, 24)
	context.rows, context.total = res["rows"], res["total"]
	context.pages = max((res["total"] + 23) // 24, 1)
	context.countries = frappe.db.sql_list("select distinct country from `tabMarketplace Vendor` where status='Approved' order by country")
	context.children = [c for c in context.mp_categories if cat and c.parent == cat.name]
	return context

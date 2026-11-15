import frappe

from thinknxg_rental_marketplace.api import public
from thinknxg_rental_marketplace.website import base


def get_context(context):
	base(context, "Supplier Directory", "suppliers")
	fd = frappe.form_dict
	context.q, context.category, context.country = fd.get("q") or "", fd.get("category") or "", fd.get("country") or ""
	res = public.suppliers(context.q, context.category or None, context.country or None, page_length=48)
	context.rows, context.total = res["rows"], res["total"]
	context.countries = frappe.db.sql_list("select distinct country from `tabMarketplace Vendor` where status='Approved' order by country")
	return context

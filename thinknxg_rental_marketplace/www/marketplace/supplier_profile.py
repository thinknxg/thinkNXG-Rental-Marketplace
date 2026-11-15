import frappe

from thinknxg_rental_marketplace.api import public
from thinknxg_rental_marketplace.website import base


def get_context(context):
	v = public.supplier_detail(frappe.form_dict.get("slug") or "")
	if not v:
		raise frappe.PageDoesNotExistError
	base(context, v["business_name"], "suppliers", v.get("description"))
	context.v = frappe._dict(v)
	return context

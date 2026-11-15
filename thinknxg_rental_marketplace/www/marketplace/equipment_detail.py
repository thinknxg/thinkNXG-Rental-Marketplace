import frappe

from thinknxg_rental_marketplace.api import public
from thinknxg_rental_marketplace.website import base


def get_context(context):
	l = public.listing_detail(frappe.form_dict.get("slug") or "")
	if not l:
		raise frappe.PageDoesNotExistError
	base(context, l["title"], "equipment", l.get("short_description"))
	context.l = frappe._dict(l)
	context.images = [i["image"] for i in l["images"]] or ([l["cover_image"]] if l.get("cover_image") else [])
	context.related = [r for r in public.listing_query(category=l["category"], page_length=5)["rows"] if r.name != l["name"]][:4]
	return context

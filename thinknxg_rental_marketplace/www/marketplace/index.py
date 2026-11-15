import frappe

from thinknxg_rental_marketplace.api import public
from thinknxg_rental_marketplace.website import base


def get_context(context):
	base(context, "Smarter Equipment Sourcing", "home")
	context.stats = public.stats()
	context.featured = public.listing_query(page_length=8)["rows"]
	context.suppliers = public.suppliers(page_length=6)["rows"]
	context.tenders = public.public_tenders(page_length=6)["rows"]
	context.testimonials = public.reviews_highlight(3)
	for t in context.testimonials:
		t.vendor_name = frappe.db.get_value("Marketplace Vendor", t.vendor, "business_name")
	context.groups = [{**g, "children": [c for c in context.mp_categories if c.parent == g.name]} for g in context.mp_top_categories]
	return context

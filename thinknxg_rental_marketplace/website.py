"""Shared context for the marketplace website and portal shells."""
from urllib.parse import quote

import frappe

from thinknxg_rental_marketplace.services import context as ctx

NAV = (
	("equipment", "/marketplace/equipment", "Browse Equipment"),
	("categories", "/marketplace/categories", "Categories"),
	("suppliers", "/marketplace/suppliers", "Suppliers"),
	("how", "/marketplace/how-it-works", "How It Works"),
	("for-suppliers", "/marketplace/for-suppliers", "For Suppliers"),
)


def base(context, title, active=None, description=None):
	s = ctx.settings()
	context.no_cache = 1
	context.mp_title = title
	context.title = f"{title} · {s.marketplace_name}"
	context.meta_description = description or s.hero_subtitle
	context.mp_active = active
	context.mp_nav = NAV
	context.mp_settings = s
	context.csrf_token = frappe.sessions.get_csrf_token()
	user = frappe.session.user
	context.mp_user = user
	context.mp_vendor = ctx.vendor_membership(user) if user != "Guest" else None
	context.mp_customer = ctx.customer_membership(user) if user != "Guest" else None
	context.mp_operator = ctx.is_operator() if user != "Guest" else False
	context.mp_full_name = frappe.db.get_value("User", user, "full_name") if user != "Guest" else None
	from thinknxg_rental_marketplace.api.public import category_tree

	cats = category_tree()
	context.mp_top_categories = [c for c in cats if c.parent == "All Equipment"]
	context.mp_categories = cats
	return context


def portal(context, kind, title):
	"""Portal shells: login required, roles checked again on every API call."""
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(frappe.request.path)
		raise frappe.Redirect
	base(context, title)
	context.mp_kind = kind
	return context

"""Guest-accessible endpoints. Only public, non-confidential data leaves here."""
import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, now_datetime

from thinknxg_rental_marketplace.api.utils import page_args, parse
from thinknxg_rental_marketplace.services import context, registration

LISTING_CARD = ["name", "title", "route", "category", "cover_image", "vendor", "allow_hire", "allow_sale", "allow_contract", "condition",
	"brand", "model", "uom", "total_qty", "available_today", "currency", "daily_rate", "weekly_rate", "monthly_rate", "sale_price",
	"contract_monthly_rate", "short_description", "featured"]
VENDOR_PUBLIC = ["name", "business_name", "business_type", "route", "logo", "city", "state", "country", "description", "website",
	"verified", "rating", "review_count", "years_in_business", "featured_until"]


def _vendor_card(name):
	return frappe.db.get_value("Marketplace Vendor", name, ["business_name", "route", "verified", "rating", "review_count", "city", "country", "logo"], as_dict=True)


def category_tree():
	cached = frappe.cache.get_value("mp_public_categories")
	if cached:
		return cached
	rows = frappe.get_all("Marketplace Category", filters={"show_on_website": 1}, fields=["name", "category_name", "parent_marketplace_category as parent",
		"is_group", "route", "icon", "image", "description", "sort_order", "allow_hire", "allow_sale", "allow_contract", "lft"], order_by="lft asc")
	counts = dict(frappe.db.sql("""select l.category, count(*) from `tabMarketplace Listing` l join `tabMarketplace Vendor` v on v.name=l.vendor
		where l.status='Published' and v.status='Approved' group by l.category"""))
	for r in rows:
		r["listing_count"] = counts.get(r.name, 0)
	frappe.cache.set_value("mp_public_categories", rows, expires_in_sec=600)
	return rows


@frappe.whitelist(allow_guest=True)
def site_info():
	s = context.settings()
	return {
		"name": s.marketplace_name, "hero_title": s.hero_title, "hero_subtitle": s.hero_subtitle, "hero_image": s.hero_image,
		"currency": s.default_currency, "country": s.default_country, "support_email": s.support_email, "support_phone": s.support_phone,
		"categories": category_tree(), "stats": stats(),
	}


def stats():
	return {
		"suppliers": frappe.db.count("Marketplace Vendor", {"status": "Approved"}),
		"listings": frappe.db.count("Marketplace Listing", {"status": "Published"}),
		"tenders": frappe.db.count("Marketplace Tender", {"status": ["in", ["Bidding Open", "Bidding Closed", "Evaluation", "Awarded"]]}),
		"offers": frappe.db.count("Supplier Offer", {"status": ["not in", ["Draft"]]}),
	}


@frappe.whitelist(allow_guest=True)
def me():
	u = frappe.session.user
	if u == "Guest":
		return {"user": "Guest"}
	v = context.vendor_membership(u)
	c = context.customer_membership(u)
	return {"user": u, "full_name": frappe.db.get_value("User", u, "full_name"), "vendor": v.vendor if v else None,
		"vendor_role": v.vendor_role if v else None, "customer": c.customer if c else None, "customer_role": c.role if c else None,
		"operator": context.is_operator(), "csrf_token": frappe.sessions.get_csrf_token()}


def listing_query(q=None, category=None, mode=None, country=None, city=None, vendor=None, sort=None, page=1, page_length=24):
	cond, vals = ["l.status='Published'", "v.status='Approved'"], {}
	if category:
		lr = frappe.db.get_value("Marketplace Category", category, ["lft", "rgt"]) or frappe.db.get_value("Marketplace Category", {"route": category}, ["lft", "rgt"])
		if lr:
			cond.append("c.lft >= %(lft)s and c.rgt <= %(rgt)s")
			vals.update(lft=lr[0], rgt=lr[1])
	if mode in ("hire", "sale", "contract"):
		cond.append(f"l.allow_{mode}=1")
	if q:
		cond.append("(l.title like %(q)s or l.brand like %(q)s or l.model like %(q)s or l.short_description like %(q)s or v.business_name like %(q)s)")
		vals["q"] = f"%{q.strip()[:80]}%"
	if country:
		cond.append("(v.country=%(country)s or exists(select 1 from `tabVendor Location` vl where vl.parent=v.name and vl.country=%(country)s))")
		vals["country"] = country
	if city:
		cond.append("(v.city like %(city)s or exists(select 1 from `tabVendor Location` vl2 where vl2.parent=v.name and vl2.city like %(city)s))")
		vals["city"] = f"%{city.strip()[:60]}%"
	if vendor:
		cond.append("v.name=%(vendor)s")
		vals["vendor"] = vendor
	order = {"price": "coalesce(nullif(l.monthly_rate,0), l.sale_price, l.contract_monthly_rate) asc", "rating": "v.rating desc",
		"newest": "l.creation desc"}.get(sort, "l.featured desc, v.rating desc, l.modified desc")
	args = page_args(page, page_length)
	where = " and ".join(cond)
	cols = ", ".join(f"l.{f}" for f in LISTING_CARD)
	rows = frappe.db.sql(f"""select {cols}, v.business_name as vendor_name, v.route as vendor_route, v.verified as vendor_verified,
		v.rating as vendor_rating, v.city as vendor_city, v.country as vendor_country
		from `tabMarketplace Listing` l join `tabMarketplace Vendor` v on v.name=l.vendor
		join `tabMarketplace Category` c on c.name=l.category where {where} order by {order}
		limit {args['limit_start']}, {args['limit_page_length']}""", vals, as_dict=True)
	total = frappe.db.sql(f"""select count(*) from `tabMarketplace Listing` l join `tabMarketplace Vendor` v on v.name=l.vendor
		join `tabMarketplace Category` c on c.name=l.category where {where}""", vals)[0][0]
	return {"rows": rows, "total": total, "page": cint(page) or 1, "page_length": args["limit_page_length"]}


@frappe.whitelist(allow_guest=True)
def listings(q=None, category=None, mode=None, country=None, city=None, sort=None, page=1, page_length=24):
	return listing_query(q, category, mode, country, city, None, sort, page, page_length)


def listing_detail(slug):
	name = frappe.db.get_value("Marketplace Listing", {"route": slug, "status": "Published"}, "name") or (
		frappe.db.exists("Marketplace Listing", {"name": slug, "status": "Published"}) and slug)
	if not name:
		return None
	l = frappe.get_doc("Marketplace Listing", name)
	if frappe.db.get_value("Marketplace Vendor", l.vendor, "status") != "Approved":
		return None
	out = {f: l.get(f) for f in LISTING_CARD + ["description", "certifications", "warranty", "min_hire_days", "min_order_qty",
		"security_deposit_rate", "min_contract_months", "delivery_available", "installation_available", "weight_per_unit_kg", "manufacture_year", "datasheet"]}
	out["specifications"] = [{"attribute": s.attribute, "value": s.value, "unit": s.unit} for s in l.specifications]
	out["images"] = [{"image": i.image, "caption": i.caption} for i in l.images]
	out["vendor"] = _vendor_card(l.vendor)
	out["category_path"] = frappe.get_all("Marketplace Category", filters={"lft": ["<=", frappe.db.get_value("Marketplace Category", l.category, "lft")],
		"rgt": [">=", frappe.db.get_value("Marketplace Category", l.category, "rgt")]}, fields=["name", "route"], order_by="lft asc")
	return out


@frappe.whitelist(allow_guest=True)
def listing(slug):
	return listing_detail(slug) or frappe.throw(frappe._("Listing not found"), frappe.DoesNotExistError)


@frappe.whitelist(allow_guest=True)
def suppliers(q=None, category=None, country=None, page=1, page_length=24):
	filters = {"status": "Approved"}
	or_filters = None
	if q:
		or_filters = {"business_name": ["like", f"%{q[:80]}%"], "city": ["like", f"%{q[:80]}%"]}
	if country:
		filters["country"] = country
	names = None
	if category:
		names = frappe.get_all("Vendor Category", filters={"category": category, "parenttype": "Marketplace Vendor"}, pluck="parent")
		filters["name"] = ["in", names or ["__none__"]]
	args = page_args(page, page_length)
	rows = frappe.get_all("Marketplace Vendor", filters=filters, or_filters=or_filters, fields=VENDOR_PUBLIC, order_by="featured_until desc, rating desc, review_count desc", **args)
	for r in rows:
		r["categories"] = frappe.get_all("Vendor Category", filters={"parent": r.name, "parenttype": "Marketplace Vendor"}, pluck="category")
		r["listing_count"] = frappe.db.count("Marketplace Listing", {"vendor": r.name, "status": "Published"})
	return {"rows": rows, "total": len(frappe.get_all("Marketplace Vendor", filters=filters, or_filters=or_filters, pluck="name"))}


def supplier_detail(slug):
	name = frappe.db.get_value("Marketplace Vendor", {"route": slug, "status": "Approved"}, "name")
	if not name:
		return None
	v = frappe.get_doc("Marketplace Vendor", name)
	out = {f: v.get(f) for f in VENDOR_PUBLIC}
	out["categories"] = [c.category for c in v.categories]
	out["locations"] = [{"city": l.city, "state": l.state, "country": l.country, "delivery_radius_km": l.delivery_radius_km} for l in v.locations]
	out["listings"] = listing_query(vendor=name, page_length=48)["rows"]
	out["reviews"] = frappe.get_all("Marketplace Review", filters={"vendor": name, "status": "Published"},
		fields=["rating", "title", "comment", "reviewer_display_name", "vendor_response", "creation"], order_by="creation desc", limit=20)
	return out


@frappe.whitelist(allow_guest=True)
def supplier(slug):
	return supplier_detail(slug) or frappe.throw(frappe._("Supplier not found"), frappe.DoesNotExistError)


@frappe.whitelist(allow_guest=True)
def public_tenders(page=1, page_length=12):
	if not context.settings().show_public_tenders:
		return {"rows": [], "total": 0}
	filters = {"status": "Bidding Open", "visibility": "Public Marketplace", "tender_type": "Open", "submission_deadline": [">", now_datetime()]}
	rows = frappe.get_all("Marketplace Tender", filters=filters, fields=["name", "title", "transaction_type", "category", "city", "country",
		"submission_deadline", "offers_count", "featured"], order_by="featured desc, submission_deadline asc", **page_args(page, page_length))
	for r in rows:
		r["lines"] = frappe.db.count("Tender Item", {"parent": r.name, "parenttype": "Marketplace Tender"})
	return {"rows": rows, "total": frappe.db.count("Marketplace Tender", filters)}


@frappe.whitelist(allow_guest=True)
def reviews_highlight(limit=6):
	"""Testimonials come only from real, published reviews of completed bookings."""
	return frappe.get_all("Marketplace Review", filters={"status": "Published", "rating": [">=", 0.8], "comment": ["is", "set"]},
		fields=["rating", "title", "comment", "reviewer_display_name", "vendor"], order_by="creation desc", limit=min(cint(limit), 12))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def register_vendor(data):
	v = registration.register_vendor(parse(data))
	return {"vendor": v.name, "status": v.status, "next": "/marketplace/vendor" if frappe.session.user != "Guest" else "/login"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def register_customer(data):
	c = registration.register_customer(parse(data))
	return {"customer": c.name, "next": "/marketplace/account" if frappe.session.user != "Guest" else "/login"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def enquiry(data):
	d = parse(data)
	if not (d.get("full_name") and d.get("email") and d.get("message")):
		frappe.throw(frappe._("Name, email and message are required"))
	doc = frappe.get_doc({"doctype": "Marketplace Enquiry", "full_name": d["full_name"][:140], "email": d["email"][:140],
		"phone": (d.get("phone") or "")[:40], "company": (d.get("company") or "")[:140],
		"enquiry_type": d.get("enquiry_type") if d.get("enquiry_type") in ("General", "Supplier Onboarding", "Customer Support", "Partnership", "Press") else "General",
		"message": d["message"][:5000]})
	doc.flags.ignore_permissions = True
	doc.insert()
	return {"ok": True}

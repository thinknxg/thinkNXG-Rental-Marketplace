"""Install / migrate: roles, default categories, plans, evaluation criteria, settings."""
import frappe

ROLES = (
	("Marketplace Admin", 1), ("Marketplace Moderator", 1), ("Marketplace Finance", 1),
	("Marketplace Vendor", 0), ("Marketplace Customer", 0),
)

CATEGORIES = {
	"Formwork": ["Wall Formwork", "Slab Formwork", "Column Formwork", "Beam Formwork", "Aluminium Formwork", "Modular Formwork"],
	"Scaffolding": ["Cuplock Scaffolding", "Ringlock Scaffolding", "H-Frame Scaffolding", "Tube and Fitting", "Aluminium Scaffolding",
		"Mobile Scaffolding", "Scaffolding Accessories"],
	"Construction Equipment": ["Concrete Equipment", "Lifting Equipment", "Earthmoving Equipment", "Material Handling",
		"Compaction Equipment", "Power Equipment"],
	"Accessories and Materials": ["Props", "Shuttering Materials", "Clamps", "Couplers", "Safety Equipment", "Construction Accessories"],
}
ICONS = {"Formwork": "formwork", "Scaffolding": "scaffold", "Construction Equipment": "excavator", "Accessories and Materials": "clamp"}
ROOT = "All Equipment"

PLANS = (
	dict(plan_code="starter", plan_name="Starter", price_monthly=0, price_yearly=0, max_listings=10, max_tender_responses=15, max_staff_users=2, sort_order=1, trial_days=30,
		description="Limited listings and tender responses, standard dashboard."),
	dict(plan_code="professional", plan_name="Professional", price_monthly=49, price_yearly=490, max_listings=100, max_tender_responses=100, max_staff_users=10,
		advanced_reports=1, featured_listings=2, sort_order=2, trial_days=30, description="More listings and responses, advanced reporting, team accounts."),
	dict(plan_code="enterprise", plan_name="Enterprise", price_monthly=199, price_yearly=1990, max_listings=0, max_tender_responses=0, max_staff_users=0,
		advanced_reports=1, api_access=1, priority_support=1, featured_listings=10, sort_order=3, trial_days=14,
		description="Unlimited listings, responses and staff; analytics, API access, priority support."),
)

CRITERIA = (("Price", "Price", 40), ("Delivery", "Delivery", 20), ("Supplier Rating", "Rating", 20), ("Technical Compliance", "Technical", 20))


UOMS = ("Nos", "Set", "Unit", "Sqm", "Meter", "Kg", "Tonne", "Day", "Month", "Lot")


def after_install():
	ensure_uoms()
	ensure_roles()
	ensure_categories()
	ensure_plans()
	ensure_criteria()
	ensure_settings()
	frappe.db.commit()


def ensure_currency_precision(currency=None):
	"""Stored Currency fields must hold what Decimal pricing computes (OMR/KWD/BHD use 3 decimals)."""
	from thinknxg_rental_marketplace.services.money import precision

	currency = currency or frappe.db.get_single_value("Marketplace Settings", "default_currency")
	current = frappe.db.get_single_value("System Settings", "currency_precision")
	if precision(currency) == 3 and str(current or "") in ("", "2"):
		frappe.db.set_single_value("System Settings", "currency_precision", "3")
		frappe.db.set_default("currency_precision", "3")


def after_migrate():
	ensure_currency_precision()
	ensure_uoms()
	ensure_roles()
	ensure_criteria()


def ensure_uoms():
	for u in UOMS:
		if not frappe.db.exists("UOM", u):
			frappe.get_doc({"doctype": "UOM", "uom_name": u, "must_be_whole_number": 1 if u in ("Nos", "Set", "Unit", "Lot") else 0}).insert(ignore_permissions=True)


def ensure_roles():
	for role, desk in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Role", role, "desk_access", desk)


def _cat(name, parent, is_group, sort, icon=None):
	from thinknxg_rental_marketplace.services.vendors import slugify

	if frappe.db.exists("Marketplace Category", name):
		return
	frappe.get_doc({"doctype": "Marketplace Category", "category_name": name, "parent_marketplace_category": parent, "is_group": is_group,
		"route": slugify(name), "sort_order": sort, "icon": icon, "show_on_website": 1, "allow_hire": 1, "allow_sale": 1, "allow_contract": 1}).insert(ignore_permissions=True)


def ensure_categories():
	_cat(ROOT, None, 1, 0)
	for i, (group, children) in enumerate(CATEGORIES.items(), 1):
		_cat(group, ROOT, 1, i, ICONS.get(group))
		for j, child in enumerate(children, 1):
			_cat(child, group, 0, j, ICONS.get(group))


def ensure_plans():
	currency = frappe.db.get_single_value("Marketplace Settings", "default_currency") or "OMR"
	for p in PLANS:
		if not frappe.db.exists("Marketplace Subscription Plan", p["plan_code"]):
			frappe.get_doc({"doctype": "Marketplace Subscription Plan", "enabled": 1, "currency": currency, **p}).insert(ignore_permissions=True)


def ensure_criteria():
	for name, basis, weight in CRITERIA:
		if not frappe.db.exists("Offer Evaluation Criterion", name):
			frappe.get_doc({"doctype": "Offer Evaluation Criterion", "criterion_name": name, "basis": basis, "default_weight": weight}).insert(ignore_permissions=True)


def ensure_settings():
	s = frappe.get_single("Marketplace Settings")
	s.marketplace_name = s.marketplace_name or "thinkNXG Rental Marketplace"
	if not s.default_currency or not frappe.db.exists("Currency", s.default_currency):
		s.default_currency = "OMR" if frappe.db.exists("Currency", "OMR") else (frappe.db.get_default("currency") or "USD")
	if frappe.db.exists("Currency", s.default_currency):
		frappe.db.set_value("Currency", s.default_currency, "enabled", 1)
	ensure_currency_precision(s.default_currency)
	s.default_country = s.default_country or ("Oman" if frappe.db.exists("Country", "Oman") else None)
	s.company = s.company or frappe.db.get_single_value("Global Defaults", "default_company")
	s.default_trial_plan = s.default_trial_plan or ("starter" if frappe.db.exists("Marketplace Subscription Plan", "starter") else None)
	s.hero_title = s.hero_title or "One Requirement. Multiple Offers. Smarter Equipment Sourcing."
	s.hero_subtitle = s.hero_subtitle or ("Discover verified scaffolding, formwork and construction equipment suppliers. Submit your requirement once "
		"and receive competitive hire, sale and contract offers from the marketplace.")
	s.support_email = s.support_email or "support@thinknxg.com"
	s.sales_email = s.sales_email or "sales@kreatao.com"
	s.flags.ignore_permissions = True
	s.save()


def before_uninstall():
	pass

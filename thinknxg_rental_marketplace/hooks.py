app_name = "thinknxg_rental_marketplace"
app_title = "thinkNXG Rental Marketplace"
app_publisher = "thinkNXG"
app_description = "Multi-vendor tender & bidding marketplace for scaffolding, formwork and construction equipment (hire, sale, contract)"
app_email = "info@thinknxg.com"
app_license = "mit"
required_apps = ["erpnext"]

add_to_apps_screen = [
	{
		"name": "thinknxg_rental_marketplace",
		"logo": "/assets/thinknxg_rental_marketplace/images/logo.svg",
		"title": "Rental Marketplace",
		"route": "/marketplace/operator",
		"has_permission": "thinknxg_rental_marketplace.api.operator.has_app_permission",
	}
]

after_install = "thinknxg_rental_marketplace.services.setup.after_install"
after_migrate = "thinknxg_rental_marketplace.services.setup.after_migrate"
before_uninstall = "thinknxg_rental_marketplace.services.setup.before_uninstall"

# Public site + three single-page portals, all under /marketplace (the source app owns /rental and /hire)
website_route_rules = [
	{"from_route": "/marketplace/equipment/<path:slug>", "to_route": "marketplace/equipment_detail"},
	{"from_route": "/marketplace/suppliers/<path:slug>", "to_route": "marketplace/supplier_profile"},
	{"from_route": "/marketplace/categories/<path:category>", "to_route": "marketplace/equipment"},
	{"from_route": "/marketplace/how-it-works", "to_route": "marketplace/how_it_works"},
	{"from_route": "/marketplace/post-requirement", "to_route": "marketplace/post_requirement"},
	{"from_route": "/marketplace/for-suppliers", "to_route": "marketplace/for_suppliers"},
	{"from_route": "/marketplace/account/<path:app_path>", "to_route": "marketplace/account"},
	{"from_route": "/marketplace/vendor/<path:app_path>", "to_route": "marketplace/vendor"},
	{"from_route": "/marketplace/operator/<path:app_path>", "to_route": "marketplace/operator"},
]

standard_portal_menu_items = [
	{"title": "Marketplace — My Requests", "route": "/marketplace/account", "role": "Marketplace Customer"},
	{"title": "Marketplace — Supplier Portal", "route": "/marketplace/vendor", "role": "Marketplace Vendor"},
]

# Defence in depth: portal roles have no DocType permissions at all; these add record-level walls for desk users.
permission_query_conditions = {
	"Marketplace Notification": "thinknxg_rental_marketplace.services.permissions.notification_query",
}
has_permission = {
	"Marketplace Notification": "thinknxg_rental_marketplace.services.permissions.notification_has_permission",
	"Marketplace Audit Event": "thinknxg_rental_marketplace.services.permissions.audit_has_permission",
	"Offer Revision": "thinknxg_rental_marketplace.services.permissions.audit_has_permission",
}

_B = "thinknxg_rental_marketplace.services.rental_bridge."
doc_events = {
	# thinkNXG Rental → marketplace status (inert when thinknxg_rental is not installed)
	"Hire Order": {"on_submit": _B + "hire_order_submitted"},
	"Rental Contract": {"on_submit": _B + "rental_contract_submitted"},
	"Hire Delivery Order": {"on_submit": _B + "hire_delivery_submitted"},
	"Hire Off-Hire Note": {"on_submit": _B + "off_hire_submitted"},
	# ERPNext sales path
	"Sales Order": {"on_submit": _B + "sales_order_submitted"},
	"Delivery Note": {"on_submit": _B + "delivery_note_submitted"},
}

scheduler_events = {
	"cron": {
		"*/5 * * * *": [
			"thinknxg_rental_marketplace.services.tender.process_deadlines",
			"thinknxg_rental_marketplace.services.booking.expire_unpaid",
		],
	},
	"daily": [
		"thinknxg_rental_marketplace.services.subscriptions.daily_lifecycle",
		"thinknxg_rental_marketplace.services.trust.expire_promotions",
		"thinknxg_rental_marketplace.services.maintenance.refresh_listing_availability",
	],
}

# Rate limits for sensitive public submissions are applied with @rate_limit on the endpoints themselves.
ignore_links_on_delete = ["Marketplace Audit Event", "Marketplace Notification"]

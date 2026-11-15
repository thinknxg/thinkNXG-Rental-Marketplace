import frappe

from thinknxg_rental_marketplace.services import availability


def refresh_listing_availability():
	for name in frappe.get_all("Marketplace Listing", filters={"status": "Published"}, pluck="name"):
		availability.refresh_available_today(name)
	for name in frappe.get_all("Marketplace Listing", filters={"featured": 1, "featured_until": ["<", frappe.utils.getdate()]}, pluck="name"):
		frappe.db.set_value("Marketplace Listing", name, "featured", 0)
	frappe.db.commit()

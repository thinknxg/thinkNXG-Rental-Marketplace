# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document


class MarketplaceVendor(Document):
	def validate(self):
		from thinknxg_rental_marketplace.services.vendors import slugify, unique_route

		if not self.route:
			self.route = unique_route("Marketplace Vendor", slugify(self.business_name), self.name)
		seen = set()
		for row in self.categories:
			if row.category in seen:
				frappe.throw(frappe._("Category {0} listed twice").format(row.category))
			seen.add(row.category)

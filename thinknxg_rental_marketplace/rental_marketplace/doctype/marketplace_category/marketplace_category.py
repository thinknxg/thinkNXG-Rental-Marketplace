# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.utils.nestedset import NestedSet


class MarketplaceCategory(NestedSet):
	nsm_parent_field = "parent_marketplace_category"

	def validate(self):
		from thinknxg_rental_marketplace.services.vendors import slugify, unique_route

		if not self.route:
			self.route = unique_route("Marketplace Category", slugify(self.category_name), self.name)

	def on_update(self):
		super().on_update()
		frappe.cache.delete_value("mp_public_categories")

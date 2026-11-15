# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

from frappe.model.document import Document


class MarketplaceListing(Document):
	def validate(self):
		from thinknxg_rental_marketplace.services.vendors import validate_listing

		validate_listing(self)

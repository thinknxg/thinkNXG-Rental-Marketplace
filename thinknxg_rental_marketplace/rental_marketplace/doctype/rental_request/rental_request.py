# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

from frappe.model.document import Document


class RentalRequest(Document):
	def validate(self):
		from thinknxg_rental_marketplace.services.requests import validate

		validate(self)

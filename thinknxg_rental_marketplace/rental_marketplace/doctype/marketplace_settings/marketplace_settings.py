# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document


class MarketplaceSettings(Document):
	def on_update(self):
		frappe.clear_document_cache("Marketplace Settings", "Marketplace Settings")
		frappe.cache.delete_value("mp_public_categories")

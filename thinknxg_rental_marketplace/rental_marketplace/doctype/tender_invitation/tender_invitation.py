# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document


class TenderInvitation(Document):
	def validate(self):
		if frappe.db.exists("Tender Invitation", {"tender": self.tender, "vendor": self.vendor, "name": ["!=", self.name or ""]}):
			frappe.throw(frappe._("Supplier {0} is already invited to {1}").format(self.vendor, self.tender))

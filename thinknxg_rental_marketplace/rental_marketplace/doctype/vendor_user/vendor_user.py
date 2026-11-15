# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document


class VendorUser(Document):
	def validate(self):
		other = frappe.db.get_value("Vendor User", {"user": self.user, "name": ["!=", self.name or ""]}, "vendor")
		if other:
			frappe.throw(frappe._("User {0} already belongs to supplier {1}").format(self.user, other))

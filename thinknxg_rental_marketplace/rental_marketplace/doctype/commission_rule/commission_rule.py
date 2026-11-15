# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate


class CommissionRule(Document):
	def validate(self):
		if self.basis == "Percentage" and not (0 <= flt(self.rate) <= 100):
			frappe.throw(frappe._("Rate must be between 0 and 100"))
		if self.valid_from and self.valid_upto and getdate(self.valid_upto) < getdate(self.valid_from):
			frappe.throw(frappe._("Valid Upto is before Valid From"))

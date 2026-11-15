# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class MarketplaceTender(Document):
	def validate(self):
		if not self.items:
			frappe.throw(frappe._("A tender needs at least one requirement line"))
		if self.criteria and abs(sum(flt(c.weight) for c in self.criteria)) <= 0:
			frappe.throw(frappe._("Evaluation weights must add up to more than zero"))
		if self.tender_type == "Reverse Auction" and self.confidentiality == "Sealed":
			self.confidentiality = "Rank Only"

# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document


class OfferRevision(Document):
	"""Insert-only record."""

	def validate(self):
		if not self.is_new() and not self.flags.allow_update:
			frappe.throw(frappe._("{0} records are immutable").format(self.doctype))

	def on_trash(self):
		if not frappe.flags.in_test and not self.flags.allow_delete:
			frappe.throw(frappe._("{0} records cannot be deleted").format(self.doctype))

"""Record-level permission hooks (desk). Portal users never reach these DocTypes through the REST API."""
import frappe

from thinknxg_rental_marketplace.services.context import OPERATOR_ROLES


def _operator(user):
	return bool(set(frappe.get_roles(user)) & OPERATOR_ROLES)


def notification_query(user=None):
	user = user or frappe.session.user
	if _operator(user) and "System Manager" in frappe.get_roles(user):
		return ""
	return f"`tabMarketplace Notification`.recipient = {frappe.db.escape(user)}"


def notification_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	return doc.recipient == user or "System Manager" in frappe.get_roles(user)


def audit_has_permission(doc, ptype=None, user=None):
	"""Insert-only: nobody edits or deletes audit rows or offer revisions."""
	if ptype in ("write", "delete", "cancel", "submit", "amend"):
		return False
	return None

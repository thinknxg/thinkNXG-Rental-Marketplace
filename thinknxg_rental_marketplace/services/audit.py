"""Insert-only audit trail. Nobody holds write/delete permission on Marketplace Audit Event."""
import json

import frappe


def log(event, doctype=None, name=None, from_state=None, to_state=None, **data):
	try:
		ip = getattr(frappe.local, "request_ip", None)
	except Exception:
		ip = None
	doc = frappe.get_doc(
		{
			"doctype": "Marketplace Audit Event",
			"event": event,
			"reference_doctype": doctype,
			"reference_name": name,
			"actor": frappe.session.user,
			"from_state": from_state,
			"to_state": to_state,
			"ip_address": ip,
			"data": json.dumps(data, default=str) if data else None,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def history(doctype, name, limit=100):
	return frappe.get_all(
		"Marketplace Audit Event",
		filters={"reference_doctype": doctype, "reference_name": name},
		fields=["event", "actor", "from_state", "to_state", "creation", "data"],
		order_by="creation asc",
		limit=limit,
	)

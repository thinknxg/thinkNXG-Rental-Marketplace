import json

import frappe
from frappe.utils import cint

MAX_PAGE = 50


def parse(value):
	if value is None or isinstance(value, (dict, list)):
		return value or {}
	try:
		return json.loads(value)
	except (TypeError, ValueError):
		return {}


def page_args(page=1, page_length=20):
	page_length = min(max(cint(page_length) or 20, 1), MAX_PAGE)
	return dict(limit_start=(max(cint(page) or 1, 1) - 1) * page_length, limit_page_length=page_length)


def paged(doctype, filters, fields, order_by="modified desc", page=1, page_length=20, or_filters=None):
	args = page_args(page, page_length)
	rows = frappe.get_all(doctype, filters=filters, or_filters=or_filters, fields=fields, order_by=order_by, **args)
	total = len(frappe.get_all(doctype, filters=filters, or_filters=or_filters, pluck="name")) if or_filters else frappe.db.count(doctype, filters)
	return {"rows": rows, "total": total, "page": cint(page) or 1, "page_length": args["limit_page_length"]}


def pick(doc, fields):
	return {f: doc.get(f) for f in fields}


def notifications_for(user, limit=30):
	return {
		"rows": frappe.get_all("Marketplace Notification", filters={"recipient": user}, fields=["name", "title", "message", "link", "category", "read", "creation"],
			order_by="creation desc", limit=limit),
		"unread": frappe.db.count("Marketplace Notification", {"recipient": user, "read": 0}),
	}


def mark_read(user, names=None):
	filters = {"recipient": user, "read": 0}
	if names:
		filters["name"] = ["in", parse(names) if isinstance(names, str) else names]
	for n in frappe.get_all("Marketplace Notification", filters=filters, pluck="name"):
		frappe.db.set_value("Marketplace Notification", n, "read", 1, update_modified=False)
	return True

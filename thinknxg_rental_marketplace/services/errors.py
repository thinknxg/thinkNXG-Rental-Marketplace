"""Stable, machine-readable marketplace errors.

Every business rule violation raises a MarketplaceError subclass whose message starts with ``[CODE]``.
The portals read the code (``mp_core.js`` → ``err.code``); the human text may change, the code may not.
"""
import frappe
from frappe import _


class MarketplaceError(frappe.ValidationError):
	http_status_code = 417


class NotAllowed(frappe.PermissionError):
	http_status_code = 403


class NotFound(frappe.DoesNotExistError):
	http_status_code = 404


class Conflict(MarketplaceError):
	http_status_code = 409


class LimitReached(MarketplaceError):
	http_status_code = 402


def fail(code, message, exc=MarketplaceError, **fmt):
	text = _(message).format(**fmt) if fmt else _(message)
	frappe.throw(f"[{code}] {text}", exc, title=_("Marketplace"))


def forbid(code="FORBIDDEN", message="You do not have access to this record."):
	fail(code, message, NotAllowed)


def not_found(doctype, name=None):
	fail("NOT_FOUND", "{doctype} not found.", NotFound, doctype=_(doctype))

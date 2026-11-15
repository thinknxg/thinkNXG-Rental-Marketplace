"""Self-service sign-up for suppliers and customers (website users, no desk access)."""
import frappe
from frappe.utils import validate_email_address

from thinknxg_rental_marketplace.services import audit, notifications
from thinknxg_rental_marketplace.services.errors import Conflict, fail
from thinknxg_rental_marketplace.services.vendors import slugify, unique_route


def ensure_user(email, full_name, role):
	email = (email or "").strip().lower()
	if not validate_email_address(email):
		fail("EMAIL_INVALID", "Enter a valid email address.")
	if frappe.db.exists("User", email):
		u = frappe.get_doc("User", email)
		if role not in [r.role for r in u.roles]:
			u.flags.ignore_permissions = True
			u.add_roles(role)
		return u.name
	first, _, last = (full_name or email.split("@")[0]).partition(" ")
	u = frappe.get_doc({"doctype": "User", "email": email, "first_name": first[:140], "last_name": last[:140], "user_type": "Website User",
		"send_welcome_email": 1, "roles": [{"role": role}]})
	u.flags.ignore_permissions = True
	u.insert()
	return u.name


def _current_or_new_user(data, role):
	if frappe.session.user != "Guest":
		u = frappe.get_doc("User", frappe.session.user)
		if role not in [r.role for r in u.roles]:
			u.flags.ignore_permissions = True
			u.add_roles(role)
		return u.name
	if not data.get("accept_terms"):
		fail("TERMS_REQUIRED", "Please accept the marketplace terms.")
	return ensure_user(data.get("email"), data.get("contact_person") or data.get("full_name"), role)


def register_vendor(data):
	required = ("business_name", "business_type", "country", "city", "address_line1", "contact_person", "email", "phone", "registration_number")
	missing = [f for f in required if not (data.get(f) or "").strip()]
	if missing:
		fail("FIELDS_REQUIRED", "Required: {m}", m=", ".join(missing))
	if frappe.db.exists("Marketplace Vendor", {"registration_number": data["registration_number"].strip(), "country": data["country"]}):
		fail("VENDOR_EXISTS", "A supplier with this registration number is already registered.", Conflict)
	user = _current_or_new_user(data, "Marketplace Vendor")
	if frappe.db.exists("Vendor User", {"user": user}):
		fail("USER_LINKED", "This account already belongs to a supplier.", Conflict)
	cats = [c for c in data.get("categories") or [] if frappe.db.exists("Marketplace Category", c)]
	v = frappe.get_doc({"doctype": "Marketplace Vendor", "status": "Draft", "owner_user": user,
		**{k: (data.get(k) or "").strip() if isinstance(data.get(k), str) else data.get(k) for k in required + ("state", "website", "description", "tax_id", "address_line2", "pincode")},
		"categories": [{"category": c} for c in dict.fromkeys(cats)],
		"locations": [{"city": data["city"], "state": data.get("state"), "country": data["country"], "is_head_office": 1, "delivery_radius_km": 150}]})
	v.route = unique_route("Marketplace Vendor", slugify(v.business_name))
	v.flags.ignore_permissions = True
	v.insert()
	vu = frappe.get_doc({"doctype": "Vendor User", "vendor": v.name, "user": user, "vendor_role": "Owner", "enabled": 1})
	vu.flags.ignore_permissions = True
	vu.insert()
	audit.log("vendor.registered", v.doctype, v.name, None, "Draft", user=user)
	if cats:
		from thinknxg_rental_marketplace.services.vendors import set_status

		set_status(v.name, "Submitted")
		set_status(v.name, "Documents Pending")
	notifications.to_operators(frappe._("New supplier registration: {0}").format(v.business_name), "", link=f"/marketplace/operator/vendors/{v.name}", category="Vendor", ref=v)
	return v


def register_customer(data):
	name = (data.get("company_name") if data.get("customer_type") == "Company" else data.get("full_name")) or data.get("full_name")
	if not (name and data.get("email")):
		fail("FIELDS_REQUIRED", "Name and email are required.")
	user = _current_or_new_user(data, "Marketplace Customer")
	from thinknxg_rental_marketplace.services.context import customer_membership

	m = customer_membership(user)
	if m:
		return frappe.get_doc("Marketplace Customer", m.customer)
	c = frappe.get_doc({"doctype": "Marketplace Customer", "customer_name": name.strip(), "customer_type": data.get("customer_type") or "Company",
		"company_name": data.get("company_name"), "industry": data.get("industry"), "email": data.get("email") or user, "phone": data.get("phone"),
		"country": data.get("country"), "city": data.get("city"), "tax_id": data.get("tax_id"), "status": "Active", "owner_user": user})
	c.flags.ignore_permissions = True
	c.insert()
	audit.log("customer.registered", c.doctype, c.name, None, "Active", user=user)
	return c

"""Who is acting. Resolved on the server for every request — never taken from the browser.

* vendor actor  : an enabled ``Vendor User`` row for the session user
* customer actor: ``Marketplace Customer.owner_user`` or an enabled ``Marketplace Customer Member`` row
* operator      : desk roles Marketplace Admin / Moderator / Finance (System Manager counts as Admin)
"""
import frappe

from thinknxg_rental_marketplace.services.errors import fail, forbid, NotAllowed

ADMIN_ROLES = {"System Manager", "Marketplace Admin"}
MODERATOR_ROLES = ADMIN_ROLES | {"Marketplace Moderator"}
FINANCE_ROLES = ADMIN_ROLES | {"Marketplace Finance"}
OPERATOR_ROLES = ADMIN_ROLES | {"Marketplace Moderator", "Marketplace Finance"}
VENDOR_ROLE_RANK = {"Staff": 1, "Manager": 2, "Owner": 3}
CUSTOMER_ROLE_RANK = {"Viewer": 1, "Buyer": 2, "Owner": 3}


def user():
	return frappe.session.user


def roles(u=None):
	return set(frappe.get_roles(u or user()))


def is_operator(kind="any", u=None):
	r = roles(u)
	return bool(r & {"any": OPERATOR_ROLES, "admin": ADMIN_ROLES, "moderator": MODERATOR_ROLES, "finance": FINANCE_ROLES}[kind])


def require_login():
	if user() == "Guest":
		fail("LOGIN_REQUIRED", "Please sign in to continue.", NotAllowed)


def require_operator(kind="any"):
	require_login()
	if not is_operator(kind):
		forbid("OPERATOR_ONLY", "This action is limited to marketplace operators.")


# ------------------------------------------------------------------ vendor
def vendor_membership(u=None):
	u = u or user()
	if u == "Guest":
		return None
	row = frappe.db.get_value("Vendor User", {"user": u, "enabled": 1}, ["vendor", "vendor_role"], as_dict=True)
	return row


def require_vendor(min_role="Staff", approved=False, active=True):
	"""Returns frappe._dict(vendor=<name>, role=<vendor_role>, status=<vendor status>, doc=<cached fields>)."""
	require_login()
	m = vendor_membership()
	if not m:
		forbid("NOT_A_VENDOR", "Your account is not linked to a supplier business.")
	if VENDOR_ROLE_RANK.get(m.vendor_role, 0) < VENDOR_ROLE_RANK[min_role]:
		forbid("VENDOR_ROLE", "Your supplier role does not allow this action.")
	v = frappe.db.get_value("Marketplace Vendor", m.vendor, ["name", "status", "business_name", "verified", "country"], as_dict=True)
	if active and v.status in ("Suspended", "Deactivated", "Rejected") and approved:
		forbid("VENDOR_INACTIVE", "Your supplier account is {status}.".format(status=v.status))
	if approved and v.status != "Approved":
		forbid("VENDOR_NOT_APPROVED", "Your supplier account must be approved by the marketplace first.")
	return frappe._dict(vendor=m.vendor, role=m.vendor_role, status=v.status, doc=v)


# ------------------------------------------------------------------ customer
def customer_membership(u=None):
	u = u or user()
	if u == "Guest":
		return None
	name = frappe.db.get_value("Marketplace Customer", {"owner_user": u}, "name")
	if name:
		return frappe._dict(customer=name, role="Owner")
	row = frappe.db.sql(
		"""select parent as customer, member_role as role from `tabMarketplace Customer Member`
		where user=%s and enabled=1 and parenttype='Marketplace Customer' limit 1""",
		u,
		as_dict=True,
	)
	return row[0] if row else None


def require_customer(min_role="Viewer"):
	require_login()
	m = customer_membership()
	if not m:
		forbid("NOT_A_CUSTOMER", "Your account is not linked to a customer profile.")
	if CUSTOMER_ROLE_RANK.get(m.role, 0) < CUSTOMER_ROLE_RANK[min_role]:
		forbid("CUSTOMER_ROLE", "Your role does not allow this action.")
	status = frappe.db.get_value("Marketplace Customer", m.customer, "status")
	if min_role != "Viewer" and status != "Active":
		forbid("CUSTOMER_RESTRICTED", "Your customer account is {status}.".format(status=status))
	return frappe._dict(customer=m.customer, role=m.role, status=status)


def customer_users(customer):
	owner = frappe.db.get_value("Marketplace Customer", customer, "owner_user")
	members = frappe.get_all("Marketplace Customer Member", filters={"parent": customer, "parenttype": "Marketplace Customer", "enabled": 1}, pluck="user")
	return sorted({u for u in [owner, *members] if u})


def vendor_users(vendor, min_role="Staff"):
	rows = frappe.get_all("Vendor User", filters={"vendor": vendor, "enabled": 1}, fields=["user", "vendor_role"])
	return [r.user for r in rows if VENDOR_ROLE_RANK.get(r.vendor_role, 0) >= VENDOR_ROLE_RANK[min_role]]


def operator_users(kind="moderator"):
	role_names = {"admin": ["Marketplace Admin"], "moderator": ["Marketplace Admin", "Marketplace Moderator"], "finance": ["Marketplace Admin", "Marketplace Finance"]}[kind]
	return sorted(set(frappe.get_all("Has Role", filters={"role": ["in", role_names], "parenttype": "User"}, pluck="parent")) - {"Administrator", "Guest"})


def settings():
	return frappe.get_cached_doc("Marketplace Settings")

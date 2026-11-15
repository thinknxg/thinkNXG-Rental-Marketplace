"""Vendor onboarding, verification, staff, and catalogue (listings) management."""
import re

import frappe
from frappe.utils import cint, flt, getdate, now_datetime, nowdate, random_string

from thinknxg_rental_marketplace.services import audit, availability, notifications, subscriptions
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid

VENDOR_TRANSITIONS = {
	"Draft": {"Submitted", "Deactivated"},
	"Submitted": {"Documents Pending", "Under Review", "Rejected", "Deactivated"},
	"Documents Pending": {"Under Review", "Submitted", "Rejected", "Deactivated"},
	"Under Review": {"Approved", "Rejected", "Documents Pending", "Deactivated"},
	"Approved": {"Suspended", "Deactivated"},
	"Rejected": {"Submitted", "Deactivated"},
	"Suspended": {"Approved", "Deactivated"},
	"Deactivated": {"Under Review"},
}
PROFILE_FIELDS = ("business_name", "business_type", "logo", "website", "description", "address_line1", "address_line2", "city", "state",
	"country", "pincode", "contact_person", "email", "phone", "registration_number", "tax_id", "years_in_business")
BANK_FIELDS = ("bank_name", "account_holder", "iban", "swift")
LISTING_FIELDS = ("title", "category", "cover_image", "allow_hire", "allow_sale", "allow_contract", "brand", "model", "condition",
	"manufacture_year", "uom", "total_qty", "min_order_qty", "weight_per_unit_kg", "currency", "daily_rate", "weekly_rate", "monthly_rate",
	"min_hire_days", "security_deposit_rate", "sale_price", "contract_monthly_rate", "min_contract_months", "delivery_available",
	"installation_available", "short_description", "description", "certifications", "warranty", "datasheet")


def slugify(text):
	return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:80] or random_string(8).lower()


def unique_route(doctype, base, name=None):
	route, n = base, 1
	while frappe.db.exists(doctype, {"route": route, "name": ["!=", name or ""]}):
		n += 1
		route = f"{base}-{n}"
	return route


def set_status(vendor, to, reason=None):
	v = frappe.get_doc("Marketplace Vendor", vendor)
	frm = v.status
	if to == frm:
		return v
	if to not in VENDOR_TRANSITIONS.get(frm, set()):
		fail("VENDOR_STATE", "Supplier cannot move from {frm} to {to}.", Conflict, frm=frm, to=to)
	updates = {"status": to, "status_reason": reason}
	if to == "Submitted":
		updates["submitted_on"] = now_datetime()
	if to == "Approved":
		updates.update(approved_on=now_datetime(), approved_by=frappe.session.user, verified=1)
	v.db_set(updates)
	audit.log("vendor.status", v.doctype, v.name, frm, to, reason=reason)
	if to == "Approved":
		subscriptions.start_trial(v.name)
	if to in ("Suspended", "Deactivated"):
		for l in frappe.get_all("Marketplace Listing", filters={"vendor": v.name, "status": "Published"}, pluck="name"):
			frappe.db.set_value("Marketplace Listing", l, "status", "Paused")
		for inv in frappe.get_all("Tender Invitation", filters={"vendor": v.name, "status": ["in", ["Invited", "Viewed", "Interested"]]}, pluck="name"):
			frappe.db.set_value("Tender Invitation", inv, "status", "Excluded")
	notifications.to_vendor(v.name, frappe._("Supplier account: {0}").format(to), reason or "", link="/marketplace/vendor/profile", category="Vendor", ref=v, min_role="Owner")
	return v


def submit_for_review(vctx):
	v = frappe.get_doc("Marketplace Vendor", vctx.vendor)
	missing = [f for f in ("business_name", "registration_number", "address_line1", "city", "country", "contact_person", "email", "phone") if not v.get(f)]
	if missing or not v.categories:
		fail("PROFILE_INCOMPLETE", "Complete the profile first: {m}", m=", ".join(missing + ([] if v.categories else ["categories"])))
	docs = frappe.db.count("Vendor Verification", {"vendor": v.name, "status": ["!=", "Rejected"]})
	to = "Under Review" if docs else "Documents Pending"
	if v.status in ("Draft", "Rejected"):
		set_status(v.name, "Submitted")
	if frappe.db.get_value("Marketplace Vendor", v.name, "status") in ("Submitted", "Documents Pending") and to == "Under Review":
		set_status(v.name, "Under Review")
	elif frappe.db.get_value("Marketplace Vendor", v.name, "status") == "Submitted":
		set_status(v.name, "Documents Pending")
	notifications.to_operators(frappe._("Supplier application: {0}").format(v.business_name), "", link=f"/marketplace/operator/vendors/{v.name}", category="Vendor", ref=v)
	return frappe.get_doc("Marketplace Vendor", v.name)


def update_profile(vctx, data):
	v = frappe.get_doc("Marketplace Vendor", vctx.vendor)
	if vctx.role not in ("Owner", "Manager"):
		forbid("VENDOR_ROLE", "Only owners and managers can edit the business profile.")
	locked = v.status in ("Under Review", "Approved", "Suspended")
	for f in PROFILE_FIELDS:
		if f in data:
			if locked and f in ("business_name", "registration_number", "tax_id", "country") and data.get(f) != v.get(f):
				fail("PROFILE_LOCKED", "Registered details change through the marketplace team once under review.")
			v.set(f, data.get(f))
	if vctx.role == "Owner":
		for f in BANK_FIELDS:
			if f in data:
				v.set(f, data.get(f))
	if "categories" in data:
		cats = [c for c in data.get("categories") or [] if frappe.db.exists("Marketplace Category", c)]
		v.set("categories", [{"category": c} for c in dict.fromkeys(cats)])
	if "locations" in data:
		v.set("locations", [])
		for l in data.get("locations") or []:
			if l.get("city") and l.get("country"):
				v.append("locations", {k: l.get(k) for k in ("location_name", "city", "state", "country", "delivery_radius_km", "is_head_office", "latitude", "longitude")})
	v.flags.ignore_permissions = True
	v.save()
	return v


def add_verification_document(vctx, document_type, file_url, document_number=None, expiry_date=None):
	# identical content shares a file_url, so always resolve the acting user's own unattached File row
	f = frappe.db.get_value("File", {"file_url": file_url, "owner": frappe.session.user, "attached_to_name": ["is", "not set"]},
		["name", "owner", "attached_to_name"], as_dict=True)
	if not f:
		forbid("FILE_FORBIDDEN", "Upload the document first.")
	d = frappe.get_doc({"doctype": "Vendor Verification", "vendor": vctx.vendor, "document_type": document_type, "attachment": file_url,
		"document_number": document_number, "expiry_date": expiry_date, "status": "Pending"})
	d.flags.ignore_permissions = True
	d.insert()
	frappe.db.set_value("File", f.name, {"attached_to_doctype": "Vendor Verification", "attached_to_name": d.name, "is_private": 1})
	if frappe.db.get_value("Marketplace Vendor", vctx.vendor, "status") == "Documents Pending":
		set_status(vctx.vendor, "Under Review")
	return d


def review_document(name, status, remarks=None):
	d = frappe.get_doc("Vendor Verification", name)
	d.db_set({"status": status, "reviewed_by": frappe.session.user, "reviewed_on": now_datetime(), "remarks": remarks})
	audit.log("vendor.document_reviewed", d.doctype, d.name, None, status)
	return d


def add_staff(vctx, email, full_name, vendor_role="Staff"):
	if vctx.role not in ("Owner", "Manager"):
		forbid("VENDOR_ROLE", "Only owners and managers can add users.")
	if vendor_role == "Owner" and vctx.role != "Owner":
		forbid("VENDOR_ROLE", "Only the owner can add another owner.")
	subscriptions.check_staff_limit(vctx.vendor)
	from thinknxg_rental_marketplace.services.registration import ensure_user

	u = ensure_user(email, full_name, "Marketplace Vendor")
	if frappe.db.exists("Vendor User", {"user": u}):
		fail("USER_LINKED", "This user already belongs to a supplier.", Conflict)
	vu = frappe.get_doc({"doctype": "Vendor User", "vendor": vctx.vendor, "user": u, "vendor_role": vendor_role, "enabled": 1})
	vu.flags.ignore_permissions = True
	vu.insert()
	audit.log("vendor.user_added", "Marketplace Vendor", vctx.vendor, user=u, role=vendor_role)
	return vu


# ------------------------------------------------------------------ listings
def validate_listing(doc):
	if flt(doc.total_qty) < 0:
		fail("LISTING_QTY", "Quantity cannot be negative.")
	if not (doc.allow_hire or doc.allow_sale or doc.allow_contract):
		fail("LISTING_MODE", "Offer the listing for hire, sale or contract.")
	cat = frappe.db.get_value("Marketplace Category", doc.category, ["allow_hire", "allow_sale", "allow_contract", "is_group"], as_dict=True)
	if not cat:
		fail("LISTING_CATEGORY", "Unknown category.")
	for mode in ("hire", "sale", "contract"):
		if doc.get("allow_" + mode) and not cat.get("allow_" + mode):
			fail("LISTING_MODE", "{m} is not offered in this category.", m=mode.capitalize())
	if doc.status == "Published":
		if doc.allow_hire and not (flt(doc.daily_rate) or flt(doc.weekly_rate) or flt(doc.monthly_rate)):
			fail("LISTING_RATE", "Set at least one hire rate.")
		if doc.allow_sale and not flt(doc.sale_price):
			fail("LISTING_RATE", "Set a sale price.")
		if doc.allow_contract and not flt(doc.contract_monthly_rate):
			fail("LISTING_RATE", "Set a contract monthly rate.")
		if flt(doc.total_qty) <= 0:
			fail("LISTING_QTY", "Published listings need a quantity.")
	for f in ("daily_rate", "weekly_rate", "monthly_rate", "sale_price", "contract_monthly_rate", "security_deposit_rate"):
		if flt(doc.get(f)) < 0:
			fail("LISTING_RATE", "Prices cannot be negative.")
	if not doc.route:
		doc.route = unique_route("Marketplace Listing", slugify(doc.title), doc.name)


def save_listing(vctx, data, name=None):
	if name:
		doc = frappe.get_doc("Marketplace Listing", name)
		if doc.vendor != vctx.vendor:
			forbid()
		if doc.status == "Suspended":
			fail("LISTING_SUSPENDED", "This listing was suspended by the marketplace.", Conflict)
	else:
		doc = frappe.new_doc("Marketplace Listing")
		doc.vendor = vctx.vendor
		doc.status = "Draft"
	for f in LISTING_FIELDS:
		if f in data:
			doc.set(f, data.get(f))
	if "item" in data:  # ERP item link only for ERP-connected vendors
		company = frappe.db.get_value("Marketplace Vendor", vctx.vendor, "erp_company")
		doc.item = data.get("item") if company and data.get("item") and frappe.db.exists("Item", data.get("item")) else None
	if "specifications" in data:
		doc.set("specifications", [{k: s.get(k) for k in ("attribute", "value", "unit")} for s in data.get("specifications") or [] if s.get("attribute") and s.get("value")])
	if "images" in data:
		doc.set("images", [{"image": i.get("image"), "caption": i.get("caption")} for i in data.get("images") or [] if i.get("image")])
	if name:
		peak = availability.peak_usage(availability._rows(doc.name, getdate(), availability.FAR_FUTURE), getdate(), availability.FAR_FUTURE)
		if flt(doc.total_qty) + 1e-9 < peak:
			fail("LISTING_QTY_ALLOCATED", "{peak} units are already allocated or blocked; quantity cannot go below that.", Conflict, peak=peak)
	validate_listing(doc)
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	availability.refresh_available_today(doc.name)
	return doc


def set_listing_status(vctx, name, status):
	doc = frappe.get_doc("Marketplace Listing", name)
	if doc.vendor != vctx.vendor:
		forbid()
	if status not in ("Published", "Paused", "Archived", "Draft"):
		fail("LISTING_STATUS", "Invalid status.")
	if doc.status == "Suspended":
		fail("LISTING_SUSPENDED", "This listing was suspended by the marketplace.", Conflict)
	if status == "Published":
		if frappe.db.get_value("Marketplace Vendor", vctx.vendor, "status") != "Approved":
			fail("VENDOR_NOT_APPROVED", "Listings can be published once your account is approved.", Conflict)
		subscriptions.check_listing_limit(vctx.vendor, exclude=doc.name)
	doc.status = status
	validate_listing(doc)
	doc.flags.ignore_permissions = True
	doc.save()
	audit.log("listing.status", doc.doctype, doc.name, None, status)
	return doc


def block_availability(vctx, listing, from_date, to_date, qty, entry_type="Blocked", remarks=None):
	doc = frappe.get_doc("Marketplace Listing", listing)
	if doc.vendor != vctx.vendor:
		forbid()
	if entry_type not in ("Blocked", "Maintenance"):
		fail("AVAILABILITY_TYPE", "Use Blocked or Maintenance.")
	if getdate(to_date) < getdate(from_date):
		fail("AVAILABILITY_DATES", "End date is before start date.")
	name = availability.allocate(listing, vctx.vendor, qty, from_date, to_date, None, entry_type)
	frappe.db.set_value("Listing Availability", name, "remarks", remarks)
	availability.refresh_available_today(listing)
	return name


def release_block(vctx, name):
	row = frappe.get_doc("Listing Availability", name)
	if row.vendor != vctx.vendor or row.booking:
		forbid("AVAILABILITY_FORBIDDEN", "Booking allocations are released by the booking itself.")
	row.db_set("status", "Released")
	availability.refresh_available_today(row.listing)

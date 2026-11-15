"""Customer rental requirements (Rental Request): validation per commercial model, creation, submission."""
import frappe
from frappe.utils import cint, date_diff, flt, getdate, now_datetime, nowdate

from thinknxg_rental_marketplace.services import audit, tender as tender_service
from thinknxg_rental_marketplace.services.context import settings
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid

HEADER_FIELDS = (
	"title", "transaction_type", "category", "required_from", "required_to", "extension_possible", "delivery_required",
	"expected_delivery_date", "delivery_terms", "contract_start", "contract_months", "expected_monthly_qty",
	"project_requirements", "project_site", "project_name", "site_address", "delivery_location", "city", "state", "country",
	"site_contact", "site_phone", "site_access", "special_requirements", "currency", "budget_min", "budget_max",
	"payment_terms_pref", "transport_required", "technical_support", "installation_required", "other_conditions",
)
ITEM_FIELDS = ("equipment_name", "category", "qty", "uom", "specifications", "condition_required", "brand_preference",
	"accept_alternatives", "certifications_required", "preferred_listing")
ATTACHMENT_TYPES = ("BOQ", "Equipment Schedule", "Technical Specification", "Drawing", "Site Plan", "Project Document", "Other")


def validate(doc, submitting=False):
	"""Called from the Rental Request controller (desk) and the API (portal)."""
	if doc.transaction_type not in ("Hire", "Sale", "Contract"):
		fail("REQ_TYPE", "Choose Hire, Sale or Contract.")
	if not doc.items:
		fail("REQ_ITEMS", "Add at least one equipment line.")
	for i in doc.items:
		if flt(i.qty) <= 0:
			fail("REQ_QTY", "Row {idx}: quantity must be greater than zero.", idx=i.idx)
		if not i.equipment_name:
			fail("REQ_ITEM_NAME", "Row {idx}: equipment name is required.", idx=i.idx)
		i.category = i.category or doc.category
	if flt(doc.budget_min) and flt(doc.budget_max) and flt(doc.budget_min) > flt(doc.budget_max):
		fail("REQ_BUDGET", "Minimum budget cannot exceed maximum budget.")
	today = getdate(nowdate())
	if doc.transaction_type == "Hire":
		if not doc.required_from or not doc.required_to:
			fail("REQ_DATES", "Rental start and expected return dates are required for hire.")
		if getdate(doc.required_to) < getdate(doc.required_from):
			fail("REQ_DATES", "Expected return date cannot be before the start date.")
		if submitting and getdate(doc.required_from) < today:
			fail("REQ_DATES", "Rental start date cannot be in the past.")
		doc.duration_days = date_diff(doc.required_to, doc.required_from) + 1
	elif doc.transaction_type == "Sale":
		if not doc.expected_delivery_date:
			fail("REQ_DATES", "Expected delivery date is required for a purchase.")
		if submitting and getdate(doc.expected_delivery_date) < today:
			fail("REQ_DATES", "Expected delivery date cannot be in the past.")
		doc.required_from = doc.required_to = None
	else:
		if not doc.contract_start or cint(doc.contract_months) < 1:
			fail("REQ_CONTRACT", "Contract start and duration (months) are required.")
		if submitting and getdate(doc.contract_start) < today:
			fail("REQ_DATES", "Contract start cannot be in the past.")
	cat = frappe.db.get_value("Marketplace Category", doc.category, ["allow_hire", "allow_sale", "allow_contract"], as_dict=True)
	if not cat:
		fail("REQ_CATEGORY", "Unknown equipment category.")
	if not cat.get("allow_" + doc.transaction_type.lower()):
		fail("REQ_CATEGORY", "{t} is not offered for this category.", t=doc.transaction_type)
	doc.currency = doc.currency or settings().default_currency


def _clean(data, fields):
	return {k: data.get(k) for k in fields if k in data}


def _attach(doc, attachments, customer):
	"""Only private files uploaded by the acting user (or already attached to this request) may be referenced."""
	for a in attachments or []:
		url = a.get("file")
		fields = ["name", "owner", "is_private", "attached_to_doctype", "attached_to_name"]
		f = (doc.name and frappe.db.get_value("File", {"file_url": url, "attached_to_doctype": "Rental Request", "attached_to_name": doc.name}, fields, as_dict=True)) \
			or frappe.db.get_value("File", {"file_url": url, "owner": frappe.session.user, "attached_to_name": ["is", "not set"]}, fields, as_dict=True)
		if not f:
			forbid("FILE_FORBIDDEN", "You can only attach files you uploaded.")
		if not f.is_private:
			frappe.db.set_value("File", f.name, "is_private", 1)
		doc.append("attachments", {"document_type": a.get("document_type") if a.get("document_type") in ATTACHMENT_TYPES else "Other",
			"title": (a.get("title") or "")[:140], "file": url, "share_with_suppliers": cint(a.get("share_with_suppliers", 1))})


def _link_files(doc):
	for a in doc.attachments:
		f = frappe.db.get_value("File", {"file_url": a.file, "owner": frappe.session.user, "attached_to_name": ["is", "not set"]}, "name")
		if f:
			frappe.db.set_value("File", f, {"attached_to_doctype": "Rental Request", "attached_to_name": doc.name, "is_private": 1})


def save(ctx, data, name=None):
	"""Create or update a Draft request for the acting customer. Returns the doc."""
	if name:
		doc = frappe.get_doc("Rental Request", name)
		if doc.customer != ctx.customer:
			forbid()
		if doc.status != "Draft":
			fail("REQ_LOCKED", "Only draft requests can be edited.", Conflict)
		doc.set("items", [])
		doc.set("attachments", [])
	else:
		key = data.get("idempotency_key")
		if key:
			existing = frappe.db.get_value("Rental Request", {"idempotency_key": key, "customer": ctx.customer}, "name")
			if existing:
				return frappe.get_doc("Rental Request", existing)
		doc = frappe.new_doc("Rental Request")
		doc.customer = ctx.customer
		doc.requested_by = frappe.session.user
		doc.status = "Draft"
		doc.idempotency_key = key
	doc.update(_clean(data, HEADER_FIELDS))
	if doc.project_site:
		site = frappe.db.get_value("Customer Project Site", doc.project_site, ["customer", "project_name", "site_address", "city", "state", "country", "site_contact", "site_phone", "site_access"], as_dict=True)
		if not site or site.customer != ctx.customer:
			forbid("SITE_FORBIDDEN", "Project site not found.")
		for k, v in site.items():
			if k != "customer" and not doc.get(k):
				doc.set(k, v)
	for it in data.get("items") or []:
		row = _clean(it, ITEM_FIELDS)
		if row.get("preferred_listing") and frappe.db.get_value("Marketplace Listing", row["preferred_listing"], "status") != "Published":
			row["preferred_listing"] = None
		doc.append("items", row)
	_attach(doc, data.get("attachments"), ctx.customer)
	validate(doc)
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	_link_files(doc)
	audit.log("request.saved", doc.doctype, doc.name, None, doc.status)
	return doc


def submit(ctx, name):
	doc = frappe.get_doc("Rental Request", name)
	if doc.customer != ctx.customer:
		forbid()
	if doc.status != "Draft":
		fail("REQ_STATE", "This request was already submitted.", Conflict)
	validate(doc, submitting=True)
	doc.status = "Submitted"
	doc.submitted_on = now_datetime()
	doc.flags.ignore_permissions = True
	doc.save()
	audit.log("request.submitted", doc.doctype, doc.name, "Draft", "Submitted")
	t = tender_service.create_from_request(doc)
	doc.db_set("tender", t.name)
	if settings().auto_publish_tenders:
		tender_service.publish(t.name)
	else:
		from thinknxg_rental_marketplace.services import notifications

		notifications.to_operators(frappe._("Tender awaiting moderation: {0}").format(t.name), doc.title, link=f"/marketplace/operator/tenders/{t.name}", ref=t)
	return doc.reload() or doc


def cancel(ctx, name, reason=None):
	doc = frappe.get_doc("Rental Request", name)
	if doc.customer != ctx.customer:
		forbid()
	if doc.status in ("Booked", "Closed", "Cancelled"):
		fail("REQ_STATE", "This request can no longer be cancelled.", Conflict)
	if doc.tender and frappe.db.get_value("Marketplace Tender", doc.tender, "status") not in ("Cancelled", "Expired"):
		tender_service.cancel(doc.tender, reason or "Cancelled by customer")
	frappe.db.set_value("Rental Request", name, {"status": "Cancelled", "cancel_reason": reason})
	audit.log("request.cancelled", "Rental Request", name, doc.status, "Cancelled", reason=reason)

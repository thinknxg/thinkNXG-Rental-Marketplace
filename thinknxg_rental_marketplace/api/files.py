"""Secure uploads and downloads for portal users.

Uploads: private by default; only images may be public (listing gallery, logo). Size and type whitelisted.
Downloads: marketplace-level access check on the document the file is attached to — Frappe's default private
file check would refuse portal users (they hold no DocType permissions), so this endpoint is the only path.
"""
import mimetypes
import os

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from thinknxg_rental_marketplace.services import context, offers, tender as tender_service
from thinknxg_rental_marketplace.services.errors import fail, forbid

MAX_BYTES = 15 * 1024 * 1024
DOC_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".dwg", ".dxf", ".zip", ".png", ".jpg", ".jpeg", ".webp", ".txt"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=60, seconds=600)
def upload(public=0):
	context.require_login()
	f = frappe.request.files.get("file")
	if not f:
		fail("FILE_REQUIRED", "Choose a file to upload.")
	name = os.path.basename(f.filename or "upload")
	ext = os.path.splitext(name)[1].lower()
	public = cint(public)
	if ext not in (IMG_EXT if public else DOC_EXT):
		fail("FILE_TYPE", "This file type is not allowed.")
	if public and ext == ".svg":
		fail("FILE_TYPE", "SVG images are not accepted.")
	content = f.stream.read(MAX_BYTES + 1)
	if len(content) > MAX_BYTES:
		fail("FILE_SIZE", "Files must be 15 MB or smaller.")
	if public and not (context.vendor_membership() or context.is_operator()):
		forbid("FILE_PUBLIC", "Only suppliers can publish images.")
	doc = frappe.get_doc({"doctype": "File", "file_name": name, "content": content, "is_private": 0 if public else 1})
	doc.flags.ignore_permissions = True
	doc.save()
	return {"file_url": doc.file_url, "file_name": doc.file_name, "name": doc.name, "is_private": doc.is_private}


def can_access(file_doc, user):
	if file_doc.owner == user and not file_doc.attached_to_name:
		return True
	if context.is_operator(u=user):
		return True
	dt, dn = file_doc.attached_to_doctype, file_doc.attached_to_name
	cm, vm = context.customer_membership(user), context.vendor_membership(user)
	if dt == "Rental Request":
		req = frappe.db.get_value("Rental Request", dn, ["customer", "tender"], as_dict=True)
		if not req:
			return False
		if cm and cm.customer == req.customer:
			return True
		if vm and req.tender:
			shared = frappe.db.exists("Request Attachment", {"parent": dn, "parenttype": "Rental Request", "file": file_doc.file_url, "share_with_suppliers": 1})
			t = frappe.get_doc("Marketplace Tender", req.tender)
			return bool(shared and tender_service.vendor_access(t, vm.vendor, create=False))
		return False
	if dt == "Supplier Offer":
		o = frappe.db.get_value("Supplier Offer", dn, ["vendor", "customer", "status"], as_dict=True)
		return bool(o and ((vm and vm.vendor == o.vendor) or (cm and cm.customer == o.customer and o.status not in ("Draft",))))
	if dt == "Vendor Verification":
		v = frappe.db.get_value("Vendor Verification", dn, "vendor")
		return bool(vm and vm.vendor == v and vm.vendor_role in ("Owner", "Manager"))
	if dt == "Marketplace Dispute":
		b = frappe.db.get_value("Marketplace Dispute", dn, "booking")
		bk = frappe.db.get_value("Marketplace Booking", b, ["customer", "vendor"], as_dict=True)
		return bool(bk and ((cm and cm.customer == bk.customer) or (vm and vm.vendor == bk.vendor)))
	return False


@frappe.whitelist()
def download(file_url):
	context.require_login()
	names = frappe.get_all("File", filters={"file_url": file_url}, pluck="name")
	if not names:
		fail("NOT_FOUND", "File not found.")
	# identical uploads share one stored file; access via any File row the user may see is access to that content
	docs = [frappe.get_doc("File", n) for n in names]
	f = next((d for d in docs if not d.is_private or can_access(d, frappe.session.user)), None)
	if not f:
		forbid("FILE_FORBIDDEN", "You do not have access to this file.")
	frappe.local.response.filename = f.file_name
	frappe.local.response.filecontent = f.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline" if (mimetypes.guess_type(f.file_name)[0] or "").startswith(("image/", "application/pdf")) else "attachment"

"""Optional bridge into thinkNXG Rental (thinknxg_rental) and ERPNext.

No import of thinknxg_rental at module load: everything is resolved at call time and only when the app is
installed, Marketplace Settings → *Use thinkNXG Rental engine* is on, and the vendor has an ERP company.

Booking confirmed (ERP-connected vendor)
  Hire / Contract + thinknxg_rental + every line linked to an Item → ERPNext Customer, Rental Site, draft Hire Order
  Sale (or Hire without thinknxg_rental) + Items                   → draft Sales Order
  otherwise                                                        → marketplace-native fulfilment
Status flows back through doc_events (see hooks.py) on Hire Order, Rental Contract, Hire Delivery Order,
Hire Off-Hire Note, Sales Order and Delivery Note.
"""
import frappe
from frappe.utils import cint, getdate, nowdate

from thinknxg_rental_marketplace.services import audit


def rental_app_available():
	return "thinknxg_rental" in frappe.get_installed_apps() and bool(frappe.db.exists("DocType", "Hire Order"))


def ensure_erp_customer(mc_name, company):
	mc = frappe.get_doc("Marketplace Customer", mc_name)
	if mc.erp_customer and frappe.db.exists("Customer", mc.erp_customer):
		return mc.erp_customer
	existing = frappe.db.get_value("Customer", {"customer_name": mc.company_name or mc.customer_name}, "name")
	if existing:
		mc.db_set("erp_customer", existing)
		return existing
	c = frappe.get_doc({"doctype": "Customer", "customer_name": mc.company_name or mc.customer_name,
		"customer_type": "Company" if mc.customer_type == "Company" else "Individual",
		"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
		"territory": frappe.db.get_single_value("Selling Settings", "territory") or frappe.db.get_value("Territory", {"is_group": 0}, "name"),
		"email_id": mc.email, "mobile_no": mc.phone})
	c.flags.ignore_permissions = True
	c.insert()
	mc.db_set("erp_customer", c.name)
	return c.name


def on_booking_confirmed(booking_name):
	s = frappe.get_cached_doc("Marketplace Settings")
	b = frappe.get_doc("Marketplace Booking", booking_name)
	company = frappe.db.get_value("Marketplace Vendor", b.vendor, "erp_company")
	if not (s.use_rental_engine and s.auto_create_erp_documents and company):
		return None
	items = [i for i in b.items]
	if not items or any(not i.item_code for i in items):
		frappe.db.set_value("Vendor Order", b.vendor_order, "erp_status", "Not linked: listings without ERP Item")
		return None
	customer = ensure_erp_customer(b.customer, company)
	b.db_set({"erp_company": company, "erp_customer": customer})
	if b.transaction_type in ("Hire", "Contract") and rental_app_available():
		ref = _make_hire_order(b, company, customer)
		mode = "thinkNXG Rental"
	else:
		ref = _make_sales_order(b, company, customer)
		mode = "ERPNext Sales"
	b.db_set({"erp_reference_doctype": ref.doctype, "erp_reference": ref.name})
	frappe.db.set_value("Vendor Order", b.vendor_order, {"fulfilment_mode": mode, "erp_reference_doctype": ref.doctype,
		"erp_reference": ref.name, "erp_status": "Draft"})
	audit.log("bridge.created", b.doctype, b.name, erp_doctype=ref.doctype, erp_name=ref.name)
	return ref


def _make_hire_order(b, company, customer):
	site_name = f"{(b.project_name or 'Site')[:80]} · {b.name}"
	if not frappe.db.exists("Rental Site", site_name):
		site = frappe.get_doc({"doctype": "Rental Site", "site_name": site_name, "customer": customer, "company": company,
			"location": b.site_address, "site_contact": None})
		site.flags.ignore_permissions = True
		site.insert()
	ho = frappe.get_doc({"doctype": "Hire Order", "company": company, "customer": customer, "rental_site": site_name,
		"order_date": nowdate(), "customer_reference": b.name, "required_from": b.start_date, "expected_return_date": b.end_date,
		"rate_basis": (b.items[0].rate_basis if b.items[0].rate_basis in ("Daily", "Weekly", "Monthly") else "Monthly"),
		"billing_cycle": "Monthly", "remarks": f"thinkNXG Rental Marketplace booking {b.name}",
		"items": [{"item_code": i.item_code, "qty": i.qty, "uom": i.uom, "rate_basis": i.rate_basis if i.rate_basis in ("Daily", "Weekly", "Monthly") else "Monthly",
			"rate": i.unit_rate} for i in b.items]})
	ho.flags.ignore_permissions = True
	ho.insert()
	return ho


def _make_sales_order(b, company, customer):
	so = frappe.get_doc({"doctype": "Sales Order", "company": company, "customer": customer, "transaction_date": nowdate(),
		"delivery_date": b.delivery_date or nowdate(), "po_no": b.name, "currency": b.currency,
		"items": [{"item_code": i.item_code, "qty": i.qty, "uom": i.uom, "rate": i.unit_rate if b.transaction_type == "Sale" else (i.amount / (i.qty or 1)),
			"delivery_date": b.delivery_date or nowdate()} for i in b.items]})
	so.flags.ignore_permissions = True
	so.insert()
	return so


# ------------------------------------------------------------------ inbound doc_events (inert when the doctypes don't exist)
def _booking_for(doctype, name):
	return frappe.db.get_value("Vendor Order", {"erp_reference_doctype": doctype, "erp_reference": name}, ["name", "booking"], as_dict=True)


def _advance(vo, erp_status, to=None):
	frappe.db.set_value("Vendor Order", vo.name, "erp_status", erp_status)
	if not to:
		return
	from thinknxg_rental_marketplace.services import fulfilment

	status = frappe.db.get_value("Marketplace Booking", vo.booking, "status")
	if to in fulfilment.FLOWS[frappe.db.get_value("Marketplace Booking", vo.booking, "transaction_type")].get(status, set()):
		fulfilment.transition(vo.booking, to, "Operator")


def hire_order_submitted(doc, method=None):
	vo = _booking_for("Hire Order", doc.name)
	if vo:
		_advance(vo, "Hire Order submitted")


def rental_contract_submitted(doc, method=None):
	if getattr(doc, "source_type", None) == "Hire Order":
		vo = _booking_for("Hire Order", doc.source_document)
		if vo:
			_advance(vo, f"Rental Contract {doc.name} active")


def _vo_from_contract(rental_contract):
	src = frappe.db.get_value("Rental Contract", rental_contract, ["source_type", "source_document"], as_dict=True) if rental_contract else None
	return _booking_for("Hire Order", src.source_document) if src and src.source_type == "Hire Order" else None


def hire_delivery_submitted(doc, method=None):
	vo = _vo_from_contract(getattr(doc, "rental_contract", None))
	if vo:
		ttype = frappe.db.get_value("Marketplace Booking", vo.booking, "transaction_type")
		_advance(vo, f"Delivered by {doc.name}", "Dispatched" if ttype == "Hire" else "Mobilized")


def off_hire_submitted(doc, method=None):
	vo = _vo_from_contract(getattr(doc, "rental_contract", None))
	if vo:
		frappe.db.set_value("Vendor Order", vo.name, "erp_status", f"Off-hire {doc.name}")


def sales_order_submitted(doc, method=None):
	vo = _booking_for("Sales Order", doc.name)
	if vo:
		_advance(vo, "Sales Order submitted")


def delivery_note_submitted(doc, method=None):
	for so in {i.against_sales_order for i in doc.items if getattr(i, "against_sales_order", None)}:
		vo = _booking_for("Sales Order", so)
		if vo:
			_advance(vo, f"Delivery Note {doc.name}", "Dispatched")

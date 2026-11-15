"""Bridge into thinkNXG Rental / ERPNext. Skipped when thinknxg_rental is not installed on the site."""
import unittest

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from thinknxg_rental_marketplace.services import booking, rental_bridge, requests, vendors
from thinknxg_rental_marketplace.tests.test_flow import (
	SFX, as_user, close, customer_ctx, make_customer, make_vendor, offer_for, pay_all_pending, vendor_ctx,
)


def _ensure(doctype, name, **fields):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **fields}).insert(ignore_permissions=True)
	return name


class TestRentalBridge(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		as_user("Administrator")
		cls.company = frappe.db.get_value("Company", {}, "name")
		if not rental_bridge.rental_app_available() or not cls.company:
			raise unittest.SkipTest("thinknxg_rental or a Company is not available on this site")
		frappe.db.set_single_value("Marketplace Settings", {"use_rental_engine": 1, "auto_create_erp_documents": 1, "auto_publish_tenders": 1})
		frappe.clear_document_cache("Marketplace Settings", "Marketplace Settings")
		_ensure("Item Group", "MP Equipment", item_group_name="MP Equipment", parent_item_group="All Item Groups", is_group=0)
		_ensure("Customer Group", "MP Customers", customer_group_name="MP Customers", parent_customer_group="All Customer Groups", is_group=0)
		_ensure("Territory", "MP Oman", territory_name="MP Oman", parent_territory="All Territories", is_group=0)
		frappe.db.set_single_value("Selling Settings", {"customer_group": "MP Customers", "territory": "MP Oman"})
		cls.item = _ensure("Item", f"MP-CUP-{SFX}", item_code=f"MP-CUP-{SFX}", item_name="Cuplock standard 3m", item_group="MP Equipment",
			stock_uom="Nos", is_stock_item=1)
		cls.v, cls.ev = make_vendor("erpco", ["Scaffolding"])
		frappe.db.set_value("Marketplace Vendor", cls.v.name, "erp_company", cls.company)
		ctx = vendor_ctx(cls.ev)
		l = vendors.save_listing(ctx, {"title": "Cuplock 3m (ERP)", "category": "Cuplock Scaffolding", "uom": "Nos", "total_qty": 2000,
			"currency": "OMR", "allow_hire": 1, "monthly_rate": 1.1, "item": cls.item})
		vendors.set_listing_status(ctx, l.name, "Published")
		cls.listing = l.name
		cls.c, cls.ec = make_customer("erpbuyer")
		as_user("Administrator")

	def tearDown(self):
		as_user("Administrator")

	def test_confirmed_hire_becomes_hire_order_and_status_flows_back(self):
		self.assertEqual(frappe.db.get_value("Marketplace Listing", self.listing, "item"), self.item)
		cctx = customer_ctx(self.ec)
		req = requests.save(cctx, {"title": "ERP hire", "transaction_type": "Hire", "category": "Cuplock Scaffolding",
			"required_from": add_days(getdate(), 10), "required_to": add_days(getdate(), 69), "project_name": "Bridge Tower",
			"site_address": "Plot 1, Duqm", "city": "Duqm", "country": "Oman", "items": [{"equipment_name": "Cuplock 3m", "qty": 500, "uom": "Nos"}]})
		req = requests.submit(cctx, req.name)
		o = offer_for(self.ev, req.tender, 1.0, self.listing)
		close(req.tender)
		b = booking.accept_offer(customer_ctx(self.ec), o.name)
		pay_all_pending(b.name, self.ec)
		as_user("Administrator")
		b.reload()
		self.assertEqual(b.status, "Confirmed")
		vo = frappe.get_doc("Vendor Order", b.vendor_order)
		self.assertEqual(vo.fulfilment_mode, "thinkNXG Rental")
		self.assertEqual(vo.erp_reference_doctype, "Hire Order")
		ho = frappe.get_doc("Hire Order", vo.erp_reference)
		self.assertEqual(ho.company, self.company)
		self.assertEqual(ho.customer, b.erp_customer)
		self.assertEqual(ho.customer_reference, b.name)
		self.assertEqual(ho.items[0].item_code, self.item)
		self.assertEqual(ho.items[0].qty, 500)
		self.assertEqual(frappe.db.get_value("Rental Site", ho.rental_site, "customer"), b.erp_customer)
		# the rental team continues in thinkNXG Rental; submission flows back to the marketplace
		ho.submit()
		self.assertEqual(frappe.db.get_value("Vendor Order", vo.name, "erp_status"), "Hire Order submitted")
		from thinknxg_rental.thinknxg_rental.doctype.hire_order.hire_order import make_contract, make_reservation

		rc = make_contract(ho.name)
		self.assertEqual(rc.source_document, ho.name)
		rmr = make_reservation(ho.name)
		self.assertEqual(rmr.items[0].required_qty, 500)

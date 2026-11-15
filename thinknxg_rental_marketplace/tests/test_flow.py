"""End-to-end marketplace workflow against a real Frappe v16 + ERPNext v16 site.

POST REQUIREMENT → TENDER → MATCH → OFFERS → COMPARE → SELECT → BOOK → PAY → FULFIL → SETTLE → REVIEW,
plus isolation, confidentiality, deadlines, revisions, availability, subscriptions, commission, webhooks.
"""
import hashlib
import hmac
import json
import time

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, getdate, now_datetime

from thinknxg_rental_marketplace.services import (
	availability, booking, evaluation, fulfilment, offers, payments, registration, requests, settlement, subscriptions,
	tender as tender_service, trust, vendors,
)
from thinknxg_rental_marketplace.services.context import require_customer, require_vendor
from thinknxg_rental_marketplace.services.errors import MarketplaceError

SFX = frappe.generate_hash(length=5)


def as_user(user):
	frappe.set_user(user)


def vendor_ctx(user):
	as_user(user)
	return require_vendor()


def customer_ctx(user):
	as_user(user)
	return require_customer()


def make_vendor(key, cats, country="Oman", city="Muscat"):
	as_user("Guest")
	email = f"{key}-{SFX}@vendor.test"
	v = registration.register_vendor({"business_name": f"{key.title()} Scaffolding {SFX}", "business_type": "Scaffolding Rental",
		"country": country, "city": city, "state": "Muscat", "address_line1": "Industrial Area", "contact_person": f"{key} Owner",
		"email": email, "phone": "+968 9000 0000", "registration_number": f"CR-{key}-{SFX}", "categories": cats, "accept_terms": 1})
	as_user(email)
	f = frappe.get_doc({"doctype": "File", "file_name": f"cr-{key}.txt", "content": b"Commercial registration certificate", "is_private": 1})
	f.insert(ignore_permissions=True)
	vendors.add_verification_document(require_vendor(active=False), "Commercial Registration", f.file_url, "CR1")
	as_user("Administrator")
	vendors.set_status(v.name, "Approved")
	return frappe.get_doc("Marketplace Vendor", v.name), email


def make_listing(email, title, category, qty, **kw):
	ctx = vendor_ctx(email)
	data = {"title": title, "category": category, "uom": "Nos", "total_qty": qty, "currency": "OMR", "allow_hire": 1,
		"monthly_rate": 1.2, "daily_rate": 0.08, "security_deposit_rate": 0.5, **kw}
	l = vendors.save_listing(ctx, data)
	vendors.set_listing_status(ctx, l.name, "Published")
	return l.name


def make_customer(key):
	as_user("Guest")
	email = f"{key}-{SFX}@customer.test"
	c = registration.register_customer({"customer_type": "Company", "company_name": f"{key.title()} Contracting {SFX}", "full_name": f"{key} Buyer",
		"email": email, "country": "Oman", "city": "Muscat", "accept_terms": 1})
	return c.name, email


def hire_request(email, qty=800, category="Cuplock Scaffolding", start=5, days=45, **kw):
	ctx = customer_ctx(email)
	data = {"title": f"Cuplock for tower {frappe.generate_hash(length=4)}", "transaction_type": "Hire", "category": category,
		"required_from": add_days(getdate(), start), "required_to": add_days(getdate(), start + days - 1), "project_name": "Tower A",
		"site_address": "Plot 12, Bausher", "city": "Muscat", "state": "Muscat", "country": "Oman", "site_contact": "Site Eng", "site_phone": "+968 1",
		"items": [{"equipment_name": "Cuplock standard 3m", "qty": qty, "uom": "Nos", "specifications": "Galvanised"}], **kw}
	req = requests.save(ctx, data)
	return requests.submit(ctx, req.name)


def offer_for(email, tender, rate, listing, qty=None, deposit=100, **kw):
	ctx = vendor_ctx(email)
	t = frappe.get_doc("Marketplace Tender", tender)
	item = t.items[0]
	o = offers.save_draft(ctx, tender, {"delivery_date": t.required_from or t.contract_start or t.expected_delivery_date, "availability_confirmed": 1,
		"payment_terms": "20% advance", "security_deposit": deposit, "transport_charges": 50, "tax_percent": 5,
		"items": [{"tender_item": item.name, "listing": listing, "qty": qty or item.qty, "unit_rate": rate, "rate_basis": kw.pop("rate_basis", "Monthly")}], **kw})
	return offers.submit(ctx, o.name)


def close(tender):
	as_user("Administrator")
	frappe.db.set_value("Marketplace Tender", tender, "submission_deadline", add_to_date(now_datetime(), minutes=-1))
	tender_service.process_deadlines()


def pay_all_pending(booking_name, customer_email):
	b = frappe.get_doc("Marketplace Booking", booking_name)
	as_user(customer_email)
	pending = [r.name for r in b.schedule if r.status == "Pending"]
	if pending:
		payments.request_lines(b, pending)
	as_user("Administrator")
	for p in frappe.get_all("Marketplace Payment", filters={"booking": booking_name, "status": "Pending"}, pluck="name"):
		payments.mark_succeeded(p, "BANK-REF", source="finance")


class TestMarketplaceFlow(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		as_user("Administrator")
		frappe.db.set_single_value("Marketplace Settings", {"auto_publish_tenders": 1, "default_visibility": "Verified Suppliers",
			"default_tender_type": "Open", "min_match_score": 30, "payment_gateway": "Manual", "default_deposit_percent": 20,
			"default_commission_rate": 5, "default_commission_basis": "Percentage", "subscription_required": 1})
		frappe.clear_document_cache("Marketplace Settings", "Marketplace Settings")
		cls.va, cls.ea = make_vendor("alpha", ["Scaffolding"])
		cls.vb, cls.eb = make_vendor("bravo", ["Cuplock Scaffolding", "Props"])
		cls.vc, cls.ec = make_vendor("charlie", ["Scaffolding"])
		cls.vd, cls.ed = make_vendor("delta", ["Formwork"], country="United Arab Emirates", city="Dubai")
		cls.la = make_listing(cls.ea, "Cuplock standard 3m (A)", "Cuplock Scaffolding", 1000)
		cls.lb = make_listing(cls.eb, "Cuplock standard 3m (B)", "Cuplock Scaffolding", 900)
		cls.lc = make_listing(cls.ec, "Cuplock standard 3m (C)", "Cuplock Scaffolding", 300)
		cls.c1, cls.e1 = make_customer("one")
		cls.c2, cls.e2 = make_customer("two")
		as_user("Administrator")

	def tearDown(self):
		as_user("Administrator")

	# ---------------------------------------------------------------- the main hire journey
	def test_01_hire_end_to_end(self):
		req = hire_request(self.e1)
		self.assertEqual(req.status, "Tendered")
		t = frappe.get_doc("Marketplace Tender", req.tender)
		self.assertEqual(t.status, "Bidding Open")
		invited = set(frappe.get_all("Tender Invitation", filters={"tender": t.name}, pluck="vendor"))
		self.assertTrue({self.va.name, self.vb.name, self.vc.name} <= invited, "eligible suppliers invited")
		self.assertNotIn(self.vd.name, invited, "wrong country/category not invited")
		scores = {i.vendor: i.match_score for i in frappe.get_all("Tender Invitation", filters={"tender": t.name}, fields=["vendor", "match_score"])}
		self.assertGreater(scores[self.va.name], scores[self.vc.name], "free quantity beats category-only coverage")

		# supplier view hides customer identity and site address before award
		view = offers.tender_for_vendor(t, self.vb.name)
		self.assertFalse(view["customer_disclosed"])
		self.assertNotIn("Bausher", json.dumps(view, default=str))

		oa = offer_for(self.ea, t.name, 1.30, self.la)
		ob = offer_for(self.eb, t.name, 1.10, self.lb)
		as_user(self.ec)
		offers.respond_invitation(t, self.vc.name, "decline", "No stock")

		# revision keeps history
		oa2 = offer_for(self.ea, t.name, 1.05, self.la)
		self.assertEqual(oa2.revision_no, 2)
		revs = frappe.get_all("Offer Revision", filters={"offer": oa.name}, fields=["revision_no", "grand_total"], order_by="revision_no")
		self.assertEqual([r.revision_no for r in revs], [1, 2])
		self.assertGreater(revs[0].grand_total, revs[1].grand_total)

		# server computes totals: 800 × 1.05 × 45/30 = 1260 + 50 transport → ×1.05 tax = 1375.5
		self.assertAlmostEqual(oa2.grand_total, 1375.5, places=3)

		# sealed: customer sees nothing while bidding is open, and cannot accept yet
		c1 = customer_ctx(self.e1)
		self.assertTrue(evaluation.compare(c1, t.name).get("sealed"))
		with self.assertRaisesRegex(MarketplaceError, "BIDDING_OPEN"):
			booking.accept_offer(c1, oa2.name)

		# suppliers never see each other's offers
		vb_ctx = vendor_ctx(self.eb)
		self.assertNotIn("1.05", json.dumps(offers.vendor_offer_view(offers.get_offer(t, self.vb.name), t), default=str))
		with self.assertRaises(frappe.PermissionError):
			offers.submit(vb_ctx, oa2.name)

		# clarification round-trip recorded against tender & offer
		c = evaluation.raise_clarification("Customer", t.name, "Galvanising spec?", "Confirm hot-dip", offer=None, vendor=self.va.name)
		as_user(self.ea)
		evaluation.respond_clarification("Supplier", c.name, "Hot-dip galvanised, EN 12811")
		self.assertEqual(frappe.db.get_value("Tender Clarification", c.name, "status"), "Answered")

		# deadline enforcement
		close(t.name)
		self.assertEqual(frappe.db.get_value("Marketplace Tender", t.name, "status"), "Evaluation")
		with self.assertRaisesRegex(MarketplaceError, "TENDER_CLOSED"):
			offer_for(self.ea, t.name, 0.9, self.la)

		cmp = evaluation.compare(customer_ctx(self.e1), t.name)
		self.assertEqual(len(cmp["offers"]), 2)
		lowest = [o for o in cmp["offers"] if "Lowest comparable price" in (o.get("flags") or [])]
		self.assertEqual(lowest[0]["name"], oa2.name)
		evaluation.shortlist(customer_ctx(self.e1), ob.name)

		# accept → booking, idempotent, no second award
		b = booking.accept_offer(customer_ctx(self.e1), oa2.name, idempotency_key=f"k-{SFX}")
		self.assertEqual(b.status, "Pending Payment")
		self.assertEqual(booking.accept_offer(customer_ctx(self.e1), oa2.name, idempotency_key=f"k-{SFX}").name, b.name)
		with self.assertRaisesRegex(MarketplaceError, "ALREADY_AWARDED|TENDER_STATE"):
			booking.accept_offer(customer_ctx(self.e1), ob.name)
		self.assertEqual(frappe.db.get_value("Supplier Offer", ob.name, "status"), "Not Awarded")
		self.assertEqual(frappe.db.get_value("Marketplace Tender", t.name, "status"), "Awarded")
		from thinknxg_rental_marketplace.services.money import q

		self.assertEqual(q(b.commission_amount, b.currency), q(q(b.grand_total, b.currency) * q("0.05", b.currency), b.currency))
		self.assertEqual(availability.available_qty(self.la, t.required_from, t.required_to), 200)

		# booking snapshot = accepted revision, immutable
		self.assertEqual(json.loads(b.snapshot)["offer"]["revision_no"], 2)

		# isolation: other vendor and other customer cannot read the booking through the portal API
		from thinknxg_rental_marketplace.api import customer as capi, vendor as vapi

		as_user(self.eb)
		with self.assertRaises(frappe.PermissionError):
			vapi.booking_get(b.name)
		as_user(self.e2)
		with self.assertRaises(frappe.PermissionError):
			capi.booking_get(b.name)
		with self.assertRaises(frappe.PermissionError):
			capi.request_get(req.name)
		# portal users hold no DocType permissions → generic document APIs are closed
		as_user(self.ea)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list("Supplier Offer", fields=["name", "grand_total"])
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Marketplace Booking", b.name).check_permission("read")

		# payment (manual: Finance confirms) → confirmed
		pay_all_pending(b.name, self.e1)
		as_user("Administrator")
		b.reload()
		self.assertEqual(b.status, "Confirmed")
		self.assertEqual(frappe.db.get_value("Rental Request", req.name, "status"), "Booked")

		# fulfilment: hire flow with off-hire, damage charge, completion gate
		with self.assertRaises(frappe.PermissionError):
			fulfilment.transition(b.name, "Dispatched", "Customer")  # only the supplier dispatches
		fulfilment.transition(b.name, "Dispatched", "Vendor", {"vehicle_details": "Truck 12"})
		fulfilment.transition(b.name, "On Hire", "Customer")
		fulfilment.transition(b.name, "Off-Hire Requested", "Customer", {"return_date": t.required_to})
		b.reload()
		fulfilment.transition(b.name, "Returned", "Vendor", {"lines": [{"name": b.items[0].name, "returned_qty": 795, "damaged_qty": 10, "lost_qty": 5}], "additional_charges": 45})
		with self.assertRaisesRegex(MarketplaceError, "BALANCE_DUE"):
			fulfilment.transition(b.name, "Completed", "Vendor")
		pay_all_pending(b.name, self.e1)
		as_user("Administrator")
		fulfilment.transition(b.name, "Completed", "Vendor")
		b.reload()
		self.assertEqual(b.status, "Completed")
		self.assertEqual(frappe.db.get_value("Marketplace Commission", {"booking": b.name}, "status"), "Earned")
		self.assertEqual(frappe.db.get_value("Marketplace Listing", self.la, "total_qty"), 995, "lost units leave the fleet")
		self.assertEqual(frappe.db.get_value("Vendor Order", b.vendor_order, "status"), "Completed")

		# review → moderation → rating
		r = trust.submit_review(customer_ctx(self.e1), b.name, {"rating": 5, "comment": "Delivered on time"})
		as_user("Administrator")
		trust.moderate_review(r.name, "Published")
		self.assertEqual(frappe.db.get_value("Marketplace Vendor", self.va.name, "rating"), 5)

		# settlement: needs payout reference to be marked paid
		s = settlement.build(self.va.name, add_days(getdate(), -1), add_days(getdate(), 1))
		paid_revenue = sum(p.amount for p in frappe.get_all("Marketplace Payment", filters={"booking": b.name, "status": "Succeeded",
			"payment_type": ["not in", ["Security Deposit", "Refund", "Cancellation Fee"]]}, fields=["amount"]))
		self.assertAlmostEqual(s.net_payable, paid_revenue - b.commission_amount, places=3)
		settlement.approve(s.name)
		with self.assertRaisesRegex(MarketplaceError, "PAYOUT_REFERENCE"):
			settlement.mark_paid(s.name, "")
		self.assertEqual(settlement.mark_paid(s.name, "WIRE-0001").status, "Paid")

		# audit trail exists for each lifecycle step
		events = set(frappe.get_all("Marketplace Audit Event", filters={"reference_name": ["in", [t.name, oa.name, b.name]]}, pluck="event"))
		for e in ("tender.status", "offer.submitted", "offer.accepted", "booking.created", "booking.status"):
			self.assertIn(e, events)

	# ---------------------------------------------------------------- over-allocation protection
	def test_02_no_double_allocation(self):
		r1 = hire_request(self.e1, qty=600, start=60, days=30)
		r2 = hire_request(self.e2, qty=600, start=70, days=30)
		o1 = offer_for(self.eb, r1.tender, 1.0, self.lb)
		o2 = offer_for(self.eb, r2.tender, 1.0, self.lb)
		close(r1.tender)
		close(r2.tender)
		booking.accept_offer(customer_ctx(self.e1), o1.name)
		with self.assertRaisesRegex(MarketplaceError, "INSUFFICIENT_AVAILABILITY"):
			booking.accept_offer(customer_ctx(self.e2), o2.name)
		self.assertEqual(frappe.db.get_value("Marketplace Tender", r2.tender, "status"), "Evaluation", "failed accept rolls nothing forward")

	# ---------------------------------------------------------------- sale workflow
	def test_03_sale_flow(self):
		ctx = vendor_ctx(self.eb)
		lp = vendors.save_listing(ctx, {"title": "Adjustable steel prop 3.5m", "category": "Props", "uom": "Nos", "total_qty": 500, "currency": "OMR",
			"allow_hire": 0, "allow_sale": 1, "sale_price": 9.5, "warranty": "12 months"})
		vendors.set_listing_status(ctx, lp.name, "Published")
		cctx = customer_ctx(self.e1)
		req = requests.save(cctx, {"title": "Props purchase", "transaction_type": "Sale", "category": "Props", "expected_delivery_date": add_days(getdate(), 10),
			"delivery_terms": "Delivered to site", "project_name": "Villa", "site_address": "Seeb", "city": "Muscat", "country": "Oman",
			"items": [{"equipment_name": "Steel prop", "qty": 200, "uom": "Nos"}]})
		req = requests.submit(cctx, req.name)
		o = offer_for(self.eb, req.tender, 9.0, lp.name, deposit=0, rate_basis="Unit")
		self.assertAlmostEqual(o.subtotal, 1800, places=3)
		close(req.tender)
		b = booking.accept_offer(customer_ctx(self.e1), o.name)
		self.assertIsNone(b.end_date)
		pay_all_pending(b.name, self.e1)
		as_user("Administrator")
		for step, party in (("Dispatched", "Vendor"), ("Delivered", "Customer")):
			fulfilment.transition(b.name, step, party)
		pay_all_pending(b.name, self.e1)
		as_user("Administrator")
		fulfilment.transition(b.name, "Completed", "Vendor")
		self.assertEqual(frappe.db.get_value("Marketplace Listing", lp.name, "total_qty"), 300, "sold units leave stock")
		with self.assertRaisesRegex(MarketplaceError, "BOOKING_STATE"):
			fulfilment.transition(b.name, "On Hire", "Vendor")

	# ---------------------------------------------------------------- contract workflow
	def test_04_contract_flow(self):
		ctx = vendor_ctx(self.ea)
		lcon = vendors.save_listing(ctx, {"title": "Ringlock system — project supply", "category": "Ringlock Scaffolding", "uom": "Set", "total_qty": 50,
			"currency": "OMR", "allow_hire": 0, "allow_contract": 1, "contract_monthly_rate": 300})
		vendors.set_listing_status(ctx, lcon.name, "Published")
		cctx = customer_ctx(self.e1)
		req = requests.save(cctx, {"title": "Ringlock framework 6 months", "transaction_type": "Contract", "category": "Ringlock Scaffolding",
			"contract_start": add_days(getdate(), 20), "contract_months": 6, "expected_monthly_qty": 10, "project_name": "Mall", "site_address": "Sohar",
			"city": "Sohar", "country": "Oman", "items": [{"equipment_name": "Ringlock set", "qty": 10, "uom": "Set"}]})
		bad = frappe.new_doc("Rental Request")
		bad.update({"transaction_type": "Contract", "category": "Ringlock Scaffolding", "items": [{"equipment_name": "x", "qty": 1, "uom": "Set"}]})
		with self.assertRaisesRegex(MarketplaceError, "REQ_CONTRACT"):
			requests.validate(bad)
		req = requests.submit(cctx, req.name)
		o = offer_for(self.ea, req.tender, 280, lcon.name, deposit=0, mobilization_charges=200, demobilization_charges=200)
		self.assertAlmostEqual(o.subtotal, 10 * 280 * 6, places=3)
		close(req.tender)
		b = booking.accept_offer(customer_ctx(self.e1), o.name)
		self.assertEqual(len([r for r in b.schedule if r.line_type == "Contract Period"]), 6)
		pay_all_pending(b.name, self.e1)
		as_user("Administrator")
		for step in ("Mobilized", "Active", "Demobilized", "Completed"):
			fulfilment.transition(b.name, step, "Vendor")
		self.assertEqual(frappe.db.get_value("Marketplace Booking", b.name, "status"), "Completed")

	# ---------------------------------------------------------------- subscriptions & entitlements
	def test_05_entitlements_enforced(self):
		as_user("Administrator")
		if not frappe.db.exists("Marketplace Subscription Plan", "tiny"):
			frappe.get_doc({"doctype": "Marketplace Subscription Plan", "plan_code": "tiny", "plan_name": "Tiny", "currency": "OMR", "price_monthly": 0,
				"max_listings": 1, "max_tender_responses": 1, "max_staff_users": 1, "enabled": 1}).insert(ignore_permissions=True)
		sub = subscriptions.subscribe(self.vc.name, "tiny")
		self.assertEqual(sub.status, "Active")
		self.assertEqual(frappe.db.count("Vendor Subscription", {"vendor": self.vc.name, "status": ["in", ["Trial", "Active", "Grace"]]}), 1)
		ctx = vendor_ctx(self.ec)
		l2 = vendors.save_listing(ctx, {"title": "Second", "category": "Cuplock Scaffolding", "uom": "Nos", "total_qty": 5, "currency": "OMR", "allow_hire": 1, "monthly_rate": 1})
		with self.assertRaisesRegex(MarketplaceError, "LISTING_LIMIT"):
			vendors.set_listing_status(ctx, l2.name, "Published")
		with self.assertRaisesRegex(MarketplaceError, "STAFF_LIMIT"):
			vendors.add_staff(ctx, f"staff-{SFX}@vendor.test", "Staff One")
		# paid upgrade stays pending until payment succeeds
		as_user("Administrator")
		up = subscriptions.subscribe(self.vc.name, "professional")
		self.assertEqual(up.status, "Pending Payment")
		pay = payments.create_subscription_payment(up.name)
		payments.mark_succeeded(pay.name, "SUB-REF", source="finance")
		self.assertEqual(frappe.db.get_value("Vendor Subscription", up.name, "status"), "Active")
		self.assertEqual(frappe.db.get_value("Vendor Subscription", sub.name, "status"), "Superseded")
		vendors.set_listing_status(vendor_ctx(self.ec), l2.name, "Published")
		# expiry → grace → expired
		as_user("Administrator")
		frappe.db.set_value("Vendor Subscription", up.name, {"end_date": add_days(getdate(), -1), "auto_renew": 0})
		subscriptions.daily_lifecycle()
		self.assertEqual(frappe.db.get_value("Vendor Subscription", up.name, "status"), "Grace")
		frappe.db.set_value("Vendor Subscription", up.name, "grace_end", add_days(getdate(), -1))
		subscriptions.daily_lifecycle()
		self.assertEqual(frappe.db.get_value("Vendor Subscription", up.name, "status"), "Expired")
		self.assertFalse(subscriptions.entitlements(self.vc.name).active)

	# ---------------------------------------------------------------- commission precedence (db)
	def test_06_commission_rules(self):
		from thinknxg_rental_marketplace.services import commission

		as_user("Administrator")
		r1 = frappe.get_doc({"doctype": "Commission Rule", "enabled": 1, "category": "Scaffolding", "basis": "Percentage", "rate": 3}).insert(ignore_permissions=True)
		r2 = frappe.get_doc({"doctype": "Commission Rule", "enabled": 1, "vendor": self.vb.name, "basis": "Fixed", "fixed_amount": 20}).insert(ignore_permissions=True)
		self.assertEqual(commission.resolve(self.va.name, "Cuplock Scaffolding", "Hire", 1000, "OMR").amount, 30)
		self.assertEqual(commission.resolve(self.vb.name, "Cuplock Scaffolding", "Hire", 1000, "OMR").amount, 20)
		r1.delete(ignore_permissions=True)
		r2.delete(ignore_permissions=True)

	# ---------------------------------------------------------------- cancellation, refunds, reopen
	def test_07_cancellation_reopens_tender(self):
		req = hire_request(self.e2, qty=100, start=120, days=30)
		oa = offer_for(self.ea, req.tender, 1.2, self.la)
		ob = offer_for(self.eb, req.tender, 1.25, self.lb)
		close(req.tender)
		b = booking.accept_offer(customer_ctx(self.e2), oa.name)
		pay_all_pending(b.name, self.e2)
		paid_before = frappe.db.get_value("Marketplace Booking", b.name, "amount_paid")
		as_user(self.ea)
		booking.cancel(b.name, "Vendor", "Fleet breakdown")
		as_user("Administrator")
		self.assertEqual(frappe.db.get_value("Marketplace Tender", req.tender, "status"), "Evaluation")
		self.assertEqual(frappe.db.get_value("Supplier Offer", ob.name, "status"), "Under Review")
		refunds = frappe.get_all("Marketplace Payment", filters={"booking": b.name, "payment_type": "Refund"}, fields=["amount", "status"])
		self.assertTrue(refunds and all(r.status == "Pending" for r in refunds), "manual refunds wait for Finance confirmation")
		self.assertAlmostEqual(sum(r.amount for r in refunds), paid_before, places=3, msg="supplier cancellation refunds everything paid")
		self.assertEqual(frappe.db.get_value("Marketplace Commission", {"booking": b.name}, "status"), "Reversed")
		self.assertEqual(frappe.db.count("Listing Availability", {"booking": b.name, "status": "Active"}), 0)
		b2 = booking.accept_offer(customer_ctx(self.e2), ob.name)
		self.assertEqual(b2.vendor, self.vb.name)

	# ---------------------------------------------------------------- expiry & unpaid hold
	def test_08_no_offers_expires_and_unpaid_released(self):
		req = hire_request(self.e1, qty=10, start=200, days=10)
		close(req.tender)
		self.assertEqual(frappe.db.get_value("Marketplace Tender", req.tender, "status"), "Expired")
		as_user(self.e1)
		tender_service.extend(req.tender, add_to_date(now_datetime(), days=2))
		self.assertEqual(frappe.db.get_value("Marketplace Tender", req.tender, "status"), "Bidding Open")
		o = offer_for(self.ea, req.tender, 1.0, self.la)
		close(req.tender)
		b = booking.accept_offer(customer_ctx(self.e1), o.name)
		as_user("Administrator")
		frappe.db.set_value("Marketplace Booking", b.name, "payment_due_by", add_to_date(now_datetime(), hours=-1))
		booking.expire_unpaid()
		self.assertEqual(frappe.db.get_value("Marketplace Booking", b.name, "status"), "Cancelled")
		self.assertEqual(frappe.db.get_value("Supplier Offer", o.name, "status"), "Expired")

	# ---------------------------------------------------------------- webhook security
	def test_09_stripe_webhook_signature_and_dedupe(self):
		as_user("Administrator")
		secret = "whsec_test"
		s = frappe.get_single("Marketplace Settings")
		s.stripe_webhook_secret = secret
		s.stripe_secret_key = "sk_test_x"
		s.save(ignore_permissions=True)
		pay = frappe.get_doc({"doctype": "Marketplace Payment", "payment_type": "Subscription", "status": "Pending", "gateway": "Stripe",
			"currency": "OMR", "amount": 49, "vendor": self.va.name}).insert(ignore_permissions=True)
		body = json.dumps({"id": f"evt_{SFX}", "type": "checkout.session.completed", "data": {"object": {"id": "cs_1", "payment_intent": "pi_1",
			"payment_status": "paid", "amount_total": 49000, "metadata": {"payment": pay.name}}}}).encode()
		ts = str(int(time.time()))
		sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
		from thinknxg_rental_marketplace.services.payments.gateways import GatewayError

		with self.assertRaises(GatewayError):
			payments.process_webhook("Stripe", {"Stripe-Signature": f"t={ts},v1=deadbeef"}, body)
		self.assertEqual(payments.process_webhook("Stripe", {"Stripe-Signature": f"t={ts},v1={sig}"}, body), {"processed": True})
		self.assertEqual(frappe.db.get_value("Marketplace Payment", pay.name, "status"), "Succeeded")
		self.assertEqual(payments.process_webhook("Stripe", {"Stripe-Signature": f"t={ts},v1={sig}"}, body), {"duplicate": True})

	# ---------------------------------------------------------------- reverse auction & negotiated revisions
	def test_10_reverse_auction_and_negotiation(self):
		req = hire_request(self.e1, qty=50, start=300, days=30)
		as_user("Administrator")
		t = frappe.get_doc("Marketplace Tender", req.tender)
		t.tender_type, t.reserve_price, t.min_decrement_percent = "Reverse Auction", 200, 5
		t.save(ignore_permissions=True)
		offer_for(self.ea, t.name, 1.5, self.la)  # 50×1.5 + 50 transport = 125 ×1.05 = 131.25
		with self.assertRaisesRegex(MarketplaceError, "BID_DECREMENT"):
			offer_for(self.eb, t.name, 1.48, self.lb)
		offer_for(self.eb, t.name, 1.2, self.lb)
		with self.assertRaisesRegex(MarketplaceError, "ABOVE_RESERVE"):
			offer_for(self.ea, t.name, 4.0, self.la)
		# negotiated: revision only on customer request after close
		req2 = hire_request(self.e1, qty=20, start=320, days=30)
		as_user("Administrator")
		frappe.db.set_value("Marketplace Tender", req2.tender, "tender_type", "Negotiated")
		o = offer_for(self.ea, req2.tender, 2.0, self.la)
		close(req2.tender)
		with self.assertRaisesRegex(MarketplaceError, "TENDER_CLOSED"):
			offer_for(self.ea, req2.tender, 1.9, self.la)
		as_user(self.e1)
		evaluation.raise_clarification("Customer", req2.tender, "Best price?", "Please revise", offer=o.name, ctype="Counteroffer", counter_amount=40)
		o2 = offer_for(self.ea, req2.tender, 1.8, self.la)
		self.assertEqual(o2.revision_no, 2)
		self.assertEqual(o2.status, "Under Review")

"""Demo data for showcasing the marketplace. Run: bench --site <site> execute thinknxg_rental_marketplace.demo.seed

Creates approved suppliers with listings, two customers, a tender in evaluation with competing offers and a
confirmed booking. Demo users get the password "Demo@12345" — change or delete them before going live.
"""
import frappe
from frappe.utils import add_days, add_to_date, getdate, now_datetime

from thinknxg_rental_marketplace.services import booking, offers, payments, registration, requests, tender as tender_service, vendors
from thinknxg_rental_marketplace.services.context import require_customer, require_vendor

PASSWORD = "Demo@12345"
SUPPLIERS = (
	("gulf-scaffold", "Gulf Scaffold & Access LLC", "Scaffolding Rental", "Muscat", ["Scaffolding", "Props"], [
		("Cuplock standard 3.0 m — galvanised", "Cuplock Scaffolding", 4000, dict(daily_rate=0.06, weekly_rate=0.3, monthly_rate=0.95, security_deposit_rate=0.4)),
		("Ringlock standard 2.5 m", "Ringlock Scaffolding", 2500, dict(monthly_rate=1.1, security_deposit_rate=0.5)),
		("Adjustable steel prop 3.5 m", "Props", 3000, dict(monthly_rate=0.45, allow_sale=1, sale_price=9.5, warranty="12 months")),
	]),
	("muscat-formwork", "Muscat Formwork Systems", "Formwork Rental", "Sohar", ["Formwork", "Scaffolding"], [
		("Aluminium slab formwork panel 1.2 × 0.6 m", "Aluminium Formwork", 1200, dict(monthly_rate=3.2, allow_contract=1, contract_monthly_rate=2.9, security_deposit_rate=2)),
		("Cuplock standard 3.0 m", "Cuplock Scaffolding", 1800, dict(monthly_rate=1.05, security_deposit_rate=0.4)),
	]),
	("oman-heavy", "Oman Heavy Plant Hire", "Equipment Rental", "Duqm", ["Construction Equipment"], [
		("50 t mobile crane with operator", "Lifting Equipment", 4, dict(daily_rate=380, weekly_rate=2300, monthly_rate=8500)),
		("Concrete pump 36 m boom", "Concrete Equipment", 3, dict(daily_rate=290, monthly_rate=6400, allow_contract=1, contract_monthly_rate=6000)),
	]),
)


def _user(email, name, role):
	if not frappe.db.exists("User", email):
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": name, "user_type": "Website User", "send_welcome_email": 0, "roles": [{"role": role}]})
		u.insert(ignore_permissions=True)
	from frappe.utils.password import update_password

	update_password(email, PASSWORD)
	return email


def seed():
	frappe.flags.mute_emails = True
	frappe.set_user("Administrator")
	out = {}
	for key, name, btype, city, cats, items in SUPPLIERS:
		email = _user(f"{key}@demo.thinknxg.com", name.split()[0] + " Sales", "Marketplace Vendor")
		vname = frappe.db.get_value("Vendor User", {"user": email}, "vendor")
		if not vname:
			frappe.set_user(email)
			v = registration.register_vendor({"business_name": name, "business_type": btype, "country": "Oman", "city": city, "state": city,
				"address_line1": "Industrial Area", "contact_person": name.split()[0] + " Sales", "email": email, "phone": "+968 2400 0000",
				"registration_number": f"CR-{key.upper()}", "categories": cats, "description": f"{name} supplies {', '.join(cats).lower()} across Oman.", "years_in_business": 12})
			vname = v.name
			frappe.set_user("Administrator")
			for s in ("Under Review", "Approved"):
				if frappe.db.get_value("Marketplace Vendor", vname, "status") != "Approved":
					vendors.set_status(vname, s)
		frappe.set_user(email)
		ctx = require_vendor()
		for title, cat, qty, rates in items:
			if frappe.db.exists("Marketplace Listing", {"vendor": vname, "title": title}):
				continue
			l = vendors.save_listing(ctx, {"title": title, "category": cat, "uom": "Nos", "total_qty": qty, "currency": "OMR", "allow_hire": 1,
				"condition": "Used - Excellent", "short_description": f"{title}, inspected and certified before every dispatch.", "brand": "SGB" if "Cuplock" in title else None,
				"specifications": [{"attribute": "Finish", "value": "Hot-dip galvanised"}, {"attribute": "Standard", "value": "EN 12811"}], **rates})
			vendors.set_listing_status(ctx, l.name, "Published")
		out[key] = (vname, email)
		frappe.set_user("Administrator")
	cust = _user("buyer@demo.thinknxg.com", "Ahmed Al Harthy", "Marketplace Customer")
	frappe.set_user(cust)
	c = registration.register_customer({"customer_type": "Company", "company_name": "Al Harthy Contracting", "full_name": "Ahmed Al Harthy", "email": cust, "country": "Oman", "city": "Muscat"})
	cctx = require_customer()
	if not frappe.db.exists("Rental Request", {"customer": c.name}):
		req = requests.save(cctx, {"title": "Cuplock scaffolding for Bausher tower, 60 days", "transaction_type": "Hire", "category": "Cuplock Scaffolding",
			"required_from": add_days(getdate(), 7), "required_to": add_days(getdate(), 66), "project_name": "Bausher Residential Tower", "site_address": "Plot 214, Bausher",
			"city": "Muscat", "state": "Muscat", "country": "Oman", "site_contact": "Eng. Salim", "site_phone": "+968 9123 4567",
			"items": [{"equipment_name": "Cuplock standard 3.0 m", "qty": 1500, "uom": "Nos", "specifications": "Galvanised, EN 12811"}]})
		req = requests.submit(cctx, req.name)
		for key, rate in (("gulf-scaffold", 0.92), ("muscat-formwork", 0.99)):
			vname, email = out[key]
			frappe.set_user(email)
			t = frappe.get_doc("Marketplace Tender", req.tender)
			listing = frappe.db.get_value("Marketplace Listing", {"vendor": vname, "category": "Cuplock Scaffolding"}, "name")
			o = offers.save_draft(require_vendor(), t.name, {"delivery_date": t.required_from, "availability_confirmed": 1, "payment_terms": "20% advance, balance monthly",
				"security_deposit": 500, "transport_charges": 120, "loading_charges": 60, "tax_percent": 5,
				"items": [{"tender_item": t.items[0].name, "listing": listing, "qty": 1500, "unit_rate": rate, "rate_basis": "Monthly"}]})
			offers.submit(require_vendor(), o.name)
		frappe.set_user("Administrator")
		frappe.db.set_value("Marketplace Tender", req.tender, "submission_deadline", add_to_date(now_datetime(), minutes=-1))
		tender_service.process_deadlines()
		# a second, still-open tender for the supplier portal
		frappe.set_user(cust)
		r2 = requests.save(require_customer(), {"title": "Slab formwork, 6-month contract", "transaction_type": "Contract", "category": "Aluminium Formwork",
			"contract_start": add_days(getdate(), 21), "contract_months": 6, "project_name": "Sohar Logistics Hub", "site_address": "Sohar Freezone", "city": "Sohar", "country": "Oman",
			"items": [{"equipment_name": "Aluminium slab panel 1.2 × 0.6", "qty": 600, "uom": "Nos"}]})
		requests.submit(require_customer(), r2.name)
	frappe.set_user("Administrator")
	frappe.db.commit()
	return {"suppliers": {k: v[1] for k, v in out.items()}, "customer": cust, "password": PASSWORD}

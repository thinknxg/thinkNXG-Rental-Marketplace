"""Pure unit tests — no database writes."""
from decimal import Decimal
from unittest import TestCase

from thinknxg_rental_marketplace.services import availability, commission, evaluation, matching, pricing
from thinknxg_rental_marketplace.services.money import q


class TestPricing(TestCase):
	def test_hire_monthly_prorata_and_tax(self):
		r = pricing.compute("Hire", [{"qty": 800, "unit_rate": "1.200", "rate_basis": "Monthly"}],
			charges={"transport_charges": 150, "loading_charges": 40}, tax_percent=5, days=45, currency="OMR", security_deposit=400)
		self.assertEqual(r["lines"][0]["periods"], Decimal("1.5000"))
		self.assertEqual(r["subtotal"], Decimal("1440.000"))
		self.assertEqual(r["charges_total"], Decimal("190.000"))
		self.assertEqual(r["tax_amount"], Decimal("81.500"))
		self.assertEqual(r["grand_total"], Decimal("1711.500"))
		self.assertEqual(r["security_deposit"], Decimal("400.000"))

	def test_sale_is_unit_priced(self):
		r = pricing.compute("Sale", [{"qty": 10, "unit_rate": 12.5}], tax_percent=0, currency="USD")
		self.assertEqual(r["lines"][0]["rate_basis"], "Unit")
		self.assertEqual(r["grand_total"], Decimal("125.00"))

	def test_contract_months(self):
		r = pricing.compute("Contract", [{"qty": 2, "unit_rate": 100, "rate_basis": "Monthly"}], months=6, currency="OMR")
		self.assertEqual(r["subtotal"], Decimal("1200.000"))

	def test_rejects_bad_input(self):
		for items, kw in (([{"qty": 0, "unit_rate": 1}], {"days": 5}), ([{"qty": 1, "unit_rate": -1}], {"days": 5}), ([{"qty": 1, "unit_rate": 1}], {"days": 0})):
			with self.assertRaises(pricing.PricingError):
				pricing.compute("Hire", items, **kw)
		with self.assertRaises(pricing.PricingError):
			pricing.compute("Hire", [{"qty": 1, "unit_rate": 1}], days=3, tax_percent=150)

	def test_schedule_contract_splits_balance(self):
		lines = pricing.booking_schedule("Contract", 1200, 100, 20, months=6, currency="OMR")
		types = [l["line_type"] for l in lines]
		self.assertEqual(types.count("Contract Period"), 6)
		self.assertEqual(sum(l["amount"] for l in lines if l["line_type"] != "Deposit"), Decimal("1200.000"))

	def test_rounding_three_decimals(self):
		self.assertEqual(q("1.23456", "OMR"), Decimal("1.235"))
		self.assertEqual(q("1.235", "USD"), Decimal("1.24"))


class TestAvailability(TestCase):
	def test_peak_counts_only_concurrent(self):
		iv = [("2026-01-01", "2026-01-10", 300), ("2026-01-11", "2026-01-20", 500), ("2026-01-05", "2026-01-12", 100)]
		self.assertEqual(availability.peak_usage(iv, "2026-01-01", "2026-01-31"), 600)  # 11th–12th: 500 + 100
		self.assertEqual(availability.peak_usage(iv, "2026-01-01", "2026-01-04"), 300)
		self.assertEqual(availability.peak_usage(iv, "2026-02-01", "2026-02-10"), 0)

	def test_back_to_back_do_not_overlap(self):
		iv = [("2026-01-01", "2026-01-10", 400), ("2026-01-11", "2026-01-20", 400)]
		self.assertEqual(availability.peak_usage(iv, "2026-01-01", "2026-01-20"), 400)


class TestCommission(TestCase):
	rules = [
		{"name": "R-default-hire", "enabled": 1, "priority": 1, "transaction_type": "Hire", "basis": "Percentage", "rate": 6},
		{"name": "R-cat", "enabled": 1, "priority": 1, "category": "Scaffolding", "basis": "Percentage", "rate": 4},
		{"name": "R-vendor", "enabled": 1, "priority": 0, "vendor": "VND-1", "basis": "Fixed", "fixed_amount": 25},
		{"name": "R-off", "enabled": 0, "vendor": "VND-2", "basis": "Percentage", "rate": 1},
	]

	def test_most_specific_wins(self):
		ctx = dict(vendor="VND-1", category="Cuplock Scaffolding", categories=["Cuplock Scaffolding", "Scaffolding"], transaction_type="Hire")
		self.assertEqual(commission.pick_rule(self.rules, ctx)["name"], "R-vendor")
		ctx["vendor"] = "VND-2"
		self.assertEqual(commission.pick_rule(self.rules, ctx)["name"], "R-cat")  # category (2) beats type (1); disabled ignored
		ctx["categories"], ctx["category"] = ["Props"], "Props"
		self.assertEqual(commission.pick_rule(self.rules, ctx)["name"], "R-default-hire")

	def test_amount_caps(self):
		basis, rate, amt = commission.amount_for({"basis": "Percentage", "rate": 10, "max_amount": 50}, 1000, "OMR")
		self.assertEqual(amt, Decimal("50.000"))
		basis, rate, amt = commission.amount_for(None, 200, "OMR", "Percentage", 5)
		self.assertEqual(amt, Decimal("10.000"))


class TestMatchingAndScoring(TestCase):
	base_v = dict(status="Approved", verified=1, sub_active=True, categories={"Scaffolding"}, countries={"Oman"}, states={"muscat"},
		cities={"muscat"}, rating=4.5, review_count=3, offers_submitted=4, offers_won=2, listing_free_qty=900, listing_count=2)
	t = dict(category_lineage={"Cuplock Scaffolding", "Scaffolding", "All Equipment"}, country="Oman", state="Muscat", city="Muscat",
		require_verified=1, min_rating=0, required_qty=800)

	def test_hard_rules(self):
		for patch, reason in ((dict(status="Suspended"), "not approved"), (dict(verified=0), "not verified"), (dict(sub_active=False), "no active subscription"),
			(dict(categories={"Formwork"}), "category not covered"), (dict(countries={"UAE"}), "does not serve country")):
			ok, _s, reasons = matching.score_vendor({**self.base_v, **patch}, self.t)
			self.assertFalse(ok)
			self.assertIn(reason, reasons)

	def test_availability_drives_score(self):
		ok, full, _ = matching.score_vendor(self.base_v, self.t)
		ok2, none, _ = matching.score_vendor({**self.base_v, "listing_free_qty": 0, "listing_count": 0}, self.t)
		self.assertTrue(ok and ok2)
		self.assertGreater(full, none + 30)

	def test_weighted_scoring_transparent(self):
		offers = [{"name": "A", "comparable_total": 1000, "delivery_date": "2026-12-10", "rating": 4, "technical_compliance": "Full"},
			{"name": "B", "comparable_total": 800, "delivery_date": "2026-12-20", "rating": 5, "technical_compliance": "Partial"}]
		crit = [{"criterion": "Price", "basis": "Price", "weight": 50}, {"criterion": "Delivery", "basis": "Delivery", "weight": 50}]
		s = evaluation.score_offers(offers, crit, today="2026-12-01")
		self.assertEqual(s["B"][1][0]["score"], 100.0)
		self.assertEqual(s["A"][1][0]["score"], 80.0)
		self.assertEqual(s["A"][1][1]["score"], 100.0)
		self.assertEqual(s["A"][0], 90.0)
		self.assertEqual(s["B"][0], 50.0)

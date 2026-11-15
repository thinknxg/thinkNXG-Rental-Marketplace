"""Commission resolution. Most specific enabled rule wins; ties broken by priority (higher first).

Specificity weights: vendor 8 · subscription plan 4 · category 2 · transaction type 1.
A rule field left empty matches anything. No matching rule → Marketplace Settings default.
"""
from decimal import Decimal

import frappe
from frappe.utils import getdate

from thinknxg_rental_marketplace.services.money import D, q

WEIGHTS = (("vendor", 8), ("subscription_plan", 4), ("category", 2), ("transaction_type", 1))


def pick_rule(rules, ctx, on_date=None):
	"""Pure. rules: list of dicts; ctx: dict(vendor, subscription_plan, category, transaction_type, categories=[ancestors])."""
	on_date = getdate(on_date) if on_date else None
	best, best_key = None, None
	cats = set(ctx.get("categories") or []) | ({ctx["category"]} if ctx.get("category") else set())
	for r in rules:
		if not r.get("enabled", 1):
			continue
		if on_date and r.get("valid_from") and getdate(r["valid_from"]) > on_date:
			continue
		if on_date and r.get("valid_upto") and getdate(r["valid_upto"]) < on_date:
			continue
		spec, ok = 0, True
		for field, w in WEIGHTS:
			val = r.get(field)
			if not val:
				continue
			matches = (val in cats) if field == "category" else (val == ctx.get(field))
			if not matches:
				ok = False
				break
			spec += w
		if not ok:
			continue
		key = (spec, int(r.get("priority") or 0), str(r.get("name") or ""))
		if best_key is None or key > best_key:
			best, best_key = r, key
	return best


def amount_for(rule, base_amount, currency=None, default_basis="Percentage", default_rate=0, default_fixed=0):
	"""Pure. Returns (basis, rate, amount)."""
	base = D(base_amount)
	if rule:
		basis = rule.get("basis") or "Percentage"
		rate = D(rule.get("rate"))
		fixed = D(rule.get("fixed_amount"))
		lo, hi = D(rule.get("min_amount")), D(rule.get("max_amount"))
	else:
		basis, rate, fixed, lo, hi = default_basis, D(default_rate), D(default_fixed), Decimal(0), Decimal(0)
	amt = base * rate / Decimal(100) if basis == "Percentage" else fixed
	if lo and amt < lo:
		amt = lo
	if hi and amt > hi:
		amt = hi
	amt = min(amt, base) if base > 0 else Decimal(0)
	return basis, float(rate if basis == "Percentage" else 0), q(amt, currency)


def category_lineage(category):
	out = []
	while category:
		out.append(category)
		category = frappe.db.get_value("Marketplace Category", category, "parent_marketplace_category")
		if category in out:
			break
	return out


def resolve(vendor, category, transaction_type, base_amount, currency):
	from thinknxg_rental_marketplace.services.subscriptions import active_subscription

	sub = active_subscription(vendor)
	ctx = dict(vendor=vendor, subscription_plan=sub.plan if sub else None, category=category,
		transaction_type=transaction_type, categories=category_lineage(category))
	rules = frappe.get_all("Commission Rule", filters={"enabled": 1}, fields=["*"])
	rule = pick_rule(rules, ctx, on_date=frappe.utils.nowdate())
	s = frappe.get_cached_doc("Marketplace Settings")
	basis, rate, amount = amount_for(rule, base_amount, currency, s.default_commission_basis or "Percentage",
		s.default_commission_rate, s.default_commission_fixed)
	return frappe._dict(rule=rule.get("name") if rule else None, basis=basis, rate=rate, amount=amount)

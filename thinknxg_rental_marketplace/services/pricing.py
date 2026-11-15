"""Server-authoritative offer pricing. Pure functions; the browser's totals are never used.

Billable periods
  Hire     Daily  : days                     Weekly: days / 7        Monthly: days / 30   (pro-rata, 4 dp)
  Contract Monthly: contract months          (other bases converted from months × 30 days)
  Sale     Unit   : 1
Totals
  subtotal        = Σ qty × unit_rate × periods
  charges_total   = transport + loading + installation + mobilization + demobilization
  tax_amount      = (subtotal + charges_total) × tax%
  grand_total     = subtotal + charges_total + tax_amount            (payable, excl. refundable deposit)
  comparable_total= grand_total                                      (used for "lowest comparable price")
"""
from decimal import Decimal

from thinknxg_rental_marketplace.services.money import D, q

CHARGE_FIELDS = ("transport_charges", "loading_charges", "installation_charges", "mobilization_charges", "demobilization_charges")
PERIOD_DAYS = {"Daily": Decimal(1), "Weekly": Decimal(7), "Monthly": Decimal(30)}


class PricingError(ValueError):
	pass


def periods_for(transaction_type, rate_basis, days=0, months=0):
	if transaction_type == "Sale" or rate_basis == "Unit":
		if transaction_type != "Sale":
			raise PricingError("Unit pricing is only valid for Sale offers")
		return Decimal(1)
	if rate_basis not in PERIOD_DAYS:
		raise PricingError(f"Unknown rate basis {rate_basis}")
	if transaction_type == "Contract":
		months = D(months)
		if months <= 0:
			raise PricingError("Contract months must be greater than zero")
		if rate_basis == "Monthly":
			return months
		return (months * Decimal(30) / PERIOD_DAYS[rate_basis]).quantize(Decimal("0.0001"))
	days = D(days)
	if days <= 0:
		raise PricingError("Rental period must be at least one day")
	return (days / PERIOD_DAYS[rate_basis]).quantize(Decimal("0.0001"))


def compute(transaction_type, items, charges=None, tax_percent=0, days=0, months=0, currency=None, security_deposit=0):
	"""items: iterable of dicts with qty, unit_rate, rate_basis. Returns a dict of Decimals plus per-line results."""
	if transaction_type not in ("Hire", "Sale", "Contract"):
		raise PricingError("Unknown transaction type")
	charges = charges or {}
	lines, subtotal = [], Decimal(0)
	for i, it in enumerate(items, 1):
		qty, rate = D(it.get("qty")), D(it.get("unit_rate"))
		if qty <= 0:
			raise PricingError(f"Line {i}: quantity must be greater than zero")
		if rate < 0:
			raise PricingError(f"Line {i}: rate cannot be negative")
		basis = "Unit" if transaction_type == "Sale" else (it.get("rate_basis") or "Monthly")
		periods = periods_for(transaction_type, basis, days, months)
		amount = q(qty * rate * periods, currency)
		lines.append({"rate_basis": basis, "periods": periods, "amount": amount})
		subtotal += amount
	if not lines:
		raise PricingError("An offer needs at least one line")
	charge_values = {}
	for f in CHARGE_FIELDS:
		v = D(charges.get(f))
		if v < 0:
			raise PricingError(f"{f} cannot be negative")
		charge_values[f] = q(v, currency)
	charges_total = sum(charge_values.values(), Decimal(0))
	tax_percent = D(tax_percent)
	if tax_percent < 0 or tax_percent > 100:
		raise PricingError("Tax percent must be between 0 and 100")
	tax_amount = q((subtotal + charges_total) * tax_percent / Decimal(100), currency)
	grand = q(subtotal + charges_total + tax_amount, currency)
	deposit = q(D(security_deposit), currency)
	if deposit < 0:
		raise PricingError("Security deposit cannot be negative")
	return {
		"lines": lines,
		"subtotal": q(subtotal, currency),
		"charges": charge_values,
		"charges_total": q(charges_total, currency),
		"tax_amount": tax_amount,
		"grand_total": grand,
		"comparable_total": grand,
		"security_deposit": deposit,
	}


def booking_schedule(transaction_type, grand_total, security_deposit, deposit_percent, start_date=None, months=0, currency=None):
	"""Payment schedule for an accepted offer. Returns list of dicts (line_type, amount, due offset marker)."""
	from thinknxg_rental_marketplace.services.money import pct

	grand, deposit = D(grand_total), D(security_deposit)
	advance = pct(grand, deposit_percent, currency)
	lines = []
	if advance > 0:
		lines.append({"line_type": "Advance", "amount": advance, "due": "on_accept"})
	if deposit > 0:
		lines.append({"line_type": "Deposit", "amount": q(deposit, currency), "due": "on_accept"})
	remaining = q(grand - advance, currency)
	if transaction_type == "Contract" and int(months or 0) > 1 and remaining > 0:
		n = int(months)
		each = q(remaining / n, currency)
		for i in range(n):
			amt = each if i < n - 1 else q(remaining - each * (n - 1), currency)
			lines.append({"line_type": "Contract Period", "amount": amt, "due": f"month_{i}"})
	elif remaining > 0:
		lines.append({"line_type": "Balance", "amount": remaining, "due": "on_start"})
	return lines

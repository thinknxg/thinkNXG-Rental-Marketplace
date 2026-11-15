"""Decimal money helpers. Pure — no database access."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

THREE_DECIMAL = {"OMR", "KWD", "BHD", "JOD", "TND", "LYD", "IQD"}
ZERO = Decimal("0")


def D(value):
	if value is None or value == "":
		return ZERO
	if isinstance(value, Decimal):
		return value
	try:
		return Decimal(str(value))
	except (InvalidOperation, ValueError):
		raise ValueError(f"Not a number: {value!r}")


def precision(currency):
	return 3 if (currency or "").upper() in THREE_DECIMAL else 2


def q(value, currency=None, places=None):
	places = precision(currency) if places is None else places
	return D(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def to_float(value, currency=None):
	return float(q(value, currency))


def pct(amount, percent, currency=None):
	return q(D(amount) * D(percent) / Decimal(100), currency)

"""Payment gateway abstraction.

A gateway creates a checkout for a Marketplace Payment, verifies and parses webhooks, and requests refunds.
Nothing here marks money as received: ``service.mark_succeeded`` is only called from a *verified* webhook or
from a Finance user's manual confirmation.
"""
import hashlib
import hmac
import json
import time

import frappe
from frappe.utils import get_url

from thinknxg_rental_marketplace.services.money import D, precision


class GatewayError(Exception):
	pass


class Gateway:
	name = "Base"

	def create_checkout(self, payment):
		raise NotImplementedError

	def parse_webhook(self, headers, body):
		"""Returns dict(event_id, event_type, payment, reference, status ∈ {succeeded, failed, refunded, ignored}, amount)."""
		raise NotImplementedError

	def refund(self, payment, amount):
		raise NotImplementedError

	@staticmethod
	def minor_units(amount, currency):
		return int((D(amount) * (10 ** precision(currency))).to_integral_value())


class ManualGateway(Gateway):
	"""Bank transfer / cash. The customer enters a transfer reference; Finance confirms receipt."""
	name = "Manual"

	def create_checkout(self, payment):
		return {"reference": payment.name, "checkout_url": f"/marketplace/account/payments/{payment.name}", "status": "Pending"}

	def parse_webhook(self, headers, body):
		raise GatewayError("Manual payments have no webhook")

	def refund(self, payment, amount):
		return {"reference": f"MANUAL-REFUND-{payment.name}", "status": "Pending"}


class StripeGateway(Gateway):
	name = "Stripe"
	api = "https://api.stripe.com/v1"

	def __init__(self, secret, webhook_secret):
		self.secret, self.webhook_secret = secret, webhook_secret

	def _post(self, path, data):
		import requests

		r = requests.post(f"{self.api}{path}", data=data, auth=(self.secret, ""), timeout=20)
		if r.status_code >= 400:
			raise GatewayError(r.text[:500])
		return r.json()

	def create_checkout(self, payment):
		cur = (payment.currency or "usd").lower()
		data = {
			"mode": "payment", "client_reference_id": payment.name, "metadata[payment]": payment.name,
			"success_url": get_url(f"/marketplace/account/payments/{payment.name}?result=success"),
			"cancel_url": get_url(f"/marketplace/account/payments/{payment.name}?result=cancel"),
			"line_items[0][quantity]": 1, "line_items[0][price_data][currency]": cur,
			"line_items[0][price_data][unit_amount]": self.minor_units(payment.amount, payment.currency),
			"line_items[0][price_data][product_data][name]": f"{payment.payment_type} {payment.booking or payment.subscription or ''}",
			"payment_intent_data[metadata][payment]": payment.name,
		}
		s = self._post("/checkout/sessions", data)
		return {"reference": s.get("id"), "checkout_url": s.get("url"), "status": "Pending"}

	def verify(self, headers, body):
		sig = headers.get("Stripe-Signature") or headers.get("stripe-signature") or ""
		parts = dict(p.split("=", 1) for p in sig.split(",") if "=" in p)
		ts, v1 = parts.get("t"), parts.get("v1")
		if not ts or not v1 or abs(time.time() - int(ts)) > 300:
			raise GatewayError("Invalid or stale Stripe signature")
		expected = hmac.new(self.webhook_secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
		if not hmac.compare_digest(expected, v1):
			raise GatewayError("Stripe signature mismatch")

	def parse_webhook(self, headers, body):
		self.verify(headers, body)
		ev = json.loads(body)
		obj = ev.get("data", {}).get("object", {})
		status = {"checkout.session.completed": "succeeded", "checkout.session.async_payment_succeeded": "succeeded",
			"checkout.session.async_payment_failed": "failed", "checkout.session.expired": "failed", "charge.refunded": "refunded"}.get(ev.get("type"), "ignored")
		if status == "succeeded" and obj.get("payment_status") not in ("paid", "no_payment_required"):
			status = "ignored"
		return {"event_id": ev.get("id"), "event_type": ev.get("type"), "payment": (obj.get("metadata") or {}).get("payment") or obj.get("client_reference_id"),
			"reference": obj.get("payment_intent") or obj.get("id"), "status": status, "amount_minor": obj.get("amount_total") or obj.get("amount")}

	def refund(self, payment, amount):
		r = self._post("/refunds", {"payment_intent": payment.gateway_reference, "amount": self.minor_units(amount, payment.currency),
			"metadata[payment]": payment.name})
		return {"reference": r.get("id"), "status": "Succeeded" if r.get("status") == "succeeded" else "Pending"}


class RazorpayGateway(Gateway):
	name = "Razorpay"
	api = "https://api.razorpay.com/v1"

	def __init__(self, key_id, key_secret, webhook_secret):
		self.key_id, self.key_secret, self.webhook_secret = key_id, key_secret, webhook_secret

	def _post(self, path, data):
		import requests

		r = requests.post(f"{self.api}{path}", json=data, auth=(self.key_id, self.key_secret), timeout=20)
		if r.status_code >= 400:
			raise GatewayError(r.text[:500])
		return r.json()

	def create_checkout(self, payment):
		o = self._post("/payment_links", {"amount": self.minor_units(payment.amount, payment.currency), "currency": payment.currency,
			"reference_id": payment.name, "description": f"{payment.payment_type} {payment.booking or ''}", "notes": {"payment": payment.name},
			"callback_url": get_url(f"/marketplace/account/payments/{payment.name}"), "callback_method": "get"})
		return {"reference": o.get("id"), "checkout_url": o.get("short_url"), "status": "Pending"}

	def parse_webhook(self, headers, body):
		sig = headers.get("X-Razorpay-Signature") or headers.get("x-razorpay-signature") or ""
		expected = hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
		if not sig or not hmac.compare_digest(expected, sig):
			raise GatewayError("Razorpay signature mismatch")
		ev = json.loads(body)
		etype = ev.get("event")
		pl = ev.get("payload", {})
		link = (pl.get("payment_link") or {}).get("entity", {})
		pay = (pl.get("payment") or {}).get("entity", {})
		status = {"payment_link.paid": "succeeded", "payment.failed": "failed", "refund.processed": "refunded"}.get(etype, "ignored")
		return {"event_id": headers.get("X-Razorpay-Event-Id") or f"{etype}:{pay.get('id') or link.get('id')}", "event_type": etype,
			"payment": (link.get("notes") or pay.get("notes") or {}).get("payment") or link.get("reference_id"),
			"reference": pay.get("id") or link.get("id"), "status": status, "amount_minor": link.get("amount_paid") or pay.get("amount")}

	def refund(self, payment, amount):
		r = self._post(f"/payments/{payment.gateway_reference}/refund", {"amount": self.minor_units(amount, payment.currency), "notes": {"payment": payment.name}})
		return {"reference": r.get("id"), "status": "Succeeded" if r.get("status") == "processed" else "Pending"}


def get_gateway(name=None):
	s = frappe.get_cached_doc("Marketplace Settings")
	name = name or s.payment_gateway or "Manual"
	if name == "Stripe":
		return StripeGateway(s.get_password("stripe_secret_key", raise_exception=False), s.get_password("stripe_webhook_secret", raise_exception=False) or "")
	if name == "Razorpay":
		return RazorpayGateway(s.razorpay_key_id, s.get_password("razorpay_key_secret", raise_exception=False), s.get_password("razorpay_webhook_secret", raise_exception=False) or "")
	return ManualGateway()

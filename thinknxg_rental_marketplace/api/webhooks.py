"""Payment provider webhooks. Signature-verified and de-duplicated by provider event id."""
import frappe

from thinknxg_rental_marketplace.services import payments
from thinknxg_rental_marketplace.services.payments.gateways import GatewayError


def _handle(gateway):
	body = frappe.request.get_data()
	try:
		res = payments.process_webhook(gateway, dict(frappe.request.headers), body)
		frappe.db.commit()
		return res
	except GatewayError as e:
		frappe.db.rollback()
		frappe.local.response.http_status_code = 400
		return {"error": str(e)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def stripe():
	return _handle("Stripe")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def razorpay():
	return _handle("Razorpay")

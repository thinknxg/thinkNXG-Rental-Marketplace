"""In-platform notifications + queued email. Never blocks the business transaction."""
import frappe
from frappe.utils import get_url

from thinknxg_rental_marketplace.services import context


def notify(users, title, message="", link=None, category="System", ref=None, email=True):
	users = [u for u in (users if isinstance(users, (list, tuple, set)) else [users]) if u and u not in ("Guest",)]
	for u in sorted(set(users)):
		doc = frappe.get_doc({
			"doctype": "Marketplace Notification", "recipient": u, "title": title[:140], "message": message,
			"link": link, "category": category,
			"reference_doctype": ref.doctype if ref else None, "reference_name": ref.name if ref else None,
		})
		doc.flags.ignore_permissions = True
		doc.insert()
	if email and users:
		try:
			frappe.sendmail(
				recipients=sorted(set(users)), subject=title,
				message=f"<p>{frappe.utils.escape_html(message or '')}</p>" + (f'<p><a href="{get_url(link)}">{frappe._("Open")}</a></p>' if link else ""),
				now=False, delayed=True,
			)
		except Exception:
			frappe.log_error(title="Marketplace email failed")


def to_vendor(vendor, title, message="", link=None, category="Tender", ref=None, min_role="Staff"):
	notify(context.vendor_users(vendor, min_role), title, message, link, category, ref)


def to_customer(customer, title, message="", link=None, category="Offer", ref=None):
	notify(context.customer_users(customer), title, message, link, category, ref)


def to_operators(title, message="", link=None, category="System", ref=None, kind="moderator"):
	notify(context.operator_users(kind), title, message, link, category, ref, email=False)


def send_tender_invitations(tender, invitations):
	"""Background job: one notification per invited vendor."""
	t = frappe.db.get_value("Marketplace Tender", tender, ["title", "submission_deadline", "transaction_type", "city"], as_dict=True)
	for inv in invitations:
		vendor = frappe.db.get_value("Tender Invitation", inv, "vendor")
		to_vendor(vendor, frappe._("New tender: {0}").format(t.title),
			frappe._("{0} requirement in {1}. Offers close {2}.").format(t.transaction_type, t.city or "-", frappe.utils.format_datetime(t.submission_deadline)),
			link=f"/marketplace/vendor/tenders/{tender}", category="Tender", ref=frappe._dict(doctype="Marketplace Tender", name=tender))

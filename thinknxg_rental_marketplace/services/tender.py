"""Tender engine: creation from a request, lifecycle state machine, matching & invitations, deadlines."""
import frappe
from frappe.utils import add_to_date, cint, flt, get_datetime, getdate, now_datetime

from thinknxg_rental_marketplace.services import audit, matching, notifications
from thinknxg_rental_marketplace.services.context import settings
from thinknxg_rental_marketplace.services.errors import Conflict, fail, forbid

TRANSITIONS = {
	"Draft": {"Submitted", "Cancelled"},
	"Submitted": {"Published", "Cancelled", "Suspended"},
	"Published": {"Supplier Matching", "Cancelled", "Suspended"},
	"Supplier Matching": {"Invitation Sent", "Bidding Open", "Cancelled", "Suspended"},
	"Invitation Sent": {"Bidding Open", "Cancelled", "Suspended"},
	"Bidding Open": {"Bidding Closed", "Cancelled", "Suspended"},
	"Bidding Closed": {"Evaluation", "Expired", "Cancelled", "Bidding Open", "Suspended"},
	"Evaluation": {"Awarded", "Cancelled", "Expired", "Bidding Open", "Suspended"},
	"Awarded": {"Evaluation"},  # only when an unpaid booking lapses
	"Suspended": {"Published", "Bidding Open", "Bidding Closed", "Evaluation", "Cancelled"},
	"Cancelled": set(),
	"Expired": {"Bidding Open"},  # re-opened by an extension
}
OPEN_FOR_OFFERS = {"Bidding Open"}
ACCEPTANCE_STATES = {"Bidding Closed", "Evaluation"}
OPEN_TYPES_VISIBLE = {"Public Marketplace", "Verified Suppliers", "Category Restricted", "Location Restricted"}
OFFER_LIVE = ("Submitted", "Under Review", "Technically Accepted", "Commercially Accepted")


def set_status(doc, to, reason=None, save=True):
	frm = doc.status
	if to == frm:
		return doc
	if to not in TRANSITIONS.get(frm, set()):
		fail("TENDER_STATE", "Tender cannot move from {frm} to {to}.", Conflict, frm=frm, to=to)
	doc.status = to
	now = now_datetime()
	if to == "Published":
		doc.published_on = doc.published_on or now
	elif to == "Bidding Open":
		doc.opening_date = doc.opening_date or now
	elif to in ("Bidding Closed",):
		doc.closing_date = now
	elif to == "Awarded":
		doc.awarded_on = now
	if reason and to == "Cancelled":
		doc.cancel_reason = reason
	if save:
		doc.flags.ignore_permissions = True
		doc.save()
	audit.log("tender.status", doc.doctype, doc.name, frm, to, reason=reason)
	return doc


def lock(name):
	row = frappe.db.sql("select name from `tabMarketplace Tender` where name=%s for update", name)
	if not row:
		fail("NOT_FOUND", "Tender not found.")
	return frappe.get_doc("Marketplace Tender", name)


def create_from_request(req):
	s = settings()
	existing = frappe.db.get_value("Marketplace Tender", {"rental_request": req.name, "status": ["not in", ["Cancelled", "Expired"]]}, "name")
	if existing:
		return frappe.get_doc("Marketplace Tender", existing)
	deadline = add_to_date(now_datetime(), hours=cint(s.default_bidding_hours) or 72)
	t = frappe.get_doc({
		"doctype": "Marketplace Tender", "title": req.title, "rental_request": req.name, "customer": req.customer,
		"transaction_type": req.transaction_type, "category": req.category, "status": "Draft",
		"tender_type": s.default_tender_type or "Open", "visibility": s.default_visibility or "Verified Suppliers",
		"confidentiality": s.default_confidentiality or "Sealed", "disclosure_stage": s.default_disclosure_stage or "On Award",
		"evaluation_method": "Customer Choice", "submission_deadline": deadline,
		"required_from": req.required_from, "required_to": req.required_to, "duration_days": req.duration_days,
		"contract_start": req.contract_start, "contract_months": req.contract_months, "expected_delivery_date": req.expected_delivery_date,
		"city": req.city, "state": req.state, "country": req.country, "currency": req.currency, "budget_max": req.budget_max,
		"require_verified": 1, "allow_revisions": 1, "max_revisions": cint(s.max_revisions) or 5, "allow_alternatives": 1,
		"items": [{"equipment_name": i.equipment_name, "category": i.category or req.category, "qty": i.qty, "uom": i.uom,
			"specifications": i.specifications, "condition_required": i.condition_required, "brand_preference": i.brand_preference,
			"accept_alternatives": i.accept_alternatives, "certifications_required": i.certifications_required, "request_item": i.name} for i in req.items],
	})
	for c in frappe.get_all("Offer Evaluation Criterion", fields=["name", "default_weight"], order_by="creation asc"):
		t.append("criteria", {"criterion": c.name, "weight": c.default_weight})
	t.flags.ignore_permissions = True
	t.insert()
	audit.log("tender.created", t.doctype, t.name, None, "Draft", rental_request=req.name)
	set_status(t, "Submitted")
	return t


def publish(name, actor="system"):
	t = lock(name)
	s = settings()
	min_hours = cint(s.min_bidding_hours) or 1
	if get_datetime(t.submission_deadline) < add_to_date(now_datetime(), hours=min_hours):
		t.submission_deadline = add_to_date(now_datetime(), hours=max(min_hours, cint(s.default_bidding_hours) or 72))
	if t.status == "Suspended":
		set_status(t, "Published")
	elif t.status == "Submitted":
		set_status(t, "Published")
	set_status(t, "Supplier Matching")
	invited = []
	if t.visibility != "Selected Suppliers":
		cands = [c for c in matching.candidates(t) if c.score >= flt(s.min_match_score)]
		limit = cint(s.max_invitations) or 25
		invited = invite(t, cands[:limit], source="Auto", notify=False)
	set_status(t, "Invitation Sent" if invited else "Bidding Open")
	if t.status == "Invitation Sent":
		set_status(t, "Bidding Open")
	refresh_counts(t)
	frappe.db.set_value("Rental Request", t.rental_request, "status", "Tendered")
	if invited:
		frappe.enqueue("thinknxg_rental_marketplace.services.notifications.send_tender_invitations", tender=t.name,
			invitations=invited, enqueue_after_commit=True, queue="short")
	notifications.to_customer(t.customer, frappe._("Your tender {0} is live").format(t.name),
		frappe._("{0} suppliers were invited. Offers close {1}.").format(len(invited), frappe.utils.format_datetime(t.submission_deadline)),
		link=f"/marketplace/account/requests/{t.rental_request}", category="Tender", ref=t)
	return t


def invite(t, candidates, source="Manual", notify=True):
	"""candidates: iterable of dicts with vendor (+ score, reasons) or vendor names."""
	created = []
	for c in candidates:
		c = c if isinstance(c, dict) else frappe._dict(vendor=c, score=0, reasons=[])
		if frappe.db.get_value("Marketplace Vendor", c["vendor"], "status") != "Approved":
			continue
		if frappe.db.exists("Tender Invitation", {"tender": t.name, "vendor": c["vendor"]}):
			continue
		inv = frappe.get_doc({"doctype": "Tender Invitation", "tender": t.name, "vendor": c["vendor"], "status": "Invited",
			"source": source, "match_score": c.get("score") or 0, "match_reasons": ", ".join(c.get("reasons") or []),
			"invited_on": now_datetime()})
		inv.flags.ignore_permissions = True
		inv.insert()
		created.append(inv.name)
	if created:
		audit.log("tender.invited", t.doctype, t.name, count=len(created), source=source)
	if notify and created:
		frappe.enqueue("thinknxg_rental_marketplace.services.notifications.send_tender_invitations", tender=t.name,
			invitations=created, enqueue_after_commit=True, queue="short")
	refresh_counts(t)
	return created


def refresh_counts(t):
	inv = frappe.db.count("Tender Invitation", {"tender": t.name, "status": ["!=", "Excluded"]})
	offers = frappe.db.count("Supplier Offer", {"tender": t.name, "status": ["in", list(OFFER_LIVE) + ["Accepted"]]})
	frappe.db.set_value("Marketplace Tender", t.name, {"invited_count": inv, "offers_count": offers}, update_modified=False)
	t.invited_count, t.offers_count = inv, offers
	req_status = frappe.db.get_value("Rental Request", t.rental_request, "status")
	if offers and req_status == "Tendered":
		frappe.db.set_value("Rental Request", t.rental_request, "status", "Offers Received")


def vendor_access(t, vendor, create=True):
	"""Returns the vendor's invitation (creating one for open tenders the vendor is eligible for), else None."""
	inv = frappe.db.get_value("Tender Invitation", {"tender": t.name, "vendor": vendor}, ["name", "status"], as_dict=True)
	if inv:
		return None if inv.status == "Excluded" else inv
	if t.tender_type == "Open" and t.visibility in OPEN_TYPES_VISIBLE and t.status in OPEN_FOR_OFFERS:
		cands = [c for c in matching.candidates(t) if c.vendor == vendor]
		if cands and create:
			name = invite(t, cands, source="Open Tender", notify=False)
			return frappe._dict(name=name[0], status="Invited") if name else None
	return None


def require_vendor_access(t, vendor):
	inv = vendor_access(t, vendor)
	if not inv:
		forbid("TENDER_NOT_AVAILABLE", "This tender is not available to your business.")
	return inv


def extend(name, new_deadline, reason=None):
	t = lock(name)
	new_deadline = get_datetime(new_deadline)
	if new_deadline <= now_datetime():
		fail("DEADLINE_PAST", "The new deadline must be in the future.")
	if t.status in ("Awarded", "Cancelled"):
		fail("TENDER_STATE", "Awarded or cancelled tenders cannot be extended.", Conflict)
	t.submission_deadline = new_deadline
	t.extension_count = cint(t.extension_count) + 1
	if t.status in ("Bidding Closed", "Evaluation", "Expired"):
		set_status(t, "Bidding Open", save=False)
	t.flags.ignore_permissions = True
	t.save()
	audit.log("tender.extended", t.doctype, t.name, deadline=str(new_deadline), reason=reason)
	for inv in frappe.get_all("Tender Invitation", filters={"tender": t.name, "status": ["!=", "Excluded"]}, pluck="vendor"):
		notifications.to_vendor(inv, frappe._("Deadline extended: {0}").format(t.title), frappe._("New deadline {0}").format(frappe.utils.format_datetime(new_deadline)),
			link=f"/marketplace/vendor/tenders/{t.name}", ref=t)
	return t


def cancel(name, reason):
	t = lock(name)
	if t.status in ("Awarded",) and t.booking and frappe.db.get_value("Marketplace Booking", t.booking, "status") not in ("Cancelled",):
		fail("TENDER_BOOKED", "Cancel the booking first.", Conflict)
	set_status(t, "Cancelled", reason)
	for off in frappe.get_all("Supplier Offer", filters={"tender": t.name, "status": ["in", list(OFFER_LIVE) + ["Draft"]]}, pluck="name"):
		frappe.db.set_value("Supplier Offer", off, "status", "Not Awarded")
	frappe.db.set_value("Rental Request", t.rental_request, {"status": "Cancelled", "cancel_reason": reason})
	for v in frappe.get_all("Tender Invitation", filters={"tender": t.name}, pluck="vendor"):
		notifications.to_vendor(v, frappe._("Tender cancelled: {0}").format(t.title), reason or "", link=f"/marketplace/vendor/tenders/{t.name}", ref=t)
	return t


def suspend(name, reason):
	t = lock(name)
	t.moderation_notes = reason
	return set_status(t, "Suspended", reason)


def resume(name):
	t = lock(name)
	if t.status != "Suspended":
		fail("TENDER_STATE", "Tender is not suspended.", Conflict)
	if not t.published_on:
		return publish(name)
	to = "Bidding Open" if get_datetime(t.submission_deadline) > now_datetime() else ("Evaluation" if t.offers_count else "Bidding Closed")
	return set_status(t, to)


def close_bidding(name, early=False):
	t = lock(name)
	if t.status != "Bidding Open":
		return t
	if early:
		pending = frappe.db.count("Tender Invitation", {"tender": t.name, "status": ["in", ["Invited", "Viewed", "Interested"]]})
		if pending:
			fail("INVITEES_PENDING", "{n} invited suppliers have not responded yet; bidding can only close early once all have.", Conflict, n=pending)
	refresh_counts(t)
	set_status(t, "Bidding Closed")
	if t.offers_count:
		set_status(t, "Evaluation")
		for off in frappe.get_all("Supplier Offer", filters={"tender": t.name, "status": "Submitted"}, pluck="name"):
			frappe.db.set_value("Supplier Offer", off, "status", "Under Review")
		notifications.to_customer(t.customer, frappe._("{0} offers ready to compare").format(t.offers_count), t.title,
			link=f"/marketplace/account/tenders/{t.name}/compare", category="Offer", ref=t)
	else:
		set_status(t, "Expired")
		frappe.db.set_value("Rental Request", t.rental_request, "status", "Closed")
		notifications.to_customer(t.customer, frappe._("No offers received for {0}").format(t.title),
			frappe._("You can extend the deadline from your request page."), link=f"/marketplace/account/requests/{t.rental_request}", ref=t)
	# drafts never submitted can no longer be sent
	for off in frappe.get_all("Supplier Offer", filters={"tender": t.name, "status": "Draft"}, pluck="name"):
		frappe.db.set_value("Supplier Offer", off, "status", "Expired")
	return t


def process_deadlines():
	"""Scheduler (every 5 min): close bidding at deadline, expire lapsed offers."""
	for name in frappe.get_all("Marketplace Tender", filters={"status": "Bidding Open", "submission_deadline": ["<=", now_datetime()]}, pluck="name"):
		try:
			close_bidding(name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Tender close failed {name}")
	for name in frappe.get_all("Supplier Offer", filters={"status": ["in", list(OFFER_LIVE)], "valid_until": ["<", getdate()]}, pluck="name"):
		frappe.db.set_value("Supplier Offer", name, "status", "Expired")
		audit.log("offer.expired", "Supplier Offer", name, None, "Expired")
	frappe.db.commit()

"""Supplier matching for a tender.

Eligibility (hard rules): vendor Approved · verified when the tender requires it · subscription live (when
required) · category coverage · service location in the tender's country · rating ≥ tender minimum.
Scoring (0–100, soft): published listings in the category with enough *free quantity for the tender window*
(the only availability evidence we accept), same state/city, rating, past win rate.
Category coverage alone gives a vendor a low score — it is not proof of physical availability.
"""
import frappe
from frappe.utils import flt, getdate

from thinknxg_rental_marketplace.services import availability, commission


def score_vendor(v, t):
	"""Pure. v: dict(status, verified, sub_active, categories:set, countries:set, states:set, cities:set, rating,
	offers_submitted, offers_won, listing_free_qty:float, listing_count:int). t: dict(category_lineage:set,
	country, state, city, require_verified, min_rating, required_qty). Returns (eligible, score, reasons)."""
	reasons = []
	if v["status"] != "Approved":
		return False, 0, ["not approved"]
	if t.get("require_verified") and not v.get("verified"):
		return False, 0, ["not verified"]
	if not v.get("sub_active"):
		return False, 0, ["no active subscription"]
	if not (v["categories"] & t["category_lineage"]):
		return False, 0, ["category not covered"]
	if t.get("country") and t["country"] not in v["countries"]:
		return False, 0, ["does not serve country"]
	if flt(t.get("min_rating")) and flt(v.get("rating")) < flt(t["min_rating"]) and v.get("review_count"):
		return False, 0, ["rating below minimum"]
	score = 20.0
	reasons.append("category covered")
	if v.get("listing_count"):
		score += 15
		reasons.append(f"{v['listing_count']} published listing(s)")
		if flt(v.get("listing_free_qty")) >= flt(t.get("required_qty")) > 0:
			score += 25
			reasons.append("free quantity covers requirement")
		elif flt(v.get("listing_free_qty")) > 0:
			score += 10
			reasons.append("partial free quantity")
	if t.get("state") and t["state"].lower() in v["states"]:
		score += 10
		reasons.append("serves state")
	if t.get("city") and t["city"].lower() in v["cities"]:
		score += 10
		reasons.append("serves city")
	if v.get("review_count"):
		score += min(flt(v.get("rating")) / 5.0 * 15, 15)
		reasons.append(f"rating {flt(v.get('rating')):.1f}")
	if v.get("offers_submitted"):
		score += min(flt(v.get("offers_won")) / max(flt(v["offers_submitted"]), 1) * 5, 5)
	return True, round(min(score, 100), 1), reasons


def descendants(category):
	lft, rgt = frappe.db.get_value("Marketplace Category", category, ["lft", "rgt"]) or (0, 0)
	return set(frappe.get_all("Marketplace Category", filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, pluck="name")) or {category}


def candidates(tender):
	t = frappe.get_doc("Marketplace Tender", tender) if isinstance(tender, str) else tender
	lineage = set(commission.category_lineage(t.category)) | descendants(t.category)
	required_qty = sum(flt(i.qty) for i in t.items)
	start, end = availability.window(t.transaction_type, t.required_from or t.contract_start or t.expected_delivery_date or getdate(),
		t.required_to or (frappe.utils.add_months(t.contract_start, t.contract_months or 1) if t.contract_start else None))
	tctx = dict(category_lineage=lineage, country=t.country, state=t.state, city=t.city, require_verified=t.require_verified,
		min_rating=t.min_vendor_rating, required_qty=required_qty)
	s = frappe.get_cached_doc("Marketplace Settings")
	vendors = frappe.get_all("Marketplace Vendor", filters={"status": "Approved"},
		fields=["name", "status", "verified", "rating", "review_count", "offers_submitted", "offers_won", "country", "state", "city"])
	out = []
	from thinknxg_rental_marketplace.services.subscriptions import active_subscription

	tx_field = {"Hire": "allow_hire", "Sale": "allow_sale", "Contract": "allow_contract"}[t.transaction_type]
	for v in vendors:
		cats = set(frappe.get_all("Vendor Category", filters={"parent": v.name, "parenttype": "Marketplace Vendor"}, pluck="category"))
		locs = frappe.get_all("Vendor Location", filters={"parent": v.name, "parenttype": "Marketplace Vendor"}, fields=["country", "state", "city"])
		countries = {l.country for l in locs} | {v.country}
		states = {(l.state or "").lower() for l in locs} | {(v.state or "").lower()}
		cities = {(l.city or "").lower() for l in locs} | {(v.city or "").lower()}
		listings = frappe.get_all("Marketplace Listing", filters={"vendor": v.name, "status": "Published", "category": ["in", list(lineage)], tx_field: 1}, pluck="name")
		free = sum(availability.available_qty(l, start, end) for l in listings)
		vctx = dict(status=v.status, verified=v.verified, sub_active=(bool(active_subscription(v.name)) or not s.subscription_required),
			categories=cats, countries=countries, states=states, cities=cities, rating=v.rating, review_count=v.review_count,
			offers_submitted=v.offers_submitted, offers_won=v.offers_won, listing_free_qty=free, listing_count=len(listings))
		ok, score, reasons = score_vendor(vctx, tctx)
		if ok:
			out.append(frappe._dict(vendor=v.name, score=score, reasons=reasons, free_qty=free))
	out.sort(key=lambda r: (-r.score, r.vendor))
	return out


def is_eligible(tender_doc, vendor):
	return any(c.vendor == vendor for c in candidates(tender_doc))

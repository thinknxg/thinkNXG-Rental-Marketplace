# Phase 2 — Technical Architecture: thinkNXG Rental Marketplace

App: `thinknxg_rental_marketplace` · Module: `Rental Marketplace` · Frappe v16 + ERPNext v16 · MariaDB.

```
POST REQUIREMENT → CREATE TENDER → MATCH SUPPLIERS → RECEIVE OFFERS → COMPARE → SELECT → BOOK → PAY → FULFIL → SETTLE → REVIEW
 Rental Request    Marketplace     Tender           Supplier Offer   Offer        accept   Marketplace  Marketplace  Vendor Order /     Marketplace   Marketplace
                   Tender          Invitation       (+ Offer         Evaluation   _offer   Booking      Payment      Hire Order bridge  Settlement    Review
                                                    Revision)
```

## 1. Layers

```
www/marketplace/*            Jinja public pages (SSR, SEO) + 3 SPAs (customer, vendor, operator)
public/js/mp_*.js            vanilla JS, no build step (same approach as the source app)
api/{public,customer,vendor,operator,files,webhooks}.py   whitelisted endpoints — thin, actor-resolving
services/*.py                business logic (pure functions where possible, unit-tested)
rental_marketplace/doctype   data model + controller validation (defence in depth)
services/rental_bridge.py    optional link into thinknxg_rental / ERPNext documents
```

Every API endpoint resolves the actor on the server (`services/context.py`) — vendor via `Vendor User`,
customer via `Marketplace Customer` membership. IDs of vendor/customer and all monetary totals sent from the
browser are ignored; totals are recomputed with `Decimal` in `services/pricing.py`.

## 2. Roles

| Role | Desk | Purpose |
|---|---|---|
| Marketplace Admin | yes | everything in the operator console |
| Marketplace Moderator | yes | vendor verification, tender moderation, reviews, disputes |
| Marketplace Finance | yes | payments, refunds, commissions, settlements, subscriptions |
| Marketplace Vendor | no (website user) | vendor portal only, through APIs |
| Marketplace Customer | no (website user) | customer portal only, through APIs |

Portal roles hold **no DocType permissions**, so `/api/resource/*` and `frappe.client.*` return 403 for them;
`permission_query_conditions` / `has_permission` hooks add a second wall on the core DocTypes.

## 3. Entities and state machines

* **Marketplace Vendor** `Draft → Submitted → Documents Pending → Under Review → Approved | Rejected`, `Approved → Suspended → Approved`, `* → Deactivated`
* **Rental Request** `Draft → Submitted → Tendered → Offers Received → Awarded → Booked → Closed | Cancelled`
* **Marketplace Tender** `Draft → Submitted → Published → Supplier Matching → Invitation Sent → Bidding Open → Bidding Closed → Evaluation → Awarded | Cancelled | Expired` (+ `Suspended` admin hold)
* **Supplier Offer** `Draft → Submitted → Under Review → Technically Accepted | Technically Rejected → Commercially Accepted → Accepted`; side exits `Withdrawn`, `Expired`, `Superseded`, `Rejected`, `Not Awarded`
* **Marketplace Booking** — per transaction type:
  * Hire: `Pending Payment → Confirmed → Dispatched → On Hire → Off-Hire Requested → Returned → Completed`
  * Sale: `Pending Payment → Confirmed → Dispatched → Delivered → Completed`
  * Contract: `Pending Payment → Confirmed → Mobilized → Active → Demobilized → Completed`
  * any pre-completion state → `Cancelled`
* **Vendor Subscription** `Trial → Active → Grace → Expired`; `Cancelled`, `Superseded` on upgrade/downgrade

## 4. Concurrency & integrity

* `accept_offer` runs in one DB transaction: `SELECT … FOR UPDATE` on the tender row, then the offer row, then
  every listing row being allocated; re-checks states, deadline, validity, vendor status and availability
  (`Listing Availability` overlap sum) before inserting the booking and allocation rows. A unique
  `idempotency_key` on the booking makes retries return the same booking.
* Offer revisions are immutable `Offer Revision` snapshots (JSON); the booking stores the accepted revision
  snapshot — later edits never change a booking.
* `Marketplace Audit Event` records every state transition (insert-only; no write/delete perms).
* Tender deadlines are enforced server-side on every offer write and by a scheduler (`every 5 min`) that closes
  bidding, expires tenders and offers.

## 5. Confidentiality

Configured per tender (`Sealed` default): suppliers never receive competitor prices, identities or counts beyond
"you are one of N invited" when allowed; `Rank Only` reveals the supplier's own rank. Customer identity and site
contact are hidden from suppliers until the tender's disclosure stage (`On Award` default). Private files are
served only through `api/files.download`, which checks marketplace-level access.

## 6. Money

`services/pricing.py` (Decimal, ROUND_HALF_UP, currency precision). Commission resolution in
`services/commission.py`: most specific enabled `Commission Rule` wins (vendor > plan > category+type > category >
type > default), ties by `priority`. Payments go through `services/payments/` — a gateway interface with
`manual`, `stripe` and `razorpay` adapters; a payment is only `Succeeded` after a verified webhook or a Finance
confirmation. Settlements are built from succeeded payments of completed bookings; `Paid` requires a payout
reference — nothing is ever reported as paid out on our own say-so.

## 7. Integration with thinkNXG Rental (optional)

Vendor has `erp_company` set → on booking confirmation the bridge creates ERPNext `Customer` (once per
marketplace customer), `Rental Site`, and a draft `Hire Order` (Hire / Contract) or `Sales Order` (Sale) in that
company, links it on the `Vendor Order`, and listens to `Hire Order`, `Rental Contract`, `Hire Delivery Order`,
`Hire Off-Hire Note`, `Sales Order`, `Delivery Note` submissions to move the vendor order/booking forward.

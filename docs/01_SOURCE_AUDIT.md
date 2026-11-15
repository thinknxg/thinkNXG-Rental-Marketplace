# Phase 1 — Source Repository Audit: thinknxg/ThinkNXG-Rental

Audited commit: `1eeb96c` (Merge PR #15, public-website), app `thinknxg_rental`, Frappe/ERPNext `>=15,<17`, Python `>=3.14`.

## 1. What the source app is

A **single-operator** formwork & scaffolding rental ERP built on ERPNext stock. One ERPNext Company owns (or
cross-hires) the equipment, keeps it in rental warehouses, and rents it to its own customers. It is not
multi-vendor: every DocType assumes one rental business per site/company.

## 2. Business capabilities found

| Area | DocTypes / services | Notes |
|---|---|---|
| Item rental master | `Rental Item Profile` (+ `Rental Item Specification`, `Rental Item Image`), Item form section (`services/item_rental.py`) | daily/weekly/monthly rates, deposit rate, replacement/repair/lost charges, website flags, slug route |
| Rates | `Rental Rate Card` (+ items), `services/utils.get_rental_rate` | customer-specific rate cards with validity |
| Deal flow | Lead → Quotation → Hire Order / Hire Order Contract / Sales Order (`services/deal_flow.py`) | quotation hooks compute hire charges |
| Track A – item hire | `Hire Order` (+ `Hire Order Item`) → `Rental Contract` (`make_contract`) | HO-, submittable; validates `Rental Site` belongs to customer |
| Track B – job-type hire | `Hire Order Contract` (+ items/materials), `Job Type`, `Job Completion Report`, `JCR Billing Schedule`, `JCR Return` | job types exploded into stock items |
| Contract | `Rental Contract` (RC-, source_type/source_document dynamic link), `Rental Contract Extension` | billing cycle, grace days, deposits, totals at site |
| Reservation | `Rental Material Reservation` (per-row source warehouse) | `lock_bins`, `get_reserved_for_others(for_update=True)` — row-locked availability |
| Dispatch | `Hire Delivery Order` (+ items) | stock entry to site warehouse |
| Material at site | `Rental Ownership Ledger`, report `Material at Site` | ownership own vs cross-hire |
| Off-hire / returns | `Hire Off-Hire Note`, `Rental Return Inspection` | partial returns |
| Damage | `Rental Damage Settlement` (+ items), report `Damage and Loss Register` | |
| Billing | `Rental Billing Schedule` (+ items), `services/billing.run_daily_billing`, `jcr_billing` | daily scheduler, Sales Invoice generation |
| Cross hire | `Cross Hire Order`, `Cross Hire Off-Hire Note`, Purchase Order/Receipt/Invoice hooks | zero valuation receipts |
| Sites | `Rental Site` (customer, company, address, site warehouses) | |
| Customer portal | `/rental` SPA (`portal/*.py`, `public/customer_portal/*.js`), `Rental Portal Request` | filters every query by customers resolved for the session user |
| Admin portal | `/rental/admin` Command Center SPA | staff only |
| Public site | `/hire` (Jinja + `rw.css/rw.js`), `Rental Website *` DocTypes | catalogue, enquiry |
| Reports | 7 script reports | |

## 3. Frontend technology found

Frappe-native: Jinja `www/` pages + vanilla-JS single-page apps served through `website_route_rules`, plain
CSS with custom properties, self-hosted Barlow fonts. **No Vue/React build step.** The marketplace follows the
same approach (no new toolchain).

## 4. Reuse decision

| Marketplace need | Decision |
|---|---|
| Physical hire lifecycle (reserve → dispatch → at site → off-hire → inspection → damage → billing) | **Reuse** via an optional bridge (`services/rental_bridge.py`): an accepted marketplace booking for an *ERP-connected* vendor creates a draft `Hire Order` (+ `Rental Site`, ERPNext `Customer`) in the vendor's Company; the rental team continues with the existing `make_reservation` / `make_contract` flow. Status flows back through `doc_events` on Hire Order, Rental Contract, Hire Delivery Order, Hire Off-Hire Note. |
| Sale | ERPNext `Sales Order` draft (bridge) or marketplace-native fulfilment |
| Contract (long-term) | `Hire Order` with monthly billing cycle (bridge) + marketplace billing schedule |
| Availability per vendor | **New** `Listing Availability` ledger: the source app's bins are one company's stock and do not describe other vendors' fleets. When a listing is linked to an Item of a connected vendor, the bridge also checks `available_own_qty` from the source app. |
| Item master / specs / images | Pattern reused (spec + gallery child tables); separate `Marketplace Listing` because listings belong to vendors |
| Portal isolation pattern | Reused (server resolves the actor, every query filtered explicitly, no desk perms for portal roles) |
| Public website styling approach | Reused (Jinja + CSS variables), new design |

## 5. Constraints that shaped the architecture

* No runtime dependency on `thinknxg_rental`: the bridge imports it lazily, only when
  `"thinknxg_rental" in frappe.get_installed_apps()` and the setting *Use thinkNXG Rental engine* is on.
  `doc_events` keyed on its DocTypes are inert when the app is absent.
* Route prefixes `/rental` and `/hire` are taken by the source app — the marketplace uses `/marketplace`.
* Role names `Rental User`, `Rental Manager` and ERPNext `Customer`/`Supplier` are not reused for portal users;
  new roles `Marketplace Customer`, `Marketplace Vendor` avoid collisions.
* The source repository is untouched; nothing was copied from `thinknxg/car_rental_marketplace` — it was read only
  to confirm the request → tender → offer concept.

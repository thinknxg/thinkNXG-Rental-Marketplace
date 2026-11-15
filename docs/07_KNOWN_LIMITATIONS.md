# Known limitations

**Payments & payouts**
* Stripe and Razorpay adapters are implemented against the providers' documented APIs and signature schemes and the
  webhook path is tested with signed payloads, but they have **not been run against live/test merchant accounts**.
  Run a provider sandbox test before enabling. Gateway availability in Oman/GCC depends on merchant eligibility.
* Vendor payouts are recorded, not executed: Finance pays out by bank and records the reference. No split-payment /
  marketplace-payout provider (Stripe Connect, Razorpay Route) is integrated yet; the settlement engine is separate so one can be added.
* No ERPNext accounting entries are posted for marketplace payments, commission or settlements (records only).
  Sales/Purchase Invoices for commission and subscriptions are a next step.

**Rental engine integration**
* The bridge creates a **draft** Hire Order (hire & contract) or Sales Order (sale) for ERP-connected suppliers on the
  **same site**; the supplier's rental team submits it and continues with reservations, delivery, off-hire, billing and
  damage settlement in thinkNXG Rental. Status flows back on Hire Order / Rental Contract / Hire Delivery Order /
  Off-Hire Note / Sales Order / Delivery Note submission. Suppliers on their own separate ERP sites are not synced.
* Job-type contracts (Hire Order Contract / JCR) are not mapped; marketplace contracts map to monthly Hire Orders.
* For ERP-connected suppliers the marketplace availability ledger is authoritative for offers; the source app's bin
  availability is not yet checked at acceptance.

**Product scope**
* Early-return credits are handled through disputes/refunds, not automatic re-pricing.
* Reverse auctions use the standard deadline (no live bidding clock / auto-extension).
* Distance-based matching uses city/state/country; `delivery_radius_km` and coordinates are stored but not yet used for geo-distance.
* Arabic (RTL) UI and translations are not included yet (all strings are wrapped for translation server-side; portal JS strings are English).
* Public site uses an original SVG illustration; upload licensed construction photography in Settings → Hero image.
  Google Fonts (Barlow) load from Google at runtime; self-host for offline/strict-CSP deployments.
* Customer-company verification is a manual operator flag; supplier verification is document review by Moderators.
* Frappe's default user-creation throttle (60/hour) applies to self-registration.

**Testing**
* Automated tests run in one bench; load/concurrency testing (many simultaneous accepts) has been reasoned through row
  locks and unit-tested logically but not load-tested.

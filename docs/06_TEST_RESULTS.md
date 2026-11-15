# Automated test results

Run: `bench --site <site> run-tests --app thinknxg_rental_marketplace`
Environment: Frappe v16 (49789a1, 16.56.0) · ERPNext v16 (8e10a34, 16.55.0) · thinkNXG Rental `1eeb96c` (unmodified) · MariaDB 10.11 · Python 3.14.6 · run on 2026-11-15.

**Result: 24 / 24 passed.**

| Suite | Tests | What it proves |
|---|---|---|
| `tests/test_pure.py` | 13 | Decimal pricing (hire pro-rata, sale, contract, tax, 3-decimal OMR rounding, bad input), payment schedule split, availability peak-overlap maths, commission precedence & caps, matching hard rules & availability-weighted score, transparent weighted scoring |
| `tests/test_flow.py` | 10 | Full hire journey (multi-supplier registration → verification → listings → request → tender → matching → invitations → competing offers → revisions with history → sealed comparison → clarification → deadline enforcement → accept (idempotent, no double award) → availability reserved → vendor/customer isolation via portal API and REST → manual payment → dispatch/on-hire/off-hire/return with damage → balance gate → completion → review → settlement with payout reference → audit trail); no double allocation across overlapping bookings; sale flow; contract flow (6 monthly invoices, mobilisation); subscription limits, paid upgrade, grace & expiry; commission rules; supplier cancellation with refunds & tender re-open; tender expiry, extension and unpaid-booking release; Stripe webhook signature + replay protection; reverse auction ceiling/decrement and negotiated revision on counter-offer |
| `tests/test_bridge.py` | 1 | Confirmed marketplace hire for an ERP-connected supplier creates ERPNext Customer, Rental Site and draft Hire Order in thinkNXG Rental; submitting the Hire Order flows back; `make_contract` / `make_reservation` of the original app work on it |

## Raw output
```
thinknxg_rental_marketplace.tests.test_flow.TestMarketplaceFlow
    ✔  test_01_hire_end_to_end
    ✔  test_02_no_double_allocation
    ✔  test_03_sale_flow
    ✔  test_04_contract_flow
    ✔  test_05_entitlements_enforced
    ✔  test_06_commission_rules
    ✔  test_07_cancellation_reopens_tender
    ✔  test_08_no_offers_expires_and_unpaid_released
    ✔  test_09_stripe_webhook_signature_and_dedupe
    ✔  test_10_reverse_auction_and_negotiation
thinknxg_rental_marketplace.tests.test_bridge.TestRentalBridge
    ✔  test_confirmed_hire_becomes_hire_order_and_status_flows_back
Ran 11 tests in 8.828s
OK
thinknxg_rental_marketplace.tests.test_pure.TestAvailability
    ✔  test_back_to_back_do_not_overlap
    ✔  test_peak_counts_only_concurrent
thinknxg_rental_marketplace.tests.test_pure.TestCommission
    ✔  test_amount_caps
    ✔  test_most_specific_wins
thinknxg_rental_marketplace.tests.test_pure.TestMatchingAndScoring
    ✔  test_availability_drives_score
    ✔  test_hard_rules
    ✔  test_weighted_scoring_transparent
thinknxg_rental_marketplace.tests.test_pure.TestPricing
    ✔  test_contract_months
    ✔  test_hire_monthly_prorata_and_tax
    ✔  test_rejects_bad_input
    ✔  test_rounding_three_decimals
    ✔  test_sale_is_unit_priced
    ✔  test_schedule_contract_splits_balance
Ran 13 tests in 0.001s
OK
```

## Browser end-to-end (headless Chrome against a fresh demo site)

Script: `tools/e2e_browser.js`. Steps and observed result:

1. Supplier opens an open contract tender, picks own listing (1,200 free), enters rate → **server totals OMR 10,951.500** (600 × 2.8 × 6 + 350 charges + 5 % tax) → submits → offer `Submitted`, revision 1.
2. Customer completes the 8-step wizard (Hire · Ringlock · 400 pcs · dates · site · budget) → `REQ-2026-00003`, tender `TND-2026-00003` live, 1 supplier invited with reasons *category covered, 1 published listing, free quantity covers requirement, serves city*.
3. Customer opens sealed-then-opened comparison, accepts lowest offer → booking `BKG-2026-00001` (Pending Payment) → submits bank reference.
4. Finance confirms the payment in the operator console → booking `Confirmed`.
5. Winning supplier records dispatch (vehicle, driver) → `Dispatched`.

No JavaScript page errors. 13 public pages return 200. XSS probe (script/img payloads in listing title and supplier name) is escaped on every public page.

## Issues the tests caught and that were fixed
* Booking cancellation voided the refunds it had just created (payments sweep) — fixed.
* Identical uploaded files share one `file_url` in Frappe; ownership lookups are now owner-scoped and downloads check every matching File row.
* Negotiated-tender revisions were blocked at draft stage — fixed.
* Page `<title>` was outside the autoescape scope — fixed.
* Clean sites lacked UOMs / 3-decimal currency precision — installer now creates them.

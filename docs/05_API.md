# API reference

All endpoints are Frappe whitelisted methods: `POST /api/method/thinknxg_rental_marketplace.api.<module>.<function>` with form or JSON parameters and the `X-Frappe-CSRF-Token` header (session auth) or `Authorization: token <key>:<secret>`.
Errors carry a stable code in the message: `[CODE] human text` (HTTP 403 permission, 404 not found, 409 conflict, 402 plan limit, 417 validation).
The acting customer/vendor is always resolved from the session — never pass vendor, customer or amounts; they are ignored and recomputed.


## Public (guest) — `api.public`

| Function | Parameters | Notes |
|---|---|---|
| `site_info` | — | guest |
| `me` | — | guest |
| `listings` | q, category, mode, country, city, sort, page, page_length | guest |
| `listing` | slug | guest |
| `suppliers` | q, category, country, page, page_length | guest |
| `supplier` | slug | guest |
| `public_tenders` | page, page_length | guest |
| `reviews_highlight` | limit | guest; Testimonials come only from real, published reviews of completed bookings. |
| `register_vendor` | data | guest; rate-limited: (limit=5, seconds=3600) |
| `register_customer` | data | guest; rate-limited: (limit=5, seconds=3600) |
| `enquiry` | data | guest; rate-limited: (limit=5, seconds=3600) |

## Customer portal (role: Marketplace Customer) — `api.customer`

| Function | Parameters | Notes |
|---|---|---|
| `dashboard` | — |  |
| `profile` | — |  |
| `profile_update` | data |  |
| `member_add` | email, full_name, member_role |  |
| `sites` | — |  |
| `site_save` | data, name |  |
| `requests_list` | status, page |  |
| `request_get` | name |  |
| `request_save` | data, name, submit | rate-limited: (limit=30, seconds=3600) |
| `request_submit` | name |  |
| `request_cancel` | name, reason |  |
| `compare` | tender |  |
| `tender_extend` | tender, deadline, reason |  |
| `tender_close_early` | tender |  |
| `offer_shortlist` | offer, value |  |
| `offer_reject` | offer, reason |  |
| `clarification_raise` | tender, subject, message, offer, clarification_type, counter_amount |  |
| `clarification_respond` | name, response, share_with_all |  |
| `accept_offer` | offer, idempotency_key | rate-limited: (limit=20, seconds=600) |
| `bookings_list` | status, page |  |
| `booking_get` | name |  |
| `booking_action` | name, action, data |  |
| `pay` | booking, lines |  |
| `payment_get` | name |  |
| `payment_reference` | name, reference |  |
| `review_submit` | booking, data |  |
| `dispute_raise` | booking, data |  |
| `notifications` | — |  |
| `notifications_read` | names |  |

## Supplier portal (role: Marketplace Vendor) — `api.vendor`

| Function | Parameters | Notes |
|---|---|---|
| `dashboard` | — |  |
| `profile` | — |  |
| `profile_update` | data |  |
| `submit_for_review` | — |  |
| `document_add` | document_type, file_url, document_number, expiry_date |  |
| `staff_add` | email, full_name, vendor_role |  |
| `staff_toggle` | name, enabled |  |
| `listings_list` | status, q, page |  |
| `listing_get` | name |  |
| `listing_save` | data, name |  |
| `listing_status` | name, status |  |
| `availability_check` | listing, from_date, to_date |  |
| `availability_block` | listing, from_date, to_date, qty, entry_type, remarks |  |
| `availability_release` | name |  |
| `tenders_list` | scope, page |  |
| `tender_get` | name |  |
| `tender_respond` | name, response, reason |  |
| `offer_save` | tender, data |  |
| `offer_submit` | offer, reason, idempotency_key | rate-limited: (limit=60, seconds=3600) |
| `offer_withdraw` | offer, reason |  |
| `clarification_raise` | tender, subject, message, clarification_type |  |
| `clarification_respond` | name, response |  |
| `bookings_list` | status, transaction_type, page |  |
| `booking_get` | name |  |
| `booking_action` | name, action, data |  |
| `booking_dispute` | booking, data |  |
| `finance` | — |  |
| `subscription` | — |  |
| `subscribe` | plan, cycle |  |
| `promote` | promotion_type, days, listing |  |
| `reviews` | — |  |
| `review_respond` | name, response |  |
| `notifications` | — |  |
| `notifications_read` | names |  |

## Operator console (Marketplace Admin / Moderator / Finance) — `api.operator`

| Function | Parameters | Notes |
|---|---|---|
| `dashboard` | — |  |
| `vendors_list` | status, q, page |  |
| `vendor_get` | name |  |
| `vendor_set_status` | name, status, reason |  |
| `vendor_document_review` | name, status, remarks |  |
| `vendor_erp_link` | name, erp_company, erp_supplier |  |
| `customers_list` | status, q, page |  |
| `customer_set_status` | name, status, verified, reason |  |
| `tenders_list` | status, q, page |  |
| `tender_get` | name |  |
| `tender_candidates` | name |  |
| `tender_action` | name, action, data |  |
| `offer_evaluate` | offer, technical_result, commercial_result, manual_score, remarks |  |
| `offer_revision` | name |  |
| `bookings_list` | status, page |  |
| `booking_get` | name |  |
| `booking_action` | name, action, data |  |
| `payments_list` | status, payment_type, page |  |
| `payment_confirm` | name, reference | Finance confirms a manual payment (bank transfer received) or a pending manual refund (money sent). |
| `payment_fail` | name, reason |  |
| `payment_refund` | name, amount, reason |  |
| `commissions_list` | status, page |  |
| `settlements_list` | status, page |  |
| `settlement_action` | action, name, vendor, period_from, period_to, payout_reference |  |
| `subscriptions_list` | status, page |  |
| `listings_list` | status, q, page |  |
| `listing_moderate` | name, action, reason, until |  |
| `reviews_list` | status, page |  |
| `review_moderate` | name, status |  |
| `disputes_list` | status, page |  |
| `dispute_get` | name |  |
| `dispute_resolve` | name, status, resolution, refund_amount |  |
| `enquiries` | page |  |
| `audit_trail` | doctype, name, page |  |
| `notifications` | — |  |
| `notifications_read` | names |  |

## Files — `api.files`

| Function | Parameters | Notes |
|---|---|---|
| `upload` | public | rate-limited: (limit=60, seconds=600) |
| `download` | file_url |  |

## Payment webhooks (guest, signature-verified) — `api.webhooks`

| Function | Parameters | Notes |
|---|---|---|
| `stripe` | — | guest |
| `razorpay` | — | guest |

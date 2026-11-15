# Permissions & security

## Model
| Layer | Control |
|---|---|
| Roles | Portal roles `Marketplace Vendor` / `Marketplace Customer` are website users (no Desk) and hold **no DocType permissions**. `/api/resource/*`, `frappe.client.*` and report views return 403 for them (tested). |
| Actor resolution | `services/context.py` resolves the vendor (`Vendor User`) or customer (`Marketplace Customer` owner/member) from the session on every call. IDs sent from the browser are never used to decide ownership. |
| Tenant isolation | Every portal query filters by the resolved vendor/customer; every document fetch checks `doc.vendor == ctx.vendor` / `doc.customer == ctx.customer` (`_own()` helpers) before returning data. Tested: supplier B cannot read supplier A's booking or submit A's offer; customer 2 cannot read customer 1's request or booking. |
| Roles inside a tenant | Vendor: Staff (catalogue, drafts, fulfilment) < Manager (submit/withdraw offers, cancel, finance, staff) < Owner (bank details, owners, subscription). Customer: Viewer < Buyer (create, accept, pay) < Owner (company, members). |
| Operator roles | Admin (all), Moderator (vendors, tenders, offers, listings, reviews, disputes), Finance (payments, refunds, settlements, subscriptions, bank fields). Refunds in disputes need Finance. |
| Money | Totals are recomputed with `Decimal` from the immutable offer revision at acceptance; browser amounts are ignored. Payments become `Succeeded` only from a signature-verified, de-duplicated webhook or a Finance confirmation with a reference. Settlements need a payout reference to be marked Paid. |
| Concurrency | Accept locks tender → offer → listing rows (`SELECT … FOR UPDATE`), re-validates availability, and uses a unique idempotency key. Offer submission locks the tender to serialise against closing/award. |
| Confidentiality | Sealed bids by default; suppliers never receive competitor prices/identities (Rank Only reveals own rank). Customers see offers after bidding closes (Open mode excepted). Customer identity, site address and contacts are withheld from suppliers until the disclosure stage (default: award); vendor contacts are shown to customers only after confirmation. Budget hidden unless the operator enables it. |
| Files | Uploads are private by default, extension/size whitelisted (15 MB), images only may be public and only from suppliers/operators, SVG refused. Private files are served by `api.files.download`, which checks marketplace access: request owner, invited supplier for attachments marked *share with suppliers*, offer parties, vendor managers for verification docs, dispute parties, operators. Ownership lookups are owner-scoped because Frappe de-duplicates identical content. |
| Web | All portal calls are POST with the CSRF token. Jinja autoescape is enabled for all marketplace templates (Frappe does not autoescape by default); rich text comes only from Frappe-sanitised Text Editor fields. Boot JSON embedded in pages escapes `</`. |
| Abuse | `@rate_limit` on guest registration/enquiry (5/hour/IP), request saves (30/hour), offer submission (60/hour), accept (20/10 min), uploads (60/10 min). Frappe's user-creation throttle also applies. |
| Audit | `Marketplace Audit Event` (insert-only, no write/delete for anyone) records every state transition with actor, IP and data; `Offer Revision` snapshots are immutable; DocType `track_changes` is on for main documents. |
| Secrets | Gateway keys are `Password` fields; vendor bank fields are permlevel 1 (hidden from Moderators, Owner-only in the portal). |

## Not covered / to do before go-live
* Penetration test and dependency audit of the deployed stack.
* Malware scanning of uploads (add ClamAV or a storage-level scanner).
* 2FA for operator roles (enable Frappe 2FA for those roles).

# Installation, migration, configuration and production deployment

## Requirements
* Frappe Framework v16 and ERPNext v16 on the same bench (Python 3.14, Node 24, MariaDB 10.6+, Redis)
* Optional: thinkNXG Rental (`thinknxg_rental`) on the same site, for ERP-connected suppliers
* Verified on: Frappe 16.56.0, ERPNext 16.55.0, MariaDB 10.11, Python 3.14.6, Node 24

## Install
```bash
cd ~/frappe-bench
bench get-app https://github.com/thinknxg/thinknxg-rental-marketplace --branch main
bench --site <site> install-app thinknxg_rental_marketplace
bench build --app thinknxg_rental_marketplace     # or: bench setup symlinks
bench --site <site> migrate
```
The installer creates roles (Marketplace Admin / Moderator / Finance / Vendor / Customer), the default category tree
(Formwork, Scaffolding, Construction Equipment, Accessories and Materials + 25 sub-categories), Starter / Professional /
Enterprise plans, evaluation criteria, common UOMs and Marketplace Settings. If the default currency uses 3 decimals
(OMR, KWD, BHD…) and no currency precision is set, System Settings → Currency Precision is set to 3.

The site needs ERPNext's setup wizard completed (company, fiscal year) like any ERPNext site.

### Optional demo data
```bash
bench --site <site> execute thinknxg_rental_marketplace.demo.seed
```
Creates 3 approved suppliers with listings, a customer, a tender in evaluation with two offers and an open contract
tender. Demo password `Demo@12345` — **remove demo users before go-live.**

## Upgrade / migration
```bash
bench update --pull --apps thinknxg_rental_marketplace   # or git pull in apps/thinknxg_rental_marketplace
bench --site <site> migrate
bench build --app thinknxg_rental_marketplace
```
`after_migrate` re-checks roles, UOMs, criteria and currency precision. Data patches go in `patches.txt`.

## Configuration checklist (Desk → Marketplace Settings, or Operator console → Configuration)
1. **General** — marketplace name, operator company, default currency/country, support & sales emails.
2. **Tenders** — auto-publish (or moderate first), default type/visibility/confidentiality/disclosure stage, bidding hours,
   max invitations, minimum match score, max revisions, offer validity.
3. **Bookings & payments** — deposit %, payment hold hours, cancellation fee and free-cancellation window,
   gateway (`Manual`, `Stripe` or `Razorpay`) with secret and webhook secret.
4. **Commission & subscriptions** — default commission; add `Commission Rule`s for category / transaction type / plan /
   supplier overrides; subscription required, trial plan & days, grace days; edit plan limits & prices.
5. **thinkNXG Rental integration** — *Use thinkNXG Rental engine* + *Auto-create ERP documents*; then set **ERP Company**
   on each ERP-connected supplier (Operator console → Supplier → ERP connection) and link listings to ERPNext Items.
6. **Website** — hero title/subtitle/image (upload a licensed construction photo), colours, terms and privacy content.
7. **Email** — configure an outgoing Email Account; notifications and invitations are queued.
8. **Webhooks** — Stripe: `https://<site>/api/method/thinknxg_rental_marketplace.api.webhooks.stripe`
   (events `checkout.session.completed`, `checkout.session.async_payment_*`, `checkout.session.expired`, `charge.refunded`).
   Razorpay: `…/api.webhooks.razorpay` (events `payment_link.paid`, `payment.failed`, `refund.processed`).
9. **User creation throttle** — Frappe allows 60 new users per hour by default; for launch campaigns set
   `bench --site <site> set-config throttle_user_limit 500 --parse`.
10. Assign operator staff the Marketplace Admin / Moderator / Finance roles (Desk users).

## URLs
| Area | URL |
|---|---|
| Public marketplace | `/marketplace` (+ `/equipment`, `/categories`, `/suppliers`, `/how-it-works`, `/post-requirement`, `/for-suppliers`, `/about`, `/contact`, `/terms`, `/privacy`, `/register`) |
| Customer workspace | `/marketplace/account` |
| Supplier portal | `/marketplace/vendor` |
| Operator console | `/marketplace/operator` |

## Production deployment
```bash
sudo bench setup production <unix-user>        # nginx + supervisor
bench --site <site> enable-scheduler            # tender deadlines, unpaid-booking expiry, subscriptions
bench setup lets-encrypt <site>                 # TLS (required for payment webhooks)
```
* Scheduler jobs: every 5 min `tender.process_deadlines`, `booking.expire_unpaid`; daily `subscriptions.daily_lifecycle`,
  `trust.expire_promotions`, `maintenance.refresh_listing_availability`. Keep at least one `short` and `default` worker
  (tender invitations are background jobs).
* Back up with `bench --site <site> backup --with-files` — private uploads (BOQs, verification documents) are in
  `sites/<site>/private/files`.
* On thinkNXG Cloud, add the app to the bench group and deploy as usual.

## Publishing (repository)
Branches: `main` (stable), `develop` (integration), `feature/*` for each workstream. Tag releases `v1.x.y` from `main`.

# ThinkNXG Rental Marketplace: campaign collateral

Powered by thinkNXG. Every asset is generated from the HTML/SVG sources in `source-files/`; rebuild with
`python3 source-files/build_all.py build_info build_print build_social && node source-files/render.js`.

Previews: `previews/*.png` (one contact sheet per category).

## Infographics (`infographics/`, PNG at 2x; sources: `source-files/html/`, editable SVG in `source-files/svg/`)
| File | Content |
|---|---|
| `01-product-overview.png` (2400x3600) | What it is, problems solved, benefits, capabilities, fulfilment journey |
| `02-how-it-works.png` (3600x2000) | 11-step workflow. **Editable SVG:** `source-files/svg/02-how-it-works.svg` |
| `03-customer-benefits.png` (2400x3480) | Customer benefits with product screenshot |
| `04-supplier-benefits.png` (2400x3480) | Supplier benefits with product screenshot |
| `05-platform-ecosystem.png` (3600x2240) | Portals, engine, operator console, rental engine, payments. **Editable SVG:** `source-files/svg/05-platform-ecosystem.svg` |
| `06-feature-comparison.png` (2400x3160) | Hire vs Sale vs Contract; Marketplace vs thinkNXG Rental |

## Brochure and print (`brochures/`, `flyers/`)
| File | Content |
|---|---|
| `brochures/ThinkNXG-Rental-Marketplace-Brochure-A4.pdf` | 10-page A4 portrait, trim size (screen and office printing) |
| `brochures/...-Brochure-A4-print-3mm-bleed.pdf` | Same, 216 x 303 mm with 3 mm bleed, safe margin 14 mm (no crop marks) |
| `brochures/pages/*.png` | Page images at 110 dpi |
| `flyers/...-Flyer-A4(.pdf / -print-3mm-bleed.pdf)` | One-page product flyer |
| `flyers/...-Executive-Overview-A4(.pdf / -print-3mm-bleed.pdf)` | 2-page executive product overview |

Brochure pages: cover, introduction, challenge and solution, features, customer journey, supplier journey, tender and bidding,
rental fulfilment, benefits, call to action and contact.

## Social, banners, mockups
| Folder | Files |
|---|---|
| `social-media/` | LinkedIn posts 1200x627 (x3), LinkedIn banner 1584x396, Instagram 1080x1080 (x3), Instagram 1080x1350 workflow, WhatsApp poster 1080x1350 (PNG at 2x) |
| `banners/` | Website hero 1920x720 and mobile 750x900 |
| `product-mockups/` | Five framed product-screenshot mockups; raw crops in `screenshots/` |
| `source-files/` | `lib.py` (design system), `build_*.py`, `render.js`, `html/`, `svg/` (logo mark and lockups, 2 editable infographics) |

## Verified facts used
Features, states and workflows come from the two repos' README, docs and tests. Contact details: `info@thinknxg.com` (app email in
both repos), `thinknxg.com`, `thinknxg.com/rental` (supplied by you). No statistics, testimonials or customers are claimed.

## Honest notes
* **Screenshots are real product screens running on demo data** (labelled "demo data" on every asset). Names in them
  (e.g. Gulf Scaffold & Access LLC, Baushar tower) are demo records, not real customers.
* **No photography.** No licensed construction photos were available, so scaffolding and crane visuals are original vector
  illustrations. Swap in licensed photos before a paid campaign if you want photographic heroes.
* **Payments wording:** Stripe and Razorpay appear only as connectors on the ecosystem infographic and the executive
  overview carries the sandbox-test note; do not promote card payments as live until a sandbox test passes.
* The hand-off to thinkNXG Rental applies to suppliers on the same site; stated on the assets that mention it.
* PDFs embed Inter as outlined Type 3 fonts (Chrome output). Fine for office and most digital presses; ask your printer
  whether they need Type 1/OpenType embedding, and add crop marks on their side.
* The marketplace screenshots were taken before the footer text change; the footer is cropped out of every image.

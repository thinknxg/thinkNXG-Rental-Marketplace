from lib import *

PCSS = """
html,body{width:auto!important;height:auto!important;overflow:visible!important}
.pg{width:calc(210mm + var(--b)*2);height:calc(297mm + var(--b)*2);padding:var(--b);position:relative;overflow:hidden;break-after:page;page-break-after:always;font-size:10pt}
.pg.bg-grid-l{background-color:#f6f8fb}
.pg:last-child{break-after:auto;page-break-after:auto}
.in{width:100%;height:100%;padding:13mm 14mm 14mm;display:flex;flex-direction:column}
.ph{display:flex;justify-content:space-between;align-items:center;margin-bottom:9mm}
.ph .lab{font-size:7.5pt;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--amber)}
.pf{position:absolute;left:calc(var(--b) + 14mm);right:calc(var(--b) + 14mm);bottom:calc(var(--b) + 7mm);display:flex;justify-content:space-between;font-size:7.5pt;color:var(--s500)}
.dark .pf{color:rgba(255,255,255,.6)}
h1.t{font-size:30pt}h2.t{font-size:22pt;margin-bottom:3mm}h3.t{font-size:13pt;margin-bottom:1.5mm}
.lead{font-size:11.5pt;line-height:1.5;color:var(--s700)}.dark .lead{color:#c9d6ea}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:5mm}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:5mm}
.c{padding:5mm 5.5mm}
.small{font-size:9pt;line-height:1.45;color:var(--s700)}
.step{display:flex;gap:4.5mm;align-items:flex-start;margin-bottom:4.5mm}
.step .n{font-weight:800;font-size:20pt;color:var(--amber);width:11mm;letter-spacing:-.03em;line-height:1}
.chk{display:flex;gap:2.2mm;margin-top:1.8mm;font-size:9.5pt;font-weight:600}.chk svg{color:var(--amber);flex:none;margin-top:.3mm}.onamber .chk svg{color:var(--navy)}.onamber .chk{color:var(--navy)}
"""

def doc(name, pages, bleed, w=210, h=297):
    css = PCSS + f":root{{--b:{bleed}mm}}@page{{size:{w+2*bleed}mm {h+2*bleed}mm;margin:0}}"
    html = (f'<!doctype html><html><head><meta charset="utf-8"><title>{PRODUCT}</title><style>{CSS}{css}</style></head><body>'
            + "".join(pages) + "</body></html>")
    save(name, html)

def pg(inner, n=None, dark=False, extra=""):
    cls = "bg-navy bg-grid dark" if dark else "bg-grid-l"
    foot = (f'<div class="pf"><span>{PRODUCT} &middot; {POWERED}</span><span>{WEB} &middot; {n}</span></div>' if n else "")
    return f'<section class="pg {cls}" style="{extra}"><div class="in">{inner}</div>{foot}</section>'

def head(label, dark=False):
    return f'<div class="ph">{brand(30, dark)}<span class="lab">{label}</span></div>'

def feat(ic, t, d, cls="s"):
    return (f'<div class="card c" style="display:flex;gap:4mm">{ico(ic,40,cls,20)}<div><h3 class="t" style="font-size:11.5pt">{t}</h3><div class="small">{d}</div></div></div>')

def chk(items):
    return "".join(f'<div class="chk"><span>{icon("check",15,2.6)}</span><span>{i}</span></div>' for i in items)

def pages(bleed):
    P = []
    # 1 cover
    P.append(pg(f'''
 <svg style="position:absolute;right:-6mm;bottom:20mm;opacity:.95" width="520" height="560" viewBox="0 0 520 560">{scaffold(60,230,300,260,4,3,"#9fb6d9","#f5a623",3.2,.9)}{crane(250,-10,1.0,"#9fb6d9","#f5a623",.85)}</svg>
 {brand(42)}
 <div style="margin-top:46mm"><div class="eyebrow" style="font-size:9pt">Premium Tender/Bid Marketplace</div>
 <h1 style="font-size:43pt;margin-top:5mm;color:#fff">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Equipment Sourcing.</span></h1>
 <p class="lead" style="margin-top:8mm;max-width:105mm;font-size:12.5pt">{PRODUCT}: {SUB}.</p></div>
 <div style="position:absolute;left:calc(var(--b) + 14mm);right:calc(var(--b) + 14mm);bottom:calc(var(--b) + 12mm);display:flex;justify-content:space-between;align-items:flex-end;color:#fff">
  <div><div style="font-weight:800;font-size:13pt;color:#fff">{POWERED}</div><div style="font-size:9pt;color:#c9d6ea;margin-top:1mm">{WEB} &middot; {EMAIL}</div></div>
  <div class="amber" style="font-weight:800;font-size:13pt">{CTA2}</div></div>''', dark=True))
    # 2 intro
    P.append(pg(f'''{head("Introduction")}
 <div class="eyebrow" style="font-size:8pt">What it is</div>
 <h2 class="t" style="font-size:25pt;margin-top:2mm">A premium digital marketplace for construction equipment.</h2>
 <p class="lead" style="margin-top:4mm">ThinkNXG Rental Marketplace connects construction companies, contractors, equipment rental businesses and suppliers. A customer posts a requirement once; matched, verified suppliers compete with sealed offers. The customer compares, clarifies, selects, books and follows the order through delivery and return.</p>
 <div style="display:flex;gap:3mm;margin-top:6mm"><span class="pill n" style="font-size:9pt">HIRE</span><span class="pill n" style="font-size:9pt">SALE</span><span class="pill n" style="font-size:9pt">LONG-TERM CONTRACT</span></div>
 <div class="grid2" style="margin-top:6mm">
  {feat("layers","Formwork &amp; scaffolding","Wall, slab, column and beam formwork; cuplock, ringlock, H-frame, tube and fitting, aluminium and mobile scaffolding.")}
  {feat("box","Equipment &amp; accessories","Concrete, lifting, earthmoving and compaction equipment; props, shuttering materials, clamps, couplers and safety equipment.")}</div>
 <div style="margin-top:6mm">{shot("marketplace-home.png","width:100%;height:74mm")}<div class="note" style="margin-top:2mm">Public marketplace home page. Product screenshot with demo data.</div></div>
 <div class="eyebrow" style="font-size:8pt;margin-top:6mm">Built for</div>
 <div style="margin-top:2mm;font-size:9.5pt;font-weight:600;color:var(--navy);line-height:1.6">Construction companies &middot; Infrastructure developers &middot; EPC contractors &middot; Scaffolding rental companies &middot; Formwork suppliers &middot; Equipment rental businesses &middot; Procurement and project managers</div>''', 2))
    # 3 challenge/solution
    ch = [("Calling yard after yard", "Post one brief and matched suppliers come to you."),
          ("Quotes that don't compare", "Every offer is totalled by the same rules, line by line."),
          ("Stock promised twice", "Accepted quantities are locked for your dates."),
          ("No record of the decision", "Every revision, clarification and decision is recorded.")]
    pains = ["Finding who has stock and a price takes call after call.", "Every supplier quotes in a different format.", "Free stock is checked by phone, then promised twice.", "Clarifications end up scattered across calls and emails."]
    left = "".join(f'<div class="card c" style="margin-bottom:4mm;border-left:3px solid var(--s300)"><h3 class="t" style="font-size:11.5pt">{a}</h3><div class="small">{pains[i]}</div></div>' for i, (a, _) in enumerate(ch))
    right = "".join(f'<div class="card c dk" style="margin-bottom:4mm;border-left:3px solid var(--amber)"><h3 class="t" style="font-size:11.5pt;color:#fff">{b}</h3><div class="small" style="color:#c9d6ea">{c}</div></div>' for (b, c) in [(ch[0][0].replace("Calling yard after yard", "One requirement, many suppliers"), ch[0][1]), ("Comparable offers", ch[1][1]), ("No double booking", ch[2][1]), ("Full audit trail", ch[3][1])])
    P.append(pg(f'''{head("Challenge &amp; solution")}
 <h2 class="t" style="font-size:25pt">From phone tag to a structured tender.</h2>
 <p class="lead" style="margin-top:4mm">Sourcing scaffolding, formwork and equipment usually means chasing several suppliers and stitching their answers together. The marketplace turns that into one requirement and one comparable set of offers.</p>
 <div style="display:grid;grid-template-columns:1fr 12mm 1fr;margin-top:9mm;align-items:start">
  <div><div class="eyebrow" style="color:var(--s500);font-size:8pt;margin-bottom:4mm">The usual way</div>{left}</div>
  <div style="display:flex;justify-content:center;padding-top:14mm;color:var(--amber)">{icon("arrow",26,2.4)}</div>
  <div style="background:var(--navy);margin:-3mm;padding:3mm;border-radius:20px;" class="dark"><div class="eyebrow" style="font-size:8pt;margin:3mm 0 4mm 2mm">With the marketplace</div>{right}</div></div>
 <div class="card c" style="margin-top:8mm;display:flex;gap:5mm;align-items:center">{ico("lock",44,"n",22)}<div><h3 class="t">Sealed by default</h3><div class="small">Suppliers never see each other's prices. Tender confidentiality can be set to Sealed, Rank Only or Open, and the customer's identity is disclosed to suppliers at the stage the tender is configured for (on award by default in the product demo).</div></div></div>''', 3))
    # 4 features
    F = [("layers", "Multi-vendor equipment marketplace", "Catalogue of listings from verified suppliers across formwork, scaffolding, equipment and accessories."),
         ("req", "Digital requirement submission", "A guided 8-step form: transaction type, category, requirements, period and delivery, project and site, commercial preferences, attachments, review."),
         ("match", "Automated supplier matching", "Hard eligibility rules plus a score, including free stock for the tender window. Matched suppliers receive tender invitations."),
         ("lock", "Competitive, sealed offers", "Suppliers bid privately. Offer revisions are kept as immutable snapshots."),
         ("compare", "Offer comparison &amp; evaluation", "Totals per the same rules; sort by price, delivery or rating; line-by-line technical compliance."),
         ("chat", "Clarification &amp; negotiation", "Ask suppliers questions and negotiate within the tender, all on record."),
         ("pay", "Booking &amp; payment workflows", "Accepting an offer creates the booking and reserves stock in one transaction. Payments are confirmed by the provider or by Finance."),
         ("shield", "Verification &amp; vendor management", "Supplier registration, document review, approval, suspension, subscriptions and entitlements."),
         ("settle", "Commission &amp; settlements", "Rule-based commission; settlements are marked paid only with a payout reference."),
         ("star", "Reviews, disputes &amp; audit", "Customer reviews, dispute handling and an insert-only audit trail.")]
    P.append(pg(f'''{head("Marketplace features")}
 <h2 class="t" style="font-size:25pt">Everything the tender needs, in one platform.</h2>
 <div class="grid2" style="margin-top:7mm;gap:4.2mm">{"".join(feat(*f) for f in F)}</div>''', 4))
    # 5 customer journey
    cs = [("Post one requirement", "Hire, buy or contract. Add items, quantities, dates, site and commercial preferences."),
          ("Suppliers are matched and invited", "Verified suppliers with the right category, coverage and free stock are invited."),
          ("Receive sealed offers", "Offers stay sealed until bidding closes."),
          ("Compare, clarify, negotiate", "Same-rules totals. The lowest price is highlighted, never chosen for you."),
          ("Award, book and pay", "The accepted offer locks stock for your dates; payments are tracked."),
          ("Receive, return, review", "Follow delivery and return, then rate the supplier.")]
    steps = "".join(f'<div class="card c" style="display:flex;gap:4mm;align-items:flex-start"><div class="n" style="font-weight:800;font-size:20pt;color:var(--amber);width:9mm;line-height:1">{i+1}</div><div><h3 class="t" style="font-size:11.5pt">{a}</h3><div class="small">{b}</div></div></div>' for i, (a, b) in enumerate(cs))
    P.append(pg(f'''{head("Customer journey")}
 <h2 class="t" style="font-size:25pt">Source with confidence.</h2>
 <p class="lead" style="margin-top:3mm">One workspace for requirements, tenders, bookings, project sites and company users.</p>
<div class="grid2" style="margin-top:7mm;gap:4mm">{steps}</div>
 <div style="margin-top:6mm">{shot("customer-compare-offers.png","width:100%;height:96mm")}<div class="note" style="margin-top:2mm">Compare offers in the customer workspace. Product screenshot, demo data.</div></div>
 <div class="grid3" style="margin-top:3mm">{chk(["Transparent offer comparison"])}{chk(["Better procurement visibility"])}{chk(["Streamlined booking and fulfilment"])}</div>''', 5))
    # 6 supplier journey
    ss = [("Register and get verified", "Supplier documents are reviewed before you can bid."),
          ("List your equipment", "Maintain a catalogue; free stock is checked per offer line."),
          ("Receive tender invitations", "Matched to your category, coverage and free stock."),
          ("Submit a sealed offer", "Build from your listings; the marketplace calculates totals. Revise any time before close."),
          ("Win and manage the booking", "Bookings and fulfilment, billing and settlements in one portal."),
          ("Build your reputation", "Ratings, reviews and subscription plans.")]
    steps = "".join(f'<div class="card c" style="display:flex;gap:4mm;align-items:flex-start"><div class="n" style="font-weight:800;font-size:20pt;color:var(--amber);width:9mm;line-height:1">{i+1}</div><div><h3 class="t" style="font-size:11.5pt">{a}</h3><div class="small">{b}</div></div></div>' for i, (a, b) in enumerate(ss))
    P.append(pg(f'''{head("Supplier journey")}
 <h2 class="t" style="font-size:25pt">Win work you would never have heard about.</h2>
 <p class="lead" style="margin-top:3mm">Receive qualified tender invitations, bid privately and run bookings from the supplier portal.</p>
<div class="grid2" style="margin-top:7mm;gap:4mm">{steps}</div>
 <div style="margin-top:6mm">{shot("supplier-tender-offer.png","width:100%;height:92mm")}<div class="note" style="margin-top:2mm">Tender and offer builder in the supplier portal. Product screenshot, demo data.</div></div>
 <div class="grid2" style="margin-top:3mm">{chk(["Access to customer requirements","Competitive bidding opportunities"])}{chk(["Equipment listing management","Booking and order management"])}</div>''', 6))
    # 7 tender & bidding
    stages = ["Published", "Supplier Matching", "Invitation Sent", "Bidding Open", "Bidding Closed", "Evaluation", "Awarded"]
    sh = "".join(f'<div style="flex:1;text-align:center;font-size:7.5pt;font-weight:700;color:#fff;background:{"var(--amber)" if i==3 else "var(--navy)"};{"color:var(--navy);" if i==3 else ""}border-radius:8px;padding:3mm 1mm;line-height:1.2">{s}</div>' for i, s in enumerate(stages))
    P.append(pg(f'''{head("Tender &amp; bidding process")}
 <h2 class="t" style="font-size:25pt">A tender engine built for fairness.</h2>
 <p class="lead" style="margin-top:3mm">Every tender follows the same state machine, so every supplier is treated by the same rules.</p>
 <div style="display:flex;gap:1.5mm;margin-top:8mm">{sh}</div>
 <div class="grid2" style="margin-top:8mm">
  {feat("lock","Confidentiality you control","Sealed, Rank Only or Open offers. Customer identity disclosure on award, on shortlist or always.")}
  {feat("compare","Evaluation","Technical acceptance, then commercial acceptance, then award.","b")}
  {feat("chat","Clarification &amp; negotiation","Questions to one or all suppliers; revised offers keep a full history.")}
  {feat("shield","Integrity","Accepting an offer locks tender, offer and stock rows together: two customers cannot be booked against the same stock for overlapping dates.","n")}</div>
 <div style="margin-top:6mm">{shot("supplier-offer-totals.png","width:100%",False)}<div class="note" style="margin-top:2mm">Offer totals are calculated by the marketplace. Product screenshot, demo data.</div></div>
 <div class="card c" style="margin-top:6mm"><h3 class="t">Same rules for every supplier</h3><div class="small">The marketplace calculates every total on the server from the supplier's inputs, so figures typed in a browser can never change the price. Hire is priced per day, week or month pro-rata; contracts by month; sales by unit; charges and tax are added in the same way for every offer.</div></div>''', 7))
    # 8 fulfilment
    fl = [("Hire Order", "Commercial order with availability and shortfall per line"), ("Rental Contract", "Rates, billing cycle, grace days, minimum hire, deposit"), ("Material Reservation", "Soft reservation per warehouse; shortfall can go to cross hire"),
          ("Delivery Order", "Dispatch from yard to site"), ("Material at Site", "Ledger of what is on each site"), ("Off-Hire &amp; Inspection", "Partial or full returns, inspection, damage and loss settlement")]
    fh = "".join(f'<div class="card c" style="display:flex;gap:4mm;align-items:center;margin-bottom:5mm;padding:6mm 6mm"><div style="font-weight:800;color:var(--amber);font-size:17pt;width:9mm">{i+1}</div><div><h3 class="t" style="font-size:12.5pt">{a}</h3><div class="small" style="font-size:10pt">{b}</div></div></div>' for i, (a, b) in enumerate(fl))
    P.append(pg(f'''{head("Rental fulfilment")}
 <h2 class="t" style="font-size:25pt">Marketplace to rental, in one journey.</h2>
 <p class="lead" style="margin-top:3mm">When a booking is confirmed, the marketplace can hand it to thinkNXG Rental, the rental management and fulfilment engine, as a draft Hire Order (or a Sales Order for a sale). Status then flows back to the booking.</p>
 <div style="margin-top:7mm">{fh}</div>
 <div class="grid2" style="margin-top:3mm">
  {feat("pin","Multi-location warehouses","Own and cross-hire warehouses at any locations; returns split per row.","n")}
  {feat("settle","Recurring rental billing","Billing schedules for material on hire, with off-hire and final settlement.","n")}</div>
 <div class="note" style="margin-top:5mm">The hand-off applies to suppliers who run thinkNXG Rental on the same site. Job-type contracts (Hire Order Contract / JCR) are not yet mapped from marketplace bookings.</div>''', 8))
    # 9 benefits
    P.append(pg(f'''{head("Business &amp; operational benefits")}
 <h2 class="t" style="font-size:25pt">Value for every side of the market.</h2>
 <div class="grid3" style="margin-top:7mm">
  <div class="card c"><div class="eyebrow" style="font-size:7.5pt">Customers</div>{chk(["One requirement, multiple offers","Transparent comparison","Procurement visibility","Reserved stock","Audit trail"])}</div>
  <div class="card c"><div class="eyebrow" style="font-size:7.5pt">Suppliers</div>{chk(["Tender invitations","Private bidding","Listing management","Booking management","Reviews and growth"])}</div>
  <div class="card c"><div class="eyebrow" style="font-size:7.5pt">Operators</div>{chk(["Supplier verification","Tender moderation","Payments and refunds","Commission and settlements","Disputes and audit"])}</div></div>
 <div style="margin-top:7mm">{shot("operator-analytics.png","width:100%")}<div class="note" style="margin-top:2mm">Operator console: marketplace analytics. Product screenshot, demo data.</div></div>
 <div class="grid2" style="margin-top:6mm">
  {feat("console","Run the marketplace","Analytics, supplier applications, tenders to moderate, payments to confirm, commissions, settlements, reviews, disputes and enquiries in one console.","b")}
  {feat("tag","Monetise it your way","Configurable commission rules, subscription plans with trial, active and grace periods, and promoted listings.","b")}</div>''', 9))
    # 10 CTA
    P.append(pg(f'''
 <svg style="position:absolute;right:-14mm;top:40mm;opacity:.9" width="400" height="460" viewBox="0 0 420 480">{scaffold(80,170,230,230,4,2,"#9fb6d9","#f5a623",3,.85)}{crane(190,-10,.8,"#9fb6d9","#f5a623",.8)}</svg>
 {brand(42)}
 <div style="margin-top:62mm"><div class="eyebrow" style="font-size:9pt">Get started</div>
 <h1 style="font-size:33pt;margin-top:5mm;max-width:100mm;color:#fff">{CTA1}</h1>
 <div class="amber" style="font-weight:800;font-size:17pt;margin-top:6mm">{CTA2}</div></div>
 <div style="margin-top:20mm;display:grid;grid-template-columns:1fr;gap:3.5mm;max-width:110mm">
  <div class="card dk c" style="display:flex;gap:4mm;align-items:center">{ico("offers",38,"w",19)}<div><div class="note" style="font-size:7.5pt">EMAIL</div><div style="font-weight:700;font-size:11pt">{EMAIL}</div></div></div>
  <div class="card dk c" style="display:flex;gap:4mm;align-items:center">{ico("globe",38,"w",19)}<div><div class="note" style="font-size:7.5pt">WEBSITE</div><div style="font-weight:700;font-size:11pt">https://{WEB}</div></div></div>
  <div class="card dk c" style="display:flex;gap:4mm;align-items:center">{ico("fulfil",38,"w",19)}<div><div class="note" style="font-size:7.5pt">THINKNXG RENTAL</div><div style="font-weight:700;font-size:11pt">https://{WEB_RENTAL}</div></div></div></div>
 <div style="position:absolute;left:calc(var(--b) + 14mm);right:calc(var(--b) + 14mm);bottom:calc(var(--b) + 12mm);display:flex;justify-content:space-between;align-items:flex-end;color:#fff"><div style="font-weight:800;font-size:12pt;color:#fff">{POWERED}</div><div class="note" style="max-width:85mm;text-align:right">Screenshots shown in this brochure are from the product running on demo data.</div></div>''', dark=True))
    return P

def flyer(bleed):
    cols = [("For customers", "n", ["One requirement, multiple offers", "Transparent offer comparison", "Procurement visibility", "Booking and fulfilment in one journey"]),
            ("For suppliers", "a", ["Tender invitations matched to your fleet", "Private, competitive bidding", "Listings, bookings and settlements", "Verified profile and reviews"]),
            ("Behind the scenes", "n", ["Sealed offers, no double booking", "Operator console and audit trail", "Commission and settlement rules", "Fulfilment via thinkNXG Rental"])]
    ch = "".join(f'<div class="card c {"onamber" if c=="a" else ""}" style="{"background:var(--amber);border-color:var(--amber)" if c=="a" else ""}"><div class="eyebrow" style="font-size:7.5pt;{"color:var(--navy)" if c=="a" else ""}">{t}</div>{chk(i)}</div>' for t, c, i in cols)
    return [pg(f'''
 <svg style="position:absolute;right:-2mm;top:14mm;opacity:.9" width="300" height="300" viewBox="0 0 300 300">{scaffold(70,130,170,140,3,2,"#9fb6d9","#f5a623",3,.9)}{crane(120,-30,.55,"#9fb6d9","#f5a623",.8)}</svg>
 {brand(38)}
 <div style="margin-top:12mm"><div class="eyebrow" style="font-size:8.5pt">Premium Tender/Bid Marketplace</div>
 <h1 style="font-size:31pt;margin-top:4mm;color:#fff">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Equipment<br>Sourcing.</span></h1>
 <p class="lead" style="margin-top:4mm;max-width:120mm;font-size:10.5pt">Scaffolding, formwork and construction equipment: hire, sale and long-term contracts from verified suppliers, compared side by side.</p></div>
 <div style="position:absolute;left:0;right:0;top:131mm;bottom:0;background:var(--s50);padding:12mm calc(var(--b) + 14mm) 0" class="bg-grid-l">
  <div style="display:flex;gap:2mm;align-items:center">{('<span style="color:var(--amber)">'+icon("arrow",14,2.6)+'</span>').join(f'<div style="flex:1;text-align:center;font-weight:700;font-size:8pt;color:var(--navy);background:#fff;border:1px solid var(--s200);border-radius:10px;padding:3.5mm 1mm;line-height:1.2">{x}</div>' for x in ["Post requirement","Receive offers","Compare","Book","Fulfil"])}</div>
  <div class="grid3" style="margin-top:6mm">{ch}</div>
  <div style="margin-top:5mm">{shot("customer-compare-offers.png","width:100%;height:40mm")}<div class="note" style="margin-top:1.5mm">Compare offers. Product screenshot, demo data.</div></div>
 </div>
 <div class="bg-navy dark" style="position:absolute;left:0;right:0;bottom:0;height:34mm;padding:0 calc(var(--b) + 14mm);display:flex;align-items:center;justify-content:space-between"><div><div style="color:#fff;font-weight:800;font-size:14pt;max-width:110mm;line-height:1.15">{CTA1}</div><div class="amber" style="font-weight:800;font-size:11pt;margin-top:1.5mm">{CTA2}</div></div><div style="text-align:right;font-size:9pt;color:#c9d6ea;line-height:1.5"><b style="color:#fff">{POWERED}</b><br>{WEB}<br>{EMAIL}</div></div>''', dark=True)]

def execsum(bleed):
    P = []
    P.append(pg(f'''{head("Executive product overview")}
 <h1 class="t" style="font-size:25pt">{PRODUCT}</h1><p class="lead" style="margin-top:2mm">{SUB}. {POWERED}.</p>
 <div class="grid2" style="margin-top:6mm">
  <div class="card c"><h3 class="t">Positioning</h3><div class="small">A premium digital marketplace connecting construction companies, contractors, equipment rental businesses and suppliers. Customers post one requirement; matched suppliers compete with sealed offers; the customer compares, selects, books and follows fulfilment.</div></div>
  <div class="card c"><h3 class="t">Two products, one journey</h3><div class="small"><b>ThinkNXG Rental Marketplace</b> sources and awards. <b>thinkNXG Rental</b> runs the rental: reservations, delivery, material at site, billing, returns and settlement.</div></div></div>
 <h2 class="t" style="font-size:15pt;margin-top:7mm">The workflow</h2>
 <div style="display:flex;flex-wrap:wrap;gap:2mm;margin-top:2mm">{"".join(f'<span class="pill n" style="font-size:8pt">{i+1}. {s}</span>' for i, s in enumerate(["Post Requirement","Create Tender","Match Suppliers","Receive Offers","Compare Offers","Select Supplier","Book","Pay","Fulfil","Settle","Review"]))}</div>
 <h2 class="t" style="font-size:15pt;margin-top:7mm">Capabilities</h2>
 <div class="grid2" style="margin-top:3mm;gap:3.5mm">{"".join(feat(*f) for f in [("layers","Multi-vendor marketplace","Verified suppliers, listings and categories."),("match","Matching &amp; invitations","Category, coverage and free stock."),("lock","Sealed bidding","Private offers with revision history."),("compare","Comparison &amp; negotiation","Same-rules totals, clarifications."),("pay","Booking, payment, commission","Stock locked on acceptance; payments tracked."),("console","Operator console","Verification, moderation, finance, audit.")])}</div>''', 1))
    P.append(pg(f'''{head("Executive product overview")}
 <h2 class="t" style="font-size:15pt">Three portals and a public site</h2>
 <div class="grid3" style="margin-top:3mm">{feat("user","Customer workspace","Requirements, tenders, compare, bookings.")}{feat("building","Supplier portal","Tenders, offers, listings, bookings, billing.")}{feat("console","Operator console","Analytics, verification, finance, trust.")}</div>
 <div style="margin-top:6mm">{shot("operator-analytics.png","width:100%;height:62mm")}<div class="note" style="margin-top:1.5mm">Operator console analytics. Product screenshot, demo data.</div></div>
 <h2 class="t" style="font-size:15pt;margin-top:5mm">Business value</h2>
 <div class="grid2" style="margin-top:3mm"><div class="card c"><div class="eyebrow" style="font-size:7.5pt">Procurement</div>{chk(["Offers compared like for like","Visibility of every revision and decision","No double-booked stock"])}</div><div class="card c"><div class="eyebrow" style="font-size:7.5pt">Supply side</div>{chk(["Qualified tender invitations","Private bidding","Bookings, billing and reviews in one portal"])}</div></div>
 <h2 class="t" style="font-size:15pt;margin-top:5mm">Scope notes</h2>
 <div class="card c" style="margin-top:3mm"><div class="small">Stripe and Razorpay payment connectors are built and their webhook handling is tested, but need a provider sandbox check before going live; bank-transfer payments confirmed by Finance work today. Supplier payouts are recorded by Finance, not paid automatically. The marketplace-to-rental hand-off applies to suppliers on the same site. The interface is English-only for now.</div></div>
 <div class="card c" style="margin-top:4mm;color:#fff;background:linear-gradient(135deg,#091a31,#1a3f73);border:0"><div style="font-weight:800;font-size:13pt;color:#fff">{CTA1}</div><div class="amber" style="font-weight:800;font-size:10.5pt;margin-top:1mm">{CTA2}</div><div style="font-size:9pt;color:#c9d6ea;margin-top:2mm">{POWERED} &middot; {WEB} &middot; {EMAIL}</div></div>''', 2))
    return P

def build():
    for b, suf, kinds in ((0, "", ("pdf",)), (3, "-print-3mm-bleed", ("pdf",))):
        w, h = 210 + 2 * b, 297 + 2 * b
        for nm, fn, folder, out in (("brochure", pages, "brochures", "ThinkNXG-Rental-Marketplace-Brochure-A4"),
                                    ("flyer", flyer, "flyers", "ThinkNXG-Rental-Marketplace-Flyer-A4"),
                                    ("exec", execsum, "flyers", "ThinkNXG-Rental-Marketplace-Executive-Overview-A4")):
            doc(f"{nm}{suf}.html", fn(b), b)
            reg(f"{nm}{suf}.html", folder, out + suf, round(w * 3.7795), round(h * 3.7795), ["pdf"])

if __name__ == "__main__":
    build()

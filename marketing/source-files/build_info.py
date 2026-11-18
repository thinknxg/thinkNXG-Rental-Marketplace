from lib import *

# ------------------------------------------------------------------ 01 product overview (HTML 1200x1800)
def overview():
    W, H = 1200, 1800
    caps = [("layers", "Multi-vendor catalogue", "Formwork, scaffolding, plant and accessories from verified suppliers"),
            ("match", "Supplier matching", "Category, coverage and free stock for your dates"),
            ("lock", "Sealed offers", "Suppliers never see each other's prices"),
            ("compare", "Offer comparison", "Same-rules totals, side by side"),
            ("chat", "Clarify & negotiate", "Questions and revisions, fully recorded"),
            ("pay", "Booking & payment", "Accepted offers lock stock; payments tracked"),
            ("shield", "Supplier verification", "Documents reviewed before anyone can bid"),
            ("settle", "Commission & settlement", "Rule-based commission, recorded payouts")]
    capshtml = "".join(f'<div class="card" style="padding:20px 20px 18px;display:flex;gap:14px;align-items:flex-start">{ico(i,46,"s",24)}'
                       f'<div><div style="font-weight:800;font-size:17px;color:var(--navy)">{t}</div><div class="muted" style="font-size:14px;margin-top:4px;line-height:1.35">{d}</div></div></div>'
                       for i, t, d in caps)
    prob = [("Calling yard after yard", "Post one brief; matched suppliers come to you."),
            ("Offers you can't compare", "Every offer is priced by the same rules, line by line."),
            ("Stock promised twice", "Accepted quantities are locked for your dates."),
            ("No paper trail", "Every revision, clarification and decision is recorded.")]
    probhtml = "".join(f'<div style="flex:1;padding:22px 20px;border-left:3px solid var(--amber);background:#fff;border-radius:0 14px 14px 0;box-shadow:0 10px 24px -18px rgba(16,24,40,.4)">'
                       f'<div style="font-weight:800;font-size:17px;color:var(--navy)">{t}</div><div style="font-size:14px;color:var(--s700);margin-top:6px;line-height:1.4">{d}</div></div>' for t, d in prob)
    flow = ["Booking confirmed", "Draft Hire Order in thinkNXG Rental", "Material reservation", "Delivery &amp; material at site", "Off-hire, billing &amp; settlement"]
    flowhtml = '<span style="color:var(--amber);margin:0 2px">' + icon("arrow", 22, 2.4) + '</span>'
    flowhtml = flowhtml.join(f'<div style="flex:1;text-align:center;font-weight:700;font-size:14.5px;line-height:1.25;color:#fff;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:16px 8px;min-height:74px;display:flex;align-items:center;justify-content:center">{f}</div>' for f in flow)
    body = f'''
<div style="position:relative;height:{H}px;background:var(--s50)" class="bg-grid-l">
 <div class="bg-navy bg-grid dark" style="height:470px;position:relative;padding:48px 64px;overflow:hidden">
  <svg style="position:absolute;right:30px;top:60px;opacity:.9" width="420" height="420" viewBox="0 0 420 420">{scaffold(20,150,250,230,3,2,"#9fb6d9","#f5a623",3,.9)}{crane(190,-20,.72,"#9fb6d9","#f5a623",.8)}</svg>
  {brand(46)}
  <div class="eyebrow" style="margin-top:42px;font-size:13px">Premium tender / bid marketplace</div>
  <h1 style="font-size:66px;margin-top:14px;max-width:700px;color:#fff">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Equipment Sourcing.</span></h1>
  <p style="color:#c9d6ea;font-size:18px;max-width:620px;margin-top:20px;line-height:1.5">A multi-vendor marketplace where construction teams post a requirement once and verified suppliers compete with sealed offers &mdash; for scaffolding, formwork and construction equipment.</p>
 </div>
 <div style="padding:34px 64px 0">
  <div style="display:flex;gap:16px;align-items:center">
   <div class="eyebrow" style="font-size:12px">What it is</div><div style="height:1px;background:var(--s300);flex:1"></div>
   <span class="pill n">HIRE</span><span class="pill n">SALE</span><span class="pill n">CONTRACT</span>
  </div>
  <div style="display:flex;gap:14px;margin-top:16px">
   {''.join(f'<div class="card" style="flex:1;padding:16px 18px;font-weight:700;color:var(--navy);font-size:16px;display:flex;align-items:center;gap:10px">{icon("box",22)}{c}</div>' for c in ["Formwork","Scaffolding","Construction Equipment","Accessories &amp; Materials"])}
  </div>
  <h2 style="font-size:34px;margin:34px 0 16px">The problems it solves</h2>
  <div style="display:flex;gap:14px">{probhtml}</div>
  <div style="display:flex;gap:18px;margin-top:30px">
   <div style="flex:1;border-radius:18px;padding:26px 28px;background:var(--navy);color:#fff" class="dark">
    <div class="eyebrow" style="font-size:12px">For customers</div><h3 style="font-size:26px;margin:8px 0 12px">Procurement without the phone tag</h3>
    <div style="font-size:15px;line-height:1.7;color:#d3def0">&#10003; One brief, many quotes<br>&#10003; Comparable totals, lowest never auto-picked<br>&#10003; Reserved stock for your dates<br>&#10003; Full audit trail of every decision</div></div>
   <div style="flex:1;border-radius:18px;padding:26px 28px;background:linear-gradient(135deg,#f5a623,#ffbf4d);color:var(--navy)">
    <div class="eyebrow" style="font-size:12px;color:var(--navy)">For suppliers</div><h3 style="font-size:26px;margin:8px 0 12px;color:var(--navy)">Win work you would never have heard about</h3>
    <div style="font-size:15px;line-height:1.7;font-weight:600">&#10003; Tender invitations matched to your fleet<br>&#10003; Bid privately &mdash; competitors never see prices<br>&#10003; Manage listings, bookings and deliveries<br>&#10003; Verified profile, ratings and reviews</div></div>
  </div>
  <h2 style="font-size:34px;margin:34px 0 16px">Major platform capabilities</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">{capshtml}</div>
 </div>
 <div class="bg-navy dark" style="position:absolute;left:0;right:0;bottom:0;height:262px;padding:26px 64px">
  <div class="eyebrow" style="font-size:12px">Marketplace-to-rental fulfilment journey</div>
  <div style="display:flex;align-items:center;gap:6px;margin-top:14px">{flowhtml}</div>
  <div class="note" style="margin-top:10px">Hand-off to thinkNXG Rental applies to suppliers connected on the same site. The marketplace confirms the booking; thinkNXG Rental runs the rental.</div>
  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-top:14px">
   <div><div style="color:#fff;font-weight:800;font-size:24px;letter-spacing:-.01em">{CTA1}</div><div class="amber" style="font-weight:800;font-size:18px;margin-top:4px">{CTA2}</div></div>
   <div style="text-align:right;color:#c9d6ea;font-size:14px;line-height:1.5"><b style="color:#fff">{POWERED}</b><br>{WEB} &middot; {EMAIL}</div>
  </div>
 </div>
</div>'''
    save("infographic-01-product-overview.html", page(W, H, body))
    reg("infographic-01-product-overview.html", "infographics", "01-product-overview", W, H)

# ------------------------------------------------------------------ SVG helpers
def svg_icon(name, x, y, s=28, color="currentColor", sw=1.7):
    return f'<g transform="translate({x} {y}) scale({s/24:.3f})" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'

def tx(x, y, s, size, fill, weight=500, anchor="start", ls=0):
    s = s.replace("&", "&amp;") if "&amp;" not in s else s
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>'

SVG_STYLE = '<style>text{font-family:Inter,"Inter Display",system-ui,sans-serif}</style>'

# ------------------------------------------------------------------ 02 how it works (native SVG 1800x1000)
def how_it_works():
    W, H = 1800, 1000
    steps = [("req", "Post Requirement", "Guided 8-step form for hire, sale or contract"),
             ("tender", "Create Tender", "Your requirement becomes a moderated, published tender"),
             ("match", "Match Suppliers", "Category, coverage and free stock for your dates"),
             ("offers", "Receive Offers", "Suppliers bid privately; offers stay sealed"),
             ("compare", "Compare Offers", "Same-rules totals by price, delivery and rating"),
             ("select", "Select Supplier", "Clarify, negotiate, then award. You decide"),
             ("book", "Book", "The accepted offer locks stock for your dates"),
             ("pay", "Pay", "Payment confirmed by the provider or Finance"),
             ("fulfil", "Fulfil", "Delivery, material at site and returns in thinkNXG Rental"),
             ("settle", "Settle", "Commission applied; supplier payout recorded"),
             ("star", "Review", "Ratings and reviews build supplier trust")]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{SVG_STYLE}',
         '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#091a31"/><stop offset=".6" stop-color="#0e2848"/><stop offset="1" stop-color="#1a3f73"/></linearGradient>'
         '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".045"/></pattern></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>']
    s.append(f'<g transform="translate(70 56)"><rect width="46" height="46" rx="12" fill="#fff"/><g transform="scale(.72)"><path d="M18 10v44M46 10v44M18 22h28M18 38h28M18 22l28 16" fill="none" stroke="#0b1f3a" stroke-width="4.5" stroke-linecap="round"/><circle cx="46" cy="22" r="5" fill="#f5a623"/></g></g>')
    s.append(tx(130, 88, "thinkNXG", 29, "#fff", 800))
    s.append(tx(131, 104, "RENTAL MARKETPLACE", 11, "#f5a623", 700, ls=2.2))
    s.append(tx(70, 190, "HOW IT WORKS", 15, "#f5a623", 700, ls=3.5))
    s.append(tx(70, 252, "From requirement to review in eleven steps", 50, "#fff", 800))
    cw, gap = 250, 40
    def pos(i):
        if i < 6: return 70 + i * (cw + gap) * 0.0 + i * ((W - 140 - 6 * cw) / 5 + cw), 330
        j = i - 6
        return 70 + j * ((W - 140 - 6 * cw) / 5 + cw), 640
    pts = [pos(i) for i in range(11)]
    for i, (ic, t, d) in enumerate(steps):
        x, y = pts[i]
        hl = i in (3,)
        s.append(f'<rect x="{x}" y="{y}" width="{cw}" height="250" rx="22" fill="#ffffff" fill-opacity=".07" stroke="#fff" stroke-opacity=".16"/>')
        s.append(f'<circle cx="{x+50}" cy="{y+56}" r="30" fill="#f5a623"/>')
        s.append(svg_icon(ic, x + 35, y + 41, 30, "#0b1f3a", 1.9))
        s.append(tx(x + cw - 26, y + 62, f"{i+1:02d}", 34, "#ffffff", 800, "end"))
        s.append(f'<text x="{x+cw-26}" y="{y+62}" opacity="0"></text>')
        s.append(tx(x + 26, y + 130, t, 24, "#fff", 800))
        # wrap description to 2-3 lines of ~26 chars
        words, lines, cur = d.split(), [], ""
        for w_ in words:
            if len(cur) + len(w_) + 1 > 25: lines.append(cur); cur = w_
            else: cur = (cur + " " + w_).strip()
        lines.append(cur)
        for k, ln in enumerate(lines[:4]):
            s.append(tx(x + 26, y + 164 + k * 24, ln, 16, "#c9d6ea", 500))
    # connectors
    for i in range(10):
        if i == 5: continue
        x1, y1 = pts[i]; x2, y2 = pts[i + 1]
        yy = y1 + 125
        s.append(f'<path d="M{x1+cw+6} {yy}H{x2-8}" stroke="#f5a623" stroke-width="3" stroke-linecap="round"/><path d="M{x2-18} {yy-8}L{x2-6} {yy}L{x2-18} {yy+8}" fill="none" stroke="#f5a623" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    x6, y6 = pts[5]; x7, y7 = pts[6]
    s.append(f'<path d="M{x6+cw/2} {y6+256}V{y6+285}H{x7+cw/2}V{y7-8}" fill="none" stroke="#f5a623" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="2 9"/>')
    s.append(f'<path d="M{x7+cw/2-8} {y7-18}L{x7+cw/2} {y7-6}L{x7+cw/2+8} {y7-18}" fill="none" stroke="#f5a623" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    # phase bands
    s.append(tx(pts[0][0], 316, "SOURCE", 13, "#f5a623", 700, ls=3))
    s.append(tx(W - 70, 626, "FULFIL &amp; GROW", 13, "#f5a623", 700, "end", 3))
    cx = pts[5][0]; cy = 640
    s.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="250" rx="22" fill="#f5a623"/>')
    s.append(tx(cx + 26, cy + 70, "Marketplace confirms.", 23, "#0b1f3a", 800))
    s.append(tx(cx + 26, cy + 100, "thinkNXG Rental delivers.", 23, "#0b1f3a", 800))
    s.append(tx(cx + 26, cy + 150, "Hand-off for suppliers", 16, "#0b1f3a", 600))
    s.append(tx(cx + 26, cy + 174, "connected on the same site.", 16, "#0b1f3a", 600))
    # right-hand annotation in empty slot of row 2
    ax = pts[10][0] + cw + 40
    s.append(tx(70, 940, CTA2, 26, "#f5a623", 800))
    s.append(tx(W - 70, 930, "Powered by thinkNXG", 18, "#fff", 700, "end"))
    s.append(tx(W - 70, 956, f"{WEB}  ·  {EMAIL}", 15, "#c9d6ea", 500, "end"))
    s.append('</svg>')
    open(os.path.join(ROOT, "source-files", "svg", "02-how-it-works.svg"), "w", encoding="utf-8").write("".join(s))
    save("infographic-02-how-it-works.html", page(W, H, f'<img src="../svg/02-how-it-works.svg" width="{W}" height="{H}" style="display:block">'))
    reg("infographic-02-how-it-works.html", "infographics", "02-how-it-works", W, H)

# ------------------------------------------------------------------ 03 / 04 benefit infographics (HTML 1200x1700)
def benefits(kind):
    W, H = 1200, 1740
    if kind == "customer":
        eb, title, sub = "For construction companies, contractors &amp; procurement teams", "One requirement.<br><span class='amber'>Multiple supplier offers.</span>", "Post what the site needs once. Verified suppliers compete. You compare clearly and choose with confidence."
        rows = [("req", "One requirement, multiple offers", "A guided 8-step form captures type, category, specifications, period, site and commercial preferences. Matched suppliers are invited automatically."),
                ("box", "Easier equipment sourcing", "Hire, buy or contract formwork, scaffolding, construction equipment and accessories from one place, or browse the verified-supplier catalogue."),
                ("compare", "Transparent offer comparison", "Every offer is totalled by the same rules. Sort by price, delivery or rating; the lowest price is highlighted but never chosen for you."),
                ("eye", "Better procurement visibility", "Requirements, bookings, project sites and company users in one workspace, with every revision, clarification and decision on record."),
                ("fulfil", "Streamlined booking &amp; fulfilment", "Accept an offer to reserve stock, then follow payment, delivery, returns and review in the same journey.")]
        proof = ["8-step guided requirement form", "Sealed offers until bidding closes", "Line-by-line technical comparison", "Clarifications &amp; negotiation thread", "Accepted stock locked, no double booking"]
        img, cap, tone = "customer-compare-offers.png", "Compare offers: customer workspace (product screenshot, demo data)", "a"
    else:
        eb, title, sub = "For scaffolding, formwork &amp; equipment rental businesses", "Win work you would<br><span class='amber'>never have heard about.</span>", "Receive qualified tender invitations, bid privately and run bookings from one supplier portal."
        rows = [("req", "Access to customer requirements", "Real project requirements with quantities, dates, site city and specifications, matched to what you actually stock."),
                ("tender", "Tender invitations", "Invitations are matched on category, coverage and free stock for the requested dates. Bidding is private; competitors never see your prices."),
                ("layers", "Equipment listing management", "Keep your catalogue in the portal. The offer form shows how many units are free for the requested dates."),
                ("offers", "Competitive bidding", "Build offers from your listings; the marketplace calculates totals, and you can revise your offer with a full revision history."),
                ("book", "Booking &amp; order management", "Won work flows into Bookings &amp; fulfilment, with billing &amp; settlements, reviews and subscription in the same portal."),
                ("chart", "Business growth", "A verified supplier profile, ratings and reviews, and subscription plans that put you in front of more tenders.")]
        proof = ["Documents reviewed before you can bid", "Private bidding", "Free-stock check per offer line", "Revision history on every offer", "Subscription plans with entitlements"]
        img, cap, tone = "supplier-tender-offer.png", "Offer builder: supplier portal (product screenshot, demo data)", "a"
    rhtml = ""
    for i, (ic, t, d) in enumerate(rows):
        rhtml += (f'<div class="card" style="display:flex;gap:22px;align-items:center;padding:22px 26px;margin-bottom:14px">'
                  f'<div style="font-weight:800;font-size:40px;color:var(--s200);width:56px;letter-spacing:-.03em">{i+1:02d}</div>{ico(ic,64,"n",30)}'
                  f'<div style="flex:1"><div style="font-weight:800;font-size:22px;color:var(--navy)">{t}</div><div style="font-size:15px;color:var(--s700);margin-top:5px;line-height:1.4">{d}</div></div></div>')
    phtml = "".join(f'<span style="display:inline-flex;align-items:center;gap:8px;background:var(--blue-soft);color:var(--navy);font-weight:700;font-size:14px;border-radius:99px;padding:9px 16px;margin:0 8px 8px 0"><span style="color:var(--blue)">{icon("check",16,2.6)}</span>{p}</span>' for p in proof)
    shot_h = 540 if kind=='customer' else 400
    body = f'''
<div style="height:{H}px;background:var(--s50);position:relative">
 <div class="bg-navy bg-grid dark" style="height:360px;padding:46px 64px;position:relative;overflow:hidden">
  <svg style="position:absolute;right:20px;top:20px;opacity:.85" width="330" height="330" viewBox="0 0 330 330">{scaffold(60,120,200,170,3,2,"#9fb6d9","#f5a623",3,.9)}</svg>
  {brand(40)}
  <div class="eyebrow" style="margin-top:34px;font-size:12px">{eb}</div>
  <h1 style="font-size:58px;margin-top:12px;color:#fff">{title}</h1>
  <p style="color:#c9d6ea;font-size:18px;max-width:640px;margin-top:16px;line-height:1.45">{sub}</p>
 </div>
 <div style="padding:30px 64px 0">{rhtml}</div>
 <div style="padding:6px 64px 0;display:flex;gap:28px;align-items:flex-start">
  <div style="width:620px;height:{shot_h}px;overflow:hidden;border-radius:12px" class="shot"><div class="bar"><i></i><i></i><i></i></div><img src="../../product-mockups/screenshots/{img}" style="width:100%;margin-top:0"></div>
  <div style="flex:1"><div class="eyebrow" style="font-size:11px;margin-bottom:12px">Built in</div>{phtml}<div class="note" style="margin-top:6px">{cap}</div></div>
 </div>
 <div class="bg-navy dark" style="position:absolute;left:0;right:0;bottom:0;height:120px;padding:0 64px;display:flex;align-items:center;justify-content:space-between">
  <div><div style="color:#fff;font-weight:800;font-size:24px">{CTA1}</div><div class="amber" style="font-weight:800;font-size:17px;margin-top:3px">{CTA2}</div></div>
  <div style="text-align:right;color:#c9d6ea;font-size:14px;line-height:1.5"><b style="color:#fff">{POWERED}</b><br>{WEB} &middot; {EMAIL}</div></div>
</div>'''
    nm = f"infographic-0{3 if kind=='customer' else 4}-{kind}-benefits"
    save(nm + ".html", page(W, H, body))
    reg(nm + ".html", "infographics", f"0{3 if kind=='customer' else 4}-{kind}-benefits", W, H)

# ------------------------------------------------------------------ 05 ecosystem (native SVG 1800x1120)
def ecosystem():
    W, H = 1800, 1120
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{SVG_STYLE}',
         '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f6f8fb"/><stop offset="1" stop-color="#e8f0fe"/></linearGradient>'
         '<linearGradient id="hub" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1f3a"/><stop offset="1" stop-color="#1a3f73"/></linearGradient>'
         '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#0b1f3a" stroke-opacity=".05"/></pattern>'
         '<marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M1 1L9 5L1 9" fill="none" stroke="#f5a623" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>']
    s.append(f'<g transform="translate(70 50)"><rect width="46" height="46" rx="12" fill="#0b1f3a"/><g transform="scale(.72)"><path d="M18 10v44M46 10v44M18 22h28M18 38h28M18 22l28 16" fill="none" stroke="#fff" stroke-width="4.5" stroke-linecap="round"/><circle cx="46" cy="22" r="5" fill="#f5a623"/></g></g>')
    s.append(tx(130, 82, "thinkNXG", 29, "#0b1f3a", 800)); s.append(tx(131, 98, "RENTAL MARKETPLACE", 11, "#f5a623", 700, ls=2.2))
    s.append(tx(W - 70, 70, "PLATFORM ECOSYSTEM", 15, "#f5a623", 700, "end", 3.5))
    s.append(tx(W - 70, 118, "Three portals, one engine, one fulfilment backbone", 34, "#0b1f3a", 800, "end"))

    def box(x, y, w, h, title, lines, ic, dark=False, accent="#f5a623"):
        fill, stroke, tc, lc = ("#0b1f3a", "#0b1f3a", "#fff", "#c9d6ea") if dark else ("#fff", "#dde3ec", "#0b1f3a", "#3d4757")
        o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="{fill}" stroke="{stroke}" stroke-width="1.5" filter="url(#sh)"/>']
        o.append(f'<rect x="{x+26}" y="{y+26}" width="54" height="54" rx="15" fill="{accent}"/>')
        o.append(svg_icon(ic, x + 40, y + 40, 26, "#0b1f3a", 1.9))
        o.append(tx(x + 98, y + 60, title, 24, tc, 800))
        for k, ln in enumerate(lines):
            o.append(tx(x + 30, y + 112 + k * 27, "•  " + ln, 17, lc, 500))
        return "".join(o)
    s.insert(2, '<defs><filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="14" stdDeviation="12" flood-color="#0b1f3a" flood-opacity=".12"/></filter></defs>')
    # operator (top centre)
    s.append(box(650, 180, 500, 188, "Operator console", ["Supplier verification &amp; moderation", "Tender oversight, payments, commissions", "Settlements, disputes, audit trail"], "console"))
    # public website (top left) & trust layer (top right)
    s.append(box(60, 190, 440, 150, "Public marketplace site", ["Catalogue, categories, suppliers", "Post a requirement"], "globe"))
    s.append(box(1300, 190, 440, 150, "Trust layer", ["Verified suppliers, reviews", "Disputes, insert-only audit events"], "shield"))
    # customer left, supplier right
    s.append(box(60, 430, 440, 235, "Customer workspace", ["Requirements &amp; tenders", "Compare offers, clarify, award", "Bookings, project sites, users", "Payments and reviews"], "user"))
    s.append(box(1300, 430, 440, 235, "Supplier portal", ["Tenders &amp; offers", "Equipment catalogue &amp; listings", "Bookings &amp; fulfilment", "Billing, settlements, subscription"], "building"))
    # hub
    s.append('<rect x="610" y="410" width="580" height="275" rx="30" fill="url(#hub)" filter="url(#sh)"/>')
    s.append('<rect x="610" y="410" width="580" height="275" rx="30" fill="url(#grid)" opacity=".9"/>')
    s.append(tx(900, 455, "THE ENGINE", 13, "#f5a623", 700, "middle", 3.5))
    s.append(tx(900, 497, "Tender &amp; bidding engine", 32, "#fff", 800, "middle"))
    chain = ["Request", "Tender", "Matching", "Offers", "Evaluation", "Booking"]
    for k, c in enumerate(chain):
        cx = 650 + (k % 3) * 170; cy = 540 + (k // 3) * 62
        s.append(f'<rect x="{cx}" y="{cy}" width="150" height="44" rx="12" fill="#fff" fill-opacity=".09" stroke="#fff" stroke-opacity=".22"/>')
        s.append(tx(cx + 75, cy + 28, c, 16, "#fff", 700, "middle"))
    s.append(tx(900, 672, "Sealed offers  ·  immutable revisions  ·  no double booking", 14, "#c9d6ea", 500, "middle"))
    # connectors
    def arrow(d, both=True):
        m = ' marker-start="url(#ar)"' if both else ""
        return f'<path d="{d}" fill="none" stroke="#f5a623" stroke-width="3.2" stroke-linecap="round"{m} marker-end="url(#ar)"/>'
    s.append(arrow("M500 548H606")); s.append(arrow("M1194 548H1296"))
    s.append(arrow("M900 372V406"))
    s.append(arrow("M280 344V426", False)); s.append(arrow("M1520 344V426", False))
    # bottom boxes
    s.append(box(60, 790, 760, 230, "thinkNXG Rental fulfilment engine", ["Hire Order and Rental Contract", "Material reservation, delivery, material at site", "Recurring rental billing, off-hire, return inspection", "Damage and loss settlement, cross hire"], "fulfil", True))
    s.append(box(980, 790, 760, 230, "Payment, commission &amp; settlement", ["Payments confirmed by provider webhook or Finance", "Rule-based marketplace commission", "Settlements marked paid only with a payout reference", "Gateway connectors: Manual, Stripe, Razorpay"], "settle"))
    s.append(arrow("M780 690C740 730 600 740 500 786")); s.append(arrow("M1020 690C1060 730 1200 740 1300 786", False))
    s.append(tx(300, 770, "Confirmed booking becomes a draft Hire Order", 15, "#0b1f3a", 700, "middle"))
    s.append(f'<rect x="395" y="738" width="0" height="0"/>')
    s.append(tx(60, 1075, CTA2, 26, "#f5a623", 800))
    s.append(tx(W - 70, 1066, "Powered by thinkNXG", 18, "#0b1f3a", 700, "end")); s.append(tx(W - 70, 1092, f"{WEB}  ·  {EMAIL}", 15, "#6b778a", 500, "end"))
    s.append('</svg>')
    open(os.path.join(ROOT, "source-files", "svg", "05-platform-ecosystem.svg"), "w", encoding="utf-8").write("".join(s))
    save("infographic-05-ecosystem.html", page(W, H, f'<img src="../svg/05-platform-ecosystem.svg" width="{W}" height="{H}" style="display:block">'))
    reg("infographic-05-ecosystem.html", "infographics", "05-platform-ecosystem", W, H)

# ------------------------------------------------------------------ 06 feature comparison (HTML 1200x1700)
def comparison():
    W, H = 1200, 1580
    def th(t, c="n"): return f'<div style="background:var(--{ "navy" if c=="n" else "amber"});color:{"#fff" if c=="n" else "var(--navy)"};font-weight:800;font-size:20px;padding:18px 20px;text-align:center">{t}</div>'
    rows = [("Priced by", "Rate per period: daily, weekly or monthly, pro-rata to the hire dates", "Price per unit", "Monthly rate over a fixed term in months"),
            ("Offer charges", "Delivery, loading, installation, mobilisation, demobilisation, tax; refundable deposit", "Same charge lines and tax", "Same charge lines and tax"),
            ("Booking journey", "Pending Payment &rarr; Confirmed &rarr; Dispatched &rarr; On Hire &rarr; Off-Hire Requested &rarr; Returned &rarr; Completed",
             "Pending Payment &rarr; Confirmed &rarr; Dispatched &rarr; Delivered &rarr; Completed",
             "Pending Payment &rarr; Confirmed &rarr; Mobilized &rarr; Active &rarr; Demobilized &rarr; Completed"),
            ("Fulfilment hand-off", "Draft Hire Order in thinkNXG Rental", "Sales Order", "Draft Hire Order (monthly) in thinkNXG Rental")]
    t = ['<div style="display:grid;grid-template-columns:200px 1fr 1fr 1fr;border-radius:18px;overflow:hidden;border:1px solid var(--s200);background:#fff;box-shadow:0 14px 30px -18px rgba(16,24,40,.3)">',
         '<div style="background:var(--navy)"></div>' + th("HIRE") + th("SALE", "a") + th("CONTRACT")]
    for i, r in enumerate(rows):
        bg = "#fff" if i % 2 == 0 else "var(--s50)"
        t.append(f'<div style="background:{bg};padding:20px;font-weight:800;color:var(--navy);font-size:16px;border-top:1px solid var(--s200)">{r[0]}</div>')
        for c in r[1:]:
            t.append(f'<div style="background:{bg};padding:20px;font-size:15px;line-height:1.45;color:var(--s700);border-top:1px solid var(--s200);border-left:1px solid var(--s200)">{c}</div>')
    t.append('</div>')
    left = ["Post requirements (hire, sale, contract)", "Tenders &amp; supplier matching", "Sealed offers &amp; comparison", "Clarification, negotiation &amp; award", "Booking &amp; payment tracking", "Commission, settlement &amp; reviews", "Verification, subscriptions &amp; operator console"]
    right = ["Hire Order &amp; Rental Contract", "Material reservation (multi-location)", "Delivery orders &amp; material-at-site ledger", "Recurring rental billing", "Off-hire &amp; return inspection", "Damage &amp; loss settlement", "Cross hire &amp; customer Command Center"]
    def col(title, sub, items, dark):
        bg = "var(--navy)" if dark else "#fff"; tc = "#fff" if dark else "var(--navy)"; lc = "#d3def0" if dark else "var(--s700)"
        lis = "".join(f'<div style="display:flex;gap:10px;margin-top:11px;font-size:16px;color:{lc};font-weight:600"><span style="color:var(--amber);flex:none">{icon("check",20,2.6)}</span>{x}</div>' for x in items)
        return f'<div style="flex:1;background:{bg};border:1px solid var(--s200);border-radius:20px;padding:30px 30px 26px;{"" if dark else "box-shadow:0 14px 30px -18px rgba(16,24,40,.3)"}"><div class="eyebrow" style="font-size:12px">{sub}</div><div style="font-weight:800;font-size:28px;color:{tc};margin-top:6px;letter-spacing:-.02em">{title}</div><div style="margin-top:14px">{lis}</div></div>'
    body = f'''
<div style="height:{H}px;background:var(--s50);position:relative" class="bg-grid-l">
 <div class="bg-navy bg-grid dark" style="height:300px;padding:46px 64px;position:relative;overflow:hidden">
  <svg style="position:absolute;right:30px;top:30px;opacity:.85" width="300" height="260" viewBox="0 0 300 260">{scaffold(40,70,200,150,3,2,"#9fb6d9","#f5a623",3,.9)}</svg>
  {brand(40)}<div class="eyebrow" style="margin-top:30px;font-size:12px">Feature comparison</div>
  <h1 style="font-size:50px;margin-top:10px;color:#fff">Three ways to source.<br><span class="amber">One marketplace.</span></h1></div>
 <div style="padding:34px 64px 0">{"".join(t)}
  <h2 style="font-size:34px;margin:44px 0 18px">Two products, one journey</h2>
  <div style="display:flex;gap:22px">{col("ThinkNXG Rental Marketplace","Sourcing &amp; award",left,True)}{col("thinkNXG Rental","Rental fulfilment engine",right,False)}</div>
  <div class="note" style="margin-top:16px">Marketplace-to-rental hand-off applies to suppliers connected on the same site. Source: product documentation and test suite.</div>
 </div>
 <div class="bg-navy dark" style="position:absolute;left:0;right:0;bottom:0;height:110px;padding:0 64px;display:flex;align-items:center;justify-content:space-between">
  <div><div style="color:#fff;font-weight:800;font-size:23px">{CTA1}</div><div class="amber" style="font-weight:800;font-size:17px;margin-top:3px">{CTA2}</div></div>
  <div style="text-align:right;color:#c9d6ea;font-size:14px;line-height:1.5"><b style="color:#fff">{POWERED}</b><br>{WEB} &middot; {EMAIL}</div></div>
</div>'''
    save("infographic-06-feature-comparison.html", page(W, H, body))
    reg("infographic-06-feature-comparison.html", "infographics", "06-feature-comparison", W, H)

def build():
    overview(); how_it_works(); benefits("customer"); benefits("supplier"); ecosystem(); comparison()

if __name__ == "__main__":
    build()

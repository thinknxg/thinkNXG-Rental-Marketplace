from lib import *

def dark(w, h, body, extra=""):
    return page(w, h, f'<div class="bg-navy bg-grid dark" style="position:relative;width:{w}px;height:{h}px;overflow:hidden;{extra}">{body}</div>')

def light(w, h, body):
    return page(w, h, f'<div class="bg-grid-l" style="position:relative;width:{w}px;height:{h}px;overflow:hidden;background-color:var(--s50)">{body}</div>')

def art(w, h, x, y, sc=1, crane_on=True, op=.85):
    return (f'<svg style="position:absolute;left:{x}px;top:{y}px" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'{scaffold(w*.12,h*.42,w*.52*sc,h*.46*sc,3,2,"#9fb6d9","#f5a623",3,op)}'
            f'{crane(w*.5,h*.0,min(w,h)/420*sc,"#9fb6d9","#f5a623",op) if crane_on else ""}</svg>')

def sig(size=15, dark_=True):
    c = "#fff" if dark_ else "var(--navy)"
    return f'<div style="font-size:{size}px;color:{c};text-align:right;line-height:1.5"><b>{POWERED}</b><br><span style="opacity:.7">{WEB}</span></div>'

def out(name, folder, fname, w, h, body, kind="dark", scale=2):
    save(name + ".html", (dark if kind == "dark" else light)(w, h, body))
    reg(name + ".html", folder, fname, w, h)
    MANIFEST[-1]["scale"] = scale

def build():
    # ---------------- LinkedIn 1200x627
    out("li1", "social-media", "linkedin-1-tagline", 1200, 627, f'''{art(520,520,700,60)}
 <div style="position:absolute;left:64px;top:52px">{brand(42)}</div>
 <div style="position:absolute;left:64px;top:170px;width:700px"><div class="eyebrow" style="font-size:14px">Premium Tender/Bid Marketplace</div>
 <h1 style="font-size:68px;margin-top:14px;color:#fff">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Sourcing.</span></h1></div>
 <div style="position:absolute;left:64px;bottom:48px;right:64px;display:flex;justify-content:space-between;align-items:flex-end"><div class="amber" style="font-weight:800;font-size:26px">{CTA2}</div>{sig()}</div>''')
    steps = [("req", "Post"), ("match", "Match"), ("offers", "Offers"), ("compare", "Compare"), ("book", "Book")]
    st = '<span style="color:var(--amber);margin:0 6px">' + icon("arrow", 26, 2.4) + "</span>"
    st = st.join(f'<div style="flex:1;text-align:center">{ico(i,76,"a",38)}<div style="color:#fff;font-weight:800;font-size:22px;margin-top:12px">{t}</div></div>' for i, t in steps)
    out("li2", "social-media", "linkedin-2-how-it-works", 1200, 627, f'''<div style="position:absolute;left:64px;top:52px">{brand(38)}</div>
 <div style="position:absolute;left:64px;top:140px;right:64px"><div class="eyebrow" style="font-size:14px">How it works</div><h2 style="font-size:50px;margin-top:10px;color:#fff">One requirement to a confirmed booking.</h2></div>
 <div style="position:absolute;left:64px;right:64px;top:320px;display:flex;align-items:flex-start">{st}</div>
 <div style="position:absolute;left:64px;bottom:48px;right:64px;display:flex;justify-content:space-between;align-items:flex-end"><div style="color:#fff;font-weight:800;font-size:24px">{CTA1}</div>{sig()}</div>''')
    out("li3", "social-media", "linkedin-3-suppliers", 1200, 627, f'''<div style="position:absolute;left:0;top:0;bottom:0;width:560px;padding:52px 0 0 64px">{brand(38)}
 <div class="eyebrow" style="font-size:14px;margin-top:62px">For suppliers</div><h2 style="font-size:52px;margin-top:12px;color:#fff;line-height:1.05">Win work you would never have heard about.</h2>
 <div style="margin-top:26px;color:#d3def0;font-size:19px;line-height:1.7;font-weight:600">&#10003; Tender invitations matched to your fleet<br>&#10003; Private, competitive bidding<br>&#10003; Bookings, billing and reviews in one portal</div></div>
 <div style="position:absolute;left:620px;top:70px;width:520px">{shot("supplier-tender-offer.png","width:520px;height:400px")}</div>
 <div style="position:absolute;left:620px;top:484px;font-size:12px;color:rgba(255,255,255,.55)">Product screenshot, demo data</div>
 <div style="position:absolute;left:64px;bottom:40px;right:64px;display:flex;justify-content:space-between;align-items:flex-end"><div class="amber" style="font-weight:800;font-size:24px">{CTA2}</div>{sig(14)}</div>''')
    out("lib", "social-media", "linkedin-banner-1584x396", 1584, 396, f'''{art(360,360,1230,-20,.9)}
 <div style="position:absolute;left:64px;top:56px">{brand(46)}</div>
 <div style="position:absolute;left:64px;top:158px;width:1100px"><div style="font-size:48px;line-height:1.08;font-weight:800;color:#fff;letter-spacing:-.02em">One Requirement. Multiple Offers.<br><span class="amber">Smarter Equipment Sourcing.</span></div>
 <div style="color:#c9d6ea;font-size:20px;margin-top:16px;font-weight:600">{SUB.replace("&amp;","&")} · {POWERED}</div></div>''')
    # ---------------- Instagram 1080x1080
    out("ig1", "social-media", "instagram-1-tagline-1080", 1080, 1080, f'''{art(480,480,600,20)}
 <div style="position:absolute;left:80px;top:80px">{brand(52)}</div>
 <div style="position:absolute;left:80px;top:420px;width:920px"><div class="eyebrow" style="font-size:18px">Premium Tender/Bid Marketplace</div>
 <h1 style="font-size:86px;margin-top:20px;color:#fff;letter-spacing:-.03em">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Equipment Sourcing.</span></h1></div>
 <div style="position:absolute;left:80px;bottom:70px;right:80px;display:flex;justify-content:space-between;align-items:flex-end"><div class="amber" style="font-weight:800;font-size:34px">{CTA2}</div>{sig(20)}</div>''')
    fe = [("lock", "Sealed offers", "Suppliers never see each other's prices"), ("compare", "Fair comparison", "Same-rules totals, line by line"), ("shield", "Verified suppliers", "Documents reviewed before they can bid")]
    fh = "".join(f'<div style="display:flex;gap:28px;align-items:center;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.16);border-radius:28px;padding:30px 34px;margin-top:22px">{ico(i,92,"a",46)}<div><div style="color:#fff;font-weight:800;font-size:40px">{t}</div><div style="color:#c9d6ea;font-size:25px;margin-top:4px">{d}</div></div></div>' for i, t, d in fe)
    out("ig2", "social-media", "instagram-2-sealed-offers-1080", 1080, 1080, f'''<div style="position:absolute;left:80px;top:80px">{brand(46)}</div>
 <div style="position:absolute;left:80px;top:200px;right:80px"><h2 style="font-size:78px;color:#fff;letter-spacing:-.03em">Bid fair.<br><span class="amber">Compare clearly.</span></h2>{fh}</div>
 <div style="position:absolute;left:80px;bottom:60px;right:80px;display:flex;justify-content:space-between;align-items:flex-end"><div style="color:#fff;font-weight:800;font-size:28px">{CTA1.replace("Construction Equipment.","<br>Construction Equipment.")}</div>{sig(20)}</div>''')
    fl = ["Booking confirmed", "Draft Hire Order in thinkNXG Rental", "Reservation &amp; delivery", "Material at site &amp; returns", "Billing &amp; settlement"]
    flh = "".join(f'<div style="display:flex;align-items:center;gap:24px;margin-top:18px"><div style="width:62px;height:62px;border-radius:50%;background:var(--amber);color:var(--navy);font-weight:800;font-size:30px;display:flex;align-items:center;justify-content:center;flex:none">{i+1}</div><div style="color:#fff;font-weight:700;font-size:34px">{t}</div></div>' for i, t in enumerate(fl))
    out("ig3", "social-media", "instagram-3-fulfilment-1080", 1080, 1080, f'''<div style="position:absolute;left:80px;top:80px">{brand(46)}</div>
 <div style="position:absolute;left:80px;top:200px;right:80px"><div class="eyebrow" style="font-size:18px">Marketplace to rental</div><h2 style="font-size:70px;color:#fff;margin-top:14px;letter-spacing:-.03em">From award to <span class="amber">on-site delivery.</span></h2><div style="margin-top:34px">{flh}</div></div>
 <div style="position:absolute;left:80px;bottom:60px;right:80px;display:flex;justify-content:space-between;align-items:flex-end"><div class="amber" style="font-weight:800;font-size:32px">{CTA2}</div>{sig(20)}</div>''')
    # ---------------- Instagram portrait 1080x1350 workflow
    names = ["Post Requirement", "Create Tender", "Match Suppliers", "Receive Offers", "Compare Offers", "Select Supplier", "Book", "Pay", "Fulfil", "Settle", "Review"]
    ic = ["req", "tender", "match", "offers", "compare", "select", "book", "pay", "fulfil", "settle", "star"]
    cells = "".join(f'<div style="display:flex;align-items:center;gap:18px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.16);border-radius:22px;padding:18px 22px">{ico(ic[i],62,"a",30)}<div><div style="color:var(--amber);font-weight:800;font-size:17px">{i+1:02d}</div><div style="color:#fff;font-weight:800;font-size:27px;line-height:1.1">{n}</div></div></div>' for i, n in enumerate(names))
    out("ig4", "social-media", "instagram-4-workflow-1080x1350", 1080, 1350, f'''<div style="position:absolute;left:70px;top:64px">{brand(44)}</div>
 <div style="position:absolute;left:70px;top:170px;right:70px"><h2 style="font-size:70px;color:#fff;letter-spacing:-.03em">Requirement to review in <span class="amber">eleven steps.</span></h2></div>
 <div style="position:absolute;left:70px;right:70px;top:380px;display:grid;grid-template-columns:1fr 1fr;gap:16px">{cells}</div>
 <div style="position:absolute;left:70px;bottom:56px;right:70px;display:flex;justify-content:space-between;align-items:flex-end"><div class="amber" style="font-weight:800;font-size:32px">{CTA2}</div>{sig(20)}</div>''')
    # ---------------- WhatsApp poster 1080x1350
    out("wa", "social-media", "whatsapp-poster-1080x1350", 1080, 1350, f'''{art(480,480,600,-60)}
 <div style="position:absolute;left:70px;top:64px">{brand(48)}</div>
 <div style="position:absolute;left:70px;top:400px;width:940px"><div class="eyebrow" style="font-size:19px">Scaffolding &middot; Formwork &middot; Equipment</div>
 <h1 style="font-size:82px;margin-top:20px;color:#fff;letter-spacing:-.03em">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Equipment Sourcing.</span></h1>
 <div style="color:#d3def0;font-size:28px;line-height:1.45;margin-top:26px;font-weight:600;max-width:800px">Hire, sale and long-term contracts from verified suppliers, compared side by side.</div></div>
 <div style="position:absolute;left:0;right:0;bottom:0;background:var(--amber);padding:44px 70px;color:var(--navy)"><div style="font-weight:800;font-size:40px;letter-spacing:-.02em;line-height:1.1">{CTA1}</div>
  <div style="display:flex;justify-content:space-between;margin-top:20px;font-size:26px;font-weight:700"><span>{WEB}</span><span>{EMAIL}</span></div></div>''')
    # ---------------- Website hero banners
    out("hero", "banners", "website-hero-1920x720", 1920, 720, f'''<div style="position:absolute;left:120px;top:60px;width:900px"><div class="eyebrow" style="font-size:17px">Premium tender / bid marketplace</div>
 <h1 style="font-size:72px;margin-top:14px;color:#fff">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Equipment Sourcing.</span></h1>
 <div style="color:#c9d6ea;font-size:22px;margin-top:20px;max-width:700px;line-height:1.4">Verified scaffolding, formwork and construction equipment suppliers compete for your requirement. Hire, sale and long-term contracts.</div>
 <div style="display:flex;gap:16px;margin-top:26px"><span style="background:var(--amber);color:var(--navy);font-weight:800;font-size:21px;padding:16px 30px;border-radius:12px">Post Your Requirement</span><span style="border:1.5px solid rgba(255,255,255,.4);color:#fff;font-weight:700;font-size:21px;padding:16px 30px;border-radius:12px">Explore Equipment</span></div></div>
 <div style="position:absolute;right:90px;top:70px;width:700px">{shot("customer-compare-offers.png","width:700px;height:520px")}<div style="font-size:13px;color:rgba(255,255,255,.55);margin-top:8px;text-align:right">Product screenshot, demo data</div></div>''')
    out("heromob", "banners", "website-hero-mobile-750x900", 750, 900, f'''{art(330,330,440,20,.9)}
 <div style="position:absolute;left:56px;top:56px">{brand(40)}</div>
 <div style="position:absolute;left:56px;top:330px;right:56px"><div class="eyebrow" style="font-size:15px">Premium tender / bid marketplace</div>
 <h1 style="font-size:62px;margin-top:16px;color:#fff">One Requirement.<br>Multiple Offers.<br><span class="amber">Smarter Equipment Sourcing.</span></h1>
 <div style="margin-top:34px"><span style="background:var(--amber);color:var(--navy);font-weight:800;font-size:22px;padding:18px 32px;border-radius:12px;display:inline-block">Post Your Requirement</span></div></div>
 <div style="position:absolute;left:56px;bottom:44px;right:56px;display:flex;justify-content:space-between;align-items:flex-end"><div class="amber" style="font-weight:800;font-size:22px">{CTA2}</div>{sig(15)}</div>''')
    # ---------------- Product mockups (real screenshots in a branded frame)
    def mock(nm, fname, img, eb, title, sub, h_img=560):
        out(nm, "product-mockups", fname, 1600, 1000, f'''<div style="position:absolute;left:80px;top:64px">{brand(40)}</div>
 <div style="position:absolute;left:80px;top:170px;width:1440px"><div class="eyebrow" style="font-size:15px">{eb}</div><h2 style="font-size:54px;margin-top:10px;color:#fff;letter-spacing:-.02em">{title}</h2><div style="color:#c9d6ea;font-size:21px;margin-top:10px">{sub}</div></div>
 <div style="position:absolute;left:230px;top:350px;width:1140px;height:{h_img}px;overflow:hidden;border-radius:14px" class="shot"><div class="bar"><i></i><i></i><i></i></div><img src="../../product-mockups/screenshots/{img}" style="width:1140px"></div>
 <div style="position:absolute;left:230px;bottom:18px;font-size:13px;color:rgba(255,255,255,.55)">Product screenshot, demo data</div>
 <div style="position:absolute;right:80px;bottom:18px">{sig(14)}</div>''')
    mock("mk1", "mockup-customer-compare-offers", "customer-compare-offers.png", "Customer workspace", "Compare offers side by side", "Same-rules totals. The lowest price is highlighted, never chosen for you.")
    mock("mk2", "mockup-supplier-offer-builder", "supplier-tender-offer.png", "Supplier portal", "Bid privately, revise with history", "Offer totals calculated by the marketplace; competitors never see your prices.")
    mock("mk3", "mockup-operator-analytics", "operator-analytics.png", "Operator console", "Run the marketplace with live analytics", "Requests, tenders, offers, conversion, commission and more.")
    mock("mk4", "mockup-public-marketplace", "marketplace-home.png", "Public marketplace", "Post a requirement in minutes", "Categories, suppliers and a guided requirement form.")
    # three-portal composition
    out("mk5", "product-mockups", "mockup-three-portals", 1800, 1000, f'''<div style="position:absolute;left:80px;top:64px">{brand(40)}</div>
 <div style="position:absolute;left:80px;top:160px"><div class="eyebrow" style="font-size:15px">Three portals, one engine</div><h2 style="font-size:54px;margin-top:10px;color:#fff;letter-spacing:-.02em">Customers, suppliers and operators on one platform.</h2></div>
 <div style="position:absolute;left:60px;top:400px;width:640px;height:470px;overflow:hidden" class="shot"><div class="bar"><i></i><i></i><i></i></div><img src="../../product-mockups/screenshots/customer-compare-offers.png" style="width:640px"></div>
 <div style="position:absolute;left:580px;top:340px;width:680px;height:520px;overflow:hidden;z-index:2" class="shot"><div class="bar"><i></i><i></i><i></i></div><img src="../../product-mockups/screenshots/supplier-tender-offer.png" style="width:680px"></div>
 <div style="position:absolute;left:1140px;top:400px;width:640px;height:470px;overflow:hidden" class="shot"><div class="bar"><i></i><i></i><i></i></div><img src="../../product-mockups/screenshots/operator-analytics.png" style="width:640px"></div>
 <div style="position:absolute;left:60px;top:884px;width:640px;text-align:center;color:#fff;font-weight:700;font-size:20px">Customer workspace</div>
 <div style="position:absolute;left:580px;top:884px;width:680px;text-align:center;color:#fff;font-weight:700;font-size:20px;z-index:3">Supplier portal</div>
 <div style="position:absolute;left:1140px;top:884px;width:640px;text-align:center;color:#fff;font-weight:700;font-size:20px">Operator console</div>
 <div style="position:absolute;left:80px;bottom:18px;font-size:13px;color:rgba(255,255,255,.55)">Product screenshots, demo data</div><div style="position:absolute;right:80px;bottom:18px">{sig(14)}</div>''')

if __name__ == "__main__":
    build()

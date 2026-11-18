"""Shared design system for the ThinkNXG Rental Marketplace campaign.
Palette, type and the logo mark are taken from the product itself (public/css/mp.css, public/images/logo.svg).
All illustrations are original vector drawings; no stock photography and no third-party logos are used."""
import os, html as _h

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # marketing/
HTML_DIR = os.path.join(ROOT, "source-files", "html")
os.makedirs(HTML_DIR, exist_ok=True)

PRODUCT = "ThinkNXG Rental Marketplace"
SUB = "Premium Tender/Bid Scaffolding &amp; Equipment Rental Marketplace"
POWERED = "Powered by thinkNXG"
TAGLINE = "One Requirement. Multiple Offers. Smarter Equipment Sourcing."
CTA1 = "Transform the Way You Source Construction Equipment."
CTA2 = "Connect. Bid. Book. Build."
EMAIL = "info@thinknxg.com"
WEB = "thinknxg.com"
WEB_RENTAL = "thinknxg.com/rental"

CSS = """
:root{--navy:#0b1f3a;--navy2:#12305a;--navy3:#1a3f73;--blue:#1d5fd6;--blue2:#3b7bf0;--blue-soft:#e8f0fe;
--amber:#f5a623;--amber2:#ffbf4d;--amber-soft:#fff4e0;--s50:#f6f8fb;--s100:#eef1f6;--s200:#dde3ec;--s300:#c3ccd9;
--s500:#6b778a;--s700:#3d4757;--ink:#101828;--green:#12a150;--green-soft:#e6f6ed;--violet:#6d4fd8}
*{box-sizing:border-box;margin:0;padding:0}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:"Inter","Inter Display",system-ui,"Segoe UI",Roboto,sans-serif;color:var(--ink);line-height:1.45;font-feature-settings:"cv11","ss01"}
h1,h2,h3,h4{font-weight:800;letter-spacing:-.02em;line-height:1.05;color:var(--navy)}
.dark h1,.dark h2,.dark h3,.dark h4{color:#fff}
.bg-navy{background:linear-gradient(135deg,#091a31 0%,#0e2848 55%,#1a3f73 130%)}
.bg-navy.bg-grid{background:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px) 0 0/40px 40px,linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px) 0 0/40px 40px,linear-gradient(135deg,#091a31 0%,#0e2848 55%,#1a3f73 130%)}
.bg-grid{background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px);background-size:40px 40px}
.bg-grid-l{background-image:linear-gradient(rgba(11,31,58,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(11,31,58,.045) 1px,transparent 1px);background-size:40px 40px}
.eyebrow{font-size:.72em;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--amber)}
.amber{color:var(--amber)}.blue{color:var(--blue)}.muted{color:var(--s500)}.white{color:#fff}
.brand{display:flex;align-items:center;gap:.7em}
.brand .wm{font-weight:800;letter-spacing:-.02em;line-height:1}
.brand .wm small{display:block;font-size:.42em;letter-spacing:.2em;font-weight:700;color:var(--amber);margin-top:.35em;text-transform:uppercase}
.dark .brand .wm{color:#fff}.brand .wm{color:var(--navy)}
.card{background:#fff;border:1px solid var(--s200);border-radius:18px;box-shadow:0 1px 2px rgba(16,24,40,.05),0 14px 30px -18px rgba(16,24,40,.25)}
.card.dk{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);box-shadow:none;color:#fff}
.ico{display:inline-flex;align-items:center;justify-content:center;border-radius:14px;flex:none}
.ico.a{background:var(--amber);color:var(--navy)}.ico.b{background:var(--blue);color:#fff}.ico.n{background:var(--navy);color:var(--amber)}
.ico.s{background:var(--blue-soft);color:var(--blue)}.ico.w{background:rgba(255,255,255,.1);color:var(--amber);border:1px solid rgba(255,255,255,.18)}
.pill{display:inline-block;border-radius:99px;padding:.32em .9em;font-weight:700;font-size:.78em;letter-spacing:.04em}
.pill.a{background:var(--amber);color:var(--navy)}.pill.n{background:var(--navy);color:#fff}.pill.o{border:1.5px solid rgba(255,255,255,.4);color:#fff}
.pill.g{background:var(--green-soft);color:var(--green)}.pill.s{background:var(--blue-soft);color:var(--blue)}
.foot{display:flex;justify-content:space-between;align-items:center;font-size:.8em}
.shot{border-radius:12px;overflow:hidden;border:1px solid var(--s200);background:#fff;box-shadow:0 30px 60px -30px rgba(11,31,58,.55)}
.shot .bar{height:26px;background:#eef1f6;display:flex;align-items:center;gap:6px;padding:0 10px;border-bottom:1px solid var(--s200)}
.shot .bar i{width:9px;height:9px;border-radius:50%;background:#c3ccd9;display:block}
.shot img{display:block;width:100%}
.note{font-size:.7em;color:var(--s500)}
.dark .note{color:rgba(255,255,255,.55)}
"""

ICONS = {
 "req": '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/>',
 "tender": '<path d="M4 4v17M4 5h13l-2.5 4L17 13H4"/>',
 "match": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6M15 14.5c3 0 6 1.7 6 5"/>',
 "offers": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
 "compare": '<path d="M12 3v18M5 21h14M5 7h14M5 7l-3 7a3.5 3 0 0 0 6 0zM19 7l-3 7a3.5 3 0 0 0 6 0z"/>',
 "select": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
 "book": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4M8 15l2.5 2.5L16 13"/>',
 "pay": '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19M6 15h4"/>',
 "fulfil": '<path d="M2 6h11v10H2zM13 9h4l4 4v3h-8"/><circle cx="7" cy="17.5" r="2"/><circle cx="17" cy="17.5" r="2"/>',
 "settle": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
 "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
 "shield": '<path d="M12 3l8 3v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
 "lock": '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
 "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
 "chart": '<path d="M3 21h18M6 17v-5M11 17V7M16 17v-8M21 17V4"/>',
 "layers": '<path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5"/>',
 "box": '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
 "pin": '<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
 "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
 "building": '<path d="M4 21V5l8-2v18M12 8h8v13M2 21h20M8 9h1M8 13h1M8 17h1M15 12h2M15 16h2"/>',
 "console": '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4M7 12l3-3 2.5 2.5L17 8"/>',
 "list": '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
 "chat": '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
 "return": '<path d="M20 12a8 8 0 1 1-2.5-5.8M20 4v5h-5"/>',
 "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
 "check": '<path d="M5 12.5l4.5 4.5L19 7"/>',
 "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/>',
 "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
 "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
 "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
 "doc": '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/>',
 "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
}

def icon(name, size=24, sw=1.7):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')

def ico(name, box=56, cls="a", size=None):
    size = size or int(box * .5)
    return f'<span class="ico {cls}" style="width:{box}px;height:{box}px;border-radius:{box*.27:.0f}px">{icon(name, size)}</span>'

MARK = ('<svg viewBox="0 0 64 64" width="{s}" height="{s}"><rect width="64" height="64" rx="16" fill="{bg}"/>'
        '<path d="M18 10v44M46 10v44M18 22h28M18 38h28M18 22l28 16" fill="none" stroke="{fg}" stroke-width="4.5" stroke-linecap="round"/>'
        '<circle cx="46" cy="22" r="5" fill="#f5a623"/></svg>')

def brand(size=44, dark=True, sub="Rental Marketplace"):
    bg, fg = ("#fff", "#0b1f3a") if dark else ("#0b1f3a", "#fff")
    cls = "dark" if dark else ""
    return (f'<div class="brand {cls}">{MARK.format(s=size, bg=bg, fg=fg)}'
            f'<div class="wm" style="font-size:{size*.62:.0f}px">thinkNXG<small>{sub}</small></div></div>')

def scaffold(x=0, y=0, w=300, h=400, levels=4, bays=2, stroke="#fff", accent="#f5a623", sw=3, op=1, deck=True):
    """Original scaffold-tower drawing: standards, ledgers, diagonal braces, amber working decks."""
    bw, lh = w / bays, h / levels
    p = [f'<g transform="translate({x} {y})" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" opacity="{op}">']
    for i in range(bays + 1):
        p.append(f'<path d="M{i*bw:.1f} 0V{h}"/>')
    for l in range(levels + 1):
        p.append(f'<path d="M0 {l*lh:.1f}H{w}"/>')
    for l in range(levels):
        for b in range(bays):
            a, bb = b * bw, (b + 1) * bw
            if (l + b) % 2 == 0:
                p.append(f'<path d="M{a:.1f} {l*lh:.1f}L{bb:.1f} {(l+1)*lh:.1f}" stroke-width="{sw*.7:.1f}"/>')
            else:
                p.append(f'<path d="M{bb:.1f} {l*lh:.1f}L{a:.1f} {(l+1)*lh:.1f}" stroke-width="{sw*.7:.1f}"/>')
    if deck:
        for l in (1, levels - 1 if levels > 2 else 1):
            p.append(f'<path d="M{-w*.04:.1f} {l*lh:.1f}H{w*1.04:.1f}" stroke="{accent}" stroke-width="{sw*2.2:.1f}"/>')
    p.append('</g>')
    return "".join(p)

def crane(x=0, y=0, s=1, stroke="#fff", accent="#f5a623", op=1):
    g = [f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{stroke}" stroke-width="3" stroke-linecap="round" opacity="{op}">']
    g.append('<path d="M60 360V60M90 360V60"/>')
    for i in range(12):
        yy = 360 - i * 25
        g.append(f'<path d="M60 {yy}L90 {yy-25}M90 {yy}L60 {yy-25}" stroke-width="1.8"/>')
    g.append(f'<path d="M30 60H340M75 20V60M75 20L340 60M75 20L20 60M20 60V80H60" />')
    g.append(f'<path d="M190 60V160" stroke="{accent}" stroke-width="2.5"/><rect x="178" y="160" width="24" height="16" rx="3" stroke="{accent}" fill="{accent}"/>')
    g.append(f'<rect x="12" y="60" width="28" height="30" fill="{accent}" stroke="none" opacity=".85"/>')
    g.append('</g>')
    return "".join(g)

def skyline(w, h, color="#fff", op=.08):
    """Abstract construction skyline strip (rectangles + scaffold frames) for backgrounds."""
    import random
    r = random.Random(7)
    out = [f'<g fill="{color}" opacity="{op}">']
    x = 0
    while x < w:
        bw = r.randint(60, 140); bh = r.randint(int(h * .25), int(h * .8))
        out.append(f'<rect x="{x}" y="{h-bh}" width="{bw}" height="{bh}"/>')
        x += bw + r.randint(6, 20)
    out.append('</g>')
    return "".join(out)

def page(w, h, body, css="", cls="", style=""):
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{PRODUCT}</title><style>{CSS}'
            f'@page{{size:{w}px {h}px;margin:0}}'
            f'html,body{{width:{w}px;height:{h}px;overflow:hidden}}{css}</style></head>'
            f'<body class="{cls}" style="{style}">{body}</body></html>')

def save(name, html):
    p = os.path.join(HTML_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    return p

def shot(src, extra="", bar=True):
    b = '<div class="bar"><i></i><i></i><i></i></div>' if bar else ""
    return f'<div class="shot" style="{extra}">{b}<img src="../../product-mockups/screenshots/{src}"></div>'

MANIFEST = []  # (html_file, out_dir, out_name, w, h, kinds)
def reg(html_name, out_dir, out_name, w, h, kinds=("png",)):
    MANIFEST.append(dict(html=html_name, dir=out_dir, name=out_name, w=w, h=h, kinds=list(kinds)))

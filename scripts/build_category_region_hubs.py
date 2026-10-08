from pathlib import Path
import re, html

ROOT = Path(".")
REGIONS = [("seoul","Seoul"),("busan","Busan"),("jeju","Jeju")]
CATEGORIES = [
    ("travel","Travel"),("food","Food"),("cafe","Cafe"),("shopping","Shopping"),
    ("culture","Culture"),("leisure","Leisure"),("stay","Stay"),("local-guide","Local Guide")
]

def title_from_html(p):
    s = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<title>(.*?)</title>", s, re.I | re.S)
    return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else p.stem.replace("-", " ").title()

CSS = """
.hub-hero{padding:72px 0 44px;border-bottom:1px solid #ddd8ce}
.hub-hero h1{font-size:clamp(42px,7vw,78px);margin:8px 0 18px}
.hub-hero p{max-width:680px;font-size:18px;line-height:1.7}
.hub-cats{display:flex;flex-wrap:wrap;gap:10px;margin:28px 0}
.hub-cats a{padding:10px 15px;border:1px solid #d8d1c5;border-radius:999px;text-decoration:none}
.hub-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:30px 0 80px}
.hub-card{display:block;padding:24px;border:1px solid #ddd8ce;text-decoration:none;color:inherit;min-height:170px}
.hub-card span{font-size:12px;letter-spacing:.12em}.hub-card h3{font-size:22px;line-height:1.3}
.hub-card b{font-size:13px}.empty{padding:40px;border:1px dashed #ccc}
@media(max-width:800px){.hub-grid{grid-template-columns:1fr}}
"""

def make_page(filename, heading, intro, cards, label):
    nav = '<a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="seoul.html">Seoul</a><a href="busan.html">Busan</a><a href="jeju.html">Jeju</a><a href="#categories">More</a>'
    category_links = ''.join(f'<a href="{c}.html">{n}</a>' for c,n in CATEGORIES)
    cards_html = []
    for p in cards:
        cards_html.append(f'<a class="hub-card" href="{p.name}"><span>{html.escape(label.upper())}</span><h3>{html.escape(title_from_html(p))}</h3><b>Read guide &rarr;</b></a>')
    if not cards_html:
        cards_html = ['<div class="empty">New guides are coming soon.</div>']
    template = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="INTRO">
<link rel="canonical" href="https://korea-plainly.com/FILENAME">
<title>HEADING | Korea Plainly</title><link rel="stylesheet" href="style.css">
<style>CSS</style></head><body>
<header><div class="nav wrap"><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a>
<nav>NAV</nav><a class="top-link" href="guides.html">Latest <span>↗</span></a><button class="menu" aria-label="menu">☰</button></div></header>
<main><section class="hub-hero"><div class="wrap"><p class="kicker"><i></i> KOREA PLAINLY</p>
<h1>HEADING</h1><p>INTRO</p><div class="hub-cats" id="categories">CATS</div></div></section>
<section class="wrap section"><div class="hub-grid">CARDS</div></section></main>
<footer><div class="wrap foot"><div><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a><p>Korea, Made Easy for Everyone.</p></div>
<div class="foot-links"><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="privacy.html">Privacy</a><a href="contact.html">Contact</a></div></div></footer>
<script>document.querySelector('.menu').addEventListener('click',()=>document.querySelector('nav').classList.toggle('show'));</script>
</body></html>"""
    doc = template.replace("INTRO", html.escape(intro)).replace("FILENAME", filename).replace("HEADING", html.escape(heading)).replace("CSS", CSS).replace("NAV", nav).replace("CATS", category_links).replace("CARDS", ''.join(cards_html))
    (ROOT / filename).write_text(doc, encoding="utf-8")

for slug,name in REGIONS:
    make_page(f"{slug}.html", name, f"Explore {name} through Travel, Food, Cafe, Shopping, Culture, Leisure, Stay and Local Guide.", sorted(ROOT.glob(f"{slug}-*.html")), name)

for slug,name in CATEGORIES:
    make_page(f"{slug}.html", f"{name} in Korea", f"Useful {name.lower()} picks and guides from Seoul, Busan, Jeju and beyond.", sorted(ROOT.glob(f"*-{slug}-*.html")), name)

p = ROOT / "index.html"
if p.exists():
    s = p.read_text(encoding="utf-8")
    old = '<nav><a href="#guides">Guides</a><a href="#seoul">Seoul</a><a href="#food">Food</a><a href="#culture">Culture</a><a href="#life">Daily Life</a></nav>'
    new = '<nav><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="seoul.html">Seoul</a><a href="busan.html">Busan</a><a href="jeju.html">Jeju</a><a href="#categories">More</a></nav>'
    p.write_text(s.replace(old,new), encoding="utf-8")

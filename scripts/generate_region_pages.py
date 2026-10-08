
from pathlib import Path
import json, re, html

ROOT = Path(__file__).resolve().parents[1]
REGION_FILE = ROOT / "content" / "region_rotation.json"

CATS = {
    "travel":"Travel","food":"Food","cafe":"Cafe","shopping":"Shopping",
    "culture":"Culture","leisure":"Leisure","stay":"Stay","local-guide":"Local Guide"
}

def esc(x):
    return html.escape(str(x), quote=True)

def get_title(p):
    s = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<title>(.*?)</title>", s, re.I|re.S)
    if not m:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.I|re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else p.stem.replace("-"," ").title()

def page(region):
    slug, name = region["slug"], region["name"]
    items = []
    for p in ROOT.glob(slug + "-*.html"):
        rest = p.stem[len(slug)+1:]
        cat = next((k for k in sorted(CATS,key=len,reverse=True) if rest == k or rest.startswith(k+"-")), None)
        if cat:
            items.append((list(CATS).index(cat), CATS[cat], get_title(p), p.name))
    items.sort(key=lambda x:(x[0],x[2]))
    cards = "".join(
        '<article class="card"><a href="{}"><div class="tag">{}</div><h2>{}</h2><span>Read guide &rarr;</span></a></article>'.format(
            esc(fn), esc(cat), esc(title)
        ) for _,cat,title,fn in items
    )
    if not cards:
        cards = '<p class="empty">New recommendations for this region will appear here automatically.</p>'
    template = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} Travel, Food, Shopping & Local Guides | Korea Plainly</title>
<meta name="description" content="Practical {name} recommendations for foreign visitors to Korea, including travel, food, cafes, shopping, culture, leisure, stays and local guides.">
<link rel="canonical" href="https://korea-plainly.com/{slug}.html">
<style>
body{{margin:0;background:#f6f1e7;color:#17233b;font-family:Arial,sans-serif;line-height:1.6}}
header{{border-bottom:1px solid #ded6c8}}.nav{{max-width:1180px;margin:auto;padding:22px;display:flex;justify-content:space-between}}
.nav a{{color:#17233b;text-decoration:none;margin-left:18px;font-weight:700;font-size:14px}}
main{{max-width:1180px;margin:auto;padding:52px 22px 80px}}.kicker,.tag{{color:#b73535;font-weight:800;letter-spacing:.1em;text-transform:uppercase;font-size:12px}}
h1{{font-size:clamp(44px,8vw,82px);line-height:1;margin:12px 0}}.intro{{max-width:700px;font-size:19px}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;margin-top:42px}}.card{{background:#fff;border:1px solid #ded6c8;min-height:210px}}
.card a{{display:block;height:100%;padding:28px;color:#17233b;text-decoration:none}}.card h2{{font-size:30px;line-height:1.12;margin:14px 0 28px}}
.card span{{font-size:14px;font-weight:700}}.empty{{padding:30px;background:#fff;border:1px solid #ded6c8}}
@media(max-width:700px){{.grid{{grid-template-columns:1fr}}.card h2{{font-size:26px}}}}
</style></head>
<body><header><div class="nav"><strong>KOREA PLAINLY</strong><div><a href="index.html">Home</a><a href="guides.html">Guides</a><a href="regions.html">Regions</a></div></div></header>
<main><div class="kicker">Regional hub</div><h1>{name}</h1>
<p class="intro">A practical collection of places and experiences in {name} for foreign visitors — from travel and food to cafes, shopping, culture, leisure and stays.</p>
<section class="grid">{cards}</section></main></body></html>'''
    return template.format(name=esc(name),slug=esc(slug),cards=cards)

data = json.loads(REGION_FILE.read_text(encoding="utf-8"))
for region in data.get("regions", []):
    (ROOT / (region["slug"] + ".html")).write_text(page(region), encoding="utf-8")

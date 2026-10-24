
from pathlib import Path
import json, re, html

ROOT = Path(__file__).resolve().parents[1]
REGION_FILE = ROOT / "content" / "region_rotation.json"
INTROS_FILE = ROOT / "content" / "region_intros.json"
OVERVIEWS_FILE = ROOT / "content" / "region_overviews.json"   # practical "planning a trip" text for each hub
INTROS = json.loads(INTROS_FILE.read_text(encoding="utf-8")) if INTROS_FILE.exists() else {}
OVERVIEWS = json.loads(OVERVIEWS_FILE.read_text(encoding="utf-8")) if OVERVIEWS_FILE.exists() else {}
# first-timer pages linked in one sentence at the top of "Planning a trip to ..." (only if the page exists)
START_LINKS = {
    "seoul": [("seoul-3-day-itinerary.html", "a 3-day itinerary"),
              ("seoul-neighborhoods-guide.html", "where to stay by neighbourhood"),
              ("seoul-subway-for-foreigners.html", "how to use the subway")],
    "busan": [("busan-1-day-itinerary.html", "a 1-day itinerary"),
              ("ktx-train-guide.html", "the KTX train from Seoul")],
}

def hub_title(name):
    t = "{} Travel Guide: Things to Do, Food and Where to Stay".format(name)
    return t if len(t) <= 60 else "{} Travel Guide: Things to Do and Local Tips".format(name)

def start_links(slug, name):
    links = ['<a href="{}">{}</a>'.format(esc(f), esc(t)) for f, t in START_LINKS.get(slug, [])
             if (ROOT / f).exists() and "kp-redirect" not in (ROOT / f).read_text(encoding="utf-8", errors="ignore")]
    if not links:
        return ""
    joined = links[0] if len(links) == 1 else ", ".join(links[:-1]) + " and " + links[-1]
    return '<p class="start">New to {}? Start with {}.</p>'.format(esc(name), joined)

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
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else p.stem.replace("-"," ").title()
    return re.sub(r"\s*\|\s*Korea Plainly\s*$", "", t)

def thumb_for(p):
    s = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'<img[^>]+class="cover"[^>]+src="([^"]+)"', s) or re.search(r'property="og:image"\s+content="https://korea-plainly\.com/([^"]+)"', s)
    src = m.group(1) if m else "og-default.jpg"
    return src if (ROOT / src).exists() else "og-default.jpg"

def page(region):
    slug, name = region["slug"], region["name"]
    items, cats_with_items = [], []
    for p in ROOT.glob(slug + "-*.html"):
        rest = p.stem[len(slug)+1:]
        cat = next((k for k in sorted(CATS,key=len,reverse=True) if rest.startswith(k+"-")), None)
        if cat and "kp-redirect" not in p.read_text(encoding="utf-8", errors="ignore"):  # an article, not a hub or merged page
            items.append((list(CATS).index(cat), CATS[cat], get_title(p), p.name, thumb_for(p)))
            if cat not in cats_with_items:
                cats_with_items.append(cat)
    items.sort(key=lambda x:(x[0],x[2]))
    cards = "".join(
        '<article class="card"><a href="{}"><img src="{}" alt="" loading="lazy"><div class="card-body"><div class="tag">{}</div><h2>{}</h2><span>Read guide &rarr;</span></div></a></article>'.format(
            esc(fn), esc(img), esc(cat), esc(title)
        ) for _,cat,title,fn,img in items
    )
    groups = [("see-do", "See &amp; Do"), ("eat-drink", "Eat &amp; Drink"), ("shop", "Shop"), ("stay", "Stay")]
    chips = "".join('<a href="{}-{}.html">{}</a>'.format(esc(slug), g, label) for g, label in groups
                    if (ROOT / "{}-{}.html".format(slug, g)).exists()
                    and "kp-redirect" not in (ROOT / "{}-{}.html".format(slug, g)).read_text(encoding="utf-8", errors="ignore"))
    if not cards:
        cards = '<p class="empty">New recommendations for this region will appear here automatically.</p>'
    template = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Korea Plainly</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://korea-plainly.com/{slug}.html">
<style>
body{{margin:0;background:#f6f1e7;color:#17233b;font-family:Arial,sans-serif;line-height:1.6}}
main{{max-width:1180px;margin:auto;padding:52px 22px 80px}}.kicker,.tag{{color:#b73535;font-weight:800;letter-spacing:.1em;text-transform:uppercase;font-size:12px}}
h1{{font-size:clamp(44px,8vw,82px);line-height:1;margin:12px 0}}.intro{{max-width:700px;font-size:19px}}
.chips{{display:flex;flex-wrap:wrap;gap:10px;margin-top:26px}}.chips a{{padding:9px 15px;border:1px solid #d8d1c5;border-radius:999px;color:#17233b;text-decoration:none;font-size:14px;background:#fff}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:38px}}.card{{background:#fff;border:1px solid #ded6c8;overflow:hidden}}
.card a{{display:block;height:100%;color:#17233b;text-decoration:none}}.card img{{display:block;width:100%;aspect-ratio:16/10;object-fit:cover}}
.card-body{{padding:20px 22px 24px}}.card h2{{font-size:21px;line-height:1.25;margin:10px 0 18px}}
.card span{{font-size:14px;font-weight:700}}
.plan{{display:grid;grid-template-columns:200px 1fr;align-items:center;gap:22px;margin-top:30px;background:#fff;border:1px solid #ded6c8;color:#17233b;text-decoration:none;overflow:hidden}}
.plan img{{width:100%;height:100%;min-height:120px;object-fit:cover;display:block}}.plan small{{color:#b73535;font-weight:800;letter-spacing:.1em;text-transform:uppercase;font-size:11px}}
.plan b{{display:block;font-size:22px;line-height:1.25;margin:6px 22px 6px 0}}.plan em{{font-style:normal;font-size:14px;font-weight:700}}
@media(max-width:600px){{.plan{{grid-template-columns:110px 1fr;gap:14px}}.plan b{{font-size:17px}}}}.empty{{padding:30px;background:#fff;border:1px solid #ded6c8}}
.overview{{max-width:760px;margin-top:56px}}.overview h2{{font-size:32px;line-height:1.15;margin:0 0 6px}}.overview h3{{font-size:19px;margin:24px 0 4px}}.overview p{{margin:0;font-size:17px}}.overview .start{{margin:8px 0 0}}.overview .start a{{color:#b73535;font-weight:700}}
@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}
</style></head>
<body><header><div class="nav"><strong>KOREA PLAINLY</strong></div></header>
<main><div class="kicker">Regional hub</div><h1>{name}</h1>
<p class="intro">{intro}</p>
<div class="chips">{chips}</div>
{plans}
<section class="grid">{cards}</section>{overview}</main></body></html>'''
    intro = INTROS.get(slug) or "A practical collection of places and experiences in {} for foreign visitors, from travel and food to cafes, shopping, culture, leisure and stays.".format(name)
    plans = "".join(
        '<a class="plan" href="{}"><img src="{}" alt="" loading="lazy"><div><small>Plan your days</small><b>{}</b><em>Read the itinerary &rarr;</em></div></a>'.format(
            esc(p.name), esc(thumb_for(p)), esc(get_title(p)))
        for p in sorted(ROOT.glob(slug + "-*itinerary*.html"))
        if "kp-redirect" not in p.read_text(encoding="utf-8", errors="ignore"))
    lead = "A {} travel guide for first-time visitors: ".format(name)
    desc = lead + intro
    description = desc if len(desc) <= 160 else desc[:157].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"
    ov = OVERVIEWS.get(slug) or []
    overview = ('<section class="overview"><h2>Planning a trip to {}</h2>{}{}</section>'.format(
        esc(name), start_links(slug, name), "".join("<h3>{}</h3><p>{}</p>".format(esc(h), esc(t)) for h, t in ov)) if ov else "")
    return template.format(name=esc(name),title=esc(hub_title(name)),slug=esc(slug),cards=cards,chips=chips,intro=esc(intro),
                           plans=plans,description=esc(description),overview=overview)

data = json.loads(REGION_FILE.read_text(encoding="utf-8"))
for region in data.get("regions", []):
    (ROOT / (region["slug"] + ".html")).write_text(page(region), encoding="utf-8")

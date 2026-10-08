
from pathlib import Path
import re

p = Path("guides.html")
s = p.read_text(encoding="utf-8")

s = re.sub(
    r'<nav>.*?</nav>',
    '<nav><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="seoul.html">Seoul</a><a href="busan.html">Busan</a><a href="jeju.html">Jeju</a><a href="#guide-categories">More</a></nav>',
    s, count=1, flags=re.S
)

old_intro = """<section class="wrap guides-hero">
<p class="kicker"><i></i> KOREA PLAINLY GUIDES</p>
<h1>Useful guides.<br><em>Nothing complicated.</em></h1>
<p class="guides-intro">Practical information about Korea, written for people who want to understand the basics quickly — from getting around Seoul to everyday Korean life.</p>
</section>"""

new_intro = """<section class="wrap guides-hero">
<p class="kicker"><i></i> KOREA PLAINLY GUIDES</p>
<h1>Useful guides.<br><em>Nothing complicated.</em></h1>
<p class="guides-intro">Practical, nationwide information for understanding Korea — transport, money, apps, food, daily life, language and more.</p>
</section>
<section class="wrap guide-category-bar" id="guide-categories">
<div class="guide-category-title">GUIDE CATEGORIES</div>
<div class="guide-category-links">
<button type="button" class="guide-filter active" data-filter="all">All Guides</button>
<button type="button" class="guide-filter" data-filter="travel">Travel Basics</button>
<button type="button" class="guide-filter" data-filter="transport">Transport</button>
<button type="button" class="guide-filter" data-filter="money">Money</button>
<button type="button" class="guide-filter" data-filter="apps">Apps & Tips</button>
<button type="button" class="guide-filter" data-filter="food">Food & Dining</button>
<button type="button" class="guide-filter" data-filter="daily">Daily Life</button>
<button type="button" class="guide-filter" data-filter="language">Language</button>
<button type="button" class="guide-filter" data-filter="culture">Culture</button>
</div>
</section>"""

if old_intro not in s:
    raise SystemExit("Guides intro block not found.")
s = s.replace(old_intro, new_intro)

category_map = {
"seoul-first-time.html":"travel","seoul-subway-for-foreigners.html":"transport","t-money-korea-guide.html":"transport",
"korean-convenience-store-guide.html":"daily","korean-restaurant-words.html":"food","naver-map-vs-google-maps-korea.html":"apps",
"cash-cards-payments-korea.html":"money","kakao-t-korea-guide.html":"transport","kakao-t-taxi-korea.html":"transport",
"korean-cafe-etiquette.html":"culture","korean-dining-etiquette.html":"food","sim-esim-wifi-korea.html":"travel",
"read-korean-menu.html":"food","korean-convenience-store-meals.html":"food","seoul-neighborhoods-guide.html":"travel",
"how-to-order-korean-food.html":"food","korea-travel-mistakes.html":"travel","useful-korean-phrases.html":"language",
"korea-public-transport-transfers.html":"transport","korean-bathhouse-guide.html":"culture","korean-street-food-guide.html":"food",
"first-evening-seoul.html":"travel","korean-convenience-store-tips.html":"daily","korea-recycling-guide.html":"daily",
"korean-atm-guide.html":"money","korea-transit-card-guide.html":"transport","seoul-bus-guide.html":"transport",
"best-time-seoul-attractions.html":"travel"
}

for slug, cat in category_map.items():
    s = re.sub(
        rf'(<a\s+class="guide-card"\s+href="{re.escape(slug)}")',
        rf'\1 data-guide-category="{cat}"',
        s, count=1
    )
    s = re.sub(
        rf'(<a\s*\n\s*class="guide-card"\s*\n\s*href="{re.escape(slug)}")',
        rf'\1 data-guide-category="{cat}"',
        s, count=1
    )

css = """<style id="guide-category-fix">
.guide-category-bar{padding:0 0 36px}
.guide-category-title{font-size:11px;font-weight:700;letter-spacing:.14em;margin-bottom:14px}
.guide-category-links{display:flex;flex-wrap:wrap;gap:9px}
.guide-filter{appearance:none;border:1px solid rgba(20,28,42,.18);background:transparent;color:inherit;border-radius:999px;padding:9px 14px;font:inherit;font-size:13px;cursor:pointer}
.guide-filter:hover,.guide-filter.active{background:#141c2a;color:#fff;border-color:#141c2a}
.guide-card.is-hidden{display:none}
</style>"""
if 'id="guide-category-fix"' not in s:
    s = s.replace("</style>\n</head>", "</style>\n" + css + "\n</head>", 1)

js = """<script id="guide-category-filter">
(function(){
  const buttons=document.querySelectorAll('.guide-filter');
  const cards=document.querySelectorAll('.guide-card');
  buttons.forEach(button=>button.addEventListener('click',()=>{
    const filter=button.dataset.filter;
    buttons.forEach(b=>b.classList.remove('active'));
    button.classList.add('active');
    cards.forEach(card=>card.classList.toggle('is-hidden',filter!=='all' && card.dataset.guideCategory!==filter));
  }));
})();
</script>"""
if 'id="guide-category-filter"' not in s:
    s = s.replace("</body>", js + "\n</body>")

s = s.replace(
'<div class="foot-links"><a href="guides.html">Guides</a><a href="index.html#seoul">Seoul</a><a href="index.html#food">Food</a><a href="index.html#culture">Culture</a><a href="index.html#life">Daily Life</a></div>',
'<div class="foot-links"><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="seoul.html">Seoul</a><a href="busan.html">Busan</a><a href="jeju.html">Jeju</a><a href="privacy.html">Privacy</a></div>'
)

p.write_text(s, encoding="utf-8")
print("Guides category structure patched.")

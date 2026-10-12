from pathlib import Path
import re, html

ROOT = Path('.')
REGIONS = [('seoul','Seoul'),('busan','Busan'),('jeju','Jeju')]
CATEGORIES = [
    ('travel','Travel'),('food','Food'),('cafe','Cafe'),('shopping','Shopping'),
    ('culture','Culture'),('leisure','Leisure'),('stay','Stay'),('local-guide','Local Guide')
]
GUIDES = [
    ('Travel Basics','travel'),('Transport','transport'),('Money','money'),('Apps & Tips','apps'),
    ('Food & Dining','food'),('Daily Life','daily'),('Language','language'),('Culture','culture')
]
CSS_VERSION = '20261009-2'

REGION_CATS = {name: [(n, f'{slug}-{cat}.html') for cat,n in CATEGORIES] for slug,name in REGIONS}
GLOBAL_CATS = [(n, f'{slug}.html') for slug,n in CATEGORIES]
GUIDE_LINKS = [(n, f'guides.html?category={slug}') for n,slug in GUIDES]

NAV_CSS = r'''
/* Korea Plainly navigation - stable v3 */
.nav-drop{position:relative;display:flex;align-items:center}
.nav-parent{font-size:12px;color:#62635f;display:flex;align-items:center;gap:5px;padding:27px 0;white-space:nowrap;cursor:pointer}
.nav-chevron{font-size:13px;line-height:1;transition:transform .18s ease}
.nav-menu{position:absolute;left:50%;top:100%;z-index:1000;transform:translateX(-50%) translateY(-6px);min-width:190px;padding:9px;background:var(--card);border:1px solid var(--line);box-shadow:0 18px 40px rgba(0,0,0,.12);opacity:0;visibility:hidden;pointer-events:none;transition:opacity .16s ease,transform .16s ease}
.nav-menu a{display:block!important;font-size:12px!important;color:var(--ink)!important;padding:10px 13px!important;white-space:nowrap}
.nav-menu a:hover{background:#eeeae1}
.nav-drop:hover>.nav-menu,.nav-drop:focus-within>.nav-menu,.nav-drop.open>.nav-menu{opacity:1;visibility:visible;pointer-events:auto;transform:translateX(-50%) translateY(0)}
.nav-drop:hover>.nav-parent .nav-chevron,.nav-drop:focus-within>.nav-parent .nav-chevron,.nav-drop.open>.nav-parent .nav-chevron{transform:rotate(180deg)}
.hub-back{display:inline-block;margin-bottom:28px;font-size:13px;color:#666;text-decoration:none}
@media(max-width:650px){
  nav{display:none;position:absolute;left:15px;right:15px;top:68px;background:var(--bg);border:1px solid var(--line);padding:12px;box-shadow:0 18px 35px #0001;z-index:1000}
  nav.show{display:flex;flex-direction:column;gap:0}
  .nav-drop{display:block;width:100%}
  .nav-parent{padding:11px 6px;font-size:13px;justify-content:space-between}
  .nav-menu{position:static;transform:none!important;opacity:1;visibility:visible;pointer-events:auto;display:none;min-width:0;padding:4px 0 8px;border:0;box-shadow:none;background:transparent}
  .nav-drop.open>.nav-menu,.nav-drop:focus-within>.nav-menu{display:block}
  .nav-menu a{padding:8px 12px!important;font-size:12px!important}
}
'''

NAV_JS = r'''<script id="kp-nav-js">
(function(){
  const drops=[...document.querySelectorAll('.nav-drop')];
  const mobile=()=>window.matchMedia('(max-width:650px)').matches;
  drops.forEach(drop=>{
    drop.addEventListener('mouseenter',()=>{ if(!mobile()) drop.classList.add('open'); });
    drop.addEventListener('mouseleave',()=>{ if(!mobile()) drop.classList.remove('open'); });
    const parent=drop.querySelector('.nav-parent');
    if(parent){
      parent.addEventListener('click',function(e){
        if(mobile()){
          if(!drop.classList.contains('open')){
            e.preventDefault();
            drops.forEach(d=>d.classList.remove('open'));
            drop.classList.add('open');
          }
        }
      });
    }
  });
  document.addEventListener('click',e=>{
    if(!e.target.closest('.nav-drop')) drops.forEach(d=>d.classList.remove('open'));
  });
})();
</script>'''

def dropdown(label, href, items):
    parts=[f'<div class="nav-drop"><a class="nav-parent" href="{href}">{label}<span class="nav-chevron">⌄</span></a><div class="nav-menu">']
    parts += [f'<a href="{u}">{html.escape(n)}</a>' for n,u in items]
    parts.append('</div></div>')
    return ''.join(parts)

def nav_html():
    import sys
    sys.path.insert(0, str(Path("scripts").resolve()))
    from kp_nav import nav_inner
    return "<nav>" + nav_inner() + "</nav>"

def _old_nav_html():
    return '<nav>'+dropdown('Guides','guides.html',GUIDE_LINKS)+dropdown('Regions','regions.html',[('Seoul','seoul.html'),('Busan','busan.html'),('Jeju','jeju.html'),('View all regions','regions.html')])+dropdown('Seoul','seoul.html',REGION_CATS['Seoul'])+dropdown('Busan','busan.html',REGION_CATS['Busan'])+dropdown('Jeju','jeju.html',REGION_CATS['Jeju'])+dropdown('More','index.html#more',GLOBAL_CATS)+'</nav>'

def title_from_html(p):
    s=p.read_text(encoding='utf-8',errors='ignore')
    m=re.search(r'<title>(.*?)</title>',s,re.I|re.S)
    t=html.unescape(re.sub(r'\s+',' ',m.group(1))).strip() if m else p.stem.replace('-',' ').title()
    return re.sub(r'\s*\|\s*Korea Plainly\s*$','',t)

def thumb_for(p):
    """Cover photo of an article (falls back to og:image, then the site default)."""
    s=p.read_text(encoding='utf-8',errors='ignore')
    m=re.search(r'<img[^>]+class="cover"[^>]+src="([^"]+)"',s) or re.search(r'<img[^>]+src="([^"]+)"[^>]+class="cover"',s)
    if not m:
        m=re.search(r'property="og:image"\s+content="https://korea-plainly\.com/([^"]+)"',s)
    src=m.group(1) if m else 'og-default.jpg'
    return src if (ROOT/src).exists() else 'og-default.jpg'

def style_version(s):
    s=re.sub(r'href=["\']style\.css(?:\?[^"\']*)?["\']', f'href="style.css?v={CSS_VERSION}"', s)
    return s

def nav_script(s):
    s=re.sub(r'<script id="kp-nav-js">[\s\S]*?</script>', '', s)
    s=s.replace('</body>', NAV_JS+'\n</body>')
    return s

def make_hub(filename, heading, intro, cards, back_href, back_label, prefix=None):
    if prefix:
        cat_links=''.join(f'<a href="{prefix}-{slug}.html">{n}</a>' for slug,n in CATEGORIES)
    else:
        cat_links=''.join(f'<a href="{slug}.html">{n}</a>' for slug,n in CATEGORIES)
    cards_html=''.join(
        f'<a class="hub-card" href="{p.name}"><img class="hub-thumb" src="{html.escape(thumb_for(p))}" alt="" loading="lazy"><span>{html.escape((heading.split(" in ")[0]).upper())}</span><h3>{html.escape(title_from_html(p))}</h3><b>Read guide &rarr;</b></a>'
        for p in cards
    )
    if not cards_html: cards_html='<div class="empty">New guides are coming soon.</div>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{html.escape(intro)}"><link rel="canonical" href="https://korea-plainly.com/{filename}"><title>{html.escape(heading)} | Korea Plainly</title><link rel="stylesheet" href="style.css?v={CSS_VERSION}"><style>
.hub-hero{{padding:42px 0 44px;border-bottom:1px solid #ddd8ce}}.hub-hero h1{{font-size:clamp(42px,7vw,78px);margin:8px 0 18px}}.hub-hero p{{max-width:680px;font-size:18px;line-height:1.7}}.hub-cats{{display:flex;flex-wrap:wrap;gap:10px;margin:28px 0}}.hub-cats a{{padding:10px 15px;border:1px solid #d8d1c5;border-radius:999px;text-decoration:none}}.hub-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:30px 0 80px}}.hub-card{{display:block;padding:0 0 22px;border:1px solid #ddd8ce;background:#fff;text-decoration:none;color:inherit;overflow:hidden}}.hub-card>*:not(img){{margin-left:22px;margin-right:22px}}.hub-thumb{{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;margin-bottom:18px}}.hub-card span{{display:block}}.hub-card span{{font-size:12px;letter-spacing:.12em}}.hub-card h3{{font-size:22px;line-height:1.3}}.hub-card b{{font-size:13px}}.empty{{padding:40px;border:1px dashed #ccc}}.hub-back{{display:inline-block;margin-bottom:28px;font-size:13px;color:#666;text-decoration:none}}@media(max-width:800px){{.hub-grid{{grid-template-columns:1fr}}}}
</style></head><body><header><div class="nav wrap"><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a>{nav_html()}<a class="top-link" href="guides.html">Latest <span>↗</span></a><button class="menu" aria-label="menu">☰</button></div></header><main><section class="hub-hero"><div class="wrap"><a class="hub-back" href="{back_href}">{back_label}</a><p class="kicker"><i></i> KOREA PLAINLY</p><h1>{html.escape(heading)}</h1><p>{html.escape(intro)}</p><div class="hub-cats">{cat_links}</div></div></section><section class="wrap section"><div class="hub-grid">{cards_html}</div></section></main><footer><div class="wrap foot"><div><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a><p>Korea, Made Easy for Everyone.</p></div><div class="foot-links"><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="privacy.html">Privacy</a><a href="contact.html">Contact</a></div></div></footer><script>document.querySelector('.menu').addEventListener('click',()=>document.querySelector('nav').classList.toggle('show'));</script>{NAV_JS}</body></html>'''

# 1. Build every region-category page and every nationwide category hub.
for slug,name in REGIONS:
    for cat_slug,cat_name in CATEGORIES:
        cards=sorted(ROOT.glob(f'{slug}-{cat_slug}-*.html'))
        (ROOT/f'{slug}-{cat_slug}.html').write_text(
            make_hub(f'{slug}-{cat_slug}.html',f'{cat_name} in {name}',f'Explore {name} through {cat_name.lower()} guides and recommendations.',cards,f'{slug}.html',f'← {name}',slug),encoding='utf-8')

for cat_slug,cat_name in CATEGORIES:
    cards=sorted(ROOT.glob(f'*-{cat_slug}-*.html'))
    (ROOT/f'{cat_slug}.html').write_text(
        make_hub(f'{cat_slug}.html',f'{cat_name} in Korea',f'Useful {cat_name.lower()} picks and guides from Seoul, Busan, Jeju and beyond.',cards,'index.html','← Home'),encoding='utf-8')

# 2. Repair region hub pages with region-only category links and a real back link.
for slug,name in REGIONS:
    p=ROOT/f'{slug}.html'
    if not p.exists():
        continue
    s=p.read_text(encoding='utf-8',errors='ignore')
    s=re.sub(r'<div class="hub-cats"[^>]*>.*?</div>', '<div class="hub-cats" id="categories">'+''.join(f'<a href="{slug}-{c}.html">{n}</a>' for c,n in CATEGORIES)+'</div>', s, flags=re.S)
    if 'class="hub-back"' not in s:
        s=s.replace('<div class="wrap"><p class="kicker">',f'<div class="wrap"><a class="hub-back" href="regions.html">← All regions</a><p class="kicker">',1)
    s=style_version(s)
    s=nav_script(s)
    s=re.sub(r'<nav>.*?</nav>',nav_html(),s,count=1,flags=re.S)
    p.write_text(s,encoding='utf-8')

# 3. Rebuild Regions landing page correctly (the old patch accidentally wrote literal {nav_html()}).
def _region_cards():
    import json, sys
    sys.path.insert(0, str(Path("scripts").resolve()))
    from kp_nav import regions as _regions
    intros_path = ROOT / "content" / "region_intros.json"
    intros = json.loads(intros_path.read_text(encoding="utf-8")) if intros_path.exists() else {}
    pub_path = ROOT / "content" / "published.json"
    published = [x for x in json.loads(pub_path.read_text(encoding="utf-8")) if isinstance(x, dict)] if pub_path.exists() else []
    out = []
    for slug, name in _regions():
        # cover of the region's best "showcase" article: travel first, then culture, ...
        order = ["Travel", "Culture", "Local Guide", "Leisure", "Food", "Cafe", "Shopping", "Stay"]
        arts = [x for x in published if x.get("region") == name and (ROOT / f"{x.get('slug')}.html").exists()]
        arts.sort(key=lambda x: order.index(x.get("category")) if x.get("category") in order else 99)
        img = thumb_for(ROOT / f"{arts[0]['slug']}.html") if arts else ""
        intro = intros.get(slug, "")
        short = intro.split(". ")[0].rstrip(".") + "." if intro else ""
        pic = f'<img src="{html.escape(img)}" alt="" loading="lazy">' if img and img != "og-default.jpg" else ""
        out.append(f'<div class="regions-card"><a href="{slug}.html">{pic}'
                   f'<h2>{html.escape(name)}</h2><p>{html.escape(short)}</p></a></div>')
    return "".join(out)

REGION_CARDS = _region_cards()

regions = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Explore Korea by region with practical travel, food, cafe, shopping, culture, leisure and stay guides."><link rel="canonical" href="https://korea-plainly.com/regions.html"><title>Regions of Korea | Korea Plainly</title><link rel="stylesheet" href="style.css?v={CSS_VERSION}"><style>.regions-hero{{padding:48px 0 30px}}.regions-hero h1{{font-size:clamp(46px,8vw,82px);line-height:1;margin:8px 0 18px}}.regions-hero p{{max-width:700px;font-size:18px;line-height:1.7}}.back-btn{{display:inline-block;margin-bottom:24px;color:#666;font-size:14px}}.regions-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;padding:25px 0 90px}}.regions-card img{{display:block;width:calc(100% + 56px);margin:-28px -28px 18px;aspect-ratio:16/9;object-fit:cover}}.regions-card{{background:var(--card);border:1px solid var(--line);padding:28px;overflow:hidden;min-height:190px}}.regions-card a{{display:block;height:100%}}.regions-card h2{{font-size:30px;margin:0 0 10px}}.regions-card p{{line-height:1.65;color:var(--muted)}}@media(max-width:800px){{.regions-grid{{grid-template-columns:1fr}}}}</style></head><body><header><div class="nav wrap"><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a>{nav_html()}<a class="top-link" href="guides.html">Latest <span>↗</span></a><button class="menu" aria-label="menu">☰</button></div></header><main><section class="wrap regions-hero"><a class="back-btn" href="index.html">← Home</a><p class="kicker"><i></i> EXPLORE KOREA</p><h1>Regions</h1><p>Discover Korea through regional travel, food, cafes, shopping, culture, leisure and stay recommendations.</p></section><section class="wrap regions-grid">{REGION_CARDS}</section></main><footer><div class="wrap foot"><div><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a><p>Korea, Made Easy for Everyone.</p></div><div class="foot-links"><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="privacy.html">Privacy</a><a href="contact.html">Contact</a></div></div></footer><script>document.querySelector('.menu').addEventListener('click',()=>document.querySelector('nav').classList.toggle('show'));</script>{NAV_JS}</body></html>'''
(ROOT/'regions.html').write_text(regions,encoding='utf-8')

# 4. Normalize navigation + cache-bust CSS on every root HTML page.
for p in ROOT.glob('*.html'):
    if p.name=='regions.html':
        continue
    s=p.read_text(encoding='utf-8',errors='ignore')
    if '<nav>' in s:
        s=re.sub(r'<nav>.*?</nav>',nav_html(),s,count=1,flags=re.S)
    s=style_version(s)
    if '</body>' in s:
        s=nav_script(s)
    p.write_text(s,encoding='utf-8')

# 5. Homepage: remove dead # links and add region-first section.
idx=ROOT/'index.html'
if idx.exists():
    s=idx.read_text(encoding='utf-8',errors='ignore')
    s=s.replace('<a href="#seoul"><strong>01</strong> Seoul</a><a href="#food"><strong>02</strong> Food</a><a href="#culture"><strong>03</strong> Culture</a><a href="#life"><strong>04</strong> Daily Life</a><a href="guides.html"><strong>05</strong> Apps & Tips</a>',
                '<a href="seoul.html"><strong>01</strong> Seoul</a><a href="food.html"><strong>02</strong> Food</a><a href="culture.html"><strong>03</strong> Culture</a><a href="guides.html?category=daily"><strong>04</strong> Daily Life</a><a href="guides.html?category=apps"><strong>05</strong> Apps & Tips</a>')
    s=s.replace('<a href="#">Read guide <span>→</span></a></div>\n</article>\n</div>\n</section>', '<a href="korean-convenience-store-guide.html">Read guide <span>→</span></a></div>\n</article>\n</div>\n</section>',1)
    s=s.replace('<a class="latest-card" href="#"><span class="index">01</span><div class="mini-icon naver">N</div><div><small>APPS & TIPS</small><h3>Can Foreigners Use Naver Map in Korea?</h3><p>A practical beginner guide.</p></div><b>↗</b></a>', '<a class="latest-card" href="naver-map-vs-google-maps-korea.html"><span class="index">01</span><div class="mini-icon naver">N</div><div><small>APPS & TIPS</small><h3>Naver Map vs Google Maps in Korea</h3><p>How to use both map apps without the guesswork.</p></div><b>↗</b></a>')
    s=s.replace('<a class="latest-card" href="#"><span class="index">02</span><div class="mini-icon tmoney">T</div><div><small>TRANSPORT</small><h3>How to Use T-money in Seoul</h3><p>Everything you need for public transport.</p></div><b>↗</b></a>', '<a class="latest-card" href="t-money-korea-guide.html"><span class="index">02</span><div class="mini-icon tmoney">T</div><div><small>TRANSPORT</small><h3>How T-money Works in Korea</h3><p>Everything you need for public transport.</p></div><b>↗</b></a>')
    s=s.replace('<a class="latest-card" href="#"><span class="index">03</span><div class="mini-icon apps">K</div><div><small>TRAVEL</small><h3>5 Korean Apps to Install Before Your Trip</h3><p>Save these before you land.</p></div><b>↗</b></a>', '<a class="latest-card" href="kakao-t-taxi-korea.html"><span class="index">03</span><div class="mini-icon apps">K</div><div><small>TRANSPORT · APPS</small><h3>Kakao T: A Simple Taxi Guide for Visitors</h3><p>A practical way to find taxis in Korea.</p></div><b>↗</b></a>')
    s=s.replace('<a class="latest-card" href="#"><span class="index">04</span><div class="mini-icon food">F</div><div><small>FOOD & CULTURE</small><h3>Korean Restaurant Etiquette for Foreigners</h3><p>Simple rules that help you fit right in.</p></div><b>↗</b></a>', '<a class="latest-card" href="korean-dining-etiquette.html"><span class="index">04</span><div class="mini-icon food">F</div><div><small>FOOD & CULTURE</small><h3>Korean Dining Etiquette: 9 Simple Things to Know</h3><p>Easy habits that make dining smoother.</p></div><b>↗</b></a>')
    if 'id="regional-hubs"' not in s:
        section='''<section class="wrap section" id="regional-hubs"><div class="heading"><div><p class="kicker"><i></i> EXPLORE BY REGION</p><h2>Find Korea<br><em>by place.</em></h2></div><a class="view-all" href="regions.html">View all regions →</a></div><div class="latest-grid"><a class="latest-card" href="seoul.html"><span class="index">01</span><div><small>REGION</small><h3>Seoul</h3><p>Travel, food, cafes, shopping, culture, leisure, stay and local guides.</p></div><b>↗</b></a><a class="latest-card" href="busan.html"><span class="index">02</span><div><small>REGION</small><h3>Busan</h3><p>Coastal-city recommendations and local picks.</p></div><b>↗</b></a><a class="latest-card" href="jeju.html"><span class="index">03</span><div><small>REGION</small><h3>Jeju</h3><p>Island travel, food, cafes and local experiences.</p></div><b>↗</b></a></div></section>'''
        s=s.replace('<section class="quote">',section+'\n<section class="quote">',1)
    s=style_version(s)
    nav=re.sub(r'<nav>.*?</nav>',nav_html(),s,count=1,flags=re.S)
    s=nav
    s=nav_script(s)
    idx.write_text(s,encoding='utf-8')

# 6. Guides filter: make dropdown category links actually filter, including direct URL entry.
g=ROOT/'guides.html'
if g.exists():
    s=g.read_text(encoding='utf-8',errors='ignore')
    for name,slug in GUIDES:
        s=s.replace(f'href="guides.html#guide-categories">{html.escape(name)}</a>', f'href="guides.html?category={slug}">{html.escape(name)}</a>')
    old='''(function(){\n  const buttons=document.querySelectorAll('.guide-filter');\n  const cards=document.querySelectorAll('.guide-card');\n  buttons.forEach(button=>button.addEventListener('click',()=>{\n    const filter=button.dataset.filter;\n    buttons.forEach(b=>b.classList.remove('active'));\n    button.classList.add('active');\n    cards.forEach(card=>card.classList.toggle('is-hidden',filter!=='all' && card.dataset.guideCategory!==filter));\n  }));\n})();'''
    new='''(function(){\n  const buttons=[...document.querySelectorAll('.guide-filter')];\n  const cards=[...document.querySelectorAll('.guide-card')];\n  function apply(filter){\n    filter=filter||'all';\n    buttons.forEach(b=>b.classList.toggle('active',b.dataset.filter===filter));\n    cards.forEach(card=>card.classList.toggle('is-hidden',filter!=='all' && card.dataset.guideCategory!==filter));\n  }\n  buttons.forEach(button=>button.addEventListener('click',()=>{\n    const filter=button.dataset.filter;\n    history.replaceState(null,'','guides.html'+(filter==='all'?'':'?category='+encodeURIComponent(filter)));\n    apply(filter);\n  }));\n  const filter=new URLSearchParams(location.search).get('category');\n  apply(buttons.some(b=>b.dataset.filter===filter)?filter:'all');\n})();'''
    s=s.replace(old,new)
    s=style_version(s)
    s=nav_script(s)
    s=re.sub(r'<nav>.*?</nav>',nav_html(),s,count=1,flags=re.S)
    g.write_text(s,encoding='utf-8')

print('Korea Plainly site-wide integrity repair complete.')

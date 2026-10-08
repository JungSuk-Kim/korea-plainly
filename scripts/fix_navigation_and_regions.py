from pathlib import Path
import re, html

ROOT = Path('.')
REGIONS = [('seoul','Seoul'),('busan','Busan'),('jeju','Jeju')]
CATEGORIES = [('travel','Travel'),('food','Food'),('cafe','Cafe'),('shopping','Shopping'),('culture','Culture'),('leisure','Leisure'),('stay','Stay'),('local-guide','Local Guide')]
GUIDES = [('Travel Basics','guides.html#guide-categories'),('Transport','guides.html#guide-categories'),('Money','guides.html#guide-categories'),('Apps & Tips','guides.html#guide-categories'),('Food & Dining','guides.html#guide-categories'),('Daily Life','guides.html#guide-categories'),('Language','guides.html#guide-categories'),('Culture','guides.html#guide-categories')]

REGION_CATS = {
    'Seoul': [(n, f'seoul-{s}.html') for s,n in CATEGORIES],
    'Busan': [(n, f'busan-{s}.html') for s,n in CATEGORIES],
    'Jeju': [(n, f'jeju-{s}.html') for s,n in CATEGORIES],
}
GLOBAL_CATS = [(n, f'{s}.html') for s,n in CATEGORIES]

NAV_CSS = r'''
/* Korea Plainly dropdown navigation v2 */
.nav-drop{position:relative;display:flex;align-items:center}
.nav-parent{font-size:12px;color:#62635f;display:flex;align-items:center;gap:5px;padding:27px 0;white-space:nowrap}
.nav-chevron{font-size:13px;line-height:1;transition:transform .18s ease}
.nav-menu{position:absolute;left:50%;top:100%;z-index:1000;transform:translateX(-50%) translateY(-6px);min-width:190px;padding:9px;background:var(--card);border:1px solid var(--line);box-shadow:0 18px 40px rgba(0,0,0,.12);opacity:0;visibility:hidden;pointer-events:none;transition:opacity .16s ease,transform .16s ease}
.nav-menu a{display:block!important;font-size:12px!important;color:var(--ink)!important;padding:10px 13px!important;white-space:nowrap}
.nav-menu a:hover{background:#eeeae1}
.nav-drop:hover>.nav-menu,.nav-drop:focus-within>.nav-menu{opacity:1;visibility:visible;pointer-events:auto;transform:translateX(-50%) translateY(0)}
.nav-drop:hover>.nav-parent .nav-chevron,.nav-drop:focus-within>.nav-parent .nav-chevron{transform:rotate(180deg)}
.hub-back{display:inline-block;margin-bottom:28px;font-size:13px;color:#666;text-decoration:none}
@media(max-width:650px){
  nav{display:none;position:absolute;left:15px;right:15px;top:68px;background:var(--bg);border:1px solid var(--line);padding:12px;box-shadow:0 18px 35px #0001;z-index:1000}
  nav.show{display:flex;flex-direction:column;gap:0}
  .nav-drop{display:block;width:100%}
  .nav-parent{padding:10px 6px;font-size:13px;justify-content:space-between}
  .nav-menu{position:static;transform:none!important;opacity:1;visibility:visible;pointer-events:auto;display:none;min-width:0;padding:4px 0 8px;border:0;box-shadow:none;background:transparent}
  .nav-drop:focus-within>.nav-menu{display:block}
  .nav-menu a{padding:8px 12px!important;font-size:12px!important}
}
'''

def dropdown(label, href, items):
    parts=[f'<div class="nav-drop"><a class="nav-parent" href="{href}">{label}<span class="nav-chevron">⌄</span></a><div class="nav-menu">']
    parts += [f'<a href="{u}">{html.escape(n)}</a>' for n,u in items]
    parts.append('</div></div>')
    return ''.join(parts)

def nav_html():
    return '<nav>'+dropdown('Guides','guides.html',GUIDES)+dropdown('Regions','regions.html',[('Seoul','seoul.html'),('Busan','busan.html'),('Jeju','jeju.html'),('View all regions','regions.html')])+dropdown('Seoul','seoul.html',REGION_CATS['Seoul'])+dropdown('Busan','busan.html',REGION_CATS['Busan'])+dropdown('Jeju','jeju.html',REGION_CATS['Jeju'])+dropdown('More','travel.html',GLOBAL_CATS)+'</nav>'

HUB_CSS = r'''
.hub-hero{padding:42px 0 44px;border-bottom:1px solid #ddd8ce}
.hub-hero h1{font-size:clamp(42px,7vw,78px);margin:8px 0 18px}
.hub-hero p{max-width:680px;font-size:18px;line-height:1.7}
.hub-cats{display:flex;flex-wrap:wrap;gap:10px;margin:28px 0}
.hub-cats a{padding:10px 15px;border:1px solid #d8d1c5;border-radius:999px;text-decoration:none}
.hub-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:30px 0 80px}
.hub-card{display:block;padding:24px;border:1px solid #ddd8ce;text-decoration:none;color:inherit;min-height:170px}
.hub-card span{font-size:12px;letter-spacing:.12em}.hub-card h3{font-size:22px;line-height:1.3}.hub-card b{font-size:13px}.empty{padding:40px;border:1px dashed #ccc}
.hub-back{display:inline-block;margin-bottom:28px;font-size:13px;color:#666;text-decoration:none}
@media(max-width:800px){.hub-grid{grid-template-columns:1fr}}
'''

def title_from_html(p):
    s=p.read_text(encoding='utf-8',errors='ignore')
    m=re.search(r'<title>(.*?)</title>',s,re.I|re.S)
    return html.unescape(re.sub(r'\s+',' ',m.group(1))).strip() if m else p.stem.replace('-',' ').title()

def make_hub(filename, heading, intro, cards, prefix=None, back='regions.html'):
    if prefix:
        cat_links=''.join(f'<a href="{prefix}-{s}.html">{n}</a>' for s,n in CATEGORIES)
    else:
        cat_links=''.join(f'<a href="{s}.html">{n}</a>' for s,n in CATEGORIES)
    cards_html=''.join(f'<a class="hub-card" href="{p.name}"><span>{html.escape((heading.split(" in ")[1] if " in " in heading else heading).upper())}</span><h3>{html.escape(title_from_html(p))}</h3><b>Read guide &rarr;</b></a>' for p in cards)
    if not cards_html: cards_html='<div class="empty">New guides are coming soon.</div>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{html.escape(intro)}"><link rel="canonical" href="https://korea-plainly.com/{filename}"><title>{html.escape(heading)} | Korea Plainly</title><link rel="stylesheet" href="style.css"><style>{HUB_CSS}</style></head><body><header><div class="nav wrap"><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a>{nav_html()}<a class="top-link" href="guides.html">Latest <span>↗</span></a><button class="menu" aria-label="menu">☰</button></div></header><main><section class="hub-hero"><div class="wrap"><a class="hub-back" href="{back}">← All regions</a><p class="kicker"><i></i> KOREA PLAINLY</p><h1>{html.escape(heading)}</h1><p>{html.escape(intro)}</p><div class="hub-cats">{cat_links}</div></div></section><section class="wrap section"><div class="hub-grid">{cards_html}</div></section></main><footer><div class="wrap foot"><div><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a><p>Korea, Made Easy for Everyone.</p></div><div class="foot-links"><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="privacy.html">Privacy</a><a href="contact.html">Contact</a></div></div></footer><script>document.querySelector('.menu').addEventListener('click',()=>document.querySelector('nav').classList.toggle('show'));</script></body></html>'''

# 1) Build region-specific category pages.
for slug,name in REGIONS:
    for cat_slug,cat_name in CATEGORIES:
        cards=sorted(ROOT.glob(f'{slug}-{cat_slug}-*.html'))
        (ROOT/f'{slug}-{cat_slug}.html').write_text(make_hub(f'{slug}-{cat_slug}.html',f'{cat_name} in {name}',f'Explore {name} through {cat_name.lower()} guides and recommendations.',cards,slug),encoding='utf-8')

# 2) Fix category links on region hubs.
for slug,name in REGIONS:
    p=ROOT/f'{slug}.html'
    if not p.exists(): continue
    s=p.read_text(encoding='utf-8',errors='ignore')
    s=re.sub(r'<div class="hub-cats" id="categories">.*?</div>', '<div class="hub-cats" id="categories">'+''.join(f'<a href="{slug}-{c}.html">{n}</a>' for c,n in CATEGORIES)+'</div>', s, flags=re.S)
    if 'class="hub-back"' not in s:
        s=s.replace('<div class="wrap"><p class="kicker">','<div class="wrap"><a class="hub-back" href="regions.html">← All regions</a><p class="kicker">',1)
    p.write_text(s,encoding='utf-8')

# 3) Install reliable dropdown nav into every root HTML page that has a nav.
for p in ROOT.glob('*.html'):
    s=p.read_text(encoding='utf-8',errors='ignore')
    if '<nav>' in s:
        s=re.sub(r'<nav>.*?</nav>',nav_html(),s,count=1,flags=re.S)
        p.write_text(s,encoding='utf-8')

# 4) Central CSS fixes the original failure where index.html had no inline dropdown CSS.
css=ROOT/'style.css'
if css.exists():
    s=css.read_text(encoding='utf-8',errors='ignore')
    if 'Korea Plainly dropdown navigation v2' not in s:
        s += '\n'+NAV_CSS
    css.write_text(s,encoding='utf-8')

# 5) Rebuild Regions landing page with consistent navigation and a real Back button.
regions='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Explore Korea by region with practical travel, food, cafe, shopping, culture, leisure and stay guides."><link rel="canonical" href="https://korea-plainly.com/regions.html"><title>Regions of Korea | Korea Plainly</title><link rel="stylesheet" href="style.css"><style>.regions-hero{padding:48px 0 30px}.regions-hero h1{font-size:clamp(46px,8vw,82px);line-height:1;margin:8px 0 18px}.regions-hero p{max-width:700px;font-size:18px;line-height:1.7}.back-btn{display:inline-block;margin-bottom:24px;color:#666;font-size:14px}.regions-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;padding:25px 0 90px}.regions-card{background:var(--card);border:1px solid var(--line);padding:28px;min-height:190px}.regions-card a{display:block;height:100%}.regions-card h2{font-size:30px;margin:0 0 10px}.regions-card p{line-height:1.65;color:var(--muted)}@media(max-width:800px){.regions-grid{grid-template-columns:1fr}}</style></head><body><header><div class="nav wrap"><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a>{nav_html()}<a class="top-link" href="guides.html">Latest <span>↗</span></a><button class="menu" aria-label="menu">☰</button></div></header><main><section class="wrap regions-hero"><a class="back-btn" href="javascript:history.back()">← Back</a><p class="kicker"><i></i> EXPLORE KOREA</p><h1>Regions</h1><p>Discover Korea through regional travel, food, cafes, shopping, culture, leisure and stay recommendations.</p></section><section class="wrap regions-grid"><div class="regions-card"><a href="seoul.html"><h2>Seoul</h2><p>Korea's capital and the main gateway for first-time visitors.</p></a></div><div class="regions-card"><a href="busan.html"><h2>Busan</h2><p>Coastal city guides for food, beaches, culture and more.</p></a></div><div class="regions-card"><a href="jeju.html"><h2>Jeju</h2><p>Island travel, food, cafes and local experiences.</p></a></div></section></main><footer><div class="wrap foot"><div><a class="brand" href="index.html"><span class="taegeuk"></span><span>Korea <b>Plainly</b></span></a><p>Korea, Made Easy for Everyone.</p></div><div class="foot-links"><a href="guides.html">Guides</a><a href="regions.html">Regions</a><a href="privacy.html">Privacy</a><a href="contact.html">Contact</a></div></div></footer><script>document.querySelector('.menu').addEventListener('click',()=>document.querySelector('nav').classList.toggle('show'));</script></body></html>'''
(ROOT/'regions.html').write_text(regions,encoding='utf-8')

print('Navigation + regional category structure fixed.')

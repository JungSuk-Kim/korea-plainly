
from pathlib import Path
import re

ROOT = Path(".")
GUIDE = [
    ("Travel Basics","guides.html#guide-categories"),("Transport","guides.html#guide-categories"),
    ("Money","guides.html#guide-categories"),("Apps & Tips","guides.html#guide-categories"),
    ("Food & Dining","guides.html#guide-categories"),("Daily Life","guides.html#guide-categories"),
    ("Language","guides.html#guide-categories"),("Culture","guides.html#guide-categories")
]
REGIONS = [("Seoul","seoul.html"),("Busan","busan.html"),("Jeju","jeju.html"),("View all regions","regions.html")]
REGION_CATS = [
    ("Travel","travel.html"),("Food","food.html"),("Cafe","cafe.html"),("Shopping","shopping.html"),
    ("Culture","culture.html"),("Leisure","leisure.html"),("Stay","stay.html"),("Local Guide","local-guide.html")
]

def dropdown(label, href, items):
    out = [f'<div class="nav-drop"><a class="nav-parent" href="{href}">{label}<span class="nav-chevron">⌄</span></a><div class="nav-menu">']
    for text, url in items:
        out.append(f'<a href="{url}">{text}</a>')
    out.append('</div></div>')
    return ''.join(out)

def nav_html():
    return (
        dropdown("Guides","guides.html",GUIDE) +
        dropdown("Regions","regions.html",REGIONS) +
        dropdown("Seoul","seoul.html",REGION_CATS) +
        dropdown("Busan","busan.html",REGION_CATS) +
        dropdown("Jeju","jeju.html",REGION_CATS) +
        dropdown("More","#",REGION_CATS)
    )

NAV_CSS = """
.nav-drop{position:relative;display:flex;align-items:center}
.nav-parent{font-size:12px;color:#62635f;display:flex;align-items:center;gap:5px;padding:27px 0}
.nav-chevron{font-size:13px;line-height:1;transition:transform .18s ease}
.nav-menu{position:absolute;left:50%;top:100%;transform:translateX(-50%) translateY(-6px);min-width:190px;padding:9px;background:var(--card);border:1px solid var(--line);box-shadow:0 18px 40px rgba(0,0,0,.12);opacity:0;visibility:hidden;pointer-events:none;transition:opacity .16s ease,transform .16s ease}
.nav-menu a{display:block;font-size:12px;color:var(--ink);padding:10px 13px;white-space:nowrap}
.nav-menu a:hover{background:#eeeae1}
.nav-drop:hover .nav-menu,.nav-drop:focus-within .nav-menu{opacity:1;visibility:visible;pointer-events:auto;transform:translateX(-50%) translateY(0)}
.nav-drop:hover .nav-chevron,.nav-drop:focus-within .nav-chevron{transform:rotate(180deg)}
"""

for p in ROOT.glob("*.html"):
    s = p.read_text(encoding="utf-8", errors="ignore")
    if "<nav>" not in s:
        continue
    s = re.sub(r"<nav>.*?</nav>", f"<nav>{nav_html()}</nav>", s, count=1, flags=re.S)
    if "Korea Plainly dropdown navigation" not in s:
        s = s.replace("</style>\n</head>", "</style>\n<style>/* Korea Plainly dropdown navigation */\n"+NAV_CSS+"</style>\n</head>", 1)
    p.write_text(s, encoding="utf-8")

style = ROOT/"style.css"
if style.exists():
    s = style.read_text(encoding="utf-8", errors="ignore")
    mobile = """
@media(max-width:650px){
  nav{display:none;position:absolute;left:15px;right:15px;top:68px;background:var(--bg);border:1px solid var(--line);padding:12px;box-shadow:0 18px 35px #0001}
  nav.show{display:flex;flex-direction:column;gap:0}
  .nav-drop{display:block;width:100%}
  .nav-parent{padding:10px 6px;font-size:13px;justify-content:space-between}
  .nav-menu{position:static;transform:none!important;opacity:1;visibility:visible;pointer-events:auto;display:none;min-width:0;padding:4px 0 8px;border:0;box-shadow:none;background:transparent}
  .nav-drop:hover .nav-menu,.nav-drop:focus-within .nav-menu{display:block}
  .nav-menu a{padding:8px 12px;font-size:12px}
}
"""
    if "Korea Plainly mobile dropdown override" not in s:
        s += "\n/* Korea Plainly mobile dropdown override */\n" + mobile
        style.write_text(s, encoding="utf-8")

print("Dropdown navigation patched across site pages.")

#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
CSS_VERSION="20261009-4"
REGIONS=[("seoul","Seoul"),("busan","Busan"),("jeju","Jeju")]
REGION_CATS=[("travel","Travel"),("food","Food"),("cafe","Cafe"),("shopping","Shopping"),
             ("culture","Culture"),("leisure","Leisure"),("stay","Stay"),("local-guide","Local Guide")]
GUIDES=[("Travel Basics","travel"),("Transport","transport"),("Money","money"),
        ("Apps & Tips","apps"),("Food & Dining","food"),("Daily Life","daily"),
        ("Language","language"),("Culture","culture")]

NAV_CSS=r"""
/* Korea Plainly stable navigation v4 */
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
"""

NAV_JS=r"""<script id="kp-nav-js">
(function(){
  const drops=[...document.querySelectorAll('.nav-drop')];
  const mobile=()=>window.matchMedia('(max-width:650px)').matches;
  drops.forEach(drop=>{
    drop.addEventListener('mouseenter',()=>{if(!mobile())drop.classList.add('open')});
    drop.addEventListener('mouseleave',()=>{if(!mobile())drop.classList.remove('open')});
    const parent=drop.querySelector('.nav-parent');
    if(parent) parent.addEventListener('click',function(e){
      if(mobile() && !drop.classList.contains('open')){
        e.preventDefault(); drops.forEach(d=>d.classList.remove('open')); drop.classList.add('open');
      }
    });
  });
  document.addEventListener('click',e=>{
    if(!e.target.closest('.nav-drop')) drops.forEach(d=>d.classList.remove('open'));
  });
})();
</script>"""

def nav_html():
    def drop(label,links):
        items="".join(f'<a href="{href}">{text}</a>' for text,href in links)
        first=links[0][1] if links else "index.html"
        return f'<div class="nav-drop"><a class="nav-parent" href="{first}">{label}<span class="nav-chevron">⌄</span></a><div class="nav-menu">{items}</div></div>'
    guides=[(n,f"guides.html?category={slug}") for n,slug in GUIDES]
    regions=[("Seoul","seoul.html"),("Busan","busan.html"),("Jeju","jeju.html"),("View all regions","regions.html")]
    more=[(n,f"{slug}.html") for slug,n in REGION_CATS]
    out=['<a href="index.html">Home</a>',drop("Guides",guides),drop("Regions",regions)]
    for slug,name in REGIONS:
        out.append(drop(name,[(n,f"{slug}-{cat}.html") for cat,n in REGION_CATS]))
    out.append(drop("More",more))
    return "\n".join(out)

def patch_css():
    p=ROOT/"style.css"
    if not p.exists(): return
    s=p.read_text(encoding="utf-8",errors="ignore")
    for name in ["seoul","street","food","store"]:
        s=s.replace(f'images/{name}.jpg',f'{name}.jpg')
    # remove previously appended navigation blocks
    s=re.sub(r'\n/\* Korea Plainly (?:navigation - stable v3|stable navigation v3|stable navigation v4) \*/.*?(?=\n/\*|\Z)','',s,flags=re.S)
    s += "\n"+NAV_CSS+"\n"
    p.write_text(s,encoding="utf-8")

def patch_nav(s):
    m=re.search(r'(<nav\b[^>]*>)(.*?)(</nav>)',s,re.S|re.I)
    if m:
        s=s[:m.start()]+m.group(1)+"\n"+nav_html()+"\n"+m.group(3)+s[m.end():]
    s=re.sub(r'\s*<script id="kp-nav-js">.*?</script>\s*','\n',s,flags=re.S)
    if "</body>" in s: s=s.replace("</body>",NAV_JS+"\n</body>",1)
    return s

def patch_guides(s):
    # normalize the actual filter attributes used by guides.html
    s=re.sub(r'data-guide-category="([^"]+)"\s+data-guide-category="\1"',r'data-guide-category="\1"',s)
    s=s.replace('data-filter="','data-guide-filter="')
    s=re.sub(r'\s*<script[^>]*id="kp-guide-filter"[^>]*>.*?</script>\s*','\n',s,flags=re.S)
    script=r"""<script id="kp-guide-filter">
(function(){
 const cards=[...document.querySelectorAll('[data-guide-category]')];
 const buttons=[...document.querySelectorAll('[data-guide-filter]')];
 const valid=new Set(['travel','transport','money','apps','food','daily','language','culture']);
 const param=new URLSearchParams(location.search).get('category');
 let current=valid.has(param)?param:'all';
 function apply(cat,push){
  current=cat;
  cards.forEach(c=>c.style.display=(cat==='all'||c.dataset.guideCategory===cat)?'':'none');
  buttons.forEach(b=>b.classList.toggle('active',b.dataset.guideFilter===cat));
  if(push){
   const u=new URL(location.href);
   if(cat==='all')u.searchParams.delete('category');else u.searchParams.set('category',cat);
   history.replaceState({},'',u);
  }
 }
 buttons.forEach(b=>b.addEventListener('click',()=>apply(b.dataset.guideFilter,true)));
 apply(current,false);
})();
</script>"""
    return s.replace("</body>",script+"\n</body>",1) if "</body>" in s else s+script

def patch_index(s):
    replacements={
      'href="index.html#more"':'href="travel.html"',
      'href="#seoul"':'href="seoul.html"',
      'href="#food"':'href="food.html"',
      'href="#culture"':'href="culture.html"',
      'href="#life"':'href="guides.html?category=daily"',
      '<a class="brand" href="#">':'<a class="brand" href="index.html">',
      '<a href="#" class="brand">':'<a href="index.html" class="brand">'
    }
    for a,b in replacements.items(): s=s.replace(a,b)
    # Homepage social destinations: use the internal landing page until channel URLs are supplied.
    s=re.sub(r'<a href="#"(\s*>\s*<span>(?:YT|IG|TK)</span>)',r'<a href="social.html"\1',s)
    return s

def ensure_canonical(s,filename):
    if re.search(r'<link\s+[^>]*rel=["\']canonical["\']',s,re.I): return s
    url="https://korea-plainly.com/" + ("" if filename=="index.html" else filename)
    tag=f'<link rel="canonical" href="{url}">\n'
    return re.sub(r'</title>',lambda m:m.group(0)+"\n"+tag,s,count=1,flags=re.I)

def patch_file(p):
    s=p.read_text(encoding="utf-8",errors="ignore")
    s=re.sub(r'style\.css(?:\?v=[^"\']*)?',f'style.css?v={CSS_VERSION}',s)
    s=patch_nav(s)
    if p.name=="index.html": s=patch_index(s)
    if p.name=="guides.html": s=patch_guides(s)
    s=s.replace('href="index.html#more"','href="travel.html"')
    s=ensure_canonical(s,p.name)
    p.write_text(s,encoding="utf-8")

def main():
    patch_css()
    for p in ROOT.glob("*.html"): patch_file(p)
    (ROOT/"SITE_INTEGRITY_VERSION.txt").write_text(CSS_VERSION+"\n",encoding="utf-8")
    print("Site integrity repair v4 complete.")
if __name__=="__main__": main()

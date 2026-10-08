#!/usr/bin/env python3
from pathlib import Path
import re,sys
ROOT=Path(__file__).resolve().parents[1]
html=list(ROOT.glob("*.html"))
errors=[]
for p in html:
    s=p.read_text(encoding="utf-8",errors="ignore")
    for href in re.findall(r'href=["\']([^"\']+)["\']',s,re.I):
        if href.startswith(("http://","https://","mailto:","tel:","#","javascript:")): continue
        target=href.split("#",1)[0].split("?",1)[0]
        if target and not (ROOT/target).exists(): errors.append(f"{p.name}: missing {target}")
    if 'href="#"' in s: errors.append(f"{p.name}: placeholder href=#")
    if re.search(r'images/(seoul|street|food|store)\.jpg',s): errors.append(f"{p.name}: legacy images/ path")
    if p.name=="guides.html":
        if 'id="kp-guide-filter"' not in s: errors.append("guides.html: filter script missing")
        if re.search(r'data-guide-category="[^"]+"\s+data-guide-category=',s): errors.append("guides.html: duplicate category attribute")
    if p.name!="privacy.html" and 'rel="canonical"' not in s: errors.append(f"{p.name}: canonical missing")
    if '<nav' in s and 'class="nav-drop"' not in s: errors.append(f"{p.name}: dropdown nav missing")
css=(ROOT/"style.css").read_text(encoding="utf-8",errors="ignore") if (ROOT/"style.css").exists() else ""
for name in ["seoul","street","food","store"]:
    if f'images/{name}.jpg' in css: errors.append(f"style.css: legacy images/{name}.jpg")
if errors:
    print("SITE AUDIT FAILED")
    for e in errors: print(" - "+e)
    sys.exit(1)
print(f"SITE AUDIT PASSED: {len(html)} HTML files checked.")

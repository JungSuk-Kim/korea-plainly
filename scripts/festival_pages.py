#!/usr/bin/env python3
"""Festival listings from content/festivals.json (fetched weekly by scripts/fetch_festivals.py). Idempotent.

  * korea-festivals.html: festivals on now, then upcoming ones by month (managed block <!-- kp-festivals -->).
  * Region hubs (seoul.html, busan.html, ...): "Festivals coming up" with the next few in that region
    (managed block <!-- kp-region-festivals -->, before Related guides).
Listings are filtered by today's date (Korea time) on every run, so finished festivals drop off.
"""
import html
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "content" / "festivals.json"
START, END = "<!-- kp-festivals -->", "<!-- /kp-festivals -->"
RSTART, REND = "<!-- kp-region-festivals -->", "<!-- /kp-region-festivals -->"
REGIONS = {  # hub slug: words in the address (English or Korean)
    "seoul": ["Seoul", "서울"], "busan": ["Busan", "부산"], "jeju": ["Jeju", "제주"], "gyeongju": ["Gyeongju", "경주"],
    "jeonju": ["Jeonju", "전주"], "gangneung": ["Gangneung", "강릉"], "incheon": ["Incheon", "인천"],
    "sokcho": ["Sokcho", "속초"], "yeosu": ["Yeosu", "여수"], "daegu": ["Daegu", "대구"], "daejeon": ["Daejeon", "대전"],
    "gwangju": [],
}
STYLE = ("<style>.kp-fest{list-style:none;padding:0;margin:14px 0 26px}.kp-fest li{display:grid;grid-template-columns:110px 1fr;"
         "gap:14px;padding:13px 0;border-bottom:1px solid rgba(20,28,42,.1)}.kp-fest time{font-size:13px;font-weight:700;"
         "color:#c9413a;line-height:1.4}.kp-fest b{display:block;font-size:16px;line-height:1.35;color:#17243c}"
         ".kp-fest small{display:block;font-size:13px;color:#5b6472;margin-top:3px}.kp-fest a{font-size:13px;font-weight:600;color:#c9413a}"
         ".kp-fest-note{font-size:13px;color:#5b6472}@media(max-width:520px){.kp-fest li{grid-template-columns:1fr;gap:4px}}</style>")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def load():
    if not DATA.exists():
        return None
    d = json.loads(DATA.read_text(encoding="utf-8"))
    t = today().isoformat()
    d["festivals"] = [f for f in d.get("festivals", []) if f["end"] >= t and length(f) <= MAX_DAYS]
    return d


MAX_DAYS = 92   # longer "festivals" are season-long performance series, not events to plan a day around
HANGUL = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]")
PROVINCES = [("서울", "Seoul"), ("부산", "Busan"), ("대구", "Daegu"), ("인천", "Incheon"), ("광주광역시", "Gwangju"),
             ("대전", "Daejeon"), ("울산", "Ulsan"), ("세종", "Sejong"), ("경기", "Gyeonggi-do"), ("강원", "Gangwon-do"),
             ("충청북도", "Chungcheongbuk-do"), ("충북", "Chungcheongbuk-do"), ("충청남도", "Chungcheongnam-do"),
             ("충남", "Chungcheongnam-do"), ("전북", "Jeonbuk-do"), ("전라북도", "Jeonbuk-do"), ("전남", "Jeollanam-do"),
             ("전라남도", "Jeollanam-do"), ("경상북도", "Gyeongsangbuk-do"), ("경북", "Gyeongsangbuk-do"),
             ("경상남도", "Gyeongsangnam-do"), ("경남", "Gyeongsangnam-do"), ("제주", "Jeju")]


def length(f):
    return (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days


def names(title):
    """(English name, Korean name or '') from titles like 'Raftman(뗏꾼)'."""
    m = re.search(r"\s*\((?=[^)]*[\uac00-\ud7af])", title)
    if m and m.start() > 0:
        ko = title[m.end():].strip()
        ko = ko[:-1] if ko.endswith(")") and ko.count("(") < ko.count(")") else ko
        return title[:m.start()].strip(), ko.strip()
    return title, ""


def place(addr):
    """An English address; for one written in Korean, its English part (usually the venue) and the province."""
    addr = re.sub(r"\s*\(.*?\)", "", addr or "").strip()
    if not HANGUL.search(addr):
        return addr
    latin = " ".join(w for w in addr.split() if not HANGUL.search(w) and not re.fullmatch(r"[\d,-]+", w))
    prov = next((en for ko, en in PROVINCES if addr.startswith(ko) or ko in addr.split()[0]), "")
    return ", ".join(x for x in (latin, prov) if x)


def nice(s):
    d = date.fromisoformat(s)
    return f"{d.day} {MONTHS[d.month - 1][:3]}"


def item(f):
    when = nice(f["start"]) if f["start"] == f["end"] else f"{nice(f['start'])} – {nice(f['end'])}"
    en, ko = names(f["title"])
    where = html.escape(place(f.get("address", "")))
    q = quote(ko or en)
    ko_html = f' <span lang="ko">{html.escape(ko)}</span>' if ko else ""
    return (f'<li><time datetime="{f["start"]}">{when}</time><div><b>{html.escape(en)}</b>'
            f'<small>{where}{" · " if where and ko else ""}{ko_html}</small>'
            f'<a href="https://map.naver.com/p/search/{q}" target="_blank" rel="noopener">Find it on Naver Map</a></div></li>')


def credit(d):
    upd = date.fromisoformat(d["updated"])
    return (f'<p class="kp-fest-note">Festival dates from the Korea Tourism Organization (TourAPI), updated '
            f'{upd.day} {MONTHS[upd.month - 1]} {upd.year}. Dates can change, so check the official festival page before you go.</p>')


def put(s, start, end, inner, anchor_re):
    nl = "\r\n" if "\r\n" in s else "\n"
    s2 = re.sub(re.escape(start) + r".*?" + re.escape(end) + r"\r?\n?", "", s, flags=re.S)
    if not inner:
        return s2
    m = re.search(anchor_re, s2)
    if not m:
        return s2
    return s2[:m.start()] + start + nl + inner + nl + end + nl + s2[m.start():]


def main_page(d):
    t = today().isoformat()
    if not d or not d["festivals"]:
        return (STYLE + '<p class="kp-fest-note">The festival calendar is being updated. In the meantime, see our '
                '<a href="korea-winter-festivals.html">winter festivals guide</a>.</p>')
    now = [f for f in d["festivals"] if f["start"] <= t]
    later = [f for f in d["festivals"] if f["start"] > t]
    out = [STYLE]
    if now:
        out.append(f'<h2 id="on-now">On now</h2><ul class="kp-fest">{"".join(item(f) for f in now[:40])}</ul>')
    by = {}
    for f in later:
        by.setdefault(f["start"][:7], []).append(f)
    for ym in sorted(by)[:4]:
        y, m = int(ym[:4]), int(ym[5:])
        out.append(f'<h2 id="festivals-{ym}">{MONTHS[m - 1]} {y}</h2><ul class="kp-fest">{"".join(item(f) for f in by[ym][:40])}</ul>')
    out.append(credit(d))
    return "".join(out)


def region_block(d, slug, name):
    words = REGIONS.get(slug, [])
    def match(f):
        a = f.get("address", "")
        if slug == "gwangju":
            # Gwangju city only (its five districts), not the wider Jeonnam-Gwangju area or Gwangju-si in Gyeonggi
            return bool(re.search(r"(Buk|Dong|Seo|Nam|Gwangsan)-gu,\s*(Jeonnam-)?Gwangju|Gwangju Metropolitan|광주광역시|광주\S*\s+(동구|서구|남구|북구|광산구)", a))
        return any(w.lower() in a.lower() for w in words)
    hits = [f for f in (d or {}).get("festivals", []) if match(f)]
    if not hits:
        return ""
    return (STYLE + f'<section class="kp-region-fest"><h2>Festivals coming up in {html.escape(name)}</h2>'
            f'<ul class="kp-fest">{"".join(item(f) for f in hits[:5])}</ul>'
            f'<p class="kp-fest-note"><a href="korea-festivals.html">See all festivals in Korea →</a></p></section>')


def main():
    d = load()
    changed = 0
    page = ROOT / "korea-festivals.html"
    if page.exists():
        s = page.read_bytes().decode("utf-8")
        new = put(s, START, END, main_page(d), r'<div id="kp-festivals-here"></div>')
        if new != s:
            page.write_bytes(new.encode("utf-8")); changed += 1
    names = {r["slug"]: r["name"] for r in json.loads((ROOT / "content" / "region_rotation.json").read_text(encoding="utf-8"))["regions"]}
    for slug, name in names.items():
        p = ROOT / f"{slug}.html"
        if not p.exists():
            continue
        s = p.read_bytes().decode("utf-8")
        new = put(s, RSTART, REND, region_block(d, slug, name), r'<section class="related-guides">')
        if new != s:
            p.write_bytes(new.encode("utf-8")); changed += 1
    print(f"festival_pages: {len((d or {}).get('festivals', []))} festivals, {changed} page(s) updated")


if __name__ == "__main__":
    main()

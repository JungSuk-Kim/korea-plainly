#!/usr/bin/env python3
"""Fill the home page "Latest guides" list with the newest articles, and the
"Find Korea by place" grid with a photo card for every region that has a hub.

Two newest general guides (cards on guides.html) and the two newest regional
articles (content/published.json), newest first. Dates come from
content/page_dates.json, which article_enhance.py keeps up to date.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGION_CSS = ('<style id="kp-home-regions">.kp-regions{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}'
              '.kp-regions a{position:relative;display:block;aspect-ratio:4/3;overflow:hidden;background:#1b2238;color:#fff}'
              '.kp-regions img{width:100%;height:100%;object-fit:cover;transition:transform .4s}'
              '.kp-regions a:hover img{transform:scale(1.04)}.kp-regions .wide{grid-column:span 2;aspect-ratio:auto}.kp-regions .wide img{position:absolute;inset:0}'
              '.kp-regions span{position:absolute;inset:auto 0 0 0;padding:34px 14px 12px;background:linear-gradient(transparent,#000a)}'
              '.kp-regions b{display:block;font-size:18px;letter-spacing:-.02em}.kp-regions small{font-size:11px;opacity:.85}'
              '@media(max-width:900px){.kp-regions{grid-template-columns:repeat(2,1fr)}.kp-regions .wide{aspect-ratio:2/1}}'
              '@media(max-width:420px){.kp-regions b{font-size:15px}.kp-regions small{display:none}}</style>')
PHOTO_ORDER = ["travel", "culture", "leisure", "local-guide", "food", "cafe", "shopping", "stay"]
ICON = {"food": "food", "transport": "tmoney", "apps": "naver"}


def read(p):
    return p.read_bytes().decode("utf-8")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def short(text, limit=80):
    text = clean(text)
    first = re.split(r"(?<=[.!?])\s", text)[0]
    if len(first) <= limit:
        return first
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def guide_cards():
    g = read(ROOT / "guides.html")
    for m in re.finditer(r'<a\s+class="guide-card"\s+href="([^"]+)"\s+data-guide-category="([^"]+)"[^>]*>(.*?)</a>', g, re.S):
        href, cat, inner = m.groups()
        label = clean((re.search(r"<small>(.*?)</small>", inner, re.S) or [None, cat])[1])
        title = clean((re.search(r"<h2>(.*?)</h2>", inner, re.S) or [None, href])[1])
        desc = clean((re.search(r"<p>(.*?)</p>", inner, re.S) or [None, ""])[1])
        yield {"href": href, "cat": cat, "label": label.replace("· NEW", "").strip(" ·"), "title": title, "desc": desc}


def regional_items():
    pub = json.loads(read(ROOT / "content" / "published.json"))
    for p in pub:
        if not (isinstance(p, dict) and p.get("place_name") and (ROOT / f"{p['slug']}.html").exists()):
            continue
        page = read(ROOT / f"{p['slug']}.html")
        desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', page)
        yield {"href": f"{p['slug']}.html", "cat": p.get("category", "").lower(),
               "label": f"{p.get('region', '')} · {p.get('category', '')}".upper(),
               "title": clean(p.get("title", "")), "desc": desc.group(1) if desc else ""}


def card(i, item):
    icon = ICON.get(item["cat"], "apps")
    letter = (item["label"] or "K")[0].upper()
    return (f'<a class="latest-card" href="{html.escape(item["href"])}"><span class="index">{i:02d}</span>'
            f'<div class="mini-icon {icon}">{html.escape(letter)}</div><div><small>{html.escape(item["label"])}</small>'
            f'<h3>{html.escape(item["title"])}</h3><p>{html.escape(short(item["desc"]))}</p></div><b>↗</b></a>')


def region_photo(slug):
    for cat in PHOTO_ORDER:
        for img in sorted(ROOT.glob(f"regional-{slug}-{cat}-*.jpg")):
            page = ROOT / (img.stem[len("regional-"):] + ".html")
            if page.exists() and "kp-redirect" not in read(page):
                return img.name
    return None


def region_grid(s, nl):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from kp_nav import regions
    intros_path = ROOT / "content" / "region_intros.json"
    intros = json.loads(read(intros_path)) if intros_path.exists() else {}
    cards = []
    for slug, name in regions():
        photo = region_photo(slug)
        if not photo:
            continue
        line = short(intros.get(slug, ""), 60)
        cards.append(f'<a href="{slug}.html"><img src="{photo}" alt="{html.escape(name)}" loading="lazy">'
                     f'<span><b>{html.escape(name)}</b><small>{html.escape(line)}</small></span></a>')
    if len(cards) % 4 == 3:  # first region (Seoul) spans two columns so the grid has no hole
        cards[0] = cards[0].replace("<a ", '<a class="wide" ', 1)
    sec = re.search(r'(<section[^>]*id="regional-hubs"[^>]*>\s*<div class="heading">.*?</a>\s*</div>)(.*?)(</section>)', s, re.S)
    if not sec or not cards:
        return s
    s = s[:sec.start(2)] + '<div class="kp-regions">' + "".join(cards) + "</div>" + s[sec.end(2):]
    if 'id="kp-home-regions"' in s:
        s = re.sub(r'<style id="kp-home-regions">.*?</style>', lambda m: REGION_CSS, s, count=1, flags=re.S)
    else:
        s = re.sub(r"</head>", lambda m: REGION_CSS + nl + m.group(0), s, count=1)
    return s


def main():
    dates_path = ROOT / "content" / "page_dates.json"
    dates = json.loads(read(dates_path)) if dates_path.exists() else {}
    order = {}  # later position in the source list = newer on the same day
    guides = list(guide_cards())
    regional = list(regional_items())
    for n, it in enumerate(guides):
        order[it["href"]] = n             # guides.html lists older guides first
    for n, it in enumerate(regional):
        order[it["href"]] = n             # published.json is in publishing order
    key = lambda it: (dates.get(it["href"], ""), order.get(it["href"], 0))
    picks = sorted(guides, key=key, reverse=True)[:2] + sorted(regional, key=key, reverse=True)[:2]
    picks.sort(key=key, reverse=True)
    if not picks:
        return

    p = ROOT / "index.html"
    s = read(p)
    nl = "\r\n" if "\r\n" in s else "\n"
    sec = s.find('id="latest"')  # the "Latest guides" section, not the regions list above it
    m = re.compile(r'(<div class="latest-grid">)(.*?)(</div>\s*</section>)', re.S).search(s, sec) if sec >= 0 else None
    if not m:
        print("home_latest: latest-grid not found")
        return
    inner = nl + nl.join(card(i + 1, it) for i, it in enumerate(picks)) + nl
    new = region_grid(s[:m.start(2)] + inner + s[m.end(2):], nl)
    if new != s:
        p.write_bytes(new.encode("utf-8"))
    print("home_latest:", ", ".join(it["href"] for it in picks))


if __name__ == "__main__":
    main()

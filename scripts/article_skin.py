#!/usr/bin/env python3
"""Give every article the shared Korea Plainly article design. Idempotent.

For each article (cards on guides.html + regional articles in published.json):

  * adds class="kp-article" to <body> and links article.css and the site fonts,
    so all three historical templates look the same;
  * regional articles: adds a small "Region · Category" kicker and moves the
    headline above the cover photo;
  * turns the "Related guides" list into three photo cards;
  * older guides: replaces the shared stock cover photo with the guide's own image;
  * regional articles: shows a "Visiting" card built from what the article
    already contains: region, address (newer articles), the Google rating noted
    when it was published, and Naver Map / Google Maps / official website buttons.
    Opening hours are deliberately not stored; the card points to the live map.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
CSS_LINK = '<link rel="stylesheet" href="article.css?v=1">'
FONTS_LINK = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700'
              '&family=Playfair+Display:ital,wght@0,600;1,600&display=swap">')


def read(p):
    return p.read_bytes().decode("utf-8")


def esc(v):
    return html.escape(str(v), quote=True)


def thumbs_from_guides():
    g = read(ROOT / "guides.html")
    out = {}
    for m in re.finditer(r'<a\s+class="guide-card"\s+href="([^"]+)"[^>]*>\s*<div\s+class="guide-image"\s+'
                         r'(?:style="background-image:url\(\'([^\']+)\'\)"|data-thumb="([^"]+)")', g):
        out[m.group(1)] = m.group(2) or m.group(3)
    return out


def thumb_for(name, guide_thumbs):
    if name in guide_thumbs and (ROOT / guide_thumbs[name]).exists():
        return guide_thumbs[name]
    p = ROOT / name
    if not p.exists():
        return "og-default.jpg"
    s = read(p)
    m = (re.search(r'<img\b[^>]*class="cover"[^>]*src="([^"]+)"', s)
         or re.search(r'property="og:image"\s+content="https://korea-plainly\.com/([^"]+)"', s))
    src = m.group(1) if m else "og-default.jpg"
    if (ROOT / src).exists() and src != "og-default.jpg":
        return src
    return hub_photo(name) or "og-default.jpg"


GROUP_CATS = {"see-do": ["travel", "culture", "leisure", "local-guide"], "eat-drink": ["food", "cafe"],
              "shop": ["shopping"], "stay": ["stay"]}


def hub_photo(name):
    """A photo for hub pages (busan.html, busan-eat-drink.html, eat-drink.html), which have no cover."""
    stem = name[:-5] if name.endswith(".html") else name
    region, group = stem, None
    for g in GROUP_CATS:
        if stem == g:
            region, group = "*", g
        elif stem.endswith("-" + g):
            region, group = stem[: -len(g) - 1], g
    cats = GROUP_CATS.get(group, ["travel", "culture", "local-guide", "leisure", "food", "cafe", "shopping", "stay"])
    for cat in cats:
        found = sorted(ROOT.glob(f"regional-{region}-{cat}-*.jpg"))
        if found:
            return found[0].name
    return None


def related_cards(s, name, guide_thumbs):
    sec = re.search(r'(<section class="related-guides"[^>]*>)(.*?)(</section>)', s, re.S)
    if not sec:
        return s
    inner = sec.group(2)
    links = re.findall(r'<a href="([^"]+)">\s*(?:<img[^>]*>)?\s*(?:<span>)?(.*?)(?:</span>)?\s*</a>', inner, re.S)
    seen = {name}  # never link to itself, never the same guide twice (merged guides share one target)
    links = [(h, re.sub(r"<[^>]+>", "", t).strip()) for h, t in links
             if h.endswith(".html") and not (h in seen or seen.add(h))][:3]
    if not links:
        return s
    cards = "".join(f'<a href="{esc(h)}"><img src="{esc(thumb_for(h, guide_thumbs))}" alt="" loading="lazy"><span>{t}</span></a>'
                    for h, t in links)
    new_inner = f'\n<h2>Related guides</h2>\n<div class="kp-related">{cards}</div>\n'
    return s[:sec.start(2)] + new_inner + s[sec.end(2):]


def regional_head(s, place, nl):
    """Kicker above the headline, and the headline above the cover photo."""
    if 'data-kp="kicker"' not in s:
        kicker = f'<p class="kp-kicker" data-kp="kicker">{esc(place.get("region", ""))} · {esc(place.get("category", ""))}</p>'
        s = re.sub(r"(<h1[^>]*>)", lambda m: kicker + nl + m.group(1), s, count=1)
    art = re.search(r"<article[^>]*>", s)
    cover = re.search(r'<img\b[^>]*class="cover"[^>]*>(?:\s*<p class="photo-credit"[^>]*>.*?</p>)?', s, re.S)
    h1 = re.search(r'<p class="kp-kicker"[^>]*>.*?</p>\s*<h1[^>]*>.*?</h1>(?:\s*<p class="kp-date"[^>]*>.*?</p>)?', s, re.S)
    if art and cover and h1 and cover.start() < h1.start():
        block_cover, block_head = cover.group(0), h1.group(0)
        s = s[:h1.start()] + s[h1.end():]                    # remove headline block
        s = s[:cover.start()] + block_head + nl + block_cover + s[cover.end():]
    return s


def nice_date(d):
    from datetime import datetime
    try:
        dt = datetime.strptime(d[:10], "%Y-%m-%d")
    except ValueError:
        return ""
    return f"{dt:%B} {dt.year}"


def visit_card(s, place):
    s = re.sub(r'\r?\n?<section class="kp-visit"[^>]*>.*?</section>', "", s, flags=re.S)
    name, region = place.get("place_name", ""), place.get("region", "")
    links = re.search(r'<section class="useful-links">(.*?)</section>', s, re.S)
    links = links.group(1) if links else ""
    gmap = re.search(r'<a href="([^"]+)"[^>]*>Google Maps</a>', links)
    site = re.search(r'<a href="([^"]+)"[^>]*>Official website</a>', links)
    rows = [("Region", esc(region))]
    found = re.search(r'<strong>Address:</strong>\s*([^<]+)', s)
    address = place.get("address") or (html.unescape(found.group(1)).strip() if found else "")
    if address and not found:  # the summary box above already shows it
        rows.append(("Address", esc(address)))
    if place.get("google_rating"):
        count = f" from {int(place['google_review_count']):,} reviews" if place.get("google_review_count") else ""
        when = nice_date(place.get("published_at", ""))
        rows.append(("Google rating", f"{place['google_rating']}/5{count}" + (f" <small>({when})</small>" if when else "")))
    naver = f"https://map.naver.com/p/search/{quote(name + ' ' + region)}"
    buttons = [f'<a href="{esc(naver)}" target="_blank" rel="noopener">Naver Map</a>']
    if gmap:
        buttons.append(f'<a class="alt" href="{gmap.group(1)}" target="_blank" rel="noopener">Google Maps</a>')
    if site:
        buttons.append(f'<a class="alt" href="{site.group(1)}" target="_blank" rel="noopener nofollow">Official website</a>')
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    card = (f'<section class="kp-visit" data-kp="visit"><h2>Visiting {esc(name)}</h2><dl>{dl}</dl>'
            f'<div class="kp-buttons">{"".join(buttons)}</div>'
            f'<p class="kp-note">Opening hours, prices and closures change. Check the map before you go.</p></section>')
    # after the summary box if there is one, otherwise after the cover photo / credit
    m = re.search(r'<div class="summary(?:-box)?">.*?</div>', s, re.S)
    if not m:
        m = re.search(r'<img\b[^>]*class="cover"[^>]*>(?:\s*<p class="photo-credit"[^>]*>.*?</p>)?', s, re.S)
    if not m:
        return s
    return s[:m.end()] + "\n" + card + s[m.end():]


def own_cover(s, name, guide_thumbs):
    """Older guides used one of three shared stock photos; show the guide's own image instead."""
    thumb = guide_thumbs.get(name)
    if not thumb or not (ROOT / thumb).exists():
        return s
    def swap(m):
        label = m.group(1) or ""
        return f'<img class="cover" src="{esc(thumb)}" alt="{label}">'
    return re.sub(r'<div class="article-cover"(?:\s+aria-label="([^"]*)")?\s*></div>', swap, s, count=1)


def main():
    published = [p for p in json.loads(read(ROOT / "content" / "published.json")) if isinstance(p, dict) and p.get("slug")]
    places = {p["slug"] + ".html": p for p in published if p.get("place_name")}
    guide_thumbs = thumbs_from_guides()
    files = set(guide_thumbs) | {p["slug"] + ".html" for p in published}
    changed = 0
    for name in sorted(files):
        p = ROOT / name
        if not p.exists():
            continue
        s = read(p)
        if "kp-redirect" in s:
            continue
        nl = "\r\n" if "\r\n" in s else "\n"
        new = s
        if not re.search(r'<body[^>]*class="[^"]*kp-article', new):
            if re.search(r"<body[^>]*class=\"", new):
                new = re.sub(r'(<body[^>]*class=")', r"\1kp-article ", new, count=1)
            else:
                new = re.sub(r"<body", '<body class="kp-article"', new, count=1)
        if "article.css" not in new:
            new = re.sub(r"</head>", lambda m: CSS_LINK + nl + m.group(0), new, count=1)
        if "family=DM+Sans" not in new:
            new = re.sub(r"</head>", lambda m: FONTS_LINK + nl + m.group(0), new, count=1)
        if name in places:
            new = regional_head(new, places[name], nl)
            new = visit_card(new, places[name])
        new = own_cover(new, name, guide_thumbs)
        new = related_cards(new, name, guide_thumbs)
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    print(f"article_skin: {len(files)} articles, updated {changed}")


if __name__ == "__main__":
    main()

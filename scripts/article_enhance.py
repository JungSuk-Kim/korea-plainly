#!/usr/bin/env python3
"""Make every article page complete. Idempotent: safe to run on every build.

For each article (every card on guides.html plus every entry in
content/published.json):

  1. A visible "Published <date>" line under the first <h1>.
  2. Article structured data (JSON-LD) for search engines.

Header and footer are handled by scripts/site_chrome.py.

Publish dates live in content/page_dates.json. A new article gets the
published_at value from published.json, or today's date, the first time this
script sees it.
"""
import hashlib
import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kp_nav import crumb_trail  # noqa: E402
BASE = "https://korea-plainly.com"
DATES_PATH = ROOT / "content" / "page_dates.json"
UPDATES_PATH = ROOT / "content" / "page_updates.json"  # {page: {"hash": text fingerprint, "updated": date}}
PUBLISHED_PATH = ROOT / "content" / "published.json"


def read(p):
    return p.read_bytes().decode("utf-8")


def write(p, s):
    p.write_bytes(s.encode("utf-8"))


def article_files():
    guides = read(ROOT / "guides.html")
    files = set(re.findall(r'<a\s+class="guide-card"\s+href="([^"]+\.html)"', guides))
    published = json.loads(read(PUBLISHED_PATH)) if PUBLISHED_PATH.exists() else []
    stamps = {}
    for p in published:
        if isinstance(p, dict) and p.get("slug"):
            files.add(p["slug"] + ".html")
            if p.get("published_at"):
                stamps[p["slug"] + ".html"] = p["published_at"][:10]
    return sorted(f for f in files if (ROOT / f).exists()), stamps


def nice(d):
    dt = datetime.strptime(d, "%Y-%m-%d")
    return f"{dt.day} {dt:%B %Y}"


def add_date(s, published, nl, updated=None):
    """Byline with the publish date (and the update date once the text has changed). Rebuilt every run."""
    line = (f'<p class="kp-date" data-kp="date">By <a href="about.html#how-we-work">Korea Plainly</a> · Published '
            f'<time datetime="{published}">{nice(published)}</time>')
    if updated and updated > published:
        line += f' · Updated <time datetime="{updated}">{nice(updated)}</time>'
    line += "</p>"
    if ".kp-date{" not in s:
        style = '<style>.kp-date{font-size:13px;color:#62635f;margin:-6px 0 22px}</style>'
        s = re.sub(r"</head>", lambda m: style + nl + m.group(0), s, count=1, flags=re.I)
    if 'data-kp="date"' in s:
        return re.sub(r'<p class="kp-date" data-kp="date">.*?</p>', lambda m: line, s, count=1, flags=re.S)
    return re.sub(r"</h1>", lambda m: m.group(0) + nl + line, s, count=1, flags=re.I)


def content_hash(s):
    """Fingerprint of the article's own text, ignoring parts other steps generate."""
    m = re.search(r"<main\b.*?</main>", s, re.S) or re.search(r"<article\b.*?</article>", s, re.S)
    body = m.group(0) if m else s
    body = re.sub(r'<(section|nav|script|style)\b[^>]*class="(?:related-guides|kp-visit|kp-toc|kp-crumbs|useful-links)".*?</\1>', " ", body, flags=re.S)
    body = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<nav\b.*?</nav>", " ", body, flags=re.S)
    body = re.sub(r'<p class="(?:kp-date|photo-credit|kp-kicker)"[^>]*>.*?</p>', " ", body, flags=re.S)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
    return hashlib.md5(text.encode()).hexdigest()[:12]


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def meta(s, pattern):
    m = re.search(pattern, s, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else None


def add_jsonld(s, name, published, nl, updated=None):
    # Rebuilt on every run so it follows title or image changes.
    s = re.sub(r'<script type="application/ld\+json" id="kp-article-ld">.*?</script>\r?\n?', "", s, flags=re.S)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S | re.I)
    headline = text_of(h1.group(1)) if h1 else (meta(s, r"<title>(.*?)</title>") or name)
    url = meta(s, r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']') or f"{BASE}/{name}"
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": headline[:110],
        "description": meta(s, r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']') or "",
        "image": [meta(s, r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\'](.*?)["\']') or f"{BASE}/og-default.jpg"],
        "datePublished": published,
        "dateModified": updated if updated and updated > published else published,
        "author": {"@type": "Organization", "name": "Korea Plainly", "url": BASE + "/"},
        "publisher": {"@type": "Organization", "name": "Korea Plainly", "url": BASE + "/"},
        "mainEntityOfPage": url,
    }
    block = ('<script type="application/ld+json" id="kp-article-ld">'
             + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    return re.sub(r"</head>", lambda m: block + nl + m.group(0), s, count=1, flags=re.I)


def add_breadcrumbs(s, name, trail, nl):
    """BreadcrumbList: Home > Guides (or the region hub) > article. Rebuilt every run."""
    s = re.sub(r'<script type="application/ld\+json" id="kp-breadcrumb-ld">.*?</script>\r?\n?', "", s, flags=re.S)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S | re.I)
    title = text_of(h1.group(1)) if h1 else name
    items = [("Home", f"{BASE}/")] + [(t, f"{BASE}/{h}") for t, h in trail] + [(title, f"{BASE}/{name}")]
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}
    block = ('<script type="application/ld+json" id="kp-breadcrumb-ld">'
             + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    return re.sub(r"</head>", lambda m: block + nl + m.group(0), s, count=1, flags=re.I)


def article_meta(s, published, nl):
    """og:type article and article:published_time, which Pinterest rich pins and others read."""
    s = re.sub(r'(<meta\s+property="og:type"\s+content=")website(")', r"\1article\2", s, count=1)
    s = re.sub(r'<meta property="article:published_time" content="[^"]*">\r?\n?', "", s)
    tag = f'<meta property="article:published_time" content="{published}">'
    return re.sub(r"</head>", lambda m: tag + nl + m.group(0), s, count=1, flags=re.I)


def main():
    files, stamps = article_files()
    published_list = json.loads(read(PUBLISHED_PATH)) if PUBLISHED_PATH.exists() else []
    places = {x["slug"] + ".html": x for x in published_list if isinstance(x, dict) and x.get("slug") and x.get("place_name")}
    guide_cats = dict(re.findall(r'<a\s+class="guide-card"\s+href="([^"]+)"\s+data-guide-category="([^"]+)"', read(ROOT / "guides.html")))
    dates = json.loads(read(DATES_PATH)) if DATES_PATH.exists() else {}
    updates = json.loads(read(UPDATES_PATH)) if UPDATES_PATH.exists() else {}
    today = date.today().isoformat()
    changed = 0
    for name in files:
        published = dates.get(name) or stamps.get(name) or today
        dates[name] = published
        p = ROOT / name
        s = read(p)
        nl = "\r\n" if "\r\n" in s else "\n"
        pl = places.get(name)
        trail = (crumb_trail(region=pl.get("region"), category=pl.get("category")) if pl
                 else crumb_trail(guide_category=guide_cats.get(name)))
        h = content_hash(s)
        entry = updates.get(name)
        if entry is None:  # first time seen: remember the text, no update date yet
            entry = {"hash": h, "updated": (pl or {}).get("rewritten_at", "")[:10] or None}
        elif entry.get("hash") != h:  # the article's own text changed
            entry = {"hash": h, "updated": today}
        updates[name] = entry
        updated = entry.get("updated")
        new = add_breadcrumbs(add_jsonld(add_date(s, published, nl, updated), name, published, nl, updated), name, trail, nl)
        new = article_meta(new, published, nl)
        if new != s:
            write(p, new)
            changed += 1
    write(DATES_PATH, json.dumps(dict(sorted(dates.items())), indent=2, ensure_ascii=False) + "\n")
    write(UPDATES_PATH, json.dumps(dict(sorted(updates.items())), indent=2, ensure_ascii=False) + "\n")
    print(f"article_enhance: {len(files)} articles, updated {changed}")


if __name__ == "__main__":
    main()

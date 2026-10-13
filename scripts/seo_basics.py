#!/usr/bin/env python3
"""Idempotent SEO basics for every root-level HTML page.

Run before scripts/update_sitemap.py. Safe to run any number of times.

  1. Adds <link rel="icon"> when a page has none.
  2. Adds og:/twitter: tags when a page has none (or only og:image is missing).
  3. Marks thin hub pages "noindex,follow" and removes that mark again
     automatically once the hub has enough guides.

The Search Console verification file (google*.html) is never touched.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://korea-plainly.com"
SITE_NAME = "Korea Plainly"
FAVICON = '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
DEFAULT_OG_IMAGE = f"{BASE}/og-default.jpg"

THIN_WORDS = 80   # visible words inside <main>
MIN_CARDS = 3     # "Read guide" cards on a hub
PROTECTED = {"index.html", "about.html", "contact.html", "privacy.html",
             "guides.html", "regions.html", "404.html"}
MARK = 'data-kp="thin-hub"'
NOINDEX_TAG = f'<meta name="robots" content="noindex,follow" {MARK}>'


def is_google_verification(name):
    return re.fullmatch(r"google[0-9a-f]+\.html", name) is not None


def main_words(s):
    m = re.search(r"<main.*?</main>", s, re.S | re.I)
    body = m.group(0) if m else s
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", body, flags=re.S | re.I)
    # the automatic "Related guides" block is not the hub's own content
    body = re.sub(r'<(section|div|aside)[^>]*class="related-guides".*?</\1>', "", body, flags=re.S | re.I)
    return len(re.sub(r"<[^>]+>", " ", body).split())


def is_thin(s, name):
    if name in PROTECTED:
        return False
    return main_words(s) < THIN_WORDS and s.count("Read guide") < MIN_CARDS


def attr(s, pattern):
    m = re.search(pattern, s, re.S | re.I)
    return m.group(1).strip() if m else None


def esc(text):
    return html.escape(html.unescape(text), quote=True)


def before_head_end(s, block, nl):
    m = re.search(r"</head>", s, re.I)
    return s if not m else s[:m.start()] + block + nl + s[m.start():]


TITLE_LIMIT = 65  # Google shows about 60 characters; keep the words that describe the page


def short_title(s):
    """Drop the " | Korea Plainly" suffix from titles too long to show in search results."""
    m = re.search(r"<title>(.*?)</title>", s, re.S | re.I)
    if not m:
        return s
    text = re.sub(r"\s+", " ", m.group(1)).strip()
    suffix = " | " + SITE_NAME
    if text.endswith(suffix) and len(text) > TITLE_LIMIT:
        return s[:m.start(1)] + text[: -len(suffix)] + s[m.end(1):]
    return s


def patch(s, name):
    nl = "\r\n" if "\r\n" in s else "\n"
    s = short_title(s)

    if not re.search(r'rel=["\'](?:shortcut )?icon["\']', s, re.I):
        s = before_head_end(s, FAVICON, nl)

    title = attr(s, r"<title>(.*?)</title>") or SITE_NAME
    desc = attr(s, r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']')
    url = attr(s, r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']') or f"{BASE}/{name}"
    if not re.search(r'property=["\']og:title["\']', s, re.I):
        tags = [f'<meta property="og:title" content="{esc(title)}">']
        if desc:
            tags.append(f'<meta property="og:description" content="{esc(desc)}">')
        tags += [f'<meta property="og:url" content="{esc(url)}">',
                 '<meta property="og:type" content="website">',
                 f'<meta property="og:image" content="{DEFAULT_OG_IMAGE}">',
                 f'<meta property="og:site_name" content="{SITE_NAME}">',
                 '<meta name="twitter:card" content="summary_large_image">',
                 f'<meta name="twitter:title" content="{esc(title)}">']
        if desc:
            tags.append(f'<meta name="twitter:description" content="{esc(desc)}">')
        tags.append(f'<meta name="twitter:image" content="{DEFAULT_OG_IMAGE}">')
        s = before_head_end(s, nl.join(tags), nl)
    elif not re.search(r'property=["\']og:image["\']', s, re.I):
        s = before_head_end(s, nl.join([
            f'<meta property="og:image" content="{DEFAULT_OG_IMAGE}">',
            f'<meta name="twitter:image" content="{DEFAULT_OG_IMAGE}">']), nl)

    thin = is_thin(s, name)
    if thin and not re.search(r'<meta[^>]+name=["\']robots["\']', s, re.I):
        s = before_head_end(s, NOINDEX_TAG, nl)
    elif not thin and MARK in s:
        s = re.sub(r"[ \t]*<meta[^>]*" + re.escape(MARK) + r"[^>]*>(?:\r?\n)?", "", s)
    return s


def main():
    changed = 0
    for p in sorted(ROOT.glob("*.html")):
        if is_google_verification(p.name):
            continue
        try:
            raw = p.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            print(f"skip (not utf-8): {p.name}")
            continue
        new = patch(raw, p.name)
        if new != raw:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    print(f"seo_basics: updated {changed} page(s)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""RSS feed of the newest articles (feed.xml), for feed readers and Google Discover.

Articles are pages with Article structured data (id="kp-article-ld"); redirect and noindex pages are skipped.
Dates come from content/page_dates.json, so the feed only changes when articles do (idempotent).
index.html and guides.html get a <link rel="alternate"> so readers can find the feed.
"""
import html
import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://korea-plainly.com"
LIMIT = 40
LINK = '<link rel="alternate" type="application/rss+xml" title="Korea Plainly" href="https://korea-plainly.com/feed.xml" id="kp-rss">'


def meta(s, name):
    m = re.search(r'<meta\s+(?:name|property)="' + re.escape(name) + r'"\s+content="([^"]*)"', s, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def main():
    dates = json.loads((ROOT / "content/page_dates.json").read_text(encoding="utf-8"))
    items = []
    for p in ROOT.glob("*.html"):
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "kp-redirect" in s or 'id="kp-article-ld"' not in s or re.search(r'name="robots"[^>]*noindex', s):
            continue
        d = dates.get(p.name)
        if not d:
            continue
        title = meta(s, "og:title") or re.sub(r"\s*\|\s*Korea Plainly\s*$", "", html.unescape(
            (re.search(r"<title>(.*?)</title>", s, re.S) or [None, p.stem])[1]).strip())
        items.append((d, p.name, title, meta(s, "description")))
    items.sort(key=lambda x: (x[0], x[1]), reverse=True)
    items = items[:LIMIT]

    def rfc(d):
        return format_datetime(datetime.fromisoformat(d).replace(hour=8, tzinfo=timezone.utc))

    e = lambda t: html.escape(t, quote=False)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">', "<channel>",
           "<title>Korea Plainly</title>", f"<link>{BASE}/</link>",
           "<description>Plain, practical English guides for first-time visitors to Korea.</description>",
           "<language>en</language>",
           f'<atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>']
    if items:
        out.append(f"<lastBuildDate>{rfc(items[0][0])}</lastBuildDate>")
    for d, name, title, desc in items:
        url = f"{BASE}/{name}"
        out += ["<item>", f"<title>{e(title)}</title>", f"<link>{url}</link>", f'<guid isPermaLink="true">{url}</guid>',
                f"<pubDate>{rfc(d)}</pubDate>", f"<description>{e(desc)}</description>", "</item>"]
    out += ["</channel>", "</rss>", ""]
    (ROOT / "feed.xml").write_text("\n".join(out), encoding="utf-8")

    for name in ("index.html", "guides.html"):
        p = ROOT / name
        b = p.read_bytes()
        if b'id="kp-rss"' not in b and b"</head>" in b:
            p.write_bytes(b.replace(b"</head>", LINK.encode() + b"\n</head>", 1))
    print(f"RSS feed: {len(items)} articles.")


if __name__ == "__main__":
    main()

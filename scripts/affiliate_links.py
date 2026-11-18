#!/usr/bin/env python3
"""Booking boxes with affiliate links in a few guides (content/affiliates.json). Idempotent.

Each guide listed under "boxes" gets one small box at the end of the section whose <h2> contains "after":
a sentence of honest context, one or two links, and the disclosure line. Links carry the Klook partner id
(?aid=...), open in a new tab and are marked rel="sponsored nofollow". A guide that is no longer listed, or
"enabled": false, loses its box on the next run. Keep it to one box per guide: these are guides, not shop pages.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "content" / "affiliates.json"
BOX = re.compile(r'[ \t]*<aside class="kp-aff"[^>]*>.*?</aside>\r?\n?', re.S)


def read(p):
    return p.read_bytes().decode("utf-8")


def with_aid(url, aid):
    return url + ("&" if "?" in url else "?") + "aid=" + aid


def box(entry, conf):
    links = " &middot; ".join(
        '<a href="{}" target="_blank" rel="sponsored nofollow noopener">{} &rarr;</a>'.format(
            html.escape(with_aid(url, conf["klook_aid"])), html.escape(label))
        for label, url in entry["links"])
    return ('<aside class="kp-aff" data-kp-aff="klook"><p class="kp-aff-k">BOOKING AHEAD</p><p>{}</p>'
            '<p class="kp-aff-l">{}</p><p class="kp-aff-d">{}</p></aside>\n').format(
                html.escape(entry["text"]), links, html.escape(conf["disclosure"]))


def place(s, entry, new):
    """Insert the box where the section named by entry["after"] ends: before the next <h2> or the FAQ block."""
    for m in re.finditer(r"<h2\b[^>]*>(.*?)</h2>", s, re.S):
        if entry["after"].lower() in re.sub(r"<[^>]+>", "", m.group(1)).lower():
            ends = [i for i in (s.find("<h2", m.end()), s.find('<section class="faq"', m.end()),
                                s.find('<section class="related-guides"', m.end()), s.find("</article>", m.end())) if i > 0]
            at = min(ends)
            return s[:at] + new + s[at:]
    return None


def main():
    conf = json.loads(read(CONF)) if CONF.exists() else {}
    boxes = conf.get("boxes", {}) if conf.get("enabled") else {}
    changed, missing = 0, []
    for p in sorted(ROOT.glob("*.html")):
        s = read(p)
        entry = boxes.get(p.stem)
        if not entry and "kp-aff" not in s:
            continue
        new = BOX.sub("", s)
        if entry and "kp-redirect" not in s[:4000]:
            placed = place(new, entry, box(entry, conf))
            if placed is None:
                missing.append(p.name)
            else:
                new = placed
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    for name in missing:
        print(f"::warning::affiliate_links: no section matching 'after' in {name}")
    print(f"affiliate_links: {len(boxes)} guide(s) with a booking box, {changed} page(s) changed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Booking boxes with affiliate links in a few guides (content/affiliates.json). Idempotent.

Each guide listed under "boxes" gets one small box at the end of the section whose <h2> contains "after":
a title, a sentence of honest context, one or two buttons, and the disclosure line. A link is [label, url] for Klook
(gets ?aid=...), [label, url, "trip"] for Trip.com (gets Allianceid and SID) or [label, url, "creatrip"] for Creatrip
(gets utm_source and aff_id); all open in a new tab and are marked
rel="sponsored nofollow". A guide that is no longer listed, or
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


def tracked(link, conf):
    """The link with its partner's ids, and the partner name: [label, url] is Klook, [label, url, "trip"] is Trip.com,
    [label, url, "creatrip"] is Creatrip."""
    partner = link[2] if len(link) > 2 else "klook"
    url = link[1]
    if partner == "trip":
        t = conf["trip"]
        return url + ("&" if "?" in url else "?") + "Allianceid={}&SID={}".format(t["allianceid"], t["sid"]), partner
    if partner == "creatrip":
        a = conf["creatrip_aff"]
        return url + ("&" if "?" in url else "?") + "utm_source={0}&aff_id={0}".format(a), partner
    return with_aid(url, conf["klook_aid"]), partner


def box(entry, conf):
    """A banner-style card in the site's own colours: title, one sentence, button(s), disclosure. No partner images or scripts."""
    links = [(link[0],) + tracked(link, conf) for link in entry["links"]]
    partners = " ".join(dict.fromkeys(p for _, _, p in links))
    buttons = "".join(
        '<a class="kp-aff-btn" href="{}" target="_blank" rel="sponsored nofollow noopener">{} &rarr;</a>'.format(
            html.escape(url), html.escape(label))
        for label, url, _ in links)
    title = '<p class="kp-aff-t">{}</p>'.format(html.escape(entry["title"])) if entry.get("title") else ""
    return ('<aside class="kp-aff" data-kp-aff="{}"><p class="kp-aff-k">BOOK AHEAD</p>{}<p>{}</p>'
            '<p class="kp-aff-l">{}</p><p class="kp-aff-d">{}</p></aside>\n').format(
                partners, title, html.escape(entry["text"]), buttons, html.escape(conf["disclosure"]))


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

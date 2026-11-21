#!/usr/bin/env python3
"""Shared text for our YouTube videos: the top of every description, and the spoken sign-off.

The first two lines of a description are all most viewers see, so they carry the link to
the free guide on the site; the summary follows, then a subscribe link.

Long-form videos also list the booking links of their guide (content/affiliates.json, the same links as the
"Book ahead" card on the site) under the summary, with a disclosure. Shorts do not: links in a Short's description
cannot be clicked.
"""
import json
from pathlib import Path

from affiliate_links import tracked

AFFILIATES = Path(__file__).resolve().parent.parent / "content" / "affiliates.json"
SITE = "https://korea-plainly.com"
CHANNEL = "https://www.youtube.com/@KoreaPlainly?sub_confirmation=1"
SHORT_OUTRO = "Subscribe for more Korea tips every Monday, Wednesday, Friday and Saturday."


def booking(article):
    """Description lines for the guide's booking links (at most two), or [] when the guide has no "Book ahead" card."""
    conf = json.loads(AFFILIATES.read_text(encoding="utf-8")) if AFFILIATES.exists() else {}
    entry = conf.get("boxes", {}).get(article) if conf.get("enabled") else None
    if not entry:
        return []
    return (["Book ahead (affiliate links: if you book through one, Korea Plainly may earn a small commission "
             "at no extra cost to you):"]
            + [f"{link[0]}: {tracked(link, conf)[0]}" for link in entry["links"][:2]] + [""])


def header(article, summary, links=False):
    return [f"Free full guide, with maps and tips: {SITE}/{article}.html", "",
            summary.strip(), ""] + (booking(article) if links else []) + [
            f"New Korea travel videos every week, subscribe: {CHANNEL}",
            f"More plain, practical Korea guides: {SITE}", ""]


def refresh(text, article, summary, links=False):
    """Swap the top of an older description (everything before the hashtags or chapters) for the current header."""
    lines = text.rstrip("\n").split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("#") or l == "Chapters:"), len(lines))
    return "\n".join(header(article, summary, links) + lines[start:]) + "\n"

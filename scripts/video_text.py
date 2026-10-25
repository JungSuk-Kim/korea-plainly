#!/usr/bin/env python3
"""Shared text for our YouTube videos: the top of every description, and the spoken sign-off.

The first two lines of a description are all most viewers see, so they carry the link to
the free guide on the site; the summary follows, then a subscribe link.
"""
SITE = "https://korea-plainly.com"
CHANNEL = "https://www.youtube.com/@KoreaPlainly?sub_confirmation=1"
SHORT_OUTRO = "Subscribe for more Korea tips every Monday, Wednesday, Friday and Saturday."


def header(article, summary):
    return [f"Free full guide, with maps and tips: {SITE}/{article}.html", "",
            summary.strip(), "",
            f"New Korea travel videos every week, subscribe: {CHANNEL}",
            f"More plain, practical Korea guides: {SITE}", ""]


def refresh(text, article, summary):
    """Swap the top of an older description (everything before the hashtags or chapters) for the current header."""
    lines = text.rstrip("\n").split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("#") or l == "Chapters:"), len(lines))
    return "\n".join(header(article, summary) + lines[start:]) + "\n"

#!/usr/bin/env python3
"""Number the guide cards on guides.html 01, 02, 03 ... in page order, and drop duplicate cards.

When an article is merged into another (content/redirects.json), its card ends up pointing at the surviving
page, so that page has two cards: keep the one whose heading matches the page's own <h1>.

New guides are added with "number of cards + 1", so after merges and redirects the numbers repeat or skip.
Cards whose label is a word (such as START) keep it and are not counted.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "guides.html"
NUM = re.compile(r'(<div\s+class="guide-image"[^>]*>(?:(?!</div>).)*?<span>\s*)(\d{1,3})(\s*</span>)', re.S)


CARD = re.compile(r'<a\s+class="guide-card"\s+href="([^"]+)".*?</a>\s*', re.S)


def h1_of(href):
    page = ROOT / href
    if not page.exists():
        return None
    m = re.search(r"<h1[^>]*>(.*?)</h1>", page.read_bytes().decode("utf-8"), re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def dedupe(raw):
    cards = list(CARD.finditer(raw))
    by_href = {}
    for m in cards:
        by_href.setdefault(m.group(1), []).append(m)
    drop = set()
    for href, ms in by_href.items():
        if len(ms) < 2:
            continue
        title = h1_of(href)
        heads = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", (re.search(r"<h2>(.*?)</h2>", m.group(0), re.S) or [0, ""])[1])).strip()
                 for m in ms]
        keep = heads.index(title) if title in heads else 0
        drop |= {m.start() for k, m in enumerate(ms) if k != keep}
    out, last = [], 0
    for m in cards:
        if m.start() in drop:
            out.append(raw[last:m.start()])
            last = m.end()
    out.append(raw[last:])
    return "".join(out)


def main():
    raw = PAGE.read_bytes().decode("utf-8")
    raw_in = raw
    raw = dedupe(raw)
    count = iter(range(1, 10000))
    new = NUM.sub(lambda m: f"{m.group(1)}{next(count):02d}{m.group(3)}", raw)
    if new != raw_in:
        PAGE.write_bytes(new.encode("utf-8"))
    print("guide_numbers: guide cards numbered")


if __name__ == "__main__":
    main()

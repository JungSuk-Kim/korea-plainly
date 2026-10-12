#!/usr/bin/env python3
"""Load guide card photos only when they scroll into view.

Cards on guides.html used CSS background images, which browsers download all at
once (about 3 MB on a phone). This turns each one into a real <img> with
loading="lazy". The first (featured) card stays eager because it is on screen
straight away. It also gives every card a data-guide-category so the category
filter on guides.html works for new guides. Idempotent.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATEGORY = {"daily korea": "daily", "daily life": "daily", "food": "food", "money": "money",
            "transport": "transport", "travel": "travel", "culture": "culture",
            "language": "language", "apps": "apps", "apps & tips": "apps"}


def main():
    p = ROOT / "guides.html"
    s = p.read_bytes().decode("utf-8")
    count = [0]

    def swap(m):
        count[0] += 1
        src = m.group(1)
        loading = "eager" if count[0] == 1 else "lazy"
        return (f'<div class="guide-image" data-thumb="{src}">'
                f'<img class="guide-thumb" src="{src}" alt="" loading="{loading}" decoding="async">')

    cats = {}
    pub_path = ROOT / "content" / "published.json"
    for item in (json.loads(pub_path.read_text(encoding="utf-8")) if pub_path.exists() else []):
        if isinstance(item, dict) and item.get("slug") and not item.get("place_name"):
            cats[item["slug"] + ".html"] = CATEGORY.get(str(item.get("category", "")).lower(), "travel")

    def add_category(m):
        tag, href = m.group(0), m.group(1)
        if "data-guide-category" in tag:
            return tag
        return tag.replace(f'href="{href}"', f'href="{href}" data-guide-category="{cats.get(href, "travel")}"', 1)

    s2 = re.sub(r'<a\s+class="guide-card"\s+href="([^"]+)"[^>]*>', add_category, s)
    new = re.sub(r'<div\s+class="guide-image"\s+style="background-image:url\(\'([^\']+)\'\)"\s*>', swap, s2)
    # a card whose photo changed keeps data-thumb and img src in step
    new = re.sub(r'<div class="guide-image" data-thumb="([^"]+)"><img class="guide-thumb" src="[^"]*"',
                 lambda m: f'<div class="guide-image" data-thumb="{m.group(1)}"><img class="guide-thumb" src="{m.group(1)}"', new)
    if ".guide-thumb{" not in new:
        css = ("<style id=\"kp-lazy-cards\">.guide-image{position:relative;overflow:hidden}"
               ".guide-image>.guide-thumb{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}"
               ".guide-image>span{position:absolute;z-index:1}</style>")
        new = re.sub(r"</head>", lambda m: css + "\n" + m.group(0), new, count=1)
    if new != s:
        p.write_bytes(new.encode("utf-8"))
    print(f"lazy_cards: {count[0]} card(s) converted")


if __name__ == "__main__":
    main()

"""The site's main menu, shared by every script that writes navigation."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GUIDE_CATEGORIES = [
    ("Travel Basics", "travel"), ("Transport", "transport"), ("Money", "money"),
    ("Apps & Tips", "apps"), ("Food & Dining", "food"), ("Daily Life", "daily"),
    ("Language", "language"), ("Culture", "culture"),
]


def regions():
    """(slug, name) for every region that has a hub page, in rotation order."""
    data = json.loads((ROOT / "content" / "region_rotation.json").read_text(encoding="utf-8"))
    return [(r["slug"], r["name"]) for r in data.get("regions", []) if (ROOT / f"{r['slug']}.html").exists()]


def _drop(label, href, links):
    items = "".join(f'<a href="{href_}">{html.escape(text)}</a>' for text, href_ in links)
    return (f'<div class="nav-drop"><a class="nav-parent" href="{href}">{label}'
            f'<span class="nav-chevron">⌄</span></a><div class="nav-menu">{items}</div></div>')


def nav_inner():
    guides = [("All guides", "guides.html")] + [(n, f"guides.html?category={s}") for n, s in GUIDE_CATEGORIES]
    regs = [(name, f"{slug}.html") for slug, name in regions()] + [("All regions", "regions.html")]
    return "\n".join([
        '<a href="index.html">Home</a>',
        _drop("Guides", "guides.html", guides),
        _drop("Regions", "regions.html", regs),
        '<a href="about.html">About</a>',
        '<a href="search.html" class="nav-search" aria-label="Search">Search</a>',
    ])

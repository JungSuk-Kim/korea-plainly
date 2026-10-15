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
        '<a href="videos.html">Videos</a>',
        '<a href="about.html">About</a>',
        '<a href="search.html" class="nav-search" aria-label="Search">Search</a>',
    ])


GROUP_OF_CATEGORY = {"travel": "see-do", "culture": "see-do", "leisure": "see-do", "local guide": "see-do",
                     "local-guide": "see-do", "food": "eat-drink", "cafe": "eat-drink",
                     "shopping": "shop", "stay": "stay"}
GROUP_NAMES = {"see-do": "See & Do", "eat-drink": "Eat & Drink", "shop": "Shop", "stay": "Stay"}


def crumb_trail(region=None, category=None, guide_category=None):
    """[(label, href)] between Home and the article: Region › Group, or Guides › Guide category."""
    if region:
        slug = region.lower().replace(" ", "-")
        trail = [(region, f"{slug}.html")] if (ROOT / f"{slug}.html").exists() else [("Regions", "regions.html")]
        g = GROUP_OF_CATEGORY.get((category or "").lower())
        hub = ROOT / f"{slug}-{g}.html" if g else None
        if hub and hub.exists() and "kp-redirect" not in hub.read_text(encoding="utf-8", errors="ignore"):
            trail.append((GROUP_NAMES[g], hub.name))
        return trail
    trail = [("Guides", "guides.html")]
    label = dict((s, n) for n, s in GUIDE_CATEGORIES).get(guide_category or "")
    if label:
        trail.append((label, f"guides.html?category={guide_category}"))
    return trail

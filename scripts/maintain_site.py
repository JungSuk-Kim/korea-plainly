#!/usr/bin/env python3
"""Run every site-maintenance step in the right order. Used by both workflows.

Each step is idempotent, so running this on an unchanged site changes nothing.
Stops at the first failing step (the audit fails the run on broken links).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS = [
    "guide_photos.py",                # first, so hub cards show the new photos; credited Wikimedia photos for guides (fetches when KP_FETCH_PHOTOS=1)
    "regional_photos.py",             # credited photos (Wikimedia, else Google Maps) + Naver Map links for regional articles
    "generate_region_pages.py",       # region hub pages from content/published.json
    "fix_navigation_and_regions.py",  # region/category hubs and menus
    "build_category_region_hubs.py",  # category hubs (travel.html, food.html, ...)
    "add_internal_links.py",          # "related guides" blocks
    "site_chrome.py",                 # same header, stylesheet and footer everywhere
    "site_integrity_fix.py",          # dropdown menu markup, CSS version, canonical tags
    "article_enhance.py",             # publish date + Article structured data
    "home_latest.py",                 # home page "Latest guides" from the newest articles
    "optimize_images.py",             # shrink oversized photos
    "seo_basics.py",                  # favicon, og tags, noindex for thin hubs
    "build_search_index.py",          # search-index.json for search.html
    "update_sitemap.py",              # sitemap without noindex pages
    "site_audit.py",                  # fail on broken links / missing basics
]


def main():
    for step in STEPS:
        print(f"::group::{step}", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / step)], cwd=ROOT)
        print("::endgroup::", flush=True)
        if result.returncode != 0:
            sys.exit(f"Step failed: {step}")
    print("Site maintenance complete.")


if __name__ == "__main__":
    main()

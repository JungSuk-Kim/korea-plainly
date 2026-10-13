#!/usr/bin/env python3
"""Credited cover photos and map links for the regional articles.

For every regional article (content/published.json entries with a place_name):

  1. Photo. Looks for a freely licensed Wikimedia Commons photo of the place
     first. If there is none, it uses the place's Google Maps photo, credited to
     its author as Google requires. The photo replaces the article's existing
     cover file (same file name), so every page that shows it updates.
  2. Credit line under the cover photo.
  3. A Naver Map link next to the Google Maps link in "Useful links".

Choices are stored in content/regional_photos.json. Add "retry": true to an
entry to look again, or {"skip": true} to leave an article alone.

Searching and downloading only happen when KP_FETCH_PHOTOS=1; Google needs
GOOGLE_PLACES_API_KEY. At most MAX_FETCH articles are fetched per run.
"""
import html
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_photos import search_commons, download, sources_in_use, USER_AGENT  # noqa: E402

STATE_PATH = ROOT / "content" / "regional_photos.json"
FETCH = os.environ.get("KP_FETCH_PHOTOS") == "1"
GOOGLE_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
MAX_FETCH = 12
# Places often share a name with their subway station; skip station photos
# unless the place itself is a station or terminal.
TRANSIT_PHOTO = re.compile(r"(?i)\b(station|stn|platform|namecard|name card|signboard|sign|exit|line \d|subway|metro)\b")
GENERIC = {"cafe", "coffee", "hotel", "restaurant", "the", "and", "korea", "korean", "seoul", "busan",
           "jeju", "temple", "beach", "market", "museum", "park", "village", "street", "branch", "city"}


def read(p):
    return p.read_bytes().decode("utf-8")


def distinctive_words(name):
    return [w for w in re.findall(r"[A-Za-z]+", name) if len(w) > 3 and w.lower() not in GENERIC]


def google_photo(place, region):
    import requests
    r = requests.post("https://places.googleapis.com/v1/places:searchText", timeout=30, headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": GOOGLE_KEY,
        "X-Goog-FieldMask": "places.displayName,places.photos"},
        json={"textQuery": f"{place} {region}", "languageCode": "en", "regionCode": "KR", "pageSize": 1})
    r.raise_for_status()
    places = r.json().get("places") or []
    photos = (places[0].get("photos") or []) if places else []
    if not photos:
        return None
    ph = photos[0]
    authors = ph.get("authorAttributions") or []
    author = (authors[0].get("displayName") or "").strip() if authors else ""
    return {"url": f"https://places.googleapis.com/v1/{ph['name']}/media?maxWidthPx=1600&maxHeightPx=1200&key={GOOGLE_KEY}",
            "credit": f"Photo: {author} via Google Maps" if author else "Photo: Google Maps",
            "source": authors[0].get("uri", "") if authors else ""}


def apply(page_path, entry, place, region):
    s = read(page_path)
    nl = "\r\n" if "\r\n" in s else "\n"
    new = re.sub(r'[ \t]*<p class="photo-credit"[^>]*>.*?</p>\r?\n?', "", s, flags=re.S)
    if entry.get("credit"):
        text = html.escape(entry["credit"])
        if entry.get("source"):
            text = f'<a href="{html.escape(entry["source"], quote=True)}" target="_blank" rel="noopener nofollow">{text}</a>'
        credit = (f'<p class="photo-credit" data-kp="photo-credit" style="font-size:12px;color:#777;margin:-20px 0 24px">'
                  f'{text}</p>')
        new = re.sub(r'(<img\b[^>]*class="cover"[^>]*>)', lambda m: m.group(1) + nl + credit, new, count=1, flags=re.S)
    if "map.naver.com" not in new:
        naver = (f'<li><a href="https://map.naver.com/p/search/{quote(place + " " + region)}" '
                 f'target="_blank" rel="noopener">Naver Map</a></li>')
        new = re.sub(r'(<section class="useful-links"><h2>Useful links</h2><ul>)', lambda m: m.group(1) + naver, new, count=1)
    if new != s:
        page_path.write_bytes(new.encode("utf-8"))


def main():
    published = [p for p in json.loads(read(ROOT / "content" / "published.json")) if isinstance(p, dict) and p.get("place_name")]
    state = json.loads(read(STATE_PATH)) if STATE_PATH.exists() else {}
    fetched = 0
    for p in published:
        slug, place, region, image = p["slug"], p["place_name"], p.get("region", ""), p.get("image")
        page = ROOT / f"{slug}.html"
        if not page.exists() or not image:
            continue
        entry = state.get(slug, {})
        if entry.get("skip"):
            continue
        done = entry.get("source_type") and not entry.get("retry")
        if not done and FETCH and fetched < MAX_FETCH:
            try:
                reject = list(entry.get("reject", []))
                if entry.get("retry") and entry.get("source"):
                    reject.append(entry["source"])
                avoid = None if re.search(r"(?i)station|terminal|airport", place) else TRANSIT_PHOTO
                found = search_commons(f"{place} {region}", reject + sorted(sources_in_use(slug)), require=distinctive_words(place) or [place], avoid=avoid)
                kind = "wikimedia"
                if not found and GOOGLE_KEY:
                    found, kind = google_photo(place, region), "google"
                elif not found and p.get("image_credit") and not entry.get("source_type"):
                    # untouched new article: its file is still the Google photo it was published with
                    found, kind = {"credit": p["image_credit"], "source": "", "url": None}, "google"
                if found:
                    if found.get("url"):
                        download(found["url"], ROOT / image)
                    entry = {"source_type": kind, "credit": found["credit"], "source": found.get("source", "")}
                    if reject:
                        entry["reject"] = sorted(set(reject))
                    fetched += 1
                    state[slug] = entry
            except Exception as e:  # network trouble: try again next run
                print(f"regional_photos: {slug}: {e}")
        apply(page, state.get(slug, {}), place, region)
    STATE_PATH.write_text(json.dumps(dict(sorted(state.items())), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    left = sum(1 for p in published if not state.get(p["slug"], {}).get("source_type"))
    print(f"regional_photos: {fetched} photo(s) set this run, {left} article(s) still without a credited photo")


if __name__ == "__main__":
    main()

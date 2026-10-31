#!/usr/bin/env python3
"""Credited cover photos and map links for the regional articles.

For every regional article (content/published.json entries with a place_name):

  1. Photo. Looks for a freely licensed Wikimedia Commons photo of the place.
     If there is none, the cover becomes a plain Korea Plainly title card (place
     name and region). Google Maps photos are no longer used (Oct 2026: they are
     uploaded by businesses and visitors, so a credit line is not a licence).
     The photo replaces the article's existing cover file (same file name), so
     every page that shows it updates.
  2. Credit line under the cover photo.
  3. A Naver Map link next to the Google Maps link in "Useful links".

Choices are stored in content/regional_photos.json. Add "retry": true to an
entry to look again, or {"skip": true} to leave an article alone.

Searching and downloading only happen when KP_FETCH_PHOTOS=1. At most
MAX_FETCH articles are fetched per run.
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


NAVY, RED, CREAM = (23, 36, 60), (201, 65, 58), (247, 245, 239)
FONTS = Path(__file__).resolve().parent / "fonts"


def title_card(path, place, region, category=""):
    """A plain cover for places with no freely licensed photo: the place name on the site's navy."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    f = lambda size, bold=True: ImageFont.truetype(str(FONTS / ("Carlito-Bold.ttf" if bold else "Carlito-Regular.ttf")), size)
    kicker = " · ".join(x for x in (region.upper(), category.upper()) if x)
    d.rectangle([90, 250, 98, 550], fill=RED)
    d.text((130, 255), kicker, font=f(40), fill=(200, 205, 215))
    words, lines, line = re.sub(r"[^\x00-\x7f]+", "", place).split(), [], ""
    for w in words:
        if line and d.textlength(f"{line} {w}", font=f(92)) > W - 230:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    lines.append(line)
    y = 330
    for ln in lines[:3]:
        d.text((130, y), ln, font=f(92), fill=CREAM)
        y += 104
    d.text((130, H - 120), "Korea Plainly", font=f(38, False), fill=(200, 205, 215))
    img.save(path, quality=90)


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
                if not found:   # no free photo: a plain title card instead of anyone else's photo
                    title_card(ROOT / image, place if place.isascii() else p.get("title", place).split(":")[0], region,
                               p.get("category", ""))
                    found, kind = {"credit": "", "source": "", "url": None}, "card"
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

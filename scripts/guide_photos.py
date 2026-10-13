#!/usr/bin/env python3
"""Real, credited photos for the general guides (the cards on guides.html).

Guides written by the publishing bot start with an SVG text card as their
thumbnail and one of four shared stock photos as their cover. This step
replaces both with a freely licensed photo from Wikimedia Commons:

  * the card on guides.html, the cover image, og:image and twitter:image all use
    photo-<slug>.jpg;
  * a credit line (author, licence, link) appears under the cover.

Every decision is stored in content/guide_photos.json, so you can review it:

  "korean-atm-guide": {"file": "photo-korean-atm-guide.jpg", "credit": "...",
                       "source": "https://commons.wikimedia.org/...", "query": "ATM Seoul"}

  * Don't like a photo? Add "retry": true to its entry (and optionally a new
    "query"). The next run looks for another photo, never re-picks a rejected
    one ("reject" list), and keeps the current photo if nothing better is found.
  * Keep the SVG card for a guide: {"skip": true}.

Searching and downloading only happens when KP_FETCH_PHOTOS=1 (set in the
GitHub workflows). Without it the script only (re)applies stored photos.
Guides that already have a JPG thumbnail keep it, but their share image
(og:image) is switched from the shared stock photo to that thumbnail.
"""
import html
import io
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://korea-plainly.com"
STATE_PATH = ROOT / "content" / "guide_photos.json"
SHARED_STOCK = {"street.jpg", "seoul.jpg", "food.jpg", "store.jpg"}
FETCH = os.environ.get("KP_FETCH_PHOTOS") == "1"
USER_AGENT = "KoreaPlainlyBot/1.0 (https://korea-plainly.com)"

# Hand-picked search words for the guides that exist today. New guides fall
# back to words from their title.
QUERIES = {
    "seollal-travel-tips": "Seollal Korea hanbok",
    "christmas-new-year-seoul": "Myeongdong Christmas Seoul",
    "korea-ski-resorts-guide": "Yongpyong ski resort Korea",
    "korea-winter-travel-guide": "Gyeongbokgung snow Seoul",
    "day-trips-from-seoul": "Hwaseong Fortress Suwon",
    "gyeongju-1-day-itinerary": "Donggung Palace Wolji Pond Gyeongju",
    "jeju-3-day-itinerary": "Seongsan Ilchulbong Jeju",
    "korea-weather-by-season": "Seoul cherry blossom season",
    "korea-entry-k-eta-e-arrival": "Incheon International Airport terminal",
    "korea-tax-refund-guide": "Myeongdong shopping street Seoul",
    "korea-autumn-foliage-2026": "autumn foliage Korea maple",
    "seoul-3-day-itinerary": "Bukchon Hanok Village Seoul",
    "busan-1-day-itinerary": "Haeundae Beach Busan",
    "korean-convenience-store-tips": "convenience store Seoul",
    "korea-recycling-guide": "recycling bins Korea",
    "korean-atm-guide": "ATM Seoul",
    "korea-transit-card-guide": "T-money card",
    "seoul-bus-guide": "Seoul city bus",
    "best-time-seoul-attractions": "Gyeongbokgung Palace visitors",
    "korean-food-delivery-guide": "delivery motorcycle Seoul",
    "korean-convenience-stores-compared": "convenience store Korea",
    "korean-cafe-menu-basics": "cafe Seoul",
    "kakaotalk-korea-guide": "smartphone Seoul",
    "arriving-in-korea-checklist": "Incheon International Airport",
}
STOP = {"a", "an", "the", "to", "in", "of", "for", "and", "how", "what", "is",
        "are", "you", "your", "do", "need", "know", "before", "using", "use",
        "works", "visitors", "foreigner", "foreigners", "guide", "simple",
        "korean", "korea", "basics", "explained", "compared", "things", "best",
        "with", "from", "when", "where", "why", "can", "will", "should", "first", "time"}
# The file title must clearly be about Korea (place names count).
# The file title must name Korea or a Korean place. "Korean" alone doesn't count: a
# "Korean dogwood" in New Jersey or a Korean restaurant abroad is not a photo of Korea.
KOREA_WORDS = re.compile(r"(?i)(korea(?!n)|seoul|busan|jeju|incheon|daegu|daejeon|gwangju|gyeong|jeonju|gangneung|"
                         r"hanok|myeong|gangnam|hongdae|insadong|jongno|itaewon|namsan|t-?money|kakao|hangul|"
                         r"naejang|seorak|bukhan|halla|seongsan|udo\b|suwon|hwaseong|nami island|gapyeong|chuncheon|"
                         r"yeouido|bulguksa|sokcho|yeosu|andong|tongyeong|haeundae|gwangalli|cheonggye|panmunjom|"
                         r"\bdmz\b|seogwipo|aewol|odaesan|jirisan|deoksugung|changdeokgung|pyeongchang|yongpyong|high1|jeongseon|"
                         r"hongcheon|vivaldi|alpensia|konjiam|gangwon)")
OLD_PHOTO = re.compile(r"\b(18|19)\d\d\b|\b200[0-4]\b")
BAD_TITLE = re.compile(r"(?i)\b(map|logo|icon|diagram|chart|flag|seal|emblem|screenshot|signature|symbol|coat of arms|poster|signboard|sign|signage|way ?out|exit|nameplate|plaque)\b")
GOOD_LICENCE = re.compile(r"(?i)^(cc0|public domain|pd\b|cc by(-sa)? \d)")


def read(p):
    return p.read_bytes().decode("utf-8")


def write(p, s):
    p.write_bytes(s.encode("utf-8"))


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def guide_cards(guides_html):
    # cards come as <div class="guide-image" style="background-image:url('X')"> from the
    # publishing bot, and as <div class="guide-image" data-thumb="X"> after lazy_cards.py
    pattern = (r'<a\s+class="guide-card"\s+href="([^"]+)\.html"[^>]*>\s*'
               r'<div\s+class="guide-image"\s+(?:style="background-image:url\(\'([^\']+)\'\)"|data-thumb="([^"]+)")')
    return [(slug, a or b) for slug, a, b in re.findall(pattern, guides_html)]


def default_query(title):
    words = [w for w in re.findall(r"[A-Za-z-]+", title) if len(w) > 2 and w.lower() not in STOP]
    return " ".join(words[:3] + ["Korea"])


# ---------------------------------------------------------------- fetching

def search_commons(query, reject=(), require=(), avoid=None):
    """Best freely licensed JPEG for `query`; `require`: the file title must contain one of these words."""
    import requests
    r = requests.get("https://commons.wikimedia.org/w/api.php", timeout=30,
                     headers={"User-Agent": USER_AGENT}, params={
                         "action": "query", "format": "json", "generator": "search",
                         "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6,
                         "gsrlimit": 25, "prop": "imageinfo",
                         "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600})
    r.raise_for_status()
    words = {w.lower() for w in re.findall(r"[A-Za-z]+", query) if len(w) > 2}
    best = None
    for page in (r.json().get("query", {}).get("pages", {}) or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        title = page.get("title", "")
        meta = info.get("extmetadata") or {}
        licence = clean((meta.get("LicenseShortName") or {}).get("value"))
        w, h = info.get("width") or 0, info.get("height") or 0
        if info.get("mime") != "image/jpeg" or w < 1200 or w < h * 1.2:
            continue
        if not GOOD_LICENCE.match(licence) or BAD_TITLE.search(title) or OLD_PHOTO.search(title):
            continue
        if not KOREA_WORDS.search(title) or info.get("descriptionurl", "") in reject:
            continue
        t = title.lower()
        title_words = max(len(re.findall(r"[a-z]+", t)), 1)
        hits = sum(word in t for word in words)
        if avoid is not None and avoid.search(title):
            continue
        if hits < 1 or (require and not any(r.lower() in t for r in require)):
            continue
        # more query words, and fewer unrelated words, is better
        score = hits + hits / title_words
        if not best or score > best[0]:
            artist = clean((meta.get("Artist") or {}).get("value")) or "Unknown author"
            best = (score, {
                "url": info.get("thumburl") or info.get("url"),
                "source": info.get("descriptionurl", ""),
                "credit": f"Photo: {artist}, {licence}, via Wikimedia Commons",
            })
    return best[1] if best else None


def sources_in_use(except_key=None):
    """Every photo source already used by another guide or regional article, so no photo appears twice."""
    used = set()
    for name in ("guide_photos.json", "regional_photos.json"):
        path = ROOT / "content" / name
        if path.exists():
            for key, entry in json.loads(path.read_text(encoding="utf-8")).items():
                if key != except_key and isinstance(entry, dict) and entry.get("source"):
                    used.add(entry["source"])
    return used


def download(url, path):
    import requests
    from PIL import Image, ImageOps
    r = requests.get(url, timeout=60, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    with Image.open(io.BytesIO(r.content)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        if im.width > 1600:
            im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
        im.save(path, "JPEG", quality=82, optimize=True, progressive=True, comment=b"kp-optimized")


# ---------------------------------------------------------------- applying

def set_share_image(s, image):
    url = f"{BASE}/{image}"
    for prop in (r'property=["\']og:image["\']', r'name=["\']twitter:image["\']'):
        s = re.sub(r'(<meta\s+[^>]*' + prop + r'[^>]*content=")[^"]*(")', lambda m: m.group(1) + url + m.group(2), s, flags=re.I)
        s = re.sub(r'(<meta\s+content=")[^"]*("[^>]*' + prop + r')', lambda m: m.group(1) + url + m.group(2), s, flags=re.I)
    return s


def apply_photo(slug, entry, guides_html):
    photo = entry["file"]
    card = re.search(r'<a\s+class="guide-card"\s+href="' + re.escape(slug) + r'\.html"[^>]*>.*?</a>', guides_html, re.S)
    if card:
        thumb = re.search(r'(?:background-image:url\(\'|data-thumb=")([^\'"]+)', card.group(0))
        if thumb and thumb.group(1) != photo:
            guides_html = guides_html.replace(card.group(0), card.group(0).replace(thumb.group(1), photo))

    page = ROOT / f"{slug}.html"
    s = read(page)
    nl = "\r\n" if "\r\n" in s else "\n"
    new = re.sub(r'(<img\b[^>]*class="cover"[^>]*src=")([^"]+)(")', lambda m: m.group(1) + photo + m.group(3), s, count=1, flags=re.S)
    new = re.sub(r'(<img\s+class="cover"\s+src=")([^"]+)(")', lambda m: m.group(1) + photo + m.group(3), new, count=1, flags=re.S)
    new = set_share_image(new, photo)
    new = re.sub(r'[ \t]*<p class="photo-credit" data-kp="photo-credit".*?</p>\r?\n?', "", new, flags=re.S)
    if entry.get("credit"):
        text = html.escape(entry["credit"])
        if entry.get("source"):
            text = f'<a href="{html.escape(entry["source"], quote=True)}" target="_blank" rel="noopener nofollow" style="color:inherit">{text}</a>'
        credit = f'<p class="photo-credit" data-kp="photo-credit" style="font-size:12px;color:#777;margin:-18px 0 24px">{text}</p>'
        new = re.sub(r'(<img\b[^>]*class="cover"[^>]*>)', lambda m: m.group(1) + nl + credit, new, count=1, flags=re.S)
    if new != s:
        write(page, new)
    return guides_html


def main():
    guides_path = ROOT / "guides.html"
    guides_html = read(guides_path)
    state = json.loads(read(STATE_PATH)) if STATE_PATH.exists() else {}
    fetched = applied = 0

    for slug, thumb in guide_cards(guides_html):
        page = ROOT / f"{slug}.html"
        if not page.exists():
            continue
        entry = state.get(slug, {})
        if entry.get("skip"):
            continue

        if not thumb.lower().endswith(".svg") and not entry.get("file"):
            # Already has a real thumbnail: only stop sharing the stock photo.
            s = read(page)
            og = re.search(r'property=["\']og:image["\'][^>]*content="[^"]*/([^"/]+)"', s, re.S)
            if og and og.group(1) in SHARED_STOCK and (ROOT / thumb).exists():
                write(page, set_share_image(s, thumb))
            continue

        has_photo = entry.get("file") and (ROOT / entry["file"]).exists()
        if has_photo and not (FETCH and entry.get("retry")):
            guides_html = apply_photo(slug, entry, guides_html)
            applied += 1
            continue

        if not FETCH or (entry.get("none") and not entry.get("retry")):
            continue
        title = clean((re.search(r"<h1[^>]*>(.*?)</h1>", read(page), re.S) or [None, slug])[1])
        query = entry.get("query") or QUERIES.get(slug) or default_query(title)
        try:
            reject = list(entry.get("reject", []))
            if has_photo and entry.get("source"):
                reject.append(entry["source"])  # asked for a different photo
            found = search_commons(query, reject + sorted(sources_in_use(slug)))
            if found:
                photo = f"photo-{slug}.jpg"
                download(found["url"], ROOT / photo)
                entry = {"file": photo, "credit": found["credit"], "source": found["source"], "query": query}
                if reject:
                    entry["reject"] = sorted(set(reject))
                guides_html = apply_photo(slug, entry, guides_html)
                fetched += 1
            elif has_photo:
                entry = {k: v for k, v in entry.items() if k != "retry"}  # keep the current photo
                guides_html = apply_photo(slug, entry, guides_html)
            else:
                entry = {"none": True, "query": query}
                if reject:
                    entry["reject"] = sorted(set(reject))
        except Exception as e:  # network trouble: try again next run
            print(f"guide_photos: {slug}: {e}")
            continue
        state[slug] = entry

    write(guides_path, guides_html)
    write(STATE_PATH, json.dumps(dict(sorted(state.items())), indent=2, ensure_ascii=False) + "\n")
    print(f"guide_photos: {fetched} new photo(s), {applied} applied")


if __name__ == "__main__":
    main()

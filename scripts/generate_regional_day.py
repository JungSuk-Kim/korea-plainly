import json
import os
import re
import html
import hashlib
from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime, timezone

import requests
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "content" / "region_rotation.json"
PUBLISHED_PATH = ROOT / "content" / "published.json"
QUERIES_PATH = ROOT / "content" / "regional_queries.json"

GOOGLE_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL = os.environ.get("OPENAI_MODEL", "gpt-6-luna").strip()

if not GOOGLE_KEY:
    raise SystemExit("Missing GOOGLE_PLACES_API_KEY")
if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    raise SystemExit("Missing NAVER_CLIENT_ID / NAVER_CLIENT_SECRET")
if not OPENAI_KEY:
    raise SystemExit("Missing OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
published = json.loads(PUBLISHED_PATH.read_text(encoding="utf-8")) if PUBLISHED_PATH.exists() else []
queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))

regions = state["regions"]
categories = state["categories"]
idx = int(state.get("current_region_index", 0))
round_no = int(state.get("current_round", 1))
region = regions[idx]
region_name = region["name"]

published_slugs = {x.get("slug") for x in published if isinstance(x, dict)}
used_places = {str(x.get("place_name","")).strip().lower() for x in published if isinstance(x, dict) and x.get("place_name")}
used_topics = {str(x.get("title","")).strip().lower() for x in published if isinstance(x, dict) and x.get("title")}

def clean_text(s):
    return re.sub(r"\s+", " ", html.unescape(str(s or ""))).strip()

def google_text_search(query):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_KEY,
        "X-Goog-FieldMask": ",".join([
            "places.id","places.displayName","places.formattedAddress",
            "places.rating","places.userRatingCount","places.websiteUri",
            "places.googleMapsUri","places.regularOpeningHours",
            "places.priceLevel","places.types","places.photos",
            "places.primaryType","places.primaryTypeDisplayName","places.editorialSummary"
        ])
    }
    r = requests.post(url, headers=headers, json={
        "textQuery": query,
        "languageCode": "en",
        "regionCode": "KR",
        "pageSize": 10
    }, timeout=30)
    r.raise_for_status()
    return r.json().get("places", [])

def naver_local(query):
    url = "https://naverapihub.apigw.ntruss.com/search/v1/local"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    r = requests.get(url, headers=headers, params={
        "query": query,
        "display": 5,
        "start": 1,
        "sort": "comment",
        "format": "json"
    }, timeout=30)
    r.raise_for_status()
    return r.json().get("items", [])


def naver_blog(query):
    url = "https://naverapihub.apigw.ntruss.com/search/v1/blog"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    r = requests.get(url, headers=headers, params={
        "query": query,
        "display": 5,
        "start": 1,
        "sort": "date",
        "format": "json"
    }, timeout=30)
    r.raise_for_status()
    return r.json().get("items", [])


def norm_name(s):
    s = re.sub(r"<[^>]+>", "", str(s or ""))
    s = clean_text(s).lower()
    return re.sub(r"[^a-z0-9가-힣]+", "", s)

# What a place must look like (Google place types) to fit a category. Categories
# not listed accept any place. A place that doesn't fit is only used when nothing
# else is left, which stops a barbecue restaurant being written up as a cafe.
CATEGORY_TYPES = {
    "food": lambda t: any(x.endswith("restaurant") or x in ("food_court", "meal_takeaway") for x in t),
    "cafe": lambda t: any(x in ("cafe", "coffee_shop", "bakery", "tea_house", "dessert_shop", "cafeteria") for x in t),
    "stay": lambda t: any(x in ("lodging", "hotel", "resort_hotel", "guest_house", "hostel", "motel", "bed_and_breakfast") for x in t),
    "shopping": lambda t: any(("store" in x or "mall" in x or "market" in x or x == "shopping_mall") for x in t),
}


def place_info(place, n_match=False):
    """The facts about one Google Places result that the writer is given."""
    name = clean_text((place.get("displayName") or {}).get("text"))
    blogs = naver_blog(f"{region_name} {name}")
    return {
        "name": name,
        "address": clean_text(place.get("formattedAddress")),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "website": place.get("websiteUri"),
        "google_maps": place.get("googleMapsUri"),
        "opening_hours": place.get("regularOpeningHours"),
        "price_level": place.get("priceLevel"),
        "types": place.get("types", []),
        "kind": clean_text((place.get("primaryTypeDisplayName") or {}).get("text")) or place.get("primaryType", ""),
        "summary": clean_text((place.get("editorialSummary") or {}).get("text")),
        "naver_match": bool(n_match),
        "naver_results": [{"title": clean_text(x.get("title")), "description": clean_text(x.get("description"))}
                          for x in blogs[:5]],
        "google_place_id": place.get("id"),
        "photos": place.get("photos", [])
    }


# Places visitors don't travel for: single-brand shops, airports, offices.
AVOID_TYPES = {"clothing_store", "shoe_store", "cell_phone_store", "electronics_store", "furniture_store",
               "hardware_store", "home_goods_store", "jewelry_store", "airport", "corporate_office",
               "car_dealer", "gas_station", "convenience_store", "supermarket", "grocery_store"}


def query_list(cat_key):
    """The searches for a category, starting with the one for this round."""
    cfg = queries[cat_key]
    qs = cfg.get("queries") or [cfg["query"]]
    start = (round_no - 1) % len(qs)
    return [q.format(region=region_name) for q in qs[start:] + qs[:start]]


def choose_place(category, query):
    google = google_text_search(query)
    if not google:
        raise RuntimeError(f"No Google Places result for: {query}")

    naver = naver_local(query)
    naver_names = {norm_name(x.get("title")) for x in naver}
    candidates = []

    for p in google:
        name = clean_text((p.get("displayName") or {}).get("text"))
        if not name:
            continue
        if norm_name(name) in {norm_name(x) for x in used_places}:
            continue

        g_rating = float(p.get("rating") or 0)
        g_count = int(p.get("userRatingCount") or 0)
        n_match = 1 if norm_name(name) in naver_names else 0

        # Prefer places with meaningful Google review volume, a strong rating,
        # and a matching Naver local result. Do not treat Naver data as a
        # numeric rating because the public Naver Search API does not expose it.
        score = (g_rating * 20) + min(g_count, 5000) / 100 + n_match * 18
        fits = CATEGORY_TYPES.get(category)
        if fits:
            score += 25 if fits(p.get("types", [])) else -60
        if AVOID_TYPES & set(p.get("types", [])) and not (category == "shopping" and "shopping_mall" in p.get("types", [])):
            continue
        candidates.append((score, p, n_match))

    if not candidates:
        raise RuntimeError(f"No unused place found for: {query}")

    candidates.sort(key=lambda x: x[0], reverse=True)
    score, place, n_match = candidates[0]
    return place_info(place, n_match)

def google_place_image(place):
    photos = place.get('photos') or []
    if not photos:
        return None
    photo_name = photos[0].get('name')
    if not photo_name:
        return None
    authors = photos[0].get('authorAttributions') or []
    author = clean_text(authors[0].get('displayName')) if authors else ''
    credit = f"Photo: {author} via Google Maps" if author else "Photo: Google Maps"
    return {'url': f'https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=1600&maxHeightPx=1200&key={GOOGLE_KEY}',
            'title': 'Google Places photo', 'credit': credit,
            'credit_url': authors[0].get('uri', '') if authors else ''}

def wikimedia_image(query):
    api = "https://commons.wikimedia.org/w/api.php"
    r = requests.get(api, params={
        "action":"query","generator":"search","gsrsearch":query,
        "gsrnamespace":6,"gsrlimit":8,"prop":"imageinfo",
        "iiprop":"url|mime|size|extmetadata","iiurlwidth":1600,"format":"json"
    }, timeout=30)
    if r.status_code != 200:
        return None
    pages = r.json().get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        mime = info.get("mime","")
        meta = info.get("extmetadata") or {}
        licence = clean_text(re.sub(r"<[^>]+>", " ", (meta.get("LicenseShortName") or {}).get("value", "")))
        if not re.match(r"(?i)(cc0|public domain|pd|cc by(-sa)? \d)", licence):
            continue  # skip files whose licence does not allow reuse with credit
        artist = clean_text(re.sub(r"<[^>]+>", " ", (meta.get("Artist") or {}).get("value", ""))) or "Unknown author"
        if url and mime in ("image/jpeg", "image/png") and (info.get("width") or 0) >= 1000:
            return {"url": url, "title": page.get("title",""),
                    "credit": f"Photo: {artist}, {licence}, via Wikimedia Commons",
                    "credit_url": info.get("descriptionurl", "")}
    return None

def download_image(info, slug):
    if not info:
        return None
    img_dir = ROOT
    ext = ".jpg"
    if ".png" in info["url"].lower():
        ext = ".png"
    path = img_dir / f"regional-{slug}{ext}"
    r = requests.get(info["url"], timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path.name

def ask_openai(category, place):
    prompt = f"""
Write an English travel article for Korea Plainly, a guide for first-time foreign visitors to Korea.

Place: {place['name']}
What it is (Google): {place.get('kind') or ', '.join(place.get('types', [])[:4])}
Short description (Google, may be empty): {place.get('summary', '')}
Region: {region_name}
Address: {place['address']}
Google rating: {place['rating']} from {place['review_count']} reviews
Official website: {place['website']}
Site section it will appear in: {category}
Background notes from recent Korean blog posts (may be noisy; use only what is clearly about this place):
{json.dumps(place['naver_results'], ensure_ascii=False)}

Voice:
- Write as a knowledgeable local guide talking directly to the reader: confident, warm, plain English.
- Never talk about your sources or what is unknown. Do not write "search results", "Naver", "blog",
  "listing", "according to", "reviews suggest", "the information provided", "not confirmed",
  "we could not verify", "this article" or "this guide". Never say the place is "listed under" a category.
- If you don't know a detail, leave it out instead of hedging about it. At most one sentence in the
  whole article (in "Good to know") may tell readers to check current hours or prices on Naver Map.
- Describe the place as what it really is. If it doesn't match the site section, still write it
  accurately as what it is; the section name is only where the article is filed.

Facts:
- Do not invent prices, opening hours, specific menu items, awards, booking rules, or travel times.
- General, reliable context is welcome: the neighbourhood, what this kind of place is like in Korea,
  local customs, how to combine it with well-known nearby sights.
- Mention the Google rating and review count once, naturally.

Format:
- 700-1000 words.
- <h1>: the place name first, then a colon and a short, specific description; at most 60 characters.
- Then <div class="summary"><p><strong>At a glance:</strong> ...</p></div>. Its first sentence (under
  150 characters) says what the place is and why it's worth a visit; it is used as the search snippet.
- Clear <h2> sections a visitor needs: what it is, what to see, do or order, how to plan the visit
  (time needed, best time of day, what to pair it with nearby), and "Good to know".
- End with <section class="faq"><h2>FAQ</h2> and exactly 3 questions as <h3> with <p> answers.</section>
- No "Useful links" section; links are added automatically.
- Output ONLY the HTML, starting with <h1> and ending after the FAQ section.
"""
    r = client.responses.create(model=MODEL, input=prompt)
    return r.output_text.strip()

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:80] or "korea-place"

def render_article(category, place, body, image_name, slug, credit=None):
    title = re.search(r"<h1>(.*?)</h1>", body, re.S)
    title_text = clean_text(title.group(1)) if title else f"{place['name']} in {region_name}: A Practical Guide"
    body_text = re.sub(r"<h1[^>]*>.*?</h1>", " ", body, count=1, flags=re.S)
    description = clean_text(re.sub(r"<[^>]+>", " ", body_text))
    description = re.sub(r"^(At a glance|In brief|Summary):\s*", "", description)
    first = re.match(r"(.{40,155}?[.!?])(\s|$)", description)
    description = first.group(1) if first else description[:155].rsplit(" ", 1)[0]
    caption = ""
    if credit and credit.get("credit"):
        text = html.escape(credit["credit"])
        if credit.get("credit_url"):
            text = f'<a href="{html.escape(credit["credit_url"], quote=True)}" target="_blank" rel="noopener nofollow">{text}</a>'
        caption = f'<p class="photo-credit">{text}</p>'

    canonical = f"https://korea-plainly.com/{slug}.html"
    links = '<section class="useful-links"><h2>Useful links</h2><ul>'
    if place.get("google_maps"):
        links += f'<li><a href="{html.escape(place["google_maps"], quote=True)}" target="_blank" rel="noopener">Google Maps</a></li>'
    if place.get("website"):
        links += f'<li><a href="{html.escape(place["website"], quote=True)}" target="_blank" rel="noopener">Official website</a></li>'
    links += "</ul></section>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title_text)} | Korea Plainly</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title_text, quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="article">
<meta property="og:image" content="https://korea-plainly.com/{image_name}">
<meta property="og:site_name" content="Korea Plainly">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title_text, quote=True)}">
<meta name="twitter:description" content="{html.escape(description, quote=True)}">
<meta name="twitter:image" content="https://korea-plainly.com/{image_name}">
<style>
body{{margin:0;background:#f6f1e7;color:#17233b;font-family:Arial,sans-serif;line-height:1.75}}
main{{max-width:900px;margin:auto;padding:40px 22px 70px}}
article{{background:#fff;padding:30px;border-radius:18px}}
.cover{{width:100%;max-height:480px;object-fit:cover;border-radius:14px;margin:10px 0 6px}}
.photo-credit{{font-size:12px;color:#777;margin:0 0 24px}}.photo-credit a{{color:#777}}
h1{{font-size:clamp(34px,6vw,58px);line-height:1.08}}
h2{{margin-top:36px}}
.summary,.good-to-know,.useful-links{{padding:20px;background:#f4eee2;border-left:4px solid #b73535;margin:24px 0}}
a{{color:#b73535}}
</style>
</head>
<body><main><article>
<img class="cover" src="{html.escape(image_name, quote=True)}" alt="{html.escape(place['name'], quote=True)}">
{caption}
{body}
{links}
</article></main></body></html>"""

PER_DAY = int(state.get("categories_per_day") or len(categories))
OFFSET = int(state.get("current_category_offset", 0)) % len(categories)
TODAY = categories[OFFSET:OFFSET + PER_DAY]  # a few categories a day; the region changes after all of them


def main():
    made = []
    for category in TODAY:
        cat_key = category["slug"] if isinstance(category, dict) else str(category)
        place, last_error = None, None
        for query in query_list(cat_key):
            try:
                place = choose_place(cat_key, query)
                break
            except RuntimeError as e:  # every result already used: try the next search
                last_error = e
        if not place:
            raise last_error
        used_places.add(place["name"].strip().lower())  # one place per article, even within the same day
        title_hint = f"{place['name']} {region_name} {category['name'] if isinstance(category, dict) else cat_key}"
        # A Korean-only place name slugifies to nothing, which would leave "<region>-<category>": the URL of an
        # old category hub that maintain_site.py turns into a redirect, overwriting the article. In that case
        # write the article first and take the slug from the English part of its headline.
        body = None
        place_part = re.sub(r"[^a-z0-9]+", "-", place["name"].lower()).strip("-")
        if not place_part:
            body = ask_openai(category["name"], place)
            h1 = re.search(r"<h1>(.*?)</h1>", body, re.S)
            headline = clean_text(h1.group(1)) if h1 else ""
            place_part = re.sub(r"[^a-z0-9]+", "-", headline.split(":")[0].lower()).strip("-")[:50].strip("-") or "place"
        slug_base = slugify(f"{region['slug']}-{cat_key}-{place_part}")
        slug = slug_base
        n = 2
        while slug in published_slugs or (ROOT / f"{slug}.html").exists():
            slug = f"{slug_base}-{n}"
            n += 1

        # Wikimedia Commons only: Google Maps photos belong to the people who uploaded them (Oct 2026)
        image_info = wikimedia_image(f"{place['name']} {region_name} Korea")
        image_name = download_image(image_info, slug) if image_info else None
        credit = image_info if image_name else None

        if not image_name:
            raise RuntimeError(f"No usable place-specific image found for {place['name']}")

        body = body or ask_openai(category["name"], place)
        out = render_article(category["name"], place, body, image_name, slug, credit)
        (ROOT / f"{slug}.html").write_text(out, encoding="utf-8")

        published.append({
            "title": clean_text(re.search(r"<h1>(.*?)</h1>", body, re.S).group(1)) if re.search(r"<h1>(.*?)</h1>", body, re.S) else f"{place['name']} in {region_name}",
            "slug": slug,
            "category": category["name"],
            "region": region_name,
            "round": round_no,
            "place_name": place["name"],
            "address": place.get("address", ""),
            "google_rating": place["rating"],
            "google_review_count": place["review_count"],
            "naver_checked": True,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "image": image_name,
            "image_credit": (credit or {}).get("credit", "")
        })
        published_slugs.add(slug)
        made.append(slug)

    # Advance only after today's categories succeed; move to the next region once all are done.
    next_offset = OFFSET + PER_DAY
    if next_offset >= len(categories):
        state["current_category_offset"] = 0
        state["current_region_index"] = (idx + 1) % len(regions)
        if state["current_region_index"] == 0:
            state["current_round"] = round_no + 1
    else:
        state["current_category_offset"] = next_offset

    PUBLISHED_PATH.write_text(json.dumps(published, ensure_ascii=False, indent=2), encoding="utf-8")
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Published regional day: {region_name} / {', '.join(made)}")

if __name__ == "__main__":
    main()

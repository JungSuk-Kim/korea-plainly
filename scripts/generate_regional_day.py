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
            "places.priceLevel","places.types","places.photos"
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
        candidates.append((score, p, n_match))

    if not candidates:
        raise RuntimeError(f"No unused place found for: {query}")

    candidates.sort(key=lambda x: x[0], reverse=True)
    score, place, n_match = candidates[0]
    name = clean_text((place.get("displayName") or {}).get("text"))

    blogs = naver_blog(f"{region_name} {name}")
    naver_signals = [
        {
            "title": clean_text(x.get("title")),
            "description": clean_text(x.get("description")),
            "link": x.get("link", "")
        }
        for x in blogs[:5]
    ]

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
        "naver_match": bool(n_match),
        "naver_results": naver_signals,
        "google_place_id": place.get("id"),
        "photos": place.get("photos", [])
    }

def google_place_image(place):
    photos = place.get('photos') or []
    if not photos:
        return None
    photo_name = photos[0].get('name')
    if not photo_name:
        return None
    return {'url': f'https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=1600&maxHeightPx=1200&key={GOOGLE_KEY}', 'title': 'Google Places photo'}

def wikimedia_image(query):
    api = "https://commons.wikimedia.org/w/api.php"
    r = requests.get(api, params={
        "action":"query","generator":"search","gsrsearch":query,
        "gsrnamespace":6,"gsrlimit":8,"prop":"imageinfo",
        "iiprop":"url|mime|size","iiurlwidth":1600,"format":"json"
    }, timeout=30)
    if r.status_code != 200:
        return None
    pages = r.json().get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        mime = info.get("mime","")
        if url and mime.startswith("image/"):
            return {"url": url, "title": page.get("title","")}
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
Write a high-quality English travel article for Korea Plainly.

Region: {region_name}
Category: {category}
Place: {place['name']}
Address: {place['address']}
Google rating: {place['rating']}
Google review count: {place['review_count']}
Google Maps URL: {place['google_maps']}
Official website: {place['website']}
Naver local match: {place['naver_match']}
Naver recent search signals: {json.dumps(place['naver_results'], ensure_ascii=False)}

Rules:
- Do not invent facts, prices, opening hours, menus, awards, reservations, or transportation details.
- Treat Google rating/review count as current verification data.
- Mention that Naver was also checked only when useful; never invent a Naver rating.
- Make the article genuinely useful to foreign visitors.
- 700-1000 words.
- Strong H1 title.
- Include a short summary box.
- Use clear H2 sections.
- Include practical "Good to know" information.
- End with a concise FAQ of exactly 3 questions and answers.
- Include a "Useful links" section with Google Maps and official website when available.
- Output ONLY the article body HTML beginning with <h1> and ending before </article>.
"""
    r = client.responses.create(model=MODEL, input=prompt)
    return r.output_text.strip()

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:80] or "korea-place"

def render_article(category, place, body, image_name, slug):
    title = re.search(r"<h1>(.*?)</h1>", body, re.S)
    title_text = clean_text(title.group(1)) if title else f"{place['name']} in {region_name}: A Practical Guide"
    description = clean_text(re.sub(r"<[^>]+>", " ", body))[:155]
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
.cover{{width:100%;max-height:480px;object-fit:cover;border-radius:14px;margin:10px 0 28px}}
h1{{font-size:clamp(34px,6vw,58px);line-height:1.08}}
h2{{margin-top:36px}}
.summary,.good-to-know,.useful-links{{padding:20px;background:#f4eee2;border-left:4px solid #b73535;margin:24px 0}}
a{{color:#b73535}}
</style>
</head>
<body><main><article>
<img class="cover" src="{html.escape(image_name, quote=True)}" alt="{html.escape(place['name'], quote=True)}">
{body}
{links}
</article></main></body></html>"""

def main():
    made = []
    for category in categories:
        cat_key = category["slug"] if isinstance(category, dict) else str(category)
        cfg = queries[cat_key]
        query = cfg["query"].format(region=region_name)

        place = choose_place(cat_key, query)
        title_hint = f"{place['name']} {region_name} {category['name'] if isinstance(category, dict) else cat_key}"
        slug_base = slugify(f"{region['slug']}-{cat_key}-{place['name']}")
        slug = slug_base
        n = 2
        while slug in published_slugs or (ROOT / f"{slug}.html").exists():
            slug = f"{slug_base}-{n}"
            n += 1

        image_info = google_place_image(place)
        image_name = download_image(image_info, slug) if image_info else None

        if not image_name:
            image_info = wikimedia_image(f"{place['name']} {region_name} Korea")
            image_name = download_image(image_info, slug) if image_info else None

        if not image_name:
            raise RuntimeError(f"No usable place-specific image found for {place['name']}")

        body = ask_openai(category["name"], place)
        out = render_article(category["name"], place, body, image_name, slug)
        (ROOT / f"{slug}.html").write_text(out, encoding="utf-8")

        published.append({
            "title": clean_text(re.search(r"<h1>(.*?)</h1>", body, re.S).group(1)) if re.search(r"<h1>(.*?)</h1>", body, re.S) else f"{place['name']} in {region_name}",
            "slug": slug,
            "category": category["name"],
            "region": region_name,
            "round": round_no,
            "place_name": place["name"],
            "google_rating": place["rating"],
            "google_review_count": place["review_count"],
            "naver_checked": True,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "image": image_name
        })
        published_slugs.add(slug)
        made.append(slug)

    # Advance only after all categories succeed.
    state["current_region_index"] = (idx + 1) % len(regions)
    if state["current_region_index"] == 0:
        state["current_round"] = round_no + 1

    PUBLISHED_PATH.write_text(json.dumps(published, ensure_ascii=False, indent=2), encoding="utf-8")
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Published regional day: {region_name} / {', '.join(made)}")

if __name__ == "__main__":
    main()

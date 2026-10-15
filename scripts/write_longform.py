#!/usr/bin/env python3
"""Write the script for the next weekly long-form video from one of the site's articles.

    python scripts/write_longform.py            # next article in content/longform/queue.json
    python scripts/write_longform.py <slug>     # a given article

Writes content/longform/<slug>.json for scripts/make_longform.py and prints its path.
The script follows the Seoul video's shape: an intro, "before you go", one chapter per
day or topic with a map of the stops, mistakes to avoid, quick questions and a summary,
about 8-9 minutes of narration. Map stops are placed with OpenStreetMap's geocoder
(Nominatim); a stop it cannot find is left off the map rather than guessed.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from write_short import MODEL, article_text, read, site_photos  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LONG = ROOT / "content" / "longform"
QUEUE = LONG / "queue.json"
UPLOADS = ROOT / "content" / "shorts" / "uploads.json"
TRACKS = json.loads((ROOT / "content" / "shorts" / "music.json").read_text(encoding="utf-8"))["tracks"]
MIN_WORDS, MAX_WORDS = 1150, 1400     # about 8-9 minutes, so mid-roll ads are possible


def done():
    have = {p.stem for p in LONG.glob("*.json")} - {"queue"}
    if UPLOADS.exists():
        have |= {v.get("article") for v in json.loads(read(UPLOADS)).values() if v.get("format") == "long"}
    return have


def next_article():
    have = done()
    queue = json.loads(read(QUEUE)).get("queue", []) if QUEUE.exists() else []
    for slug in queue:
        if slug not in have and (ROOT / f"{slug}.html").exists():
            return slug
    guides = re.findall(r'<a\s+class="guide-card"\s+href="([^"]+)\.html"', read(ROOT / "guides.html"))
    for slug in guides:
        if slug not in have and "itinerary" in slug:
            return slug
    return None


PROMPT = """You write long-form YouTube videos (8-9 minutes, 16:9) for Korea Plainly, an English travel guide for
first-time visitors to Korea, narrated by a warm, plain-spoken local. Turn the article below into one video.

Return JSON only:
{{
 "title": "YouTube title, at most 70 characters, specific and searchable, e.g. 'Busan in One Day: An Easy East Coast Itinerary'",
 "intro": "two sentences for the video description",
 "hashtags": "#Place #KoreaTravel ... (4-6)",
 "thumb": {{"big": "at most 8 characters, e.g. '1 DAY'", "mid": "at most 10 characters, e.g. 'IN BUSAN'", "small": "at most 22 characters"}},
 "maps": {{"<map id>": {{"stops": [{{"name": "short label", "geocode": "full place name, district, city, South Korea"}}],
                        "route": true/false, "note": "short line, e.g. 'All on foot'"}}}},
 "chapters": [{{"name": "chapter name", "segments": [
    {{"voice": "...", "show": [VISUAL, ...], "label": {{"kicker": "DAY 1 · MORNING", "title": "Place name"}}}}
 ]}}]
}}
VISUAL is one of:
  {{"image": "<site photo file>"}}  |  {{"photo_query": "2-4 words naming the place, e.g. 'Haeundae Beach' or 'Haedong Yonggungsa'", "require": ["1-2 lowercase words that must be in the file title, e.g. 'haeundae'"]}}
  {{"map": "<map id>"}}  |  {{"card": {{"big": "SHORT CAPS", "title": "...", "sub": "..."}}}}  |  {{"list": {{"heading": "...", "items": ["...", "..."]}}}}

Structure (use these chapter names where they fit):
- "Intro": a hook (2-3 photos), a segment over an overview map of all stops, then a title card.
- "Before you go": 3-4 practical tips from the article (closing days, transport cards, map apps, where to stay, arriving).
- One chapter per day or per main part of the article, each starting with a title card and that part's route map,
  then one segment per stop, each with a "label" naming the place.
- "Getting around", "Mistakes to avoid" (a list of 3-4, then a segment explaining them), "Quick questions" (2-3 Q&A
  from the article's FAQ), "Summary" (a list recapping the plan, then a closing card with "korea-plainly.com" and
  the line "The full guide, with links for every stop, is on Korea Plainly. The link is in the description.
  If this helped, subscribe for more plain, practical guides to Korea."). The closing card is
  {{"card": {{"big": "KOREA PLAINLY", "title": "The full guide is in the description", "sub": "korea-plainly.com"}}}}.

Rules:
- Narration: {min_words}-{max_words} words in total. Short spoken sentences, numbers as spoken, no emoji.
  English letters only: never write Korean script (say "show the driver the name on your map app" instead).
- Use only facts from the article. Never invent prices, times or dates; for things that change say "check before you go".
- Every picture must show exactly what its segment talks about. Prefer a site photo when its description matches;
  otherwise a photo_query for that exact place. Never use one photo twice.
- Keep it visual: cards ONLY for each chapter's opening and the closing; never more than one card in a row.
  For practical tips use a fitting site photo (subway platforms, buses, taxis, airports, convenience stores, cafes,
  markets, crowds, payment counters are all in the list below). Every other segment needs a photo or a map.
- Keep segments short: at most 45 words each, with 2 visuals for segments over 25 words.
- "Quick questions": one segment per question, each with a photo of what the answer is about (a place, a train,
  a bus, a street, a market) and a label with kicker "Q&A" and the question as the title. No cards here.
- "Summary": the recap list, then the closing card. The list segment should also show one photo of the place.
- Maps: 2-6 stops each; "geocode" must be precise enough for OpenStreetMap to find (official name + district + city).
  Use "route": true only for stops visited in that order.
- Each segment has 1-3 visuals. Labels: kicker in capitals, at most 24 characters; title at most 34 characters.

Site photos (file: what it shows):
{photos}

Article: {title}
{text}
"""


def geocode(query, cache={}):
    """(lat, lon) from OpenStreetMap Nominatim, or None. At most one request a second (their usage policy)."""
    if query in cache:
        return cache[query]
    import requests
    time.sleep(1.1)
    r = requests.get("https://nominatim.openstreetmap.org/search", timeout=30,
                     params={"q": query, "format": "json", "limit": 1, "countrycodes": "kr"},
                     headers={"User-Agent": "KoreaPlainlyVideo/1.0 (https://korea-plainly.com; koreaplainly@gmail.com)"})
    hit = r.json()[0] if r.ok and r.json() else None
    cache[query] = (float(hit["lat"]), float(hit["lon"])) if hit else None
    return cache[query]


HANGUL = re.compile(r"\s*[(\[]?[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]+[)\]]?")


def short_query(q):
    """Commons search works best with a few words: drop 'in Busan, South Korea' style tails."""
    q = re.sub(r",.*$", "", q)
    q = re.sub(r"\b(in|at|on|of|the|and|near)\b.*$", "", q, flags=re.I).strip() or q
    return " ".join(q.split()[:4])


def clean(spec, photos):
    """Make the model's script safe to render: real site photos only, maps with found stops, no repeated photos,
    no Korean script (the subtitle font cannot show it, and the English voice cannot read it)."""
    used = set()
    for ch in spec["chapters"]:
        for seg in ch["segments"]:
            seg["voice"] = re.sub(r",\s*\.", ".", re.sub(r"\s+([,.])", r"\1", HANGUL.sub("", seg["voice"]))).strip()
            for v in seg.get("show", []):
                if "photo_query" in v:
                    v["photo_query"] = short_query(v["photo_query"])
                for key in ("card", "list"):
                    if key in v:
                        for k2 in ("big", "title", "sub", "heading"):
                            if isinstance(v[key].get(k2), str):
                                v[key][k2] = HANGUL.sub("", v[key][k2]).strip()
                        if key == "list":
                            v[key]["items"] = [HANGUL.sub("", i).strip() for i in v[key].get("items", [])]
    for m in spec.get("maps", {}).values():
        stops = []
        for s in m.get("stops", []):
            ll = geocode(s.get("geocode") or s["name"] + ", South Korea")
            if ll:
                stops.append({"name": s["name"][:28], "lat": ll[0], "lon": ll[1]})
            else:
                print(f"::warning::map stop not found: {s.get('geocode')}")
        m["stops"] = stops
    good_maps = {k for k, m in spec.get("maps", {}).items() if len(m["stops"]) >= 2}
    for ch in spec["chapters"]:
        for seg in ch["segments"]:
            show = []
            for v in seg.get("show", []):
                if "image" in v:
                    if v["image"] not in photos or v["image"] in used:
                        continue
                    used.add(v["image"])
                if "map" in v and v["map"] not in good_maps:
                    continue
                show.append(v)
            seg["show"] = show or [{"card": {"big": (seg.get("label") or {}).get("kicker", ch["name"]).upper()[:20],
                                              "title": (seg.get("label") or {}).get("title", ch["name"]), "sub": "Korea Plainly"}}]
            if seg.get("label"):
                seg["label"]["kicker"] = seg["label"].get("kicker", "").upper()[:24]
                seg["label"]["title"] = seg["label"]["title"][:34]
    return spec


def words(spec):
    return sum(len(s["voice"].split()) for c in spec["chapters"] for s in c["segments"])


def write(slug):
    from openai import OpenAI
    title, text, cover = article_text(slug)
    photos = site_photos()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = PROMPT.format(min_words=MIN_WORDS, max_words=MAX_WORDS, title=title, text=text,
                           photos="\n".join(f"{f}: {d}" for f, d in sorted(photos.items())))
    spec = None
    for attempt in range(2):
        r = client.responses.create(model=MODEL, input=prompt if not spec else
                                    prompt + f"\n\nYour last version had {words(spec)} words of narration. "
                                             f"Write it again with {MIN_WORDS}-{MAX_WORDS} words.")
        raw = r.output_text.strip()
        spec = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        if MIN_WORDS * 0.9 <= words(spec) <= MAX_WORDS * 1.1:
            break
    spec = clean(spec, photos)
    spec.update(article=slug, music=TRACKS[(len(done()) + 2) % len(TRACKS)],
                fallback=cover if cover in photos else "", thumb_photo=cover if cover in photos else None)
    if not spec["thumb_photo"]:
        spec.pop("thumb_photo")
    path = LONG / f"{slug}.json"
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{words(spec)} words", file=sys.stderr)
    return path


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else next_article()
    if not slug:
        print("no article left for a long-form video")
        return
    print(write(slug).relative_to(ROOT))


if __name__ == "__main__":
    main()

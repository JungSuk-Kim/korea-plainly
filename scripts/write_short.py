#!/usr/bin/env python3
"""Write the script for the next short video from one of the site's articles.

    python scripts/write_short.py            # next article in content/shorts/queue.json (or the newest guide not done)
    python scripts/write_short.py <slug>     # a given article

Writes content/shorts/<slug>.json for scripts/make_short.py and prints its path.
Every slide shows exactly what its narration names: a Wikimedia photo already on
the site whose title matches, or a Commons search for that place or thing.
Google Maps photos are never used in videos.
"""
import json
import os
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
SHORTS = ROOT / "content" / "shorts"
QUEUE = SHORTS / "queue.json"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-6-luna").strip()
MAX_WORDS = 100          # keeps the video under about 50 seconds
TRACKS = json.loads((SHORTS / "music.json").read_text(encoding="utf-8"))["tracks"]


def read(p):
    return Path(p).read_text(encoding="utf-8")


def done():
    """Articles that already have a short (a script, or an uploaded video)."""
    have = {p.stem for p in SHORTS.glob("*.json")} - {"queue", "music", "photos", "uploads"}
    for name in ("uploads.json",):
        p = SHORTS / name
        if p.exists():
            have |= {v.get("article", k) for k, v in json.loads(read(p)).items() if v.get("format") != "long"}
    return have


def next_article():
    have = done()
    queue = json.loads(read(QUEUE)).get("queue", []) if QUEUE.exists() else []
    for slug in queue:
        if slug not in have and (ROOT / f"{slug}.html").exists():
            return slug
    # then the newest hand-picked or generated guides (not regional place articles)
    guides = re.findall(r'<a\s+class="guide-card"\s+href="([^"]+)\.html"', read(ROOT / "guides.html"))
    dates = json.loads(read(ROOT / "content" / "page_dates.json"))
    for slug in sorted(set(guides), key=lambda s: dates.get(s + ".html", ""), reverse=True):
        if slug not in have and "kp-redirect" not in read(ROOT / f"{slug}.html"):
            return slug
    return None


def article_text(slug):
    s = read(ROOT / f"{slug}.html")
    title = unescape(re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S).group(1))).strip()
    body = re.search(r"<article.*?</article>", s, re.S)
    body = body.group(0) if body else s
    body = re.sub(r"<(script|style|nav)[^>]*>.*?</\1>", " ", body, flags=re.S)
    body = re.sub(r'<(section|div|aside)[^>]*class="(?:related-guides|kp-related)[^"]*".*?</\1>', " ", body, flags=re.S)
    body = re.sub(r"</(p|h2|h3|li)>", "\n", body)
    text = unescape(re.sub(r"<[^>]+>", " ", body))
    text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()
    cover = re.search(r'<img\b[^>]*class="cover"[^>]*\bsrc="([^"]+)"', s, re.S)
    return title, text[:7000], cover.group(1) if cover else None


def site_photos():
    """{file: what it shows} for the site's own Wikimedia photos (never the Google Maps ones)."""
    out = {}
    for name, prefix in (("guide_photos.json", None), ("regional_photos.json", "regional-")):
        for key, e in json.loads(read(ROOT / "content" / name)).items():
            if not isinstance(e, dict) or "commons.wikimedia.org" not in e.get("source", ""):
                continue
            f = e.get("file") or f"{prefix}{key}.jpg"
            if (ROOT / f).exists():
                shows = unquote(e["source"].rsplit("File:", 1)[-1]).rsplit(".", 1)[0]
                out[f] = shows.replace("_", " ").strip()
    return out


PROMPT = """You write vertical short videos (YouTube Shorts / Reels) for Korea Plainly, an English travel guide
for first-time visitors to Korea. Turn the article below into one short.

Return JSON only, in this form:
{{"title": "...", "hashtags": "#Korea #KoreaTravel ...", "slides": [
  {{"kicker": "...", "title": "...", "sub": "...", "voice": "...", "image": "..."}} or
  {{"kicker": "...", "title": "...", "sub": "...", "voice": "...", "photo_query": "...", "require": ["..."]}}
]}}

Rules:
- 6 to 8 slides. The first is a hook that makes a traveller stop scrolling (a question or a surprising, useful fact).
  Do not add an ending slide; it is added for you.
- Narration ("voice"): warm, plain spoken English, like a friendly local. All slides together at most {max_words} words.
  Short sentences. Spell numbers as they are spoken. No hashtags or emoji in the voice.
- On screen: "kicker" is 1-4 words in capitals (e.g. "DAY 1", "TIP 2", "BUSAN"); "title" at most 32 characters;
  "sub" at most 45 characters, one concrete tip. Use the article's facts only; never invent prices, hours or dates.
  Where something changes (hours, prices), say "check before you go" rather than a number.
- Every slide's picture must show exactly what that slide's narration is about.
  * If one of the site photos below clearly shows it, set "image" to that file name.
  * Otherwise set "photo_query" to a Wikimedia Commons search for that exact place or thing in Korea
    (e.g. "Haedong Yonggungsa Temple Busan", "Gamcheon Culture Village"), and "require" to 1-3 lowercase words
    that must appear in the photo's file title (e.g. ["haedong", "yonggungsa"]).
  * For a general tip with no single place, pick the site photo that fits best, or a concrete thing
    (e.g. "T-money card", "Incheon Airport arrivals hall").
- Never use the same site photo twice in one video.
- "title" of the video: at most 60 characters, plain and specific (e.g. "Busan in one day: a simple plan").
- "hashtags": 4-6 hashtags, the place first.

Site photos (file: what it shows):
{photos}

Article: {title}
{text}
"""


def write(slug):
    from openai import OpenAI
    title, text, cover = article_text(slug)
    photos = site_photos()
    prompt = PROMPT.format(max_words=MAX_WORDS, title=title, text=text,
                           photos="\n".join(f"{f}: {d}" for f, d in sorted(photos.items())))
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = client.responses.create(model=MODEL, input=prompt)
    raw = r.output_text.strip()
    spec = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    slides = []
    for s in spec["slides"][:8]:
        s = {k: v for k, v in s.items() if k in ("kicker", "title", "sub", "voice", "image", "photo_query", "require")}
        if s.get("image") and s["image"] not in photos:
            s.pop("image")  # not one of ours: search instead
            s.setdefault("photo_query", s["title"] + " Korea")
        if s.get("image") and s["image"] in {x.get("image") for x in slides}:
            s["photo_query"] = s.pop("image") and f"{s['title']} Korea"  # the same photo twice: find another
        if not s.get("image") and not s.get("photo_query"):
            s["image"] = cover if cover in photos else next(iter(photos))
        s["kicker"] = s.get("kicker", "").upper()[:28]
        slides.append(s)
    # keep the narration short: drop middle slides until it fits
    while sum(len(s["voice"].split()) for s in slides) > MAX_WORDS and len(slides) > 5:
        slides.pop(-2)
    slides.append({"end": True, "title": "Full guide and tips", "sub": "korea-plainly.com",
                   "voice": "The full guide is on Korea Plainly. Link in bio."})
    out = {"article": slug, "fallback": cover if cover in photos else slides[0].get("image", ""), "title": spec["title"][:90], "hashtags": spec.get("hashtags", "#Korea #KoreaTravel"),
           "music": TRACKS[len(done()) % len(TRACKS)], "slides": slides}
    path = SHORTS / f"{slug}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else next_article()
    if not slug:
        print("no article left for a short")
        return
    print(write(slug).relative_to(ROOT))


if __name__ == "__main__":
    main()

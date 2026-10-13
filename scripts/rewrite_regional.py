#!/usr/bin/env python3
"""Rewrite existing regional articles with the current writing rules.

    python scripts/rewrite_regional.py busan-cafe-waveon-coffee jeonju-food-ondam
    python scripts/rewrite_regional.py --flagged      # every article that talks about its sources

Keeps the URL, cover photo (its credit comes back from content/regional_photos.json),
publish date and region; fetches fresh place details from Google Places, asks the
writer again and updates the title in content/published.json. Run from the
"Rewrite regional articles" workflow, which has the API keys.
Articles that were merged from several (content/redirects.json) are skipped,
because a rewrite would drop the sections they gained.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_regional_day as g  # noqa: E402  (module only reads state on import)

ROOT = g.ROOT
META = re.compile(r"(?i)(search results?|supplied information|not confirmed|cannot confirm|can't confirm|"
                  r"is listed (here )?under|listed here|information (provided|available) (here|does)|surfaced|"
                  r"visitor account|naver search|no official website is listed|unverified)")


def article_text(slug):
    s = (ROOT / f"{slug}.html").read_text(encoding="utf-8")
    a = re.search(r"<article.*?</article>", s, re.S)
    a = re.sub(r'<section class="(kp-visit|useful-links|related-guides)".*?</section>', "", a.group(0) if a else "", flags=re.S)
    return s, re.sub(r"<[^>]+>", " ", a)


def merged_targets():
    path = ROOT / "content" / "redirects.json"
    return {v["to"][:-5] for v in json.loads(path.read_text(encoding="utf-8")).values()} if path.exists() else set()


def main():
    args = sys.argv[1:]
    entries = {p["slug"]: p for p in g.published if isinstance(p, dict) and p.get("place_name")}
    skip = merged_targets()
    if args == ["--flagged"]:
        slugs = [s for s in entries if (ROOT / f"{s}.html").exists() and len(META.findall(article_text(s)[1])) >= 2]
    else:
        slugs = [a for a in args if a in entries]
    slugs = [s for s in slugs if s not in skip]
    print("rewriting:", ", ".join(slugs) or "nothing")
    done = []
    for slug in slugs:
        entry = entries[slug]
        g.region_name = entry["region"]
        results = g.google_text_search(f"{entry['place_name']} {entry['region']}")
        match = [p for p in results if g.norm_name((p.get("displayName") or {}).get("text")) == g.norm_name(entry["place_name"])]
        if not (match or results):
            print(f"  {slug}: place not found, skipped")
            continue
        place = g.place_info((match or results)[0])
        place["name"] = entry["place_name"]
        page, _ = article_text(slug)
        cover = re.search(r'<img\b[^>]*class="cover"[^>]*src="([^"]+)"', page)
        image = cover.group(1) if cover else entry.get("image", "og-default.jpg")
        body = g.ask_openai(entry["category"], place)
        if not re.search(r"<h1>", body) or len(re.sub(r"<[^>]+>", " ", body).split()) < 400:
            print(f"  {slug}: writer returned too little, kept the old article")
            continue
        (ROOT / f"{slug}.html").write_text(g.render_article(entry["category"], place, body, image, slug), encoding="utf-8")
        h1 = re.search(r"<h1>(.*?)</h1>", body, re.S)
        if h1:
            entry["title"] = g.clean_text(re.sub(r"<[^>]+>", "", h1.group(1)))
        entry["address"] = place.get("address") or entry.get("address", "")
        entry["google_rating"] = place.get("rating") or entry.get("google_rating")
        entry["google_review_count"] = place.get("review_count") or entry.get("google_review_count")
        entry["rewritten_at"] = g.datetime.now(g.timezone.utc).isoformat()
        done.append(slug)
        print(f"  {slug}: rewritten")
    g.PUBLISHED_PATH.write_text(json.dumps(g.published, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"rewrote {len(done)} article(s)")


if __name__ == "__main__":
    main()

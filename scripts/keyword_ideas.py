#!/usr/bin/env python3
"""What foreign visitors type into Google about Korea, and which of those searches the site does not answer yet.

    python scripts/keyword_ideas.py        # writes content/keyword_ideas.json (needs open internet: run in Actions)

Google Trends has no public API, so this uses Google's search autocomplete, which lists the most common searches
that start with a phrase. Every seed in SEEDS (plus a few seasonal seeds for the coming months) is expanded,
and each suggestion is checked against the site's own page titles and descriptions:
  - "gaps": common searches no page title/description covers -> ideas for new guides (content/topics.json)
  - "retitle": searches whose main words appear only in a page's body or description, not its title -> title ideas
The morning proposals and the daily check read this file. Nothing here changes pages.
"""
import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "keyword_ideas.json"
KST = timezone(timedelta(hours=9))
URL = "https://suggestqueries.google.com/complete/search"

SEEDS = [
    "korea travel", "korea trip", "south korea travel tips", "first time in korea", "things to do in korea",
    "seoul travel", "things to do in seoul", "seoul itinerary", "where to stay in seoul", "seoul food",
    "busan travel", "things to do in busan", "busan itinerary", "jeju island", "things to do in jeju",
    "gyeongju", "jeonju hanok village", "day trips from seoul", "korea itinerary",
    "korea transport", "seoul subway", "t money card", "ktx train", "incheon airport to seoul",
    "korea sim card", "korea esim", "naver map", "kakao t", "korea apps for tourists",
    "korea money", "cash in korea", "wowpass", "tax refund korea", "korea budget",
    "korean food to try", "korean street food", "korean bbq", "vegetarian korea", "halal korea",
    "korea visa", "k-eta", "korea entry requirements", "korea weather", "korea packing list",
    "korea shopping", "olive young", "myeongdong", "hongdae", "gangnam", "korean skincare shopping",
    "korean temple stay", "dmz tour", "hanbok rental", "nami island", "seoraksan", "korean festivals",
    "jjimjilbang", "noraebang", "korea nightlife", "korean phrases for travelers",
]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december"]
STOP = set("a an the in to of for and or is are do does with on at from by vs best what how where when why can i you "
           "my your near me 2025 2026 2027 korea korean south".split())


# searches that are not about visiting Korea (US Koreatowns, pop culture, recipes, news) are dropped
NOISE = re.compile(r"\b(lyrics|recipes?|usa|us store|california|nyc|new york|los angeles|la|orlando|texas|houston|atlanta|"
                   r"chicago|toronto|london|sydney|koreatown|wahiawa|pasadena|honolulu|hawaii|money heist|collapse|missing|"
                   r"gangnam style|psy|olympics|girls?|guys?|drama|kdrama|movie|netflix|song|bts|blackpink|stock|ipo|"
                   r"shares|news|war|north korea|kim jong|hongdae 33|meat company|near me|delivery|order online)\b")
STRIP = re.compile(r"\s+(reddit|quora|tripadvisor|blog|youtube)$")


def seasonal_seeds():
    now = datetime.now(KST)
    out = []
    for k in range(0, 4):   # this month and the next three: content needs weeks to rank
        m = MONTHS[(now.month - 1 + k) % 12]
        out += [f"korea in {m}", f"seoul in {m}", f"jeju in {m}", f"busan in {m}"]
    season = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
              6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
    for k in (0, 2):
        s = season[(now.month - 1 + k) % 12 + 1]
        out += [f"korea {s}", f"seoul {s}", f"korea {s} travel"]
    return list(dict.fromkeys(out))


def suggest(q):
    for attempt in range(3):
        try:
            r = requests.get(URL, params={"client": "firefox", "hl": "en", "gl": "us", "q": q}, timeout=15,
                             headers={"User-Agent": "Mozilla/5.0 (Korea Plainly keyword research)"})
            if r.status_code == 200:
                return [s for s in r.json()[1] if isinstance(s, str)]
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return []


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", text.lower()) if w not in STOP and len(w) > 1}


def site_pages():
    pages = []
    for p in ROOT.glob("*.html"):
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "kp-redirect" in s[:4000] or re.search(r'name="robots"[^>]*noindex', s):
            continue
        title = html.unescape(re.sub(r"<[^>]+>", " ", (re.search(r"<title>(.*?)</title>", s, re.S) or [0, ""])[1]))
        h1 = html.unescape(re.sub(r"<[^>]+>", " ", (re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S) or [0, ""])[1]))
        desc = html.unescape((re.search(r'name="description" content="([^"]*)"', s) or [0, ""])[1])
        body = html.unescape(re.sub(r"<[^>]+>", " ", (re.search(r"<article\b.*?</article>", s, re.S) or [""])[0]))
        pages.append({"page": p.name, "head": words(title + " " + h1 + " " + p.stem.replace("-", " ")),
                      "desc": words(desc), "body": words(body)})
    return pages


def main():
    seeds = SEEDS + seasonal_seeds()
    seen = {}
    for i, seed in enumerate(seeds):
        for rank, s in enumerate(suggest(seed)):
            s = STRIP.sub("", s.strip().lower())
            if not s or s == seed or NOISE.search(s):
                continue
            e = seen.setdefault(s, {"query": s, "seeds": [], "score": 0})
            e["seeds"].append(seed)
            e["score"] += max(1, 10 - rank)   # higher in the list = more common
        time.sleep(0.4)
    pages = site_pages()
    gaps, retitle, covered = [], [], []
    for e in sorted(seen.values(), key=lambda e: -e["score"]):
        w = words(e["query"])
        if not w:
            continue
        in_head = [p["page"] for p in pages if w <= p["head"]]
        if in_head:
            covered.append({**e, "page": in_head[0]})
            continue
        # a page that answers it in its text: most of the words in its title, all of them somewhere on the page
        near = sorted((p for p in pages if w <= (p["head"] | p["desc"] | p["body"]) and len(w & p["head"]) * 2 >= len(w)),
                      key=lambda p: (-len(w & p["head"]), -len(w & p["desc"])))
        (retitle if near else gaps).append({**e, "pages": [p["page"] for p in near[:3]]} if near else e)
    out = {"updated": datetime.now(KST).isoformat(timespec="minutes"), "seeds": len(seeds), "suggestions": len(seen),
           "gaps": gaps[:80], "retitle": retitle[:60], "covered": len(covered),
           "note": "gaps = common searches no page title covers (new guide ideas); retitle = searches a page answers "
                   "in its text but not in its title. Scores are relative, from autocomplete position."}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"keyword ideas: {len(seen)} suggestions from {len(seeds)} seeds; {len(gaps)} gaps, {len(retitle)} retitle, "
          f"{len(covered)} covered")
    for e in gaps[:15]:
        print(f"::notice::gap: {e['query']} ({e['score']})")


if __name__ == "__main__":
    main()

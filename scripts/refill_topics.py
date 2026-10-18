#!/usr/bin/env python3
"""Keep content/topics.json from running dry: when few unused topics remain, choose new ones.

    python scripts/refill_topics.py            # needs OPENAI_API_KEY; does nothing while enough topics remain
    python scripts/refill_topics.py --dry-run  # show what would be added, write nothing

Daily Publish runs this just before it writes the day's guide. When fewer than MIN_UNUSED unused topics are left,
it reads the weekly Google autocomplete research (content/keyword_ideas.json "gaps": common visitor searches with
no page), lists every page already on the site, and asks the model to pick the strongest genuine gaps (plus a
seasonal topic for the next 1-2 months) as new guide topics. Each new topic is checked (slug format, no existing
page or topic with that slug, allowed category, title not a near-copy of an existing title) and appended after the
remaining unused topics, strongest first. The searched phrase is kept as "query" for reference.
If the API is unavailable the script prints a warning and exits 0, so the day's guide still gets written.
"""
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "content" / "topics.json"
PUBLISHED = ROOT / "content" / "published.json"
IDEAS = ROOT / "content" / "keyword_ideas.json"
KST = timezone(timedelta(hours=9))

MIN_UNUSED = 7          # refill when fewer than this many unused topics remain
TARGET_UNUSED = 12      # ...up to this many
CATEGORIES = ["Travel", "Transport", "Money", "Food", "Daily Korea", "Culture", "Language", "Apps"]
STOP = set("a an the in to of for and or is are do does with on at from by vs your you what how where when why "
           "can guide korea korean south first time visitors visitor know".split())
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def words(text):
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w not in STOP and len(w) > 1:
            out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def close(a, b):
    """Two word sets name the same subject: mostly the same words, or one almost inside the other."""
    if not a or not b:
        return False
    common = len(a & b)
    return common / len(a | b) >= 0.6 or (common >= 2 and common / min(len(a), len(b)) >= 0.8)


def page_titles():
    out = []
    for p in sorted(ROOT.glob("*.html")):
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "kp-redirect" in s[:4000]:
            continue
        m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S) or re.search(r"<title>(.*?)</title>", s, re.S)
        if m:
            t = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).split("|")[0]
            out.append((p.stem, re.sub(r"\s+", " ", t).strip()))
    return out


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def ask_model(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-6-luna"), input=prompt)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", r.output_text.strip(), flags=re.I).strip()
    return json.loads(text)


def main():
    dry = "--dry-run" in sys.argv
    raw = TOPICS.read_bytes()
    crlf = b"\r\n" in raw
    topics = json.loads(raw.decode("utf-8"))
    used = {x.get("slug") for x in load_json(PUBLISHED, []) if isinstance(x, dict)}
    unused = [t for t in topics if t["slug"] not in used and not (ROOT / f"{t['slug']}.html").exists()]
    print(f"topics: {len(unused)} unused of {len(topics)}")
    if len(unused) >= MIN_UNUSED and not dry:
        return
    want = max(3, TARGET_UNUSED - len(unused))

    pages = page_titles()
    taken_slugs = {t["slug"] for t in topics} | {s for s, _ in pages}
    known_titles = [t for _, t in pages] + [t["title"] for t in topics]
    # word sets of every existing page and topic (title and slug), for the near-copy check
    known = [(t, words(t), words(sl.replace("-", " "))) for sl, t in pages] + \
            [(t["title"], words(t["title"]), words(t["slug"].replace("-", " "))) for t in topics]
    ideas = load_json(IDEAS, {})
    asked = {t.get("query") for t in topics if t.get("query")}
    gaps = [g for g in ideas.get("gaps", []) if g.get("query") not in asked][:60]
    now = datetime.now(KST)
    ahead = [MONTHS[(now.month - 1 + k) % 12] for k in (1, 2)]

    prompt = f"""You plan new guides for Korea Plainly, an English website of practical travel guides for
first-time foreign visitors to Korea. Choose {want} new guide topics.

Common Google searches by visitors that may have no page yet (query, relative popularity):
{json.dumps([[g['query'], g.get('score', 0)] for g in gaps], ensure_ascii=False)}

Pages and planned topics the site already has (do NOT repeat or overlap these, even with different wording):
{json.dumps(known_titles, ensure_ascii=False)}

Rules:
- Prefer the most popular searches above that are genuinely about visiting Korea and that no existing page
  already answers. Skip searches answered by an existing page (for example an eSIM or SIM search when a SIM/eSIM
  page exists), tour packages, news, other countries, and single restaurants, hotels or shops.
- Include at least one seasonal topic useful for visitors in {ahead[0]} or {ahead[1]}, unless the site already covers it.
- One practical, evergreen-as-possible subject per topic, broad enough for an 800-1000 word guide.
- Title: plain British-leaning English, under 70 characters, containing the searched phrase naturally when the
  topic comes from a search. No years unless the topic is a dated event.
- slug: lowercase words joined by hyphens, 2-6 words.
- category: one of {CATEGORIES}.
- query: the search it answers, copied exactly from the list, or "" for a seasonal idea.
- Order from strongest to weakest.

Return ONLY JSON: a list of objects with keys title, slug, category, query."""

    try:
        picks = ask_model(prompt)
    except Exception as e:  # never block the day's guide
        print(f"::warning::refill_topics: could not get new topics ({type(e).__name__}: {e})")
        return

    added = []
    for p in picks if isinstance(picks, list) else []:
        if len(added) >= want or not isinstance(p, dict):
            continue
        title = re.sub(r"\s+", " ", str(p.get("title", ""))).strip()
        slug = str(p.get("slug", "")).strip().lower()
        cat = str(p.get("category", "")).strip()
        query = str(p.get("query", "")).strip()
        why = None
        if not title or len(title) > 90:
            why = "bad title"
        elif not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+){1,7}", slug):
            why = "bad slug"
        elif slug in taken_slugs:
            why = "slug exists"
        elif cat not in CATEGORIES:
            why = f"category {cat!r}"
        else:
            w, wsl = words(title), words(slug.replace("-", " "))
            for t, ot, osl in known:
                if close(w, ot) or close(wsl, osl):
                    why = f"too close to {t!r}"
                    break
        if why:
            print(f"skip {slug or title}: {why}")
            continue
        topic = {"title": title, "slug": slug, "category": cat}
        if query:
            topic["query"] = query
        added.append(topic)
        taken_slugs.add(slug)
        known_titles.append(title)
        known.append((title, words(title), words(slug.replace("-", " "))))

    for t in added:
        print(f"::notice::new topic: {t['title']} ({t['category']}, {t['slug']})")
    if dry or not added:
        return
    text = json.dumps(topics + added, ensure_ascii=False, indent=2) + "\n"
    if crlf:
        text = text.replace("\n", "\r\n")
    TOPICS.write_bytes(text.encode("utf-8"))
    print(f"topics: added {len(added)}; {len(unused) + len(added)} unused now")


if __name__ == "__main__":
    main()

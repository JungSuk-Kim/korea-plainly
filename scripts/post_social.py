#!/usr/bin/env python3
"""Share articles on social networks, a few at a time. Run by the "Social posts" workflow.

    python scripts/post_social.py bluesky [--max 1] [--dry-run]

Picks the newest article not yet shared on that network (guides and regional
articles; redirects and noindex pages are skipped), posts its title, a short
summary, the link and its photo, and records it in content/social_posted.json so
nothing is posted twice. Older articles follow, one or two a run, so the backlog
goes out slowly instead of all at once.

Bluesky needs the repository secrets BLUESKY_HANDLE and BLUESKY_APP_PASSWORD
(an app password, not the account password).
"""
import argparse
import html
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://korea-plainly.com"
STATE = ROOT / "content" / "social_posted.json"
HASHTAGS = ["KoreaTravel", "Korea"]


def read(p):
    return p.read_text(encoding="utf-8")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def articles():
    """[{slug, title, desc, image, date}] for every article worth sharing, newest first."""
    dates = json.loads(read(ROOT / "content" / "page_dates.json"))
    names = set(re.findall(r'<a\s+class="guide-card"\s+href="([^"]+\.html)"', read(ROOT / "guides.html")))
    for p in json.loads(read(ROOT / "content" / "published.json")):
        if isinstance(p, dict) and p.get("slug"):
            names.add(p["slug"] + ".html")
    out = []
    for name in names:
        path = ROOT / name
        if not path.exists():
            continue
        s = read(path)
        if "kp-redirect" in s or re.search(r'name="robots"[^>]*noindex', s):
            continue
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', s)
        cover = (re.search(r'<img\b[^>]*class="cover"[^>]*\bsrc="([^"]+)"', s, re.S)
                 or re.search(r'property="og:image"\s+content="https://korea-plainly\.com/([^"]+)"', s))
        image = cover.group(1) if cover and (ROOT / cover.group(1)).exists() else None
        if not h1 or not image or image == "og-default.jpg":
            continue  # wait until the article has its own photo
        out.append({"slug": name[:-5], "title": clean(h1.group(1)), "desc": html.unescape(desc.group(1)) if desc else "",
                    "image": image, "date": dates.get(name, "")})
    return sorted(out, key=lambda a: (a["date"], a["slug"]), reverse=True)


def shorten(text, limit):
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def thumbnail(image, max_bytes=950_000):
    from PIL import Image
    with Image.open(ROOT / image) as im:
        im = im.convert("RGB")
        im.thumbnail((1200, 1200))
        for q in (82, 72, 62, 52):
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=q, optimize=True)
            if buf.tell() <= max_bytes:
                return buf.getvalue()
    return buf.getvalue()


# ---------------------------------------------------------------- Bluesky

def bluesky_text(a):
    """Post text plus facets (clickable link and hashtags). Bluesky allows 300 characters."""
    url = f"{BASE}/{a['slug']}.html"
    tags = " ".join("#" + t for t in HASHTAGS)
    room = 300 - len(url) - len(tags) - 4
    title = shorten(a["title"], 120)
    desc = shorten(a["desc"], max(room - len(title) - 2, 0)) if room - len(title) > 40 else ""
    text = title + ("\n\n" + desc if desc else "") + "\n\n" + url + "\n" + tags
    facets = []
    b = text.encode("utf-8")
    start = b.find(url.encode())
    facets.append({"index": {"byteStart": start, "byteEnd": start + len(url.encode())},
                   "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]})
    pos = b.rfind(tags.encode())  # the hashtag line is last; walk it tag by tag
    for t in HASHTAGS:
        tag = ("#" + t).encode()
        facets.append({"index": {"byteStart": pos, "byteEnd": pos + len(tag)},
                       "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": t}]})
        pos += len(tag) + 1
    return text, facets


def post_bluesky(a, dry_run=False):
    import requests
    text, facets = bluesky_text(a)
    if dry_run:
        print("---\n" + text)
        return "dry-run"
    host = "https://bsky.social/xrpc"
    session = requests.post(f"{host}/com.atproto.server.createSession", timeout=30, json={
        "identifier": os.environ["BLUESKY_HANDLE"].strip().lstrip("@"),
        "password": os.environ["BLUESKY_APP_PASSWORD"].strip()})
    session.raise_for_status()
    s = session.json()
    auth = {"Authorization": f"Bearer {s['accessJwt']}"}
    blob = requests.post(f"{host}/com.atproto.repo.uploadBlob", timeout=60, data=thumbnail(a["image"]),
                         headers={**auth, "Content-Type": "image/jpeg"})
    blob.raise_for_status()
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "facets": facets,
        "langs": ["en"],
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "embed": {"$type": "app.bsky.embed.external", "external": {
            "uri": f"{BASE}/{a['slug']}.html", "title": shorten(a["title"], 120),
            "description": shorten(a["desc"], 280), "thumb": blob.json()["blob"]}},
    }
    r = requests.post(f"{host}/com.atproto.repo.createRecord", timeout=30, headers=auth,
                      json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": record})
    r.raise_for_status()
    return r.json().get("uri", "")


NETWORKS = {"bluesky": post_bluesky}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("network", choices=sorted(NETWORKS))
    ap.add_argument("--max", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    state = json.loads(read(STATE)) if STATE.exists() else {}
    done = state.setdefault(args.network, {})
    todo = [a for a in articles() if a["slug"] not in done][: args.max]
    if not todo:
        print(f"{args.network}: nothing new to share")
        return
    for a in todo:
        try:
            ref = NETWORKS[args.network](a, args.dry_run)
        except Exception as e:  # keep going next run; report in the log
            print(f"{args.network}: could not share {a['slug']}: {e}")
            sys.exit(1)
        if not args.dry_run:
            done[a["slug"]] = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ref": ref}
        print(f"{args.network}: shared {a['slug']}")
    if not args.dry_run:
        STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

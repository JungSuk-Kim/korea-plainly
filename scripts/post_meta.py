#!/usr/bin/env python3
"""Share our videos and articles on Instagram, Facebook and Threads. Run by the "Social posts" workflow.

    python scripts/post_meta.py videos   [--max 1] [--dry-run]   # public YouTube videos -> Reels, Page video, Threads
    python scripts/post_meta.py articles [--max 1] [--dry-run]   # newest articles -> Facebook Page and Threads (link posts)

Videos: a Short (9:16) becomes an Instagram Reel and a Facebook Page video, and a Threads post
linking to it on YouTube and to its guide. A long-form video goes to the Page and Threads only.
The video file comes from the GitHub artifact the make run kept for 30 days (name = slug, or
slug-long); if it has expired, only the Threads link post is made.
State is kept in content/social_posted.json (keys instagram_videos, facebook_videos,
threads_videos, facebook, threads) so nothing is posted twice.

Secrets: IG_USER_ID, IG_ACCESS_TOKEN (Instagram Login, 60 days, refreshed by meta_refresh.py),
FB_PAGE_ID, FB_PAGE_TOKEN (never expires), THREADS_ACCESS_TOKEN (60 days, refreshed);
GITHUB_TOKEN and GITHUB_REPOSITORY to fetch the video artifacts.
"""
import argparse
import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from post_social import BASE, STATE, articles, read, shorten, videos  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GV = "v23.0"
E = os.environ
TAGS = "#KoreaTravel #Korea #TravelKorea #KoreaPlainly"


def note(level, msg):
    print(f"::{level}::{msg}")


def hashtags(v):
    spec = ROOT / "content" / ("longform" if v["long"] else "shorts") / f"{v['slug']}.json"
    try:
        tags = json.loads(read(spec)).get("hashtags", "")
    except Exception:
        tags = ""
    tags = " ".join(t for t in (tags or TAGS).split() if t.startswith("#"))
    return tags if "#KoreaPlainly" in tags else tags + " #KoreaPlainly"


# ---------------------------------------------------------------- the video file

def video_file(v):
    """Bytes of the rendered mp4 from the make run's artifact, or None if it has expired."""
    repo, token = E.get("GITHUB_REPOSITORY"), E.get("GITHUB_TOKEN")
    if not (repo and token):
        return None
    name = v["slug"] + ("-long" if v["long"] else "")
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    r = requests.get(f"https://api.github.com/repos/{repo}/actions/artifacts", params={"name": name, "per_page": 5},
                     headers=h, timeout=30)
    arts = [a for a in r.json().get("artifacts", []) if not a.get("expired")] if r.ok else []
    if not arts:
        return None
    z = requests.get(arts[0]["archive_download_url"], headers=h, timeout=300)
    if not z.ok:
        return None
    with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
        mp4 = [n for n in zf.namelist() if n.endswith(".mp4")]
        return zf.read(mp4[0]) if mp4 else None


# ---------------------------------------------------------------- Instagram (Reels)

def instagram_reel(v, data, caption):
    uid, tok = E["IG_USER_ID"].strip(), E["IG_ACCESS_TOKEN"].strip()
    api = f"https://graph.instagram.com/{GV}"
    r = requests.post(f"{api}/{uid}/media", timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true",
        "access_token": tok})
    r.raise_for_status()
    cid, uri = r.json()["id"], r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GV}/{r.json()['id']}"
    up = requests.post(uri, data=data, timeout=600, headers={
        "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(data))})
    up.raise_for_status()
    for _ in range(40):  # Instagram processes the video before it can be published
        time.sleep(15)
        s = requests.get(f"{api}/{cid}", params={"fields": "status_code,status", "access_token": tok}, timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram could not process the video: {s.get('status')}")
    else:
        raise RuntimeError("Instagram took too long to process the video")
    p = requests.post(f"{api}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
    p.raise_for_status()
    return p.json()["id"]


# ---------------------------------------------------------------- Facebook Page

def facebook_video(v, data, text):
    pid, tok = E["FB_PAGE_ID"].strip(), E["FB_PAGE_TOKEN"].strip()
    r = requests.post(f"https://graph-video.facebook.com/{GV}/{pid}/videos", timeout=900,
                      data={"title": shorten(v["title"], 90), "description": text, "access_token": tok},
                      files={"source": (f"{v['slug']}.mp4", data, "video/mp4")})
    r.raise_for_status()
    return r.json()["id"]


def facebook_link(url, text):
    pid, tok = E["FB_PAGE_ID"].strip(), E["FB_PAGE_TOKEN"].strip()
    r = requests.post(f"https://graph.facebook.com/{GV}/{pid}/feed", timeout=60,
                      data={"message": text, "link": url, "access_token": tok})
    r.raise_for_status()
    return r.json()["id"]


# ---------------------------------------------------------------- Threads

def threads_post(text, link):
    tok = E["THREADS_ACCESS_TOKEN"].strip()
    api = "https://graph.threads.net/v1.0"
    uid = E.get("THREADS_USER_ID", "").strip() or requests.get(f"{api}/me", params={"access_token": tok}, timeout=30).json()["id"]
    r = requests.post(f"{api}/{uid}/threads", timeout=60, data={
        "media_type": "TEXT", "text": text[:500], "link_attachment": link, "access_token": tok})
    r.raise_for_status()
    time.sleep(5)
    p = requests.post(f"{api}/{uid}/threads_publish", data={"creation_id": r.json()["id"], "access_token": tok}, timeout=60)
    p.raise_for_status()
    return p.json()["id"]


# ---------------------------------------------------------------- runs

def stamp(ref):
    return {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ref": ref}


def run_videos(state, limit, dry):
    done = {k: state.setdefault(k, {}) for k in ("instagram_videos", "facebook_videos", "threads_videos")}
    todo = [v for v in videos() if any(v["key"] not in done[k] for k in done
                                       if not (k == "instagram_videos" and v["long"]))][:limit]
    if not todo:
        print("meta videos: nothing new")
    for v in todo:
        guide = f"{BASE}/{v['slug']}.html"
        tags = hashtags(v)
        ig_caption = f"{v['title']}\n\n{v['desc']}\n\nThe full guide is free on korea-plainly.com (link in bio).\n\n{tags}"
        fb_text = f"{v['title']}\n\n{v['desc']}\n\nFull guide: {guide}\n\n{tags}"
        th_text = f"{'New video' if v['long'] else 'New one-minute video'}: {v['title']}\n\nWatch: {v['youtube']}\nFull guide: {guide}"
        if dry:
            print("--- video", v["key"], v["slug"], "\n", ig_caption, "\n", th_text)
            continue
        need_file = (not v["long"] and v["key"] not in done["instagram_videos"]) or v["key"] not in done["facebook_videos"]
        data = video_file(v) if need_file else None
        if need_file and data is None:
            note("warning", f"{v['slug']}: video file no longer kept; Reel and Page video skipped")
        for key, ok, fn in (("instagram_videos", not v["long"] and E.get("IG_ACCESS_TOKEN") and data, lambda: instagram_reel(v, data, ig_caption)),
                            ("facebook_videos", E.get("FB_PAGE_TOKEN") and data, lambda: facebook_video(v, data, fb_text)),
                            ("threads_videos", E.get("THREADS_ACCESS_TOKEN"), lambda: threads_post(th_text, guide))):
            if v["key"] in done[key]:
                continue
            if not ok:
                if key != "instagram_videos" or not v["long"]:
                    done[key][v["key"]] = stamp("skipped")   # do not try again every run
                continue
            try:
                done[key][v["key"]] = stamp(fn())
                note("notice", f"{key}: shared {v['slug']} ({v['key']})")
            except Exception as e:
                note("error", f"{key}: could not share {v['slug']}: {getattr(e, 'response', None) and e.response.text[:300] or e}")


def run_articles(state, limit, dry):
    for key, fn, ok in (("facebook", facebook_link, E.get("FB_PAGE_TOKEN")), ("threads", lambda url, t: threads_post(t, url), E.get("THREADS_ACCESS_TOKEN"))):
        if not ok and not dry:
            continue
        done = state.setdefault(key, {})
        todo = [a for a in articles() if a["slug"] not in done][:limit]
        for a in todo:
            url = f"{BASE}/{a['slug']}.html"
            text = f"{a['title']}\n\n{shorten(a['desc'], 300)}\n\n{url}\n\n{TAGS}" if key == "facebook" else \
                   f"{shorten(a['title'], 120)}\n\n{shorten(a['desc'], 280)}"
            if dry:
                print("---", key, a["slug"], "\n", text)
                continue
            try:
                done[a["slug"]] = stamp(fn(url, text))
                note("notice", f"{key}: shared {a['slug']}")
            except Exception as e:
                note("error", f"{key}: could not share {a['slug']}: {getattr(e, 'response', None) and e.response.text[:300] or e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["videos", "articles"])
    ap.add_argument("--max", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    state = json.loads(read(STATE)) if STATE.exists() else {}
    (run_videos if args.what == "videos" else run_articles)(state, args.max, args.dry_run)
    if not args.dry_run:
        STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

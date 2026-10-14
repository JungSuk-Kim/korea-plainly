#!/usr/bin/env python3
"""Upload shorts to the Korea Plainly YouTube channel and show them on the site once they are public.

    python scripts/youtube_shorts.py upload <slug>    # upload _shorts/<slug>-voice.mp4 (private) and log it
    python scripts/youtube_shorts.py check            # any uploads made public since? add them to their articles

Needs the repository secrets YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN
(an OAuth client of the koreaplainly@gmail.com Google Cloud project, scope youtube).

YouTube keeps videos uploaded by an app it has not audited private. The owner looks
each one over in the YouTube Studio app and makes it public; `check` then notices
and adds the video to its article (content/videos.json, a poster frame in img/).
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "content" / "shorts" / "uploads.json"
VIDEOS = ROOT / "content" / "videos.json"
KST = timezone(timedelta(hours=9))


def load(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save(p, data):
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def token():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": os.environ["YT_CLIENT_ID"].strip(), "client_secret": os.environ["YT_CLIENT_SECRET"].strip(),
        "refresh_token": os.environ["YT_REFRESH_TOKEN"].strip(), "grant_type": "refresh_token"})
    if r.status_code != 200:
        sys.exit(f"YouTube sign-in failed ({r.status_code}): {r.text[:300]}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def upload(slug):
    spec = json.loads((ROOT / "content" / "shorts" / f"{slug}.json").read_text(encoding="utf-8"))
    video = ROOT / "_shorts" / f"{slug}-voice.mp4"
    desc_file = ROOT / "_shorts" / f"{slug}-voice.txt"
    log = load(UPLOADS)
    if slug in log:
        print(f"{slug}: already uploaded ({log[slug]['youtube']})")
        return
    title = spec["title"]
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"
    description = desc_file.read_text(encoding="utf-8").replace("<", "(").replace(">", ")")
    tags = [t.lstrip("#") for t in spec.get("hashtags", "").split() if t.startswith("#")]
    auth = token()
    meta = {"snippet": {"title": title[:100], "description": description[:4900], "tags": tags + ["Korea travel", "Korea Plainly"],
                        "categoryId": "19", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True}}
    data = video.read_bytes()
    start = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                          timeout=60, json=meta, headers={**auth, "X-Upload-Content-Type": "video/mp4",
                                                          "X-Upload-Content-Length": str(len(data))})
    if start.status_code != 200:
        sys.exit(f"upload could not start ({start.status_code}): {start.text[:500]}")
    r = requests.put(start.headers["Location"], data=data, timeout=600,
                     headers={**auth, "Content-Type": "video/mp4"})
    if r.status_code not in (200, 201):
        sys.exit(f"upload failed ({r.status_code}): {r.text[:500]}")
    vid = r.json()["id"]
    log[slug] = {"article": spec["article"], "youtube": vid, "status": "private",
                 "uploaded": datetime.now(KST).isoformat(timespec="seconds"), "title": spec["title"],
                 "seconds": round(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                        "-of", "csv=p=0", str(video)],
                                                       capture_output=True, text=True).stdout.strip() or 0))}
    # a small poster frame for the article; the video itself is not kept in the repository
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1.2", "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=540:-1", "-q:v", "4", str(ROOT / "_shorts" / f"{slug}-poster.jpg")], check=True)
    save(UPLOADS, log)
    print(f"{slug}: uploaded as private, https://youtube.com/shorts/{vid}")


def check():
    log = load(UPLOADS)
    pending = {k: v for k, v in log.items() if v.get("status") != "public"}
    if not pending:
        print("no private uploads waiting")
        return
    auth = token()
    r = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=30, headers=auth,
                     params={"part": "status", "id": ",".join(v["youtube"] for v in pending.values())})
    r.raise_for_status()
    status = {i["id"]: i["status"]["privacyStatus"] for i in r.json().get("items", [])}
    videos = load(VIDEOS)
    for slug, v in pending.items():
        now = status.get(v["youtube"], "deleted")
        if now == v["status"]:
            continue
        v["status"] = now
        print(f"{slug}: now {now}")
        have = videos.get(v["article"]) or []
        have = have if isinstance(have, list) else [have]
        if now == "public" and all(e.get("youtube") != v["youtube"] for e in have):
            poster = f"img/video-{v['article']}.jpg"
            (ROOT / poster).write_bytes((ROOT / "_shorts" / f"{slug}-poster.jpg").read_bytes())
            entry = {"youtube": v["youtube"], "title": v["title"],
                     "description": f"{v['title']}: the short version of our guide.",
                     "caption": "Watch the one-minute version", "uploaded": v["uploaded"],
                     "seconds": v["seconds"], "poster": poster}
            if any(e.get("format") == "long" for e in have):   # a long-form video is already at the top
                entry.update(place="end", caption="Short on time? The guide in under a minute")
            videos[v["article"]] = have + [entry] if have else entry
    save(UPLOADS, log)
    save(VIDEOS, videos)


if __name__ == "__main__":
    if sys.argv[1:2] == ["upload"]:
        upload(sys.argv[2])
    elif sys.argv[1:2] == ["check"]:
        check()
    else:
        sys.exit(__doc__)

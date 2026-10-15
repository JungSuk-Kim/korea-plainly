#!/usr/bin/env python3
"""Update the title and description of videos already on YouTube. Run by the "YouTube titles" workflow.

    python scripts/youtube_meta.py            # every video listed in content/shorts/retitle.json

content/shorts/retitle.json maps an upload (key in content/shorts/uploads.json) to its new
"title" and "summary". The description keeps its hashtags, chapters and credits; only its top
is replaced (scripts/video_text.py), so the link to the free guide comes first. The new title
is also written to uploads.json and content/videos.json so the site matches. Entries are
removed from retitle.json once done.
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_text import refresh  # noqa: E402
from youtube_shorts import UPLOADS, VIDEOS, load, save, token  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TODO = ROOT / "content" / "shorts" / "retitle.json"
API = "https://www.googleapis.com/youtube/v3/videos"


def main():
    todo = load(TODO) if TODO.exists() else {}
    if not todo:
        print("nothing to update")
        return
    log, videos = load(UPLOADS), load(VIDEOS)
    auth = token()
    for key, new in list(todo.items()):
        up = log[key]
        r = requests.get(API, params={"part": "snippet", "id": up["youtube"]}, headers=auth, timeout=30)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            print(f"::warning::{key}: video {up['youtube']} not found")
            continue
        sn = items[0]["snippet"]
        old = sn.get("description", "")
        if not any(l.startswith("#") or l == "Chapters:" for l in old.split("\n")):
            # typed by hand in Studio: start from the description file we made, so the credits stay
            local = ROOT / "_shorts" / f"{key}{'' if up.get('format') == 'long' else '-voice'}.txt"
            if not local.exists():
                print(f"::warning::{key}: no hashtags or chapters in its description and no local copy; skipped")
                continue
            old = local.read_text(encoding="utf-8")
        title = new["title"]
        if up.get("format") != "long" and "#shorts" not in title.lower():
            title += " #Shorts"
        snippet = {"title": title[:100], "description": refresh(old, up["article"], new["summary"])[:4900],
                   "categoryId": sn.get("categoryId", "19"), "tags": sn.get("tags", []),
                   "defaultLanguage": sn.get("defaultLanguage", "en"),
                   "defaultAudioLanguage": sn.get("defaultAudioLanguage", "en")}
        u = requests.put(API, params={"part": "snippet"}, headers=auth, timeout=30,
                         json={"id": up["youtube"], "snippet": snippet})
        if u.status_code != 200:
            print(f"::error::{key}: update failed ({u.status_code}) {u.text[:300]}")
            continue
        print(f"::notice::{key}: now '{snippet['title']}'")
        up["title"] = new["title"]
        entries = videos.get(up["article"])
        for e in entries if isinstance(entries, list) else [entries] if entries else []:
            if e.get("youtube") == up["youtube"]:
                e["title"] = new["title"]
        del todo[key]
    save(UPLOADS, log)
    save(VIDEOS, videos)
    save(TODO, todo)


if __name__ == "__main__":
    main()

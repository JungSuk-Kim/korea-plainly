#!/usr/bin/env python3
"""Keep our YouTube videos sorted into playlists, so a viewer who likes one sees the next one to watch.

    python scripts/youtube_playlists.py          # create missing playlists, add every uploaded video to its lists

Playlists are chosen from the article slug of each upload in content/shorts/uploads.json (Shorts and long-form).
State lives in content/youtube_playlists.json (playlist ids and which videos were added), so each video is added once.
Private videos can sit in a public playlist; viewers only see them once they are public.
Needs YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (scope youtube), like youtube_shorts.py.
"""
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_shorts import token, load, save, UPLOADS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "content" / "youtube_playlists.json"
API = "https://www.googleapis.com/youtube/v3"
SITE = "https://korea-plainly.com"

# key: (title, description, rule on the article slug)
LISTS = {
    "seoul": ("Seoul Travel Guide", "Plain, practical Seoul tips for first-time visitors: itineraries, neighbourhoods, food and getting around.",
              r"seoul"),
    "busan": ("Busan Travel Guide", "Beaches, temples, seafood and easy routes around Busan, Korea's seaside city.", r"busan"),
    "jeju": ("Jeju Island Travel Guide", "How to see Jeju Island: routes, beaches, volcano hikes and food.", r"jeju"),
    "regions": ("Beyond Seoul: Korea's Cities and Regions", "Gyeongju, Jeonju, Gangneung, Sokcho and more of Korea outside the capital.",
                r"gyeongju|jeonju|gangneung|sokcho|incheon|yeosu|daegu|daejeon|gwangju|andong|suwon|tongyeong"),
    "itinerary": ("Korea Itineraries", "Day-by-day plans for Korea: Seoul, Busan, Jeju and one-week and ten-day routes.",
                  r"itinerary|days?-in"),
    "seasons": ("Korea by Season", "When to go and what to see: cherry blossoms, autumn leaves, winter festivals and month-by-month guides.",
                r"autumn|foliage|cherry|blossom|winter|summer|spring|christmas|new-year|sunrise|festival|korea-in-|best-time"),
    "basics": ("Korea Travel Tips for First-Timers", "The basics, plainly explained: transport, money, apps, food and everyday life in Korea.",
               None),   # anything that fits no place or season list
}


def lists_for(article):
    keys = [k for k, (_, _, rule) in LISTS.items() if rule and re.search(rule, article)]
    if not any(k in keys for k in ("seoul", "busan", "jeju", "regions", "seasons")):
        keys.append("basics")
    return keys


def main():
    uploads = load(UPLOADS)
    state = load(STATE) or {}
    state.setdefault("playlists", {})
    state.setdefault("added", {})
    todo = []
    for v in uploads.values():
        for k in lists_for(v.get("article", "")):
            if k not in state["added"].get(v["youtube"], []):
                todo.append((k, v))
    if not todo:
        print("playlists up to date")
        return
    auth = token()
    for k, v in todo:
        if k not in state["playlists"]:
            title, desc, _ = LISTS[k]
            r = requests.post(f"{API}/playlists", params={"part": "snippet,status"}, headers=auth, timeout=30, json={
                "snippet": {"title": title, "description": f"{desc}\n\nFree full guides: {SITE}", "defaultLanguage": "en"},
                "status": {"privacyStatus": "public"}})
            if r.status_code != 200:
                print(f"::error::could not create playlist {title} ({r.status_code}): {r.text[:300]}")
                break
            state["playlists"][k] = r.json()["id"]
            print(f"created playlist {title}")
        r = requests.post(f"{API}/playlistItems", params={"part": "snippet"}, headers=auth, timeout=30, json={
            "snippet": {"playlistId": state["playlists"][k], "resourceId": {"kind": "youtube#video", "videoId": v["youtube"]}}})
        if r.status_code == 200 or "videoAlreadyInPlaylist" in r.text:
            state["added"].setdefault(v["youtube"], []).append(k)
            print(f"added {v['title']} to {LISTS[k][0]}")
        elif r.status_code == 404:   # the video was deleted
            print(f"::warning::{v['youtube']} not found, skipped")
            state["added"].setdefault(v["youtube"], []).append(k)
        else:
            print(f"::error::could not add {v['youtube']} to {k} ({r.status_code}): {r.text[:300]}")
            break
    save(STATE, state)


if __name__ == "__main__":
    main()

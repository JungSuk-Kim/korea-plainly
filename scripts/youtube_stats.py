#!/usr/bin/env python3
"""How our YouTube videos are doing, for the owner's ops map and for tuning the next videos.

    python scripts/youtube_stats.py        # writes content/youtube_stats.json

Always: views, likes and comments per video (YouTube Data API, scope youtube).
If the refresh token also has yt-analytics.readonly: average % viewed, average view length, subscribers gained,
shares, and a retention summary (how many viewers are still watching at 10%, 25%, 50%, 75% and 95% of the video,
and where the biggest drop is). Analytics numbers lag YouTube Studio by about two days.
Analytics calls are retried on 5xx/429 (5s, 15s, 45s). If they still fail, the last good analytics numbers are
carried over from the previous content/youtube_stats.json with "analytics_stale_since" set to their date.
Needs YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_shorts import token, load, save, UPLOADS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "youtube_stats.json"
KST = timezone(timedelta(hours=9))
DATA = "https://www.googleapis.com/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
MARKS = (0.1, 0.25, 0.5, 0.75, 0.95)
BACKOFF = (5, 15, 45)   # seconds between retries of an Analytics call
CARRY = ("avg_view_seconds", "avg_view_percent", "subscribers_gained", "shares", "retention")


def analytics_get(auth, params):
    """GET an Analytics report, retrying on 5xx and 429 only."""
    for wait in BACKOFF + (None,):
        try:
            r = requests.get(ANALYTICS, headers=auth, timeout=30, params=params)
        except requests.RequestException as exc:
            if wait is None:
                raise
            print(f"Analytics request failed ({exc.__class__.__name__}); retrying in {wait}s")
            time.sleep(wait)
            continue
        if wait is None or not (r.status_code == 429 or r.status_code >= 500):
            return r
        print(f"Analytics returned {r.status_code}; retrying in {wait}s")
        time.sleep(wait)


def carry_over(out, prev):
    """Keep the last good analytics numbers when today's Analytics call failed."""
    if prev.get("analytics"):
        since = str(prev.get("updated", ""))[:10]
    else:
        since = prev.get("analytics_stale_since")
    if not since:
        return
    old = {v.get("id"): v for v in prev.get("videos", [])}
    for e in out["videos"]:
        o = old.get(e["id"], {})
        e.update({k: o[k] for k in CARRY if k in o})
    for k in ("countries", "traffic_sources"):
        if k in prev:
            out[k] = prev[k]
    out["analytics_stale_since"] = since


def retention(auth, vid, start, end):
    r = analytics_get(auth, {
        "ids": "channel==MINE", "startDate": start, "endDate": end, "dimensions": "elapsedVideoTimeRatio",
        "metrics": "audienceWatchRatio", "filters": f"video=={vid}"})
    if r.status_code != 200:
        return None
    rows = r.json().get("rows") or []
    if not rows:
        return None
    curve = [(float(x), float(y)) for x, y in rows]

    def at(t):
        return round(min(curve, key=lambda p: abs(p[0] - t))[1] * 100)
    drops = [(curve[i][0], curve[i - 1][1] - curve[i][1]) for i in range(1, len(curve))]
    worst = max(drops, key=lambda d: d[1]) if drops else (0, 0)
    return {"at": {f"{int(m * 100)}%": at(m) for m in MARKS}, "biggest_drop_at": f"{round(worst[0] * 100)}%",
            "biggest_drop": round(worst[1] * 100)}


def main():
    uploads = load(UPLOADS)
    videos = {v["youtube"]: v for v in uploads.values()}
    if not videos:
        print("no videos yet")
        return
    auth = token()
    info = requests.get("https://oauth2.googleapis.com/tokeninfo", timeout=30,
                        params={"access_token": auth["Authorization"].split()[-1]}).json()
    scopes = info.get("scope", "").split()
    print(f"::notice::YouTube token scopes: {', '.join(x.rsplit('/', 1)[-1] for x in scopes) or 'unknown'}")
    out = {"updated": datetime.now(KST).isoformat(timespec="minutes"), "analytics": False, "videos": [],
           "scopes": [x.rsplit("/", 1)[-1] for x in scopes]}
    r = requests.get(f"{DATA}/videos", headers=auth, timeout=30,
                     params={"part": "statistics,status", "id": ",".join(videos)})
    r.raise_for_status()
    stats = {i["id"]: i for i in r.json().get("items", [])}

    end = datetime.now(KST).date().isoformat()
    start = min(v.get("uploaded", end)[:10] for v in videos.values())
    a = analytics_get(auth, {
        "ids": "channel==MINE", "startDate": start, "endDate": end, "dimensions": "video",
        "metrics": "views,averageViewDuration,averageViewPercentage,subscribersGained,shares,likes",
        "filters": "video==" + ",".join(videos), "sort": "-views", "maxResults": 200})
    rows = {}
    if a.status_code == 200:
        out["analytics"] = True
        cols = [c["name"] for c in a.json().get("columnHeaders", [])]
        rows = {row[0]: dict(zip(cols, row)) for row in a.json().get("rows") or []}
    else:
        out["analytics_error"] = f"{a.status_code}: {a.text[:200]}"
        print(f"::notice::YouTube Analytics not available yet ({a.status_code}); saving views, likes and comments only")

    if out["analytics"]:   # where viewers are, to choose when to publish
        c = analytics_get(auth, {
            "ids": "channel==MINE", "startDate": start, "endDate": end, "dimensions": "country",
            "metrics": "views,estimatedMinutesWatched", "sort": "-views", "maxResults": 15})
        if c.status_code == 200:
            out["countries"] = [{"country": r[0], "views": r[1], "minutes": r[2]} for r in c.json().get("rows") or []]
        t = analytics_get(auth, {
            "ids": "channel==MINE", "startDate": start, "endDate": end, "dimensions": "insightTrafficSourceType",
            "metrics": "views", "sort": "-views"})
        if t.status_code == 200:
            out["traffic_sources"] = [{"source": r[0], "views": r[1]} for r in t.json().get("rows") or []]

    for vid, v in videos.items():
        s = stats.get(vid, {})
        st = s.get("statistics", {})
        e = {"id": vid, "title": v.get("title", ""), "article": v.get("article", ""),
             "format": "long" if v.get("format") == "long" else "short", "uploaded": v.get("uploaded", ""),
             "status": s.get("status", {}).get("privacyStatus", "missing"), "seconds": v.get("seconds"),
             "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
             "comments": int(st.get("commentCount", 0))}
        if out["analytics"]:
            row = rows.get(vid, {})
            e.update(avg_view_seconds=row.get("averageViewDuration"), avg_view_percent=row.get("averageViewPercentage"),
                     subscribers_gained=row.get("subscribersGained", 0), shares=row.get("shares", 0))
            if e["status"] == "public" and e["views"] >= 20:
                e["retention"] = retention(auth, vid, start, end)
        out["videos"].append(e)
    out["videos"].sort(key=lambda e: e["uploaded"], reverse=True)
    if not out["analytics"]:
        carry_over(out, load(OUT) if OUT.exists() else {})
    total = {k: sum(e.get(k) or 0 for e in out["videos"]) for k in ("views", "likes", "comments", "subscribers_gained")}
    out["total"] = total
    save(OUT, out)
    print(f"YouTube stats: {len(out['videos'])} videos, {total['views']} views, analytics {'on' if out['analytics'] else 'off'}")


if __name__ == "__main__":
    main()

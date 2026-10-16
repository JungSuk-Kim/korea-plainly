#!/usr/bin/env python3
"""A snapshot of how the whole Korea Plainly system is doing, as JSON, for the "Korea Plainly 운영 지도" page.

    python scripts/ops_status.py > /tmp/status.json      # uses `gh api` for workflow runs when available

A scheduled Claude task runs this and writes the result into the page's database
(document status/current), so the page shows live numbers without being republished.
"""
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
REPO = "JungSuk-Kim/korea-plainly"
WORKFLOWS = [  # file, label shown on the page
    ("daily-publish.yml", "새 글 발행"), ("site-maintenance.yml", "사이트 정비"), ("shorts-auto.yml", "숏츠"),
    ("longform-auto.yml", "롱폼"), ("social-posts.yml", "SNS 공유"), ("festivals.yml", "축제 갱신"),
    ("meta-refresh.yml", "토큰 갱신"),
]


def load(p, default):
    try:
        return json.loads((ROOT / p).read_text(encoding="utf-8"))
    except Exception:
        return default


def gh(path):
    try:
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout) if out.returncode == 0 else None
    except Exception:
        return None


def workflows():
    out = []
    for f, label in WORKFLOWS:
        d = gh(f"repos/{REPO}/actions/workflows/{f}/runs?per_page=5")
        runs = (d or {}).get("workflow_runs", [])
        done = [r for r in runs if r.get("status") == "completed"]
        last = done[0] if done else None
        out.append({"file": f, "label": label,
                    "status": (last or {}).get("conclusion") or ("running" if runs else "unknown"),
                    "at": (last or {}).get("updated_at", "")})
    return out


def today_runs():
    """Which of today's scheduled jobs (Korea time) have finished successfully, and when."""
    now = datetime.now(KST)
    today = now.date()

    def runs(f, n=40):
        d = gh(f"repos/{REPO}/actions/workflows/{f}/runs?per_page={n}")
        out = []
        for r in (d or {}).get("workflow_runs", []):
            t = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(KST)
            if t.date() == today:
                out.append({"t": t, "ok": r.get("conclusion") == "success", "done": r.get("status") == "completed",
                            "event": r.get("event"), "end": r.get("updated_at", "")})
        return out

    def first(rs, cond=lambda r: True):
        hit = [r for r in rs if r["ok"] and cond(r)]
        if hit:
            r = min(hit, key=lambda r: r["t"])
            return {"done": True, "at": r["t"].isoformat(timespec="minutes")}
        if any(not r["done"] and cond(r) for r in rs):
            return {"done": False, "running": True}
        if any(r["done"] and not r["ok"] and cond(r) for r in rs):
            return {"done": False, "failed": True}
        return {"done": False}

    shorts = runs("shorts-auto.yml")
    social = runs("social-posts.yml")
    checks = [r for r in shorts if r["ok"] and r["t"].hour != 10]   # the 10:07 run makes a Short; the rest are checks
    return {
        "date": today.isoformat(), "weekday": today.weekday(),
        "fest": first(runs("festivals.yml")),
        "publish": first(runs("daily-publish.yml")),
        "shorts": first(shorts, lambda r: r["t"].hour == 10),
        "longform": first(runs("longform-auto.yml")),
        "social_am": first(social, lambda r: 6 <= r["t"].hour < 15),
        "social_pm": first(social, lambda r: r["t"].hour >= 15),
        "tokens": first(runs("meta-refresh.yml")),
        "check": {"done": bool(checks), "at": max(r["t"] for r in checks).isoformat(timespec="minutes") if checks else ""},
    }


def main():
    published = [p for p in load("content/published.json", []) if isinstance(p, dict) and p.get("slug")]
    dates = load("content/page_dates.json", {})
    pages = [p for p in ROOT.glob("*.html") if "kp-redirect" not in p.read_text(encoding="utf-8", errors="ignore")[:4000]]
    videos = load("content/videos.json", {})
    vlist = []
    for slug, entries in videos.items():
        for v in entries if isinstance(entries, list) else [entries]:
            long = v.get("format") == "long"
            vlist.append({"title": v["title"], "slug": slug, "long": long, "uploaded": v.get("uploaded", ""),
                          "url": (f"https://www.youtube.com/watch?v={v['youtube']}" if long else f"https://www.youtube.com/shorts/{v['youtube']}")})
    vlist.sort(key=lambda v: v["uploaded"], reverse=True)
    uploads = load("content/shorts/uploads.json", {})
    pending = [{"title": v.get("title", k), "long": v.get("format") == "long", "uploaded": v.get("uploaded", ""),
                "url": f"https://studio.youtube.com/video/{v['youtube']}/edit"}
               for k, v in uploads.items() if v.get("status") != "public"]
    social = load("content/social_posted.json", {})
    counts = {k: sum(1 for x in v.values() if x.get("ref") != "skipped") for k, v in social.items() if isinstance(v, dict)}
    fest = load("content/festivals.json", {})
    today = datetime.now(KST).date().isoformat()
    upcoming = [f for f in fest.get("festivals", []) if f.get("end", "") >= today]
    recent = sorted(((dates.get(p["slug"] + ".html", ""), p) for p in published), key=lambda x: x[0], reverse=True)[:6]
    done_shorts = {v.get("article") for v in uploads.values() if v.get("format") != "long"}
    done_long = {v.get("article") for v in uploads.values() if v.get("format") == "long"}
    nq = next((s for s in load("content/shorts/queue.json", {}).get("queue", []) if s not in done_shorts and (ROOT / f"{s}.html").exists()), "")
    nl = next((s for s in load("content/longform/queue.json", {}).get("queue", []) if s not in done_long and (ROOT / f"{s}.html").exists()), "")
    title_of = {p["slug"]: p.get("title", p["slug"]) for p in published}
    status = {
        "updated": datetime.now(KST).isoformat(timespec="minutes"),
        "stats": {"pages": len(pages), "articles": len(published), "videos": len(vlist),
                  "shorts": sum(1 for v in vlist if not v["long"]), "longs": sum(1 for v in vlist if v["long"]),
                  "festivals": len(upcoming), "channels": 6},
        "social": {
            "bluesky": counts.get("bluesky", 0) + counts.get("bluesky_videos", 0),
            "instagram": counts.get("instagram_videos", 0),
            "facebook": counts.get("facebook", 0) + counts.get("facebook_videos", 0),
            "threads": counts.get("threads", 0) + counts.get("threads_videos", 0),
        },
        "videos": vlist[:4],
        "pending": pending,
        "articles": [{"title": p.get("title", p["slug"]), "slug": p["slug"], "date": d} for d, p in recent],
        "next": {"short": {"slug": nq, "title": title_of.get(nq, nq)}, "long": {"slug": nl, "title": title_of.get(nl, nl)}},
        "workflows": workflows(),
        "today": today_runs(),
    }
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

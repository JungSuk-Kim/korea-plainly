#!/usr/bin/env python3
"""Fetch upcoming festivals in Korea from the Korea Tourism Organization's English TourAPI.

    TOURAPI_KEY=... python scripts/fetch_festivals.py

Writes content/festivals.json (festivals that end today or later, starting within the next
120 days), used by scripts/festival_pages.py. The key is the "decoding" service key from
data.go.kr for 한국관광공사_영문 관광정보 서비스 (English tourism information). Only titles,
dates, places and coordinates are kept; we do not copy the API's photos or long descriptions.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "festivals.json"
KST = timezone(timedelta(hours=9))
ENDPOINTS = [("https://apis.data.go.kr/B551011/EngService2/searchFestival2", "EngService2"),
             ("https://apis.data.go.kr/B551011/EngService1/searchFestival1", "EngService1")]


def get(url, key, start, page):
    r = requests.get(url, timeout=40, params={
        "serviceKey": key, "MobileOS": "ETC", "MobileApp": "KoreaPlainly", "_type": "json",
        "eventStartDate": start, "numOfRows": 100, "pageNo": page, "arrange": "A"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    try:
        body = r.json()["response"]["body"]
    except Exception:
        raise RuntimeError(f"unexpected reply: {r.text[:200]}")
    items = body.get("items") or {}
    items = items.get("item", []) if isinstance(items, dict) else []
    return (items if isinstance(items, list) else [items]), int(body.get("totalCount") or 0)


def day(s):
    s = re.sub(r"\D", "", str(s or ""))[:8]
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else ""


def main():
    key = os.environ.get("TOURAPI_KEY", "").strip()
    if not key:
        print("::warning::TOURAPI_KEY is not set; festivals not updated")
        return
    today = datetime.now(KST).date()
    start = (today - timedelta(days=120)).strftime("%Y%m%d")   # long festivals that began earlier are still running
    horizon = today + timedelta(days=120)
    raw, used, last = [], None, None
    for url, name in ENDPOINTS:
        try:
            page = 1
            while True:
                items, total = get(url, key, start, page)
                raw += items
                if page * 100 >= total or not items or page >= 20:
                    break
                page += 1
            used = name
            break
        except Exception as e:  # try the older service name
            last = e
            raw = []
    if not used:
        print(f"::error::TourAPI festival search failed: {last}")
        sys.exit(1)
    out, seen = [], set()
    for it in raw:
        s, e = day(it.get("eventstartdate")), day(it.get("eventenddate"))
        title = re.sub(r"\s+", " ", str(it.get("title") or "")).strip()
        if not (title and s and e) or e < today.isoformat() or s > horizon.isoformat():
            continue
        k = (title.lower(), s)
        if k in seen:
            continue
        seen.add(k)
        out.append({"id": str(it.get("contentid") or ""), "title": title, "start": s, "end": e,
                    "address": re.sub(r"\s+", " ", f"{it.get('addr1') or ''} {it.get('addr2') or ''}").strip(),
                    "lat": float(it["mapy"]) if it.get("mapy") else None,
                    "lon": float(it["mapx"]) if it.get("mapx") else None})
    out.sort(key=lambda f: (f["start"], f["title"]))
    OUT.write_text(json.dumps({"updated": today.isoformat(), "source": used, "festivals": out},
                              indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"festivals: {len(out)} upcoming or running (from {len(raw)} records, {used})")


if __name__ == "__main__":
    main()

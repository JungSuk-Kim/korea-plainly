#!/usr/bin/env python3
"""One credited photo for each region page (content/region_photos.json).

    {"seoul": {"file": "...jpg", "credit": "Photo: ...", "source": "https://commons...", "alt": "..."},
     "yeosu": {"query": "Yeosu Dolsan Bridge"}}

An entry with a "file" is used as it is. An entry with only a "query" gets a freely licensed Wikimedia Commons
photo when KP_FETCH_PHOTOS=1 (GitHub Actions), saved as region-<slug>.jpg; add "retry": true for a different one.
The region page shows the photo with its credit; the home page and regions.html use the same file.
Never Google Maps photos.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "content" / "region_photos.json"
FETCH = os.environ.get("KP_FETCH_PHOTOS") == "1"


def load():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def photo(slug):
    """The region's photo entry, or None when there is no usable file."""
    e = load().get(slug) or {}
    return e if e.get("file") and (ROOT / e["file"]).exists() else None


def main():
    state = load()
    if not FETCH:
        print("region_photos: no fetch")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from guide_photos import download, search_commons, sources_in_use
    fetched = 0
    for slug, e in state.items():
        has = e.get("file") and (ROOT / e["file"]).exists()
        if not e.get("query") or (has and not e.get("retry")) or (e.get("none") and not e.get("retry")):
            continue
        reject = list(e.get("reject", []))
        if has and e.get("source"):
            reject.append(e["source"])
        try:
            found = search_commons(e["query"], reject + sorted(sources_in_use()))
        except Exception as err:   # network trouble: try again next run
            print(f"region_photos: {slug}: {err}")
            continue
        new = {"query": e["query"]}
        if reject:
            new["reject"] = sorted(set(reject))
        if found:
            name = f"region-{slug}.jpg"
            download(found["url"], ROOT / name)
            new.update(file=name, credit=found["credit"], source=found["source"], alt=e.get("alt", ""))
            fetched += 1
        elif has:
            new.update({k: e[k] for k in ("file", "credit", "source", "alt") if k in e})
        else:
            new["none"] = True
        state[slug] = new
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"region_photos: {fetched} new photo(s)")


if __name__ == "__main__":
    main()

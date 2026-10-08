import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "content" / "region_rotation.json"
PUBLISHED = ROOT / "content" / "published.json"

state = json.loads(STATE.read_text(encoding="utf-8"))
published = json.loads(PUBLISHED.read_text(encoding="utf-8"))

regions = state["regions"]
categories = state["categories"]

idx = state.get("current_region_index", 0)
region = regions[idx]
round_no = state.get("current_round", 1)

published_keys = {
    (item.get("region"), item.get("category"), item.get("round"))
    for item in published
}

queue = []
for category in categories:
    key = (region["slug"], category["slug"], round_no)
    if key not in published_keys:
        queue.append({
            "region": region["name"],
            "region_slug": region["slug"],
            "category": category["name"],
            "category_slug": category["slug"],
            "round": round_no
        })

print(json.dumps({
    "region": region,
    "round": round_no,
    "remaining_categories": queue
}, ensure_ascii=False, indent=2))

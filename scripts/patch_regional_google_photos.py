from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "generate_regional_day.py"
s = TARGET.read_text(encoding="utf-8")

old = '"google_place_id": place.get("id")\n    }'
new = '"google_place_id": place.get("id"),\n        "photos": place.get("photos", [])\n    }'

if old not in s:
    if '"photos": place.get("photos", [])' in s:
        print("Google Places photos are already included.")
    else:
        raise SystemExit("Target block not found.")
else:
    s = s.replace(old, new, 1)
    TARGET.write_text(s, encoding="utf-8")
    print("Google Places photos added to regional place data.")

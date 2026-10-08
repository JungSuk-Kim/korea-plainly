from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "generate_regional_day.py"
s = TARGET.read_text(encoding="utf-8")

if '"places.photos"' not in s:
    s = s.replace('"places.priceLevel","places.types"',
                  '"places.priceLevel","places.types","places.photos"')

if "def google_place_image(" not in s:
    marker = "def wikimedia_image(query):"
    helper = (
        "def google_place_image(place):\n"
        "    photos = place.get('photos') or []\n"
        "    if not photos:\n"
        "        return None\n"
        "    photo_name = photos[0].get('name')\n"
        "    if not photo_name:\n"
        "        return None\n"
        "    return {'url': f'https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=1600&maxHeightPx=1200&key={GOOGLE_KEY}', "
        "'title': 'Google Places photo'}\n\n"
    )
    if marker not in s:
        raise SystemExit("Could not find Wikimedia image helper.")
    s = s.replace(marker, helper + marker, 1)

start = s.find("        image_info = wikimedia_image(")
end = s.find("        body = ask_openai", start)
if start < 0 or end < 0:
    raise SystemExit("Could not find image selection block.")

replacement = (
    "        image_info = google_place_image(place)\n"
    "        image_name = download_image(image_info, slug) if image_info else None\n\n"
    "        if not image_name:\n"
    "            image_info = wikimedia_image(f\"{place['name']} {region_name} Korea\")\n"
    "            image_name = download_image(image_info, slug) if image_info else None\n\n"
    "        if not image_name:\n"
    "            raise RuntimeError(f\"No usable place-specific image found for {place['name']}\")\n\n"
)
s = s[:start] + replacement + s[end:]
TARGET.write_text(s, encoding="utf-8")
print("Regional image sourcing patched.")


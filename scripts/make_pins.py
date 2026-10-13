#!/usr/bin/env python3
"""Pinterest pin images and a bulk-upload CSV for every guide. Idempotent.

For each guide card on guides.html this makes pins/<slug>.jpg (1000x1500: the
guide's photo on top, its title below) and lists all pins in pins/pins.csv,
which can be uploaded with Pinterest's "Bulk create Pins". A pin is only redrawn
when its title or photo changes (content/pins.json keeps a fingerprint).
"""
import csv
import hashlib
import html
import io
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pins"
STATE = ROOT / "content" / "pins.json"
FONT_BOLD = Path(__file__).resolve().parent / "fonts" / "Carlito-Bold.ttf"
FONT_REG = Path(__file__).resolve().parent / "fonts" / "Carlito-Regular.ttf"
BASE = "https://korea-plainly.com"
W, H, PHOTO_H = 1000, 1500, 900
NAVY, RED, WHITE, MUTED = (23, 36, 60), (201, 65, 58), (255, 255, 255), (190, 198, 212)
BOARDS = {"food": "Korean Food Guide", "travel": "Korea Travel Planning"}
DEFAULT_BOARD = "Korea Travel Tips"


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def guides():
    g = (ROOT / "guides.html").read_text(encoding="utf-8")
    for m in re.finditer(r'<a\s+class="guide-card"\s+href="([^"]+)\.html"\s+data-guide-category="([^"]+)"[^>]*>(.*?)</a>', g, re.S):
        slug, cat, inner = m.groups()
        thumb = re.search(r'(?:data-thumb="|background-image:url\(\')([^"\']+)', inner)
        title = clean((re.search(r"<h2>(.*?)</h2>", inner, re.S) or [None, slug])[1])
        desc = clean((re.search(r"<p>(.*?)</p>", inner, re.S) or [None, ""])[1])
        if thumb and (ROOT / f"{slug}.html").exists():
            yield {"slug": slug, "cat": cat, "title": title, "desc": desc, "photo": thumb.group(1)}


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=font) <= width:
            line = test
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def draw_pin(item, path):
    img = Image.new("RGB", (W, H), NAVY)
    src = ROOT / item["photo"]
    if src.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and src.exists():
        with Image.open(src) as photo:
            img.paste(ImageOps.fit(photo.convert("RGB"), (W, PHOTO_H), Image.LANCZOS), (0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, PHOTO_H, W, PHOTO_H + 10], fill=RED)
    kicker = ImageFont.truetype(str(FONT_BOLD), 30)
    d.text((70, PHOTO_H + 60), "KOREA PLAINLY", font=kicker, fill=RED)
    title = item["title"].split(":")[0] if len(item["title"]) > 60 else item["title"]
    for size in (78, 70, 62, 56):
        font = ImageFont.truetype(str(FONT_BOLD), size)
        lines = wrap(d, title, font, W - 140)
        if len(lines) <= 4:
            break
    y = PHOTO_H + 115
    for line in lines[:4]:
        d.text((70, y), line, font=font, fill=WHITE)
        y += int(size * 1.12)
    small = ImageFont.truetype(str(FONT_REG), 30)
    d.text((70, H - 75), "korea-plainly.com", font=small, fill=MUTED)
    OUT.mkdir(exist_ok=True)
    img.save(path, "JPEG", quality=84, optimize=True, progressive=True)


def main():
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    items, made = list(guides()), 0
    for item in items:
        src = ROOT / item["photo"]
        fp = hashlib.md5((item["title"] + "|" + item["photo"] + "|").encode() + (src.read_bytes() if src.exists() else b"")).hexdigest()[:12]
        path = OUT / f"{item['slug']}.jpg"
        if state.get(item["slug"]) != fp or not path.exists():
            draw_pin(item, path)
            state[item["slug"]] = fp
            made += 1
    keep = {i["slug"] for i in items}
    for f in OUT.glob("*.jpg") if OUT.exists() else []:
        if f.stem not in keep:
            f.unlink()
    state = {k: v for k, v in sorted(state.items()) if k in keep}
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["Title", "Media URL", "Pinterest board", "Description", "Link", "Publish date", "Keywords"])
    for i in items:
        w.writerow([i["title"][:100], f"{BASE}/pins/{i['slug']}.jpg", BOARDS.get(i["cat"], DEFAULT_BOARD),
                    i["desc"][:500], f"{BASE}/{i['slug']}.html", "", "Korea travel, Seoul, Korea tips"])
    (OUT / "pins.csv").write_text(buf.getvalue(), encoding="utf-8")
    print(f"make_pins: {len(items)} pins, {made} drawn")


if __name__ == "__main__":
    main()

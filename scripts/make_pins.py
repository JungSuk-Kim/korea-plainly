#!/usr/bin/env python3
"""Pinterest pin images, a bulk-upload CSV and RSS feeds. Idempotent.

For each guide card on guides.html this makes pins/<slug>.jpg (1000x1500: the
guide's photo on top, its title below) and lists all pins in pins/pins.csv,
which can be uploaded with Pinterest's "Bulk create Pins". A pin is only redrawn
when its title or photo changes (content/pins.json keeps a fingerprint).

Regional articles get pins too (their cover photo + title). Two RSS feeds let
Pinterest publish new pins automatically, one board per feed:
  pins/places.xml  every regional article  -> board "Places to Visit in Korea"
  pins/guides.xml  guides not in content/pins_uploaded.json (those were uploaded
                   once with pins.csv, so they are left out)
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
FEED_SIZE = 50
UPLOADED = ROOT / "content" / "pins_uploaded.json"


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


def places():
    pub = json.loads((ROOT / "content" / "published.json").read_text(encoding="utf-8"))
    for p in pub:
        if not (isinstance(p, dict) and p.get("place_name")):
            continue
        page = ROOT / f"{p['slug']}.html"
        if not page.exists():
            continue
        s = page.read_text(encoding="utf-8")
        if "kp-redirect" in s:
            continue
        cover = re.search(r'<img\b[^>]*class="cover"[^>]*src="([^"]+)"', s, re.S) or re.search(r'<img\s+class="cover"\s+src="([^"]+)"', s)
        desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', s)
        if cover:
            yield {"slug": p["slug"], "cat": "place", "title": clean(p.get("title", "")), "region": p.get("region", ""),
                   "desc": html.unescape(desc.group(1)) if desc else "", "photo": cover.group(1)}


def rss(items, dates, title, description):
    from email.utils import format_datetime
    from datetime import datetime, timezone
    esc = lambda t: html.escape(t or "", quote=False)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>',
           f"<title>{esc(title)}</title><link>{BASE}/</link><description>{esc(description)}</description><language>en</language>"]
    for i in items:
        d = dates.get(f"{i['slug']}.html", "2026-01-01")
        when = format_datetime(datetime.strptime(d[:10], "%Y-%m-%d").replace(hour=9, tzinfo=timezone.utc))
        img = f"{BASE}/pins/{i['slug']}.jpg"
        size = (OUT / f"{i['slug']}.jpg").stat().st_size
        out.append(f"<item><title>{esc(i['title'])}</title><link>{BASE}/{i['slug']}.html</link>"
                   f"<guid isPermaLink=\"true\">{BASE}/{i['slug']}.html</guid><pubDate>{when}</pubDate>"
                   f"<description>{esc(i['desc'])}</description>"
                   f'<enclosure url="{img}" length="{size}" type="image/jpeg"/>'
                   f'<media:content url="{img}" medium="image" type="image/jpeg" width="{W}" height="{H}"/></item>')
    out.append("</channel></rss>")
    return "\n".join(out) + "\n"


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
    label = f"{item['region'].upper()} · KOREA PLAINLY" if item.get("region") else "KOREA PLAINLY"
    d.text((70, PHOTO_H + 60), label, font=kicker, fill=RED)
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
    guide_items, place_items = list(guides()), list(places())
    items, made = guide_items + place_items, 0
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
    for i in guide_items:
        w.writerow([i["title"][:100], f"{BASE}/pins/{i['slug']}.jpg", BOARDS.get(i["cat"], DEFAULT_BOARD),
                    i["desc"][:500], f"{BASE}/{i['slug']}.html", "", "Korea travel, Seoul, Korea tips"])
    (OUT / "pins.csv").write_text(buf.getvalue(), encoding="utf-8")
    dates_path = ROOT / "content" / "page_dates.json"
    dates = json.loads(dates_path.read_text(encoding="utf-8")) if dates_path.exists() else {}
    newest = lambda lst: sorted(lst, key=lambda i: dates.get(f"{i['slug']}.html", ""), reverse=True)[:FEED_SIZE]
    (OUT / "places.xml").write_text(rss(newest(place_items), dates, "Korea Plainly: places to visit",
                                        "Places worth visiting across Korea, for first-time visitors."), encoding="utf-8")
    uploaded = set(json.loads(UPLOADED.read_text(encoding="utf-8")).get("slugs", [])) if UPLOADED.exists() else set()
    new_guides = [i for i in guide_items if i["slug"] not in uploaded]
    (OUT / "guides.xml").write_text(rss(newest(new_guides), dates, "Korea Plainly: guides",
                                        "Plain-English guides for first-time visitors to Korea."), encoding="utf-8")
    print(f"make_pins: {len(items)} pins ({len(place_items)} places), {made} drawn; feeds: "
          f"{min(len(place_items), FEED_SIZE)} places, {len(new_guides)} new guides")


if __name__ == "__main__":
    main()

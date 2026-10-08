from pathlib import Path
import re

p = Path("guides.html")
s = p.read_text(encoding="utf-8")

mapping = {
    "korean-convenience-store-tips.html": ("thumb-auto-korean-convenience-store-tips.svg", "22"),
    "korea-recycling-guide.html": ("thumb-auto-korea-recycling-guide.svg", "23"),
    "korean-atm-guide.html": ("thumb-korean-atm-guide.svg", "24"),
    "korea-transit-card-guide.html": ("thumb-korea-transit-card-guide.svg", "25"),
    "seoul-bus-guide.html": ("thumb-seoul-bus-guide.svg", "26"),
    "best-time-seoul-attractions.html": ("thumb-best-time-seoul-attractions.svg", "27"),
}

for href, (image, number) in mapping.items():
    start = s.find(f'href="{href}"')
    if start == -1:
        continue
    end = s.find("</a>", start)
    if end == -1:
        continue
    block = s[start:end]
    block = re.sub(
        r"background-image:url\('[^']+'\)",
        f"background-image:url('{image}')",
        block,
        count=1,
    )
    block = re.sub(r"<span>\s*\d+\s*</span>", f"<span>{number}</span>", block, count=1)
    s = s[:start] + block + s[end:]

p.write_text(s, encoding="utf-8")
print("Guides thumbnails and numbering fixed.")

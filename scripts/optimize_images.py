#!/usr/bin/env python3
"""Shrink oversized photos in the site root (same file name, same format).

JPEGs wider than MAX_WIDTH are resized; large JPEGs are recompressed once and
tagged with a JPEG comment, so later runs skip them. Needs Pillow.
"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
MAX_WIDTH = 1600
QUALITY = 82
SKIP_BYTES = 350_000
MARK = b"kp-optimized"


def main():
    saved = 0
    for p in sorted(ROOT.glob("*")):
        if p.suffix.lower() not in {".jpg", ".jpeg"} or p.stat().st_size < SKIP_BYTES:
            continue
        before = p.stat().st_size
        with Image.open(p) as im:
            if im.info.get("comment") == MARK and im.width <= MAX_WIDTH:
                continue
            im = ImageOps.exif_transpose(im).convert("RGB")
            if im.width > MAX_WIDTH:
                im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
            tmp = p.with_suffix(".tmp.jpg")
            im.save(tmp, "JPEG", quality=QUALITY, optimize=True, progressive=True, comment=MARK)
        # Keep the new file even when it is not smaller, so it carries the
        # marker and is never recompressed again.
        tmp.replace(p)
        saved += before - p.stat().st_size
    print(f"optimize_images: saved {saved / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

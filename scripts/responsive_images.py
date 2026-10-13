#!/usr/bin/env python3
"""Smaller images for phones. Idempotent.

Photos are stored at up to 1600px wide (300-450 KB), but most are shown much
smaller: cards, thumbnails and phone screens. This step

  * makes WebP copies at 480, 800 and 1200px in img/ for every large JPEG a page
    uses, named after a hash of the original so a replaced photo gets new copies;
  * gives every <img> of such a photo a srcset/sizes, so each browser downloads
    the smallest copy that looks sharp (the original JPEG stays as the fallback
    and as the share image);
  * loads cover photos first (fetchpriority="high", no lazy loading);
  * does the same for the background photos in style.css with image-set();
  * deletes copies that nothing uses any more.
"""
import hashlib
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "img"
WIDTHS = (480, 800, 1200)
MIN_WIDTH = 900          # smaller originals are left alone
QUALITY = 72
COVER_SIZES = "(max-width: 860px) 100vw, 820px"
CARD_SIZES = "(max-width: 600px) 100vw, (max-width: 1000px) 50vw, 400px"

_cache = {}


def variants(name):
    """{width: 'img/x.w800.webp'} for a local JPEG, creating missing copies; {} if not worth it."""
    if name in _cache:
        return _cache[name]
    src = ROOT / name
    result = {}
    if src.suffix.lower() in (".jpg", ".jpeg") and src.is_file() and "/" not in name:
        data = src.read_bytes()
        digest = hashlib.md5(data).hexdigest()[:8]
        with Image.open(src) as im:
            width = im.width
            if width >= MIN_WIDTH:
                OUT.mkdir(exist_ok=True)
                for w in WIDTHS:
                    if w >= width:
                        continue
                    out = OUT / f"{src.stem}.{digest}.w{w}.webp"
                    if not out.exists():
                        copy = im.convert("RGB").resize((w, round(im.height * w / width)), Image.LANCZOS)
                        copy.save(out, "WEBP", quality=QUALITY, method=6)
                    result[w] = f"img/{out.name}"
                if result:
                    result[width] = name
    _cache[name] = result
    return result


def srcset(v):
    return ", ".join(f"{path} {w}w" for w, path in sorted(v.items()))


def fix_img(tag):
    src = re.search(r'\bsrc="([^"]+)"', tag)
    if not src:
        return tag
    v = variants(src.group(1))
    if not v:
        return tag
    cover = re.search(r'class="[^"]*\bcover\b', tag) is not None
    # remove what this step adds, then add it again in a fixed order (keeps reruns stable)
    new = re.sub(r'\s(?:srcset|sizes|fetchpriority|decoding)="[^"]*"', "", tag)
    attrs = f' srcset="{srcset(v)}" sizes="{COVER_SIZES if cover else CARD_SIZES}"'
    if cover:
        new = re.sub(r'\sloading="lazy"', "", new)
        attrs += ' fetchpriority="high"'
    else:
        attrs += ' decoding="async"'
    return re.sub(r"\s*/?>$", lambda m: attrs + m.group(0), new, count=1)


CSS_START = "/* kp-responsive: smaller WebP backgrounds, written by scripts/responsive_images.py */"
CSS_END = "/* /kp-responsive */"


def fix_css(css):
    """Overrides in one managed block at the top of style.css; the original rules are left untouched.
    The block uses !important so it wins over the later shorthand rules; other steps append at the end."""
    css = re.sub(re.escape(CSS_START) + r".*?" + re.escape(CSS_END) + r"\r?\n", "", css, flags=re.S)
    rules = []
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
        selector, body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S).strip(), m.group(2)
        if selector.startswith("@") or not selector:
            continue
        u = re.search(r'background(?:-image)?\s*:\s*url\(["\']?([^"\')]+\.jpe?g)["\']?\)', body)
        if not u:
            continue
        v = variants(u.group(1))
        best = v.get(1200) or v.get(800)
        if best and best != u.group(1):
            rules.append(f'{selector}{{background-image:image-set(url("{best}") type("image/webp"),'
                         f'url("{u.group(1)}") type("image/jpeg"))!important}}')
    if rules:
        css = CSS_START + "\n" + "\n".join(rules) + "\n" + CSS_END + "\n" + css
    return css


def main():
    changed = 0
    for p in sorted(ROOT.glob("*.html")):
        s = p.read_bytes().decode("utf-8")
        if "kp-redirect" in s:
            continue
        new = re.sub(r"<img\b[^>]*>", lambda m: fix_img(m.group(0)), s)
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    css_path = ROOT / "style.css"
    css = css_path.read_bytes().decode("utf-8")
    new_css = fix_css(css)
    if new_css != css:
        css_path.write_bytes(new_css.encode("utf-8"))
    used = {path for v in _cache.values() for path in v.values() if path.startswith("img/")}
    removed = 0
    for f in OUT.glob("*.webp") if OUT.exists() else []:
        if f"img/{f.name}" not in used:
            f.unlink()
            removed += 1
    print(f"responsive_images: {changed} page(s) updated, {len(used)} copies in use, {removed} unused removed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Kkachi, the Korea Plainly magpie, on the site. Idempotent.

  * kkachi.png: a small web copy of the mascot (from scripts/mascot/kkachi_closed.png).
  * Articles: a short sign-off from Kkachi at the end, with a link to our videos.
  * About: a "Meet Kkachi" section before "How our guides are made".
  * 404: Kkachi next to the "couldn't find that page" message.

Every insertion is a managed block (<!-- kp-kkachi --> ... <!-- /kp-kkachi -->) that is
removed and written again on each run.
"""
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scripts" / "mascot" / "kkachi_closed.png"
WEB = ROOT / "kkachi.png"
START, END = "<!-- kp-kkachi -->", "<!-- /kp-kkachi -->"
YOUTUBE = "https://www.youtube.com/@KoreaPlainly"
SUBSCRIBE = "https://www.youtube.com/@KoreaPlainly?sub_confirmation=1"

STYLE = ("<style>.kp-kkachi{display:flex;gap:16px;align-items:center;margin:34px 0 8px;padding:16px 18px;"
         "border:1px solid rgba(20,28,42,.12);border-radius:14px;background:#fffdf8}"
         ".kp-kkachi img{width:72px;height:auto;flex:none;margin:0}"
         ".kp-kkachi p{margin:0;font-size:15px;line-height:1.6;color:#4b5363}"
         ".kp-kkachi a{color:#c9413a;font-weight:600}"
         ".kp-kkachi .kp-sub{margin-top:10px}"
         ".kp-sub{display:inline-flex;align-items:center;gap:8px;background:#c9413a;color:#fff!important;font-weight:700;font-size:14px;line-height:1;padding:10px 16px;border-radius:999px;text-decoration:none!important;white-space:nowrap}.kp-sub:before{content:'';border-style:solid;border-width:6px 0 6px 10px;border-color:transparent transparent transparent #fff}.kp-sub:hover{background:#a8332d}</style>")


def web_copy():
    """kkachi.png at 260px high, written only when missing or when the source drawing changes."""
    if not SRC.exists():
        return False
    if WEB.exists() and WEB.stat().st_mtime >= SRC.stat().st_mtime:
        return True
    with Image.open(SRC) as im:
        im = im.convert("RGBA")
        im = im.resize((round(im.width * 260 / im.height), 260), Image.LANCZOS)
        im.save(WEB, optimize=True)
    return True


def strip(s):
    return re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\r?\n?", "", s, flags=re.S)


def block(nl, inner):
    return nl.join([START, inner, END]) + nl


def article_box(nl):
    return block(nl, STYLE + '<aside class="kp-kkachi"><img src="kkachi.png" alt="Kkachi, the Korea Plainly magpie" '
                     'width="72" height="78" loading="lazy">'
                     "<p><strong>Kkachi says:</strong> in Korea, a magpie's call is said to mean good news and welcome "
                     f'guests are on the way. Have a wonderful trip! New one-minute Korea tips every Monday, Wednesday and Friday on '
                     f'<a href="{YOUTUBE}" target="_blank" rel="noopener">YouTube</a>.<br>'
                     f'<a class="kp-sub" href="{SUBSCRIBE}" target="_blank" rel="noopener">Subscribe on YouTube</a></p></aside>')


def about_section(nl):
    return block(nl, '<div style="border-top:1px solid var(--line);margin-top:35px;padding-top:35px;display:flex;'
                     'gap:22px;align-items:center;flex-wrap:wrap">'
                     '<img src="kkachi.png" alt="Kkachi, the Korea Plainly magpie" width="110" height="119" '
                     'loading="lazy" style="flex:none">'
                     '<div style="flex:1;min-width:220px">'
                     '<h2 style="font-size:34px;letter-spacing:-.05em;margin:0 0 15px;">Meet Kkachi</h2>'
                     '<p style="font-size:15px;line-height:1.8;color:var(--muted);">Kkachi is our mascot, a Korean '
                     'magpie (<em>kkachi</em>) in a red scarf, with a map in hand. In Korea, a magpie calling '
                     'outside your house is said to mean good news or that welcome guests are coming, which is how '
                     'we hope visitors feel. You will meet Kkachi in our '
                     f'<a href="{YOUTUBE}" target="_blank" rel="noopener" style="color:var(--red)">video guides</a>.</p>'
                     "</div></div>")


def not_found(nl):
    return block(nl, '<p><img src="kkachi.png" alt="Kkachi, the Korea Plainly magpie, looking at a map" width="110" '
                     'height="119" style="margin:10px 0 0"></p>'
                     '<p style="color:#5b6472">Kkachi checked the map too.</p>')


def main():
    if not web_copy():
        print("site_mascot: no mascot drawing, skipped")
        return
    changed = 0
    for p in sorted(ROOT.glob("*.html")):
        s = p.read_bytes().decode("utf-8")
        if "kp-redirect" in s:
            continue
        nl = "\r\n" if "\r\n" in s else "\n"
        new = strip(s)
        if p.name == "about.html":
            m = re.search(r'<div style="border-top:[^"]*">\s*<h2 id="how-we-work"', new)
            if m:
                new = new[:m.start()] + about_section(nl) + new[m.start():]
        elif p.name == "404.html":
            m = re.search(r'<div class="links">', new)
            if m:
                new = new[:m.start()] + not_found(nl) + new[m.start():]
        elif 'class="kp-article"' in new and "<article" in new:
            art = new.find("<article")
            rel = re.search(r'<section class="related-guides">', new[art:])
            end = re.search(r"</article>", new[art:])
            at = art + (rel.start() if rel else end.start() if end else -1)
            if at > art:
                new = new[:at] + article_box(nl) + new[at:]
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    print(f"site_mascot: {changed} page(s) updated")


if __name__ == "__main__":
    main()

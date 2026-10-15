#!/usr/bin/env python3
"""The videos page (videos.html) and a "Watch" section on the home page, from content/videos.json. Idempotent.

Long-form videos (16:9) come first, then Shorts (9:16), newest first. Each card links to
the guide the video comes from (where it plays at the top or bottom of the article) and
to the video on YouTube.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNEL = "https://www.youtube.com/@KoreaPlainly"
START, END = "<!-- kp-videos -->", "<!-- /kp-videos -->"
HOME_START, HOME_END = "<!-- kp-home-videos -->", "<!-- /kp-home-videos -->"

STYLE = ("<style>.kp-vgrid{display:grid;gap:22px;margin:34px 0}.kp-vgrid.long{grid-template-columns:repeat(2,1fr)}"
         ".kp-vgrid.short{grid-template-columns:repeat(4,1fr)}"
         ".kp-vcard{display:block;color:inherit;text-decoration:none}"
         ".kp-vcard .pic{position:relative;display:block;overflow:hidden;border-radius:12px;background:#111}"
         ".kp-vgrid.long .pic{aspect-ratio:16/9}.kp-vgrid.short .pic{aspect-ratio:9/16}"
         ".kp-vcard img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;margin:0}"
         ".kp-vcard .len{position:absolute;right:8px;bottom:8px;background:rgba(0,0,0,.75);color:#fff;font-size:12px;"
         "font-weight:700;padding:2px 7px;border-radius:5px}"
         ".kp-vcard .play{position:absolute;left:50%;top:50%;width:54px;height:54px;margin:-27px 0 0 -27px;border-radius:50%;"
         "background:rgba(201,65,58,.92)}.kp-vcard .play:after{content:'';position:absolute;left:21px;top:16px;"
         "border-style:solid;border-width:11px 0 11px 17px;border-color:transparent transparent transparent #fff}"
         ".kp-vcard b{display:block;font-size:17px;line-height:1.35;margin:10px 0 4px;letter-spacing:-.01em}"
         ".kp-vlinks{font-size:13px;color:#5b6472}.kp-vlinks a{color:#c9413a;font-weight:600}"
         ".kp-vhead{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-top:40px}"
         ".kp-vhead h2{margin:0;font-size:30px;letter-spacing:-.03em}"
         "@media(max-width:800px){.kp-vgrid.long{grid-template-columns:1fr}.kp-vgrid.short{grid-template-columns:repeat(2,1fr)}}"
         "</style>")


def all_videos():
    data = json.loads((ROOT / "content" / "videos.json").read_text(encoding="utf-8"))
    out = []
    for slug, entries in data.items():
        for v in entries if isinstance(entries, list) else [entries]:
            if (ROOT / v["poster"]).exists() and (ROOT / f"{slug}.html").exists():
                out.append({**v, "slug": slug, "long": v.get("format") == "long"})
    return sorted(out, key=lambda v: v.get("uploaded", ""), reverse=True)


def length(seconds):
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


def card(v):
    url = f"https://www.youtube.com/watch?v={v['youtube']}" if v["long"] else f"https://www.youtube.com/shorts/{v['youtube']}"
    t = html.escape(v["title"])
    size = 'width="640" height="360"' if v["long"] else 'width="270" height="480"'
    return (f'<div class="kp-vcard"><a class="pic" href="{v["slug"]}.html"><img src="{v["poster"]}" alt="{t}" {size} '
            f'loading="lazy"><span class="play"></span><span class="len">{length(v["seconds"])}</span></a>'
            f'<a href="{v["slug"]}.html" style="color:inherit"><b>{t}</b></a>'
            f'<span class="kp-vlinks"><a href="{v["slug"]}.html">Read the guide</a> · '
            f'<a href="{url}" target="_blank" rel="noopener">Watch on YouTube</a></span></div>')


def grid(videos, kind):
    return f'<div class="kp-vgrid {kind}">' + "".join(card(v) for v in videos) + "</div>"


def put(s, start, end, inner, anchor=None):
    """Replace the managed block, or insert it before `anchor` the first time."""
    nl = "\r\n" if "\r\n" in s else "\n"
    blockText = start + nl + inner + nl + end
    if start in s:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda m: blockText, s, count=1, flags=re.S)
    if anchor and anchor in s:
        return s.replace(anchor, blockText + nl + anchor, 1)
    return s


def main():
    videos = all_videos()
    longs = [v for v in videos if v["long"]]
    shorts = [v for v in videos if not v["long"]]
    page = ROOT / "videos.html"
    changed = 0
    if page.exists():
        inner = STYLE
        if longs:
            inner += f'<div class="kp-vhead"><h2>Full travel plans</h2></div>{grid(longs, "long")}'
        if shorts:
            inner += f'<div class="kp-vhead"><h2>One-minute guides</h2></div>{grid(shorts, "short")}'
        inner += (f'<p style="margin:30px 0 0;font-size:15px">New videos every week: '
                  f'<a href="{CHANNEL}" target="_blank" rel="noopener" style="color:var(--red);font-weight:700">'
                  f'subscribe to Korea Plainly on YouTube</a>.</p>')
        s = page.read_text(encoding="utf-8")
        new = put(s, START, END, inner)
        if new != s:
            page.write_text(new, encoding="utf-8")
            changed += 1
    home = ROOT / "index.html"
    s = home.read_bytes().decode("utf-8")
    pick = longs[:2] + shorts[:4]
    inner = ""
    if pick:
        inner = (STYLE + '<section class="wrap section" id="videos"><div class="heading"><div><p class="kicker"><i></i> WATCH</p>'
                 '<h2>Korea in<br><em>a few minutes.</em></h2></div><a class="view-all" href="videos.html">All videos →</a></div>'
                 + (grid(longs[:2], "long") if longs else "") + (grid(shorts[:4], "short") if shorts else "") + "</section>")
    new = put(s, HOME_START, HOME_END, inner, anchor='<section class="quote">')
    if new != s:
        home.write_bytes(new.encode("utf-8"))
        changed += 1
    print(f"video_hub: {len(longs)} long-form, {len(shorts)} Shorts, {changed} page(s) updated")


if __name__ == "__main__":
    main()

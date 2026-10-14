#!/usr/bin/env python3
"""Show our YouTube Shorts inside the articles they come from. Idempotent.

content/videos.json lists the uploaded videos (one, or a list of several per article;
"format": "long" for a 16:9 video, "place": "end" to show it near the end of the article):

    {"seoul-3-day-itinerary": {"youtube": "0Adi6IjLADs", "title": "...", "uploaded": "2026-10-14T08:30:00+09:00",
                               "seconds": 57, "poster": "img/video-seoul-3-day-itinerary.jpg"}}

Each article gets one managed block (<!-- kp-video --> ... <!-- /kp-video -->) just
before its first section. It shows our own poster frame and loads the YouTube
player only when the reader taps it, so the page stays fast; without JavaScript
the poster simply links to the video. The block carries VideoObject structured
data so search engines can show the video with the article.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://korea-plainly.com"
START, END = "<!-- kp-video -->", "<!-- /kp-video -->"
STYLE = ("<style>.kp-video{margin:1.5rem auto;max-width:300px;text-align:center}"
         ".kp-video .kp-video-box{position:relative;display:block;aspect-ratio:9/16;border-radius:14px;overflow:hidden;"
         "background:#111}"
         ".kp-video img,.kp-video iframe{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border:0;margin:0}"
         ".kp-video .kp-play{position:absolute;left:50%;top:30%;width:72px;height:72px;margin:-36px 0 0 -36px;"
         "border-radius:50%;background:rgba(201,65,58,.92);box-shadow:0 4px 18px rgba(0,0,0,.35)}"
         ".kp-video .kp-play:after{content:'';position:absolute;left:29px;top:22px;border-style:solid;"
         "border-width:14px 0 14px 22px;border-color:transparent transparent transparent #fff}"
         ".kp-video p{font-size:.9rem;margin:.5rem 0 0;color:#5b6472}"
         ".kp-video.kp-long{max-width:820px}.kp-video.kp-long .kp-video-box{aspect-ratio:16/9}"
         ".kp-video.kp-long .kp-play{top:50%}</style>")
SCRIPT = ("<script>document.querySelectorAll('.kp-video-box[data-yt]').forEach(function(a){a.addEventListener('click',"
          "function(e){e.preventDefault();var f=document.createElement('iframe');f.src='https://www.youtube-nocookie.com/embed/'"
          "+a.dataset.yt+'?autoplay=1&playsinline=1&rel=0';f.title=a.getAttribute('aria-label');"
          "f.allow='autoplay; encrypted-media; picture-in-picture';f.allowFullscreen=true;"
          "var d=document.createElement('div');d.className='kp-video-box';d.appendChild(f);a.replaceWith(d);"
          "});});</script>")


def block(slug, v, nl, first=True):
    vid, title = v["youtube"], v["title"]
    long = v.get("format") == "long"          # a long-form video (16:9) rather than a Short
    url = f"https://www.youtube.com/watch?v={vid}" if long else f"https://www.youtube.com/shorts/{vid}"
    size = 'width="1280" height="720"' if long else 'width="540" height="960"'
    data = {"@context": "https://schema.org", "@type": "VideoObject", "name": title,
            "description": v.get("description", title), "thumbnailUrl": [f"{BASE}/{v['poster']}"],
            "uploadDate": v["uploaded"], "duration": f"PT{int(v['seconds'])}S",
            "embedUrl": f"https://www.youtube.com/embed/{vid}", "url": url}
    t = html.escape(title, quote=True)
    return nl.join([
        START,
        f'<figure class="kp-video{" kp-long" if long else ""}">{STYLE if first else ""}',
        f'<a class="kp-video-box" href="{url}" data-yt="{vid}" aria-label="Play video: {t}" target="_blank" rel="noopener">'
        f'<img src="{v["poster"]}" alt="{t}" {size} loading="lazy"><span class="kp-play"></span></a>',
        f'<p>{html.escape(v.get("caption", "Watch the one-minute version"))}</p>',
        f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>{SCRIPT if first else ""}',
        "</figure>",
        END,
    ])


def main():
    path = ROOT / "content" / "videos.json"
    videos = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    changed = 0
    for p in sorted(ROOT.glob("*.html")):
        s = p.read_bytes().decode("utf-8")
        if "kp-redirect" in s:
            continue
        nl = "\r\n" if "\r\n" in s else "\n"
        new = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\r?\n?", "", s, flags=re.S)
        entries = videos.get(p.stem) or []
        entries = [e for e in (entries if isinstance(entries, list) else [entries]) if (ROOT / e["poster"]).exists()]
        art = new.find("<article")
        for k, v in enumerate(entries):
            # "top" (default): just after the table of contents; "end": before the FAQ, or the last section
            if art < 0:
                break
            body = new[art:]
            if v.get("place") == "end":
                spot = (re.search(r'<h2[^>]*id="faq"', body) or re.search(r"<h2>Related guides", body)
                        or re.search(r"</article>", body))
                at = art + spot.start() if spot else -1
            else:
                toc = re.search(r"<nav class=\"kp-toc\".*?</nav>\r?\n?", body, re.S)
                h2 = re.search(r"<h2\b", body)
                at = art + (toc.end() if toc else h2.start() if h2 else -1)
            if at > art:
                new = new[:at] + block(p.stem, v, nl, first=k == 0) + nl + new[at:]
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    print(f"embed_videos: {changed} page(s) updated, {len(videos)} video(s) listed")


if __name__ == "__main__":
    main()

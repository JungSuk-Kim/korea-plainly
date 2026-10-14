#!/usr/bin/env python3
"""Make a long-form YouTube video (1920x1080) from a script in content/longform/<name>.json.

    python scripts/make_longform.py content/longform/seoul-3-day-itinerary.json

The script is a list of chapters; each chapter has segments of narration, and each
segment shows one or more visuals in turn while it is spoken:

    {"image": "photo-x.jpg"}                         a site photo, slowly panned
    {"photo_query": "...", "require": [...]}         a Wikimedia Commons photo of exactly that place
    {"map": "day1"}                                  an OpenStreetMap map with the day's stops (route drawn live)
    {"card": {"big": ..., "title": ..., "sub": ...}} a title card
    {"list": {"heading": ..., "items": [...]}}       a checklist, items appearing one by one

Narration is OpenAI text-to-speech; subtitles are timed to it; music ducks under it.
Writes _shorts/<name>-long.mp4, a description with chapters and credits, and a thumbnail.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_short import (FONTS, NAVY, RED, WHITE, CREAM, chunks, duration, font, pick_music, run,  # noqa: E402
                        slide_photo, tts, word_times, wrap)

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1920, 1080, 30
OUT = ROOT / "_shorts"
TILES = OUT / "tiles"
GAP = 0.45                     # pause after each segment's narration
WEIGHT = {"card": 0.8, "map": 1.4, "list": 1.2}


# ---------------------------------------------------------------- visuals

def cover(im, w, h):
    """Scale and centre-crop to exactly w x h."""
    s = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def label_png(label, path):
    """Place name in the top-left corner (kicker on a red tab, title below), brand top-right."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if label:
        kf, tf = font(30), font(56)
        tw = max(d.textlength(label.get("kicker", ""), font=kf) + 40, d.textlength(label["title"], font=tf) + 60)
        d.rounded_rectangle([48, 48, 48 + tw, 196], radius=14, fill=(12, 18, 30, 200))
        if label.get("kicker"):
            kw = d.textlength(label["kicker"], font=kf)
            d.rounded_rectangle([72, 66, 72 + kw + 28, 108], radius=8, fill=RED)
            d.text((86, 70), label["kicker"], font=kf, fill=WHITE)
        d.text((74, 118), label["title"], font=tf, fill=WHITE)
    brand = "korea-plainly.com"
    d.text((W - 48 - d.textlength(brand, font=font(30, False)), 52), brand, font=font(30, False), fill=(255, 255, 255, 190))
    img.save(path)


def clip_photo(path, secs, idx, overlay, out):
    """Slow pan and zoom across a photo, with the label on top."""
    with Image.open(ROOT / path) as im:
        big = cover(im.convert("RGB"), int(W * 1.12), int(H * 1.12))
    src = out.with_suffix(".jpg")
    big.save(src, quality=92)
    dx, dy = big.width - W, big.height - H
    # alternate the direction of travel from one photo to the next
    sx, ex = (0, dx) if idx % 2 == 0 else (dx, 0)
    sy, ey = (dy, 0) if idx % 3 == 0 else (0, dy)
    x = f"{sx}+({ex}-{sx})*t/{secs:.2f}"
    y = f"{sy}+({ey}-{sy})*t/{secs:.2f}"
    run(["ffmpeg", "-y", "-loop", "1", "-t", f"{secs:.2f}", "-i", str(src), "-loop", "1", "-t", f"{secs:.2f}", "-i", str(overlay),
         "-filter_complex", f"[0]fps={FPS},crop={W}:{H}:x='{x}':y='{y}'[bg];[bg][1]overlay=0:0,format=yuv420p[v]",
         "-map", "[v]", "-t", f"{secs:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", str(out)])


def backdrop(photo):
    """A dark, blurred version of a photo for cards and lists."""
    if photo:
        with Image.open(ROOT / photo) as im:
            bg = cover(im.convert("RGB"), W, H).filter(ImageFilter.GaussianBlur(28))
        bg = ImageEnhance.Brightness(bg).enhance(0.35)
    else:
        bg = Image.new("RGB", (W, H), NAVY)
    shade = Image.new("RGB", (W, H), NAVY)
    return Image.blend(bg, shade, 0.45)


def card_png(card, photo, path):
    img = backdrop(photo)
    d = ImageDraw.Draw(img)
    y = 360
    for text, f, col, gap in ((card["big"], font(124), WHITE, 150), (card.get("title", ""), font(64, False), CREAM, 96),
                             (card.get("sub", ""), font(46), RED, 0)):
        for line in wrap(d, text, f, W - 300):
            d.text(((W - d.textlength(line, font=f)) / 2, y), line, font=f, fill=col)
            y += gap or 60
    d.rectangle([W / 2 - 60, 330, W / 2 + 60, 338], fill=RED)
    img.save(path)


def clip_still(png, secs, out, zoom=True):
    zf = f",zoompan=z='1+0.04*on/{int(secs * FPS)}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}" if zoom else ""
    run(["ffmpeg", "-y", "-loop", "1", "-t", f"{secs:.2f}", "-i", str(png), "-vf",
         f"fps={FPS}{zf},fade=t=in:st=0:d=0.3,format=yuv420p", "-t", f"{secs:.2f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", str(out)])


def frames_clip(frames_dir, fps, secs, out):
    run(["ffmpeg", "-y", "-framerate", str(fps), "-i", str(frames_dir / "f%04d.png"), "-vf",
         f"fps={FPS},format=yuv420p", "-t", f"{secs:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", str(out)])


def list_clip(spec, photo, secs, out, tmp):
    """A checklist; the items appear one by one across the first 80% of the time."""
    base = backdrop(photo)
    frames = tmp / f"{out.stem}_frames"
    frames.mkdir()
    items = spec["items"]
    steps = len(items) + 1
    fps = 10
    n = int(secs * fps) + 1
    for i in range(n):
        shown = min(len(items), int((i / fps) / (secs * 0.8 / steps)))
        img = base.copy()
        d = ImageDraw.Draw(img)
        d.text((180, 170), spec["heading"], font=font(80), fill=WHITE)
        d.rectangle([180, 280, 300, 288], fill=RED)
        y = 350
        for k, item in enumerate(items[:shown]):
            d.ellipse([180, y + 8, 230, y + 58], fill=RED)
            d.text((193 if k < 9 else 186, y + 10), str(k + 1), font=font(38), fill=WHITE)
            for j, line in enumerate(wrap(d, item, font(54, False), W - 460)):
                d.text((270, y + j * 64), line, font=font(54, False), fill=WHITE)
            y += 64 * len(wrap(d, item, font(54, False), W - 460)) + 46
        img.save(frames / f"f{i:04d}.png")
    frames_clip(frames, fps, secs, out)


# ---------------------------------------------------------------- maps (OpenStreetMap)

def lonlat_px(lon, lat, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def tile(z, x, y):
    """One OpenStreetMap tile, cached (a video uses a few dozen; see the OSM tile usage policy)."""
    path = TILES / f"{z}_{x}_{y}.png"
    if not path.exists():
        import requests
        r = requests.get(f"https://tile.openstreetmap.org/{z}/{x}/{y}.png", timeout=30,
                         headers={"User-Agent": "KoreaPlainlyVideo/1.0 (https://korea-plainly.com; koreaplainly@gmail.com)"})
        r.raise_for_status()
        TILES.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return Image.open(path).convert("RGB")


def base_map(stops):
    """(map image W x H, function lon/lat -> pixel): the stops fill most of the frame.
    Tiles come from one zoom level closer than needed and are scaled down, so the map stays sharp."""
    lons, lats = [s["lon"] for s in stops], [s["lat"] for s in stops]
    z = 16
    x0, y1 = lonlat_px(min(lons), min(lats), z)
    x1, y0 = lonlat_px(max(lons), max(lats), z)
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    while z > 10 and (w > W * 1.3 or h > H * 1.1):      # too big even after scaling down: go out a level
        z -= 1
        x0, x1, y0, y1, w, h = x0 / 2, x1 / 2, y0 / 2, y1 / 2, w / 2, h / 2
    r = min(W * 0.66 / w, H * 0.56 / h, 1.0)            # scale factor applied to the tile mosaic
    cw, chh = W / r, H / r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 30 / r     # a little lower: the label box sits at the top
    left, top = cx - cw / 2, cy - chh / 2
    big = Image.new("RGB", (math.ceil(cw), math.ceil(chh)))
    for tx in range(int(left // 256), int((left + cw) // 256) + 1):
        for ty in range(int(top // 256), int((top + chh) // 256) + 1):
            try:
                t = tile(z, tx, ty)
            except Exception as e:  # no map today: a plain background still shows the route
                print(f"map tile {z}/{tx}/{ty} failed: {e}")
                t = Image.new("RGB", (256, 256), (226, 230, 236))
            big.paste(t, (int(tx * 256 - left), int(ty * 256 - top)))
    img = big.resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Color(img).enhance(0.35)
    img = ImageEnhance.Brightness(img).enhance(0.92)
    d = ImageDraw.Draw(img)
    note = "© OpenStreetMap contributors"
    f = font(22, False)
    d.rectangle([W - d.textlength(note, font=f) - 24, H - 40, W, H], fill=(255, 255, 255))
    d.text((W - d.textlength(note, font=f) - 12, H - 35), note, font=f, fill=(60, 60, 60))

    def px(lon, lat):
        x, y = lonlat_px(lon, lat, z)
        return (x - left) * r, (y - top) * r
    return img, px


def map_clip(m, label, secs, out, tmp):
    stops, route = m["stops"], m.get("route")
    base, px = base_map(stops)
    pts = [px(s["lon"], s["lat"]) for s in stops]
    over = Image.open(label).convert("RGBA")
    frames = tmp / f"{out.stem}_frames"
    frames.mkdir()
    fps = 15
    n = int(secs * fps) + 1
    seg_len = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg_len) or 1
    for i in range(n):
        p = min(1, (i / fps) / (secs * 0.75))       # progress of the route / reveal
        img = base.copy().convert("RGBA")
        d = ImageDraw.Draw(img)
        reached = 1
        if route and len(pts) > 1:
            left = p * total
            path = [pts[0]]
            for k, L in enumerate(seg_len):
                if left >= L:
                    path.append(pts[k + 1])
                    left -= L
                    reached = k + 2
                else:
                    a, b = pts[k], pts[k + 1]
                    path.append((a[0] + (b[0] - a[0]) * left / L, a[1] + (b[1] - a[1]) * left / L))
                    break
            d.line(path, fill=(255, 255, 255, 255), width=14, joint="curve")
            d.line(path, fill=RED + (255,), width=8, joint="curve")
        else:
            reached = max(1, math.ceil(p * len(pts)))
        for k, ((x, y), s) in enumerate(zip(pts, stops)):
            if k >= reached:
                continue
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=WHITE)
            d.ellipse([x - 17, y - 17, x + 17, y + 17], fill=RED)
            num = str(k + 1)
            d.text((x - d.textlength(num, font=font(26)) / 2, y - 15), num, font=font(26), fill=WHITE)
            f = font(34)
            tw = d.textlength(s["name"], font=f)
            lx = x + 30 if x + 30 + tw + 24 < W - 20 else x - 30 - tw - 24
            d.rounded_rectangle([lx, y - 26, lx + tw + 24, y + 26], radius=10, fill=(12, 18, 30, 225))
            d.text((lx + 12, y - 20), s["name"], font=f, fill=WHITE)
        if m.get("note") and p >= 1:
            f = font(36)
            tw = d.textlength(m["note"], font=f)
            d.rounded_rectangle([W / 2 - tw / 2 - 26, H - 150, W / 2 + tw / 2 + 26, H - 90], radius=12, fill=RED + (235,))
            d.text((W / 2 - tw / 2, H - 143), m["note"], font=f, fill=WHITE)
        Image.alpha_composite(img, over).convert("RGB").save(frames / f"f{i:04d}.png")
    frames_clip(frames, fps, secs, out)


# ---------------------------------------------------------------- subtitles

def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def write_ass(lines, path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Carlito,58,&H00FFFFFF,&H00FFFFFF,&H00141008,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,160,160,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{t}\n" for t, a, b in lines)
    path.write_text(head + body, encoding="utf-8")


# ---------------------------------------------------------------- thumbnail

def thumbnail(spec, photo, path):
    with Image.open(ROOT / photo) as im:
        img = cover(im.convert("RGB"), 1280, 720)
    img = ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(1.25)).enhance(1.1)
    shade = Image.new("L", (1280, 720))
    for x in range(1280):
        for_y = int(max(0, 1 - x / 820) * 210)
        ImageDraw.Draw(shade).line([(x, 0), (x, 720)], fill=for_y)
    img.paste(Image.new("RGB", (1280, 720), (8, 12, 22)), (0, 0), shade)
    d = ImageDraw.Draw(img)
    t = spec.get("thumb", {"big": "3 DAYS", "mid": "IN SEOUL", "small": "First-timer's plan"})
    d.text((56, 150), t["big"], font=font(170), fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((60, 330), t["mid"], font=font(110), fill=(255, 214, 64), stroke_width=4, stroke_fill=(0, 0, 0))
    d.rounded_rectangle([60, 480, 60 + d.textlength(t["small"], font=font(50)) + 40, 556], radius=12, fill=RED)
    d.text((80, 488), t["small"], font=font(50), fill=WHITE)
    img.save(path, quality=92)


# ---------------------------------------------------------------- main

def main():
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    name = spec_path.stem + "-long"
    OUT.mkdir(exist_ok=True)
    taken, used_photos = set(), []
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        clips, wavs, subs, chapters = [], [], [], []
        clock, n = 0.0, 0
        for ch in spec["chapters"]:
            chapters.append((clock, ch["name"]))
            for seg in ch["segments"]:
                n += 1
                voice = tmp / f"v{n:03d}.mp3"
                tts(seg["voice"], voice)
                secs = duration(voice) + GAP
                for text, a, b in chunks(word_times(voice, seg["voice"]), max_words=9, max_chars=46):
                    subs.append((text, clock + a, clock + min(b, secs - 0.05)))
                wav = tmp / f"v{n:03d}.wav"
                run(["ffmpeg", "-y", "-i", str(voice), "-af", "apad", "-t", f"{secs:.3f}", "-ar", "44100", "-ac", "2", str(wav)])
                wavs.append(wav)
                # the segment's photos (resolved first, so cards and lists can use one as a backdrop)
                for v in seg["show"]:
                    if "image" in v or "photo_query" in v:
                        v["file"] = slide_photo(v, taken, spec.get("fallback"))
                        used_photos.append(v["file"])
                seg_photo = next((v["file"] for v in seg["show"] if "file" in v), used_photos[-1] if used_photos else None)
                weights = [WEIGHT.get(next(iter(k for k in v if k in WEIGHT), ""), 1.0) for v in seg["show"]]
                label = tmp / f"l{n:03d}.png"
                label_png(seg.get("label"), label)
                done = 0.0
                for k, (v, w) in enumerate(zip(seg["show"], weights)):
                    part = secs - done if k == len(weights) - 1 else round(secs * w / sum(weights), 2)
                    done += part
                    out = tmp / f"c{n:03d}_{k}.mp4"
                    if "file" in v:
                        clip_photo(v["file"], part, n + k, label, out)
                    elif "card" in v:
                        png = tmp / f"card{n:03d}_{k}.png"
                        card_png(v["card"], seg_photo, png)
                        clip_still(png, part, out)
                    elif "map" in v:
                        map_clip(spec["maps"][v["map"]], label, part, out, tmp)
                    elif "list" in v:
                        list_clip(v["list"], seg_photo, part, out, tmp)
                    clips.append(out)
                clock += secs
                print(f"segment {n}: {secs:.1f}s ({clock / 60:.1f} min)", flush=True)
        # join pictures and narration
        (tmp / "v.txt").write_text("".join(f"file '{c}'\n" for c in clips))
        (tmp / "a.txt").write_text("".join(f"file '{w}'\n" for w in wavs))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "v.txt"), "-c", "copy", str(tmp / "video.mp4")])
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "a.txt"), "-c", "copy", str(tmp / "voice.wav")])
        ass = tmp / "subs.ass"
        write_ass(subs, ass)
        track, music = pick_music(spec, spec_path.stem)
        fade = f"afade=t=in:d=2,afade=t=out:st={max(clock - 4, 0):.2f}:d=4"
        graph = (f"[1:a]asplit=2[v][key];[2:a]volume=0.22,{fade}[m];"
                 "[m][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=500[duck];"
                 "[v][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a];"
                 f"[0:v]subtitles={ass}:fontsdir={FONTS}[vs]")
        run(["ffmpeg", "-y", "-i", str(tmp / "video.mp4"), "-i", str(tmp / "voice.wav"), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex", graph, "-map", "[vs]", "-map", "[a]", "-t", f"{clock:.2f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
             "-movflags", "+faststart", str(OUT / f"{name}.mp4")])
        def srt_time(x):
            return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x % 1 * 1000)) % 1000:03d}"
        srt = "".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n\n" for i, (t, a, b) in enumerate(subs, 1))
        (OUT / f"{name}.srt").write_text(srt, encoding="utf-8")
    thumbnail(spec, spec.get("thumb_photo", used_photos[0]), OUT / f"{name}-thumb.jpg")
    # description: chapters (YouTube needs 0:00 first), links and credits
    from make_short import credits
    stamp = lambda s: f"{int(s // 60)}:{int(s % 60):02d}"  # noqa: E731
    credit_spec = {"slides": [{"file": f} for f in dict.fromkeys(used_photos)]}
    desc = [spec["title"], "", spec.get("intro", "A relaxed three-day plan for your first trip to Seoul, with the route for "
            "every day, what to eat, and the small mistakes to avoid."), "",
            f"Full guide with links for every stop: https://korea-plainly.com/{spec['article']}.html", "", "Chapters:"]
    desc += [f"{stamp(s)} {c}" for s, c in chapters]
    desc += ["", spec.get("hashtags", "#Seoul #KoreaTravel #SeoulItinerary #Korea"), "", "Photos (Wikimedia Commons, text added):"]
    desc += [c.replace("Photo: ", "• ") for c in credits(credit_spec)]
    desc += ["", "Maps: © OpenStreetMap contributors (openstreetmap.org/copyright)", "", "Music:",
             f'"{track}" Kevin MacLeod (incompetech.com)', "Licensed under Creative Commons: By Attribution 4.0 License",
             "http://creativecommons.org/licenses/by/4.0/", "", "Narration is AI-generated."]
    (OUT / f"{name}.txt").write_text("\n".join(desc) + "\n", encoding="utf-8")
    print(f"{name}.mp4: {clock / 60:.1f} min, {len(chapters)} chapters")


if __name__ == "__main__":
    main()

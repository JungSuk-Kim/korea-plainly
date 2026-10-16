#!/usr/bin/env python3
"""Make a vertical short video (1080x1920) from a script in content/shorts/<name>.json.

    python scripts/make_short.py content/shorts/seoul-3-day-itinerary.json            # silent, captions only
    python scripts/make_short.py content/shorts/seoul-3-day-itinerary.json --voice    # AI narration + spoken subtitles (OPENAI_API_KEY)

Each slide pans slowly across one of the site's photos with a caption on top; the
last slide is an end card. Output goes to _shorts/ (not published on the site),
with a description file that credits every photo, as their licences require.
"""
import argparse
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / "fonts"
W, H, FPS = 1080, 1920, 30
NAVY, RED, WHITE, CREAM = (23, 36, 60), (201, 65, 58), (255, 255, 255), (247, 245, 239)
SILENT_SECONDS = 3.6
PHOTOS = ROOT / "_shorts" / "photos"
PHOTO_LOG = ROOT / "content" / "shorts" / "photos.json"   # {query: {file, source, credit}}


def slide_photo(slide, taken, fallback=None):
    """The slide's photo: "image" (one of the site's photos) or "photo_query", a Wikimedia Commons search
    for a photo of exactly the place the narration names. Found photos are kept, so a rerun uses the same one."""
    if slide.get("image"):
        return slide["image"]
    q = slide["photo_query"]
    log = json.loads(PHOTO_LOG.read_text(encoding="utf-8")) if PHOTO_LOG.exists() else {}
    if q not in log:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from guide_photos import download, search_commons
        reject = sorted(taken | set(slide.get("reject", [])))
        # photos of a place, not of people: skip celebrity, event and portrait shots
        people = re.compile(r"(?i)\b(bts|blackpink|exo|twice|concert|fan ?meeting|idol|performing|perform|press conference|"
                            r"portrait|members|singer|actor|actress|celebrity|showcase)\b")
        # always keep the place words: a photo of somewhere else is worse than no photo (the caller shows a card)
        hit = search_commons(q, reject=reject, require=slide.get("require", ()), avoid=people)
        if not hit and slide.get("require"):
            hit = search_commons(" ".join(slide["require"]) + " Korea", reject=reject, require=slide["require"], avoid=people)
        if not hit:
            if fallback:
                print(f"warning: no freely licensed photo for {q!r}; using {fallback}")
                return fallback
            raise SystemExit(f"no freely licensed photo for {q!r}; change the query or set an image")
        PHOTOS.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-") + ".jpg"
        download(hit["url"], PHOTOS / name)
        log[q] = {"file": f"_shorts/photos/{name}", "source": hit["source"], "credit": hit["credit"]}
        PHOTO_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    taken.add(log[q]["source"])
    return log[q]["file"]


def font(size, bold=True):
    return ImageFont.truetype(str(FONTS / ("Carlito-Bold.ttf" if bold else "Carlito-Regular.ttf")), size)


def wrap(draw, text, f, width):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=f) <= width:
            line = test
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


# YouTube Shorts, Reels and TikTok cover the bottom ~25% (title, channel, music) and a strip on the right
# (like/comment buttons) with their own buttons, so all text stays in the upper area and the left/centre.
SAFE_RIGHT = W - 170


def caption_overlay(slide, path):
    """Transparent PNG: a dark fade from the top with kicker, title and subtitle, clear of the app's buttons."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(min(1, max(0, (H * 0.5 - y) / (H * 0.32))) * 215))
    img.paste(Image.new("RGBA", (W, H), (10, 16, 28, 255)), (0, 0), grad.resize((W, H)))
    y = int(H * 0.11)
    kicker = slide.get("kicker", "")
    if kicker:  # white on a red label, readable on any photo
        kw = d.textlength(kicker, font=font(40))
        d.rounded_rectangle([80, y - 4, 80 + kw + 36, y + 56], radius=10, fill=RED)
        d.text((98, y + 4), kicker, font=font(40), fill=WHITE)
    y += 84
    for line in wrap(d, slide["title"], font(92), SAFE_RIGHT - 80):
        d.text((80, y), line, font=font(92), fill=WHITE)
        y += 100
    y += 12
    for line in wrap(d, slide.get("sub", ""), font(50, False), SAFE_RIGHT - 80):
        d.text((80, y), line, font=font(50, False), fill=CREAM)
        y += 62
    d.text((80, y + 18), "korea-plainly.com", font=font(36, False), fill=(200, 205, 215))
    img.save(path)


def end_card(slide, path):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2, int(H * 0.2), 130
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 90, 270, fill=RED)
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 270, 90, fill=(240, 242, 246))
    d.ellipse([cx - 48, cy - 48, cx + 48, cy + 48], fill=NAVY)
    for i, (text, f, col) in enumerate([("Korea Plainly", font(104), WHITE), (slide["title"], font(62, False), CREAM),
                                        (slide["sub"], font(70), RED)]):
        tw = d.textlength(text, font=f)
        d.text(((W - tw) / 2, int(H * 0.31) + i * 120), text, font=f, fill=col)
    # a subscribe button, the thing we want viewers to do before the next Short starts
    by = int(H * 0.31) + 400
    bf = font(64)
    label = "SUBSCRIBE"
    bw, bh = d.textlength(label, font=bf) + 150, 120
    bx = (W - bw) / 2
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=RED)
    tri = [(bx + 52, by + 38), (bx + 52, by + bh - 38), (bx + 92, by + bh / 2)]
    d.polygon(tri, fill=WHITE)
    d.text((bx + 112, by + (bh - 64) / 2 - 6), label, font=bf, fill=WHITE)
    note = "Full guide free: link in the description"
    d.text(((W - d.textlength(note, font=font(42, False))) / 2, by + bh + 50), note, font=font(42, False), fill=(200, 205, 215))
    img.save(path)


def tts(text, path):
    """OpenAI text-to-speech, retried a few times: one slow reply should not sink a whole video."""
    import time
    import requests
    for attempt in range(4):
        try:
            r = requests.post("https://api.openai.com/v1/audio/speech", timeout=180,
                              headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                              json={"model": os.environ.get("TTS_MODEL", "gpt-4o-mini-tts"),
                                    "voice": os.environ.get("TTS_VOICE", "coral"), "input": text, "response_format": "mp3",
                                    "instructions": "Warm, friendly local travel guide. Clear, relaxed pace."})
            r.raise_for_status()
            Path(path).write_bytes(r.content)
            return
        except Exception as e:
            if attempt == 3:
                raise
            print(f"text-to-speech retry {attempt + 1}: {e}")
            time.sleep(10 * (attempt + 1))


def word_times(audio, text):
    """[(word, start, end)] for the script's words, timed to the narration.

    Uses OpenAI's transcription word timestamps when they line up with the script
    (the script's own spelling is shown, so place names stay correct); otherwise
    spreads the words over the speech by length."""
    words = text.split()
    total = duration(audio)
    span = (0.05, total - 0.05)
    try:
        import requests
        with open(audio, "rb") as f:
            r = requests.post("https://api.openai.com/v1/audio/transcriptions", timeout=120,
                              headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                              data={"model": "whisper-1", "response_format": "verbose_json",
                                    "timestamp_granularities[]": "word"},
                              files={"file": (Path(audio).name, f, "audio/mpeg")})
        r.raise_for_status()
        heard = r.json().get("words") or []
        if heard:
            span = (heard[0]["start"], heard[-1]["end"])
        if len(heard) == len(words):
            return [(w, h["start"], h["end"]) for w, h in zip(words, heard)]
    except Exception as e:  # timing by length is good enough as a fallback
        print(f"word timing fallback: {e}")
    weights = [len(w) + 2 for w in words]
    t, out = span[0], []
    for w, k in zip(words, weights):
        d = (span[1] - span[0]) * k / sum(weights)
        out.append((w, t, t + d))
        t += d
    return out


def chunks(timed, max_words=4, max_chars=22):
    """Group timed words into short subtitle lines, breaking after punctuation."""
    out, cur = [], []
    for w in timed:
        if cur and (len(cur) >= max_words or len(" ".join(x[0] for x in cur + [w])) > max_chars):
            out.append(cur)
            cur = []
        cur.append(w)
        if w[0][-1] in ".,?!:;":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    # don't leave one word on its own ("Market.") when it fits with the words before it
    merged = []
    for c in out:
        prev = merged[-1] if merged else None
        if (prev and len(c) == 1 and prev[-1][0][-1] not in ".?!"
                and len(" ".join(x[0] for x in prev + c)) <= max_chars + 10):
            prev.extend(c)
        else:
            merged.append(c)
    out = merged
    # each line stays up until the next one starts, so the screen never flickers empty mid-sentence
    lines = []
    for i, c in enumerate(out):
        end = out[i + 1][0][1] if i + 1 < len(out) else c[-1][2] + 0.3
        lines.append((" ".join(x[0] for x in c).rstrip(","), c[0][1], end))
    return lines


def subtitle_png(text, path, y_center, x_center=W // 2, width=None):
    """White bold text with a dark outline, centred, as spoken."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(78)
    lines = wrap(d, text, f, width or 2 * min(W // 2 - 70, SAFE_RIGHT - W // 2))
    y = y_center - len(lines) * 92 // 2
    for line in lines:
        tw = d.textlength(line, font=f)
        x = x_center - tw / 2 if width else (W - tw) / 2 - 40
        d.text((x, y), line, font=f, fill=WHITE, stroke_width=7, stroke_fill=(12, 14, 20))
        y += 92
    img.save(path)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    return float(out.stdout.strip())


def sub_inputs(subs, dur):
    return [a for png, _, _ in subs for a in ("-loop", "1", "-t", f"{dur:.2f}", "-i", str(png))]


def sub_chain(subs, first_input, label_in):
    """Filter text overlaying each subtitle PNG only while it is being spoken."""
    chain, cur = "", label_in
    for k, (_, a, b) in enumerate(subs):
        chain += f";[{cur}][{first_input + k}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[s{k}]"
        cur = f"s{k}"
    return chain, cur


MASCOT_DIR = Path(__file__).resolve().parent / "mascot"
MASCOT_H = 330                      # Kkachi, the Korea Plainly magpie, low on the left, above the video title
MASCOT_X, MASCOT_Y = 14, int(H * 0.62)
SUB_BESIDE = (620, 580, int(H * 0.70))   # with Kkachi: subtitles to its right (centre x, width, centre y),
                                          # clear of the like/comment buttons on the right


def mascot_pngs(tmp, height=None):
    """Kkachi's three states (closed, open, blink) scaled for the video, made once per run."""
    height = height or MASCOT_H
    out = {}
    for state in ("closed", "open", "blink"):
        dst = tmp / f"kkachi_{state}_{height}.png"
        if not dst.exists():
            with Image.open(MASCOT_DIR / f"kkachi_{state}.png") as im:
                im = im.convert("RGBA").resize((round(im.width * height / im.height), height), Image.LANCZOS)
            # a white outline keeps the navy bird visible on dark photos and the end card
            pad = 8
            canvas = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
            canvas.paste(im, (pad, pad), im)
            halo = canvas.getchannel("A").filter(ImageFilter.MaxFilter(11))
            out_img = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
            out_img.putalpha(halo.point(lambda v: 235 if v > 40 else 0))
            out_img.alpha_composite(canvas)
            out_img.save(dst)
        out[state] = dst
    return out


def talk_intervals(audio, fps=12):
    """[(start, end)] when the beak should be open: loud moments of the narration, flapping rather than held open."""
    from array import array
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    pcm = array("h")
    pcm.frombytes(raw[: len(raw) // 2 * 2])
    win = 8000 // fps
    rms = [math.sqrt(sum(v * v for v in pcm[k:k + win]) / win) for k in range(0, len(pcm) - win, win)]
    if not rms:
        return []
    thr = max(rms) * 0.18
    spans, start = [], None
    for k, r in enumerate(rms):
        talking = r > thr and k % 3 != 2
        if talking and start is None:
            start = k / fps
        elif not talking and start is not None:
            spans.append((start, k / fps))
            start = None
    if start is not None:
        spans.append((start, len(rms) / fps))
    return spans


def mascot_layer(audio, dur, first_input, label_in, tmp, offset=0.0):
    """Inputs and filter text that put Kkachi on the video: bobbing gently, blinking, beak moving with the voice."""
    pngs = mascot_pngs(tmp)
    inputs = [a for st in ("closed", "open", "blink") for a in ("-loop", "1", "-t", f"{dur:.2f}", "-i", str(pngs[st]))]
    talk = talk_intervals(audio) if audio else []
    blinks = [(t, t + 0.15) for t in [1.1 + 3.4 * n - offset % 3.4 for n in range(int(dur / 3.4) + 2)] if 0 < t < dur - 0.2]
    def when(spans):
        return "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in spans) or "0"
    y = f"{MASCOT_Y}+6*sin(2*PI*(t+{offset:.2f})/1.5)"
    c, o, b = first_input, first_input + 1, first_input + 2
    chain = (f";[{label_in}][{c}]overlay=x={MASCOT_X}:y='{y}':eval=frame[mk1]"
             f";[mk1][{o}]overlay=x={MASCOT_X}:y='{y}':eval=frame:enable='{when(talk)}'[mk2]"
             f";[mk2][{b}]overlay=x={MASCOT_X}:y='{y}':eval=frame:enable='{when(blinks)}'[mk3]")
    return inputs, chain, "mk3"


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def segment(slide, i, tmp, voice, mascot=False):
    seg = tmp / f"seg{i:02d}.mp4"
    audio = None
    if voice and slide.get("voice"):
        audio = tmp / f"voice{i:02d}.mp3"
        tts(slide["voice"], audio)
        dur = duration(audio) + 0.45
    else:
        dur = SILENT_SECONDS if not slide.get("end") else 3.0
    subs = []
    if audio and not (mascot and slide.get("end")):  # the end card already shows what is said
        for k, (text, a, b) in enumerate(chunks(word_times(audio, slide["voice"]))):
            png = tmp / f"sub{i:02d}_{k:02d}.png"
            if mascot:
                subtitle_png(text, png, SUB_BESIDE[2], SUB_BESIDE[0], SUB_BESIDE[1])
            else:
                subtitle_png(text, png, int(H * 0.6))
            subs.append((png, a, min(b, dur)))
    audio_in = ["-i", str(audio)] if audio else ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
    fade = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.25:.2f}:d=0.25"
    if slide.get("end"):
        card = tmp / f"end{i:02d}.png"
        end_card(slide, card)
        chain, last = sub_chain(subs, 2, "base")
        m_in, m_chain = [], ""
        if mascot:
            m_in, m_chain, last = mascot_layer(audio, dur, 2 + len(subs), last, tmp, offset=i * 1.7)
        run(["ffmpeg", "-y", "-loop", "1", "-t", f"{dur:.2f}", "-i", str(card), *audio_in, *sub_inputs(subs, dur), *m_in,
             "-filter_complex", f"[0]fps={FPS}[base]{chain}{m_chain};[{last}]{fade},format=yuv420p[v]", "-map", "[v]", "-map", "1:a",
             "-af", "apad", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", str(seg)])
        return seg, dur
    # photo scaled to fill the height; pan slowly from left to right across it
    with Image.open(ROOT / slide["file"]) as im:
        im = im.convert("RGB")
        scale = H / im.height
        pan = im.resize((max(W, int(im.width * scale)), H), Image.LANCZOS)
    photo = tmp / f"photo{i:02d}.jpg"
    pan.save(photo, quality=92)
    over = tmp / f"cap{i:02d}.png"
    caption_overlay(slide, over)
    travel = max(pan.width - W, 0)
    x = f"min({travel},{travel}*t/{dur:.2f})" if i % 2 == 0 else f"max(0,{travel}-{travel}*t/{dur:.2f})"
    chain, last = sub_chain(subs, 3, "base")
    m_in, m_chain = [], ""
    if mascot:
        m_in, m_chain, last = mascot_layer(audio, dur, 3 + len(subs), last, tmp, offset=i * 1.7)
    run(["ffmpeg", "-y", "-loop", "1", "-t", f"{dur:.2f}", "-i", str(photo), "-loop", "1", "-t", f"{dur:.2f}", "-i", str(over),
         *audio_in, *sub_inputs(subs, dur), *m_in, "-filter_complex",
         f"[0]fps={FPS},crop={W}:{H}:x='{x}':y=0[bg];[bg][1]overlay=0:0[base]{chain}{m_chain};[{last}]{fade},format=yuv420p[v]",
         "-map", "[v]", "-map", "2:a", "-af", "apad", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", str(seg)])
    return seg, dur


def credits(spec):
    """Credit lines for every photo the video shows (site photos and Commons finds), in order, once each."""
    by_file = {}
    for name, prefix in (("guide_photos.json", None), ("regional_photos.json", "regional-")):
        for key, e in json.loads((ROOT / "content" / name).read_text(encoding="utf-8")).items():
            if isinstance(e, dict) and e.get("credit"):
                by_file[e.get("file") or f"{prefix}{key}.jpg"] = f'{e["credit"]} ({e.get("source", "")})'.replace(" ()", "")
    for e in (json.loads(PHOTO_LOG.read_text(encoding="utf-8")) if PHOTO_LOG.exists() else {}).values():
        by_file[e["file"]] = f'{e["credit"]} ({e["source"]})'
    out = []
    for s in spec["slides"]:
        c = by_file.get(s.get("file") or s.get("image"))
        if c and c not in out:
            out.append(c)
    return out


MUSIC = ROOT / "_shorts" / "music"
MUSIC_LIST = ROOT / "content" / "shorts" / "music.json"


def pick_music(spec, name):
    """(title, path) of the background track: the spec's "music", else one chosen by the video's name."""
    tracks = json.loads(MUSIC_LIST.read_text(encoding="utf-8"))["tracks"]
    title = spec.get("music") or tracks[sum(map(ord, name)) % len(tracks)]
    path = MUSIC / f"{title}.mp3"
    if not path.exists():
        import requests
        from urllib.parse import quote
        r = requests.get(f"https://incompetech.com/music/royalty-free/mp3-royaltyfree/{quote(title)}.mp3", timeout=120,
                         headers={"User-Agent": "KoreaPlainlyShorts/1.0 (https://korea-plainly.com)"})
        r.raise_for_status()
        MUSIC.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return title, path


def mix_music(video, music, total, voiced, out):
    """Lay the track under the video: quiet, fading in and out, and ducking further whenever the narrator speaks."""
    fade = f"afade=t=in:d=1.5,afade=t=out:st={max(total - 2.5, 0):.2f}:d=2.5"
    if voiced:
        graph = (f"[0:a]asplit=2[v][key];[1:a]volume=0.30,{fade}[m];"
                 "[m][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=450[duck];"
                 "[v][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    else:
        graph = f"[1:a]volume=0.55,{fade},loudnorm=I=-16:TP=-1.5[a]"
    run(["ffmpeg", "-y", "-i", str(video), "-stream_loop", "-1", "-i", str(music), "-filter_complex", graph,
         "-map", "0:v", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
         "-movflags", "+faststart", str(out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--voice", action="store_true")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    out_dir = ROOT / "_shorts"
    out_dir.mkdir(exist_ok=True)
    name = Path(args.spec).stem + ("-voice" if args.voice else "-silent")
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        taken = set()
        for s in spec["slides"]:
            if not s.get("end"):
                s["file"] = slide_photo(s, taken, spec.get("fallback"))
        mascot = spec.get("mascot", True) and (MASCOT_DIR / "kkachi_closed.png").exists()
        segs = [segment(s, i, tmp, args.voice, mascot) for i, s in enumerate(spec["slides"])]
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p, _ in segs))
        joined = tmp / "joined.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
        total = sum(d for _, d in segs)
        track, music = pick_music(spec, Path(args.spec).stem)
        # music under the narration; the whole mix levelled to the loudness phones expect (about -14 LUFS)
        mix_music(joined, music, total, args.voice, out_dir / f"{name}.mp4")
    from video_text import header
    desc = header(spec["article"], spec.get("summary") or spec["title"]) + [
            spec.get("hashtags", "#KoreaTravel #Korea #TravelTips"), "", "Photos (Wikimedia Commons, text added):"]
    desc += [c.replace("Photo: ", "• ") for c in credits(spec)]
    desc += ["", "Music:", f'"{track}" Kevin MacLeod (incompetech.com)',
             "Licensed under Creative Commons: By Attribution 4.0 License", "http://creativecommons.org/licenses/by/4.0/"]
    (out_dir / f"{name}.txt").write_text("\n".join(desc) + "\n", encoding="utf-8")
    print(f"{name}.mp4: {total:.1f}s")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Make a vertical short video (1080x1920) from a script in content/shorts/<name>.json.

    python scripts/make_short.py content/shorts/seoul-3-day-itinerary.json            # silent, captions only
    python scripts/make_short.py content/shorts/seoul-3-day-itinerary.json --voice    # with AI narration (OPENAI_API_KEY)

Each slide pans slowly across one of the site's photos with a caption on top; the
last slide is an end card. Output goes to _shorts/ (not published on the site),
with a description file that credits every photo, as their licences require.
"""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / "fonts"
W, H, FPS = 1080, 1920, 30
NAVY, RED, WHITE, CREAM = (23, 36, 60), (201, 65, 58), (255, 255, 255), (247, 245, 239)
SILENT_SECONDS = 3.6


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


def caption_overlay(slide, path):
    """Transparent PNG: a dark band in the lower third with kicker, title and subtitle."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(min(1, max(0, (y - H * 0.42) / (H * 0.3))) * 225))
    img.paste(Image.new("RGBA", (W, H), (10, 16, 28, 255)), (0, 0), grad.resize((W, H)))
    y = int(H * 0.62)
    kicker = slide.get("kicker", "")
    if kicker:  # white on a red label, readable on any photo
        kw = d.textlength(kicker, font=font(40))
        d.rounded_rectangle([80, y - 4, 80 + kw + 36, y + 56], radius=10, fill=RED)
        d.text((98, y + 4), kicker, font=font(40), fill=WHITE)
    y += 84
    for line in wrap(d, slide["title"], font(96), W - 160):
        d.text((80, y), line, font=font(96), fill=WHITE)
        y += 104
    y += 16
    for line in wrap(d, slide.get("sub", ""), font(52, False), W - 160):
        d.text((80, y), line, font=font(52, False), fill=CREAM)
        y += 64
    d.text((80, H - 150), "korea-plainly.com", font=font(38, False), fill=(200, 205, 215))
    img.save(path)


def end_card(slide, path):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2, int(H * 0.36), 150
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 90, 270, fill=RED)
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 270, 90, fill=(240, 242, 246))
    d.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill=NAVY)
    for i, (text, f, col) in enumerate([("Korea Plainly", font(110), WHITE), (slide["title"], font(64, False), CREAM),
                                        (slide["sub"], font(72), RED)]):
        tw = d.textlength(text, font=f)
        d.text(((W - tw) / 2, int(H * 0.52) + i * 130), text, font=f, fill=col)
    d.text(((W - d.textlength("Link in bio", font=font(48, False))) / 2, int(H * 0.52) + 420), "Link in bio",
           font=font(48, False), fill=(200, 205, 215))
    img.save(path)


def tts(text, path):
    import requests
    r = requests.post("https://api.openai.com/v1/audio/speech", timeout=120,
                      headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                      json={"model": os.environ.get("TTS_MODEL", "gpt-4o-mini-tts"), "voice": os.environ.get("TTS_VOICE", "coral"),
                            "input": text, "response_format": "mp3",
                            "instructions": "Warm, friendly local travel guide. Clear, relaxed pace."})
    r.raise_for_status()
    Path(path).write_bytes(r.content)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    return float(out.stdout.strip())


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def segment(slide, i, tmp, voice):
    seg = tmp / f"seg{i:02d}.mp4"
    audio = None
    if voice and slide.get("voice"):
        audio = tmp / f"voice{i:02d}.mp3"
        tts(slide["voice"], audio)
        dur = duration(audio) + 0.45
    else:
        dur = SILENT_SECONDS if not slide.get("end") else 3.0
    audio_in = ["-i", str(audio)] if audio else ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
    fade = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.25:.2f}:d=0.25"
    if slide.get("end"):
        card = tmp / f"end{i:02d}.png"
        end_card(slide, card)
        run(["ffmpeg", "-y", "-loop", "1", "-t", f"{dur:.2f}", "-i", str(card), *audio_in,
             "-filter_complex", f"[0]fps={FPS},{fade},format=yuv420p[v]", "-map", "[v]", "-map", "1:a",
             "-af", "apad", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", str(seg)])
        return seg, dur
    # photo scaled to fill the height; pan slowly from left to right across it
    with Image.open(ROOT / slide["image"]) as im:
        im = im.convert("RGB")
        scale = H / im.height
        pan = im.resize((max(W, int(im.width * scale)), H), Image.LANCZOS)
    photo = tmp / f"photo{i:02d}.jpg"
    pan.save(photo, quality=92)
    over = tmp / f"cap{i:02d}.png"
    caption_overlay(slide, over)
    travel = max(pan.width - W, 0)
    x = f"min({travel},{travel}*t/{dur:.2f})" if i % 2 == 0 else f"max(0,{travel}-{travel}*t/{dur:.2f})"
    run(["ffmpeg", "-y", "-loop", "1", "-t", f"{dur:.2f}", "-i", str(photo), "-loop", "1", "-t", f"{dur:.2f}", "-i", str(over),
         *audio_in, "-filter_complex",
         f"[0]fps={FPS},crop={W}:{H}:x='{x}':y=0[bg];[bg][1]overlay=0:0,{fade},format=yuv420p[v]",
         "-map", "[v]", "-map", "2:a", "-af", "apad", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", str(seg)])
    return seg, dur


def credits(spec):
    out = []
    for s in spec["slides"]:
        img = s.get("image")
        if not img:
            continue
        credit = ""
        for name in ("guide_photos.json", "regional_photos.json"):
            for e in json.loads((ROOT / "content" / name).read_text(encoding="utf-8")).values():
                if isinstance(e, dict) and e.get("credit") and (e.get("file") == img or img.endswith(".jpg") and False):
                    credit = e["credit"]
            if credit:
                break
        if not credit:  # regional photos are stored by article slug
            slug = img[len("regional-"):-4] if img.startswith("regional-") else None
            e = json.loads((ROOT / "content" / "regional_photos.json").read_text(encoding="utf-8")).get(slug or "", {})
            credit = e.get("credit", "")
        if credit and credit not in out:
            out.append(credit)
    return out


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
        segs = [segment(s, i, tmp, args.voice) for i, s in enumerate(spec["slides"])]
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p, _ in segs))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart",
             str(out_dir / f"{name}.mp4")])
    total = sum(d for _, d in segs)
    desc = [spec["title"], "", f"Full guide: https://korea-plainly.com/{spec['article']}.html", "",
            "#Seoul #KoreaTravel #SeoulItinerary #Korea #TravelTips", "", "Photos (Wikimedia Commons, text added):"]
    desc += [c.replace("Photo: ", "• ") for c in credits(spec)]
    (out_dir / f"{name}.txt").write_text("\n".join(desc) + "\n", encoding="utf-8")
    print(f"{name}.mp4: {total:.1f}s")


if __name__ == "__main__":
    main()

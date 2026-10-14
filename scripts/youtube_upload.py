#!/usr/bin/env python3
"""Upload a finished video to the Korea Plainly channel as private, with its description, captions and thumbnail.

    python scripts/youtube_upload.py _shorts/seoul-3-day-itinerary-long.mp4 "Title" [tags,comma,separated]

Uses _shorts/<name>.txt as the description, _shorts/<name>.srt as English captions and
_shorts/<name>-thumb.jpg as the thumbnail when they exist. Prints the video link.
Same secrets as youtube_shorts.py.
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_shorts import token  # noqa: E402


def main():
    video, title = Path(sys.argv[1]), sys.argv[2]
    tags = sys.argv[3].split(",") if len(sys.argv) > 3 else []
    stem = video.with_suffix("")
    desc = Path(f"{stem}.txt").read_text(encoding="utf-8").replace("<", "(").replace(">", ")")
    auth = token()
    meta = {"snippet": {"title": title[:100], "description": desc[:4900], "tags": tags, "categoryId": "19",
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True}}
    data = video.read_bytes()
    start = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                          timeout=60, json=meta, headers={**auth, "X-Upload-Content-Type": "video/mp4",
                                                          "X-Upload-Content-Length": str(len(data))})
    start.raise_for_status()
    r = requests.put(start.headers["Location"], data=data, timeout=1800, headers={**auth, "Content-Type": "video/mp4"})
    r.raise_for_status()
    vid = r.json()["id"]
    print(f"uploaded (private): https://youtu.be/{vid}")
    thumb = Path(f"{stem}-thumb.jpg")
    if thumb.exists():  # custom thumbnails need a verified channel; fine if refused
        t = requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}", timeout=60,
                          data=thumb.read_bytes(), headers={**auth, "Content-Type": "image/jpeg"})
        print("thumbnail:", "set" if t.ok else f"not set ({t.status_code}: {t.text[:200]})")
    srt = Path(f"{stem}.srt")
    if srt.exists():
        boundary = "kpcaptions"
        meta = '{"snippet":{"videoId":"%s","language":"en","name":"English"}}' % vid
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
                f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + srt.read_bytes() + \
            f"\r\n--{boundary}--\r\n".encode()
        c = requests.post("https://www.googleapis.com/upload/youtube/v3/captions?uploadType=multipart&part=snippet",
                          timeout=60, data=body, headers={**auth, "Content-Type": f"multipart/related; boundary={boundary}"})
        print("captions:", "added" if c.ok else f"not added ({c.status_code}: {c.text[:200]})")
    Path(f"{stem}.youtube").write_text(vid + "\n")


if __name__ == "__main__":
    main()

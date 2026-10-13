#!/usr/bin/env python3
"""Tell search engines (Bing, Naver, Yandex, Seznam... via IndexNow) which pages changed.

    python scripts/indexnow_ping.py [base-commit]

Lists the .html files changed between base-commit (default: the commit this
workflow run started from, $GITHUB_SHA) and HEAD, skips redirects, noindex
pages and the Google verification file, and submits their URLs. The key file
e2c6381e679c35f682125f233010d0ec.txt in the site root proves we own the site; don't delete it.
Google doesn't use IndexNow; it reads sitemap.xml.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "korea-plainly.com"
KEY = "e2c6381e679c35f682125f233010d0ec"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not base or set(base) == {"0"} or git("cat-file", "-e", base + "^{commit}").returncode:
        base = os.environ.get("GITHUB_SHA", "HEAD~1")
    changed = git("diff", "--name-only", base, "HEAD", "--", "*.html").stdout.split()
    urls = []
    for name in changed:
        p = ROOT / name
        if "/" in name or not p.exists() or re.fullmatch(r"google[0-9a-f]+\.html", name):
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "kp-redirect" in s or re.search(r'name="robots"[^>]*noindex', s):
            continue
        urls.append(f"https://{HOST}/" if name == "index.html" else f"https://{HOST}/{name}")
    if not urls:
        print("indexnow: nothing to submit")
        return
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt",
                       "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"indexnow: submitted {len(urls)} URL(s), HTTP {r.status}")
    except Exception as e:  # never fail the run over this
        print(f"indexnow: submit failed ({e})")


if __name__ == "__main__":
    main()

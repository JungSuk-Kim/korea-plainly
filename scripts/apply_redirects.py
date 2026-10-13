#!/usr/bin/env python3
"""Keep merged articles redirecting to the article they were merged into. Idempotent.

content/redirects.json maps an old page to the page that replaced it:
    {"old.html": {"to": "new.html", "title": "Title of new page"}}

For each entry the old page becomes a small noindex redirect page (unless it
already is one), and every link to it across the site is pointed at the new page.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "content" / "redirects.json"


def read(p):
    return p.read_bytes().decode("utf-8")


def redirect_page(old, new, title):
    t = html.escape(title)
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>Moved: {t} | Korea Plainly</title>\n'
            f'<meta name="robots" content="noindex,follow">\n<link rel="canonical" href="https://korea-plainly.com/{new}">\n'
            f'<meta http-equiv="refresh" content="0; url={new}">\n<!-- kp-redirect: {old} was merged into {new} -->\n</head>\n'
            f'<body>\n<p>This guide has moved: <a href="{new}">{t}</a>.</p>\n</body>\n</html>\n')


def main():
    if not MAP.exists():
        return
    redirects = json.loads(read(MAP))
    # follow chains (a -> b -> c) so links never land on another redirect
    def final(name, seen=()):
        nxt = redirects.get(name, {}).get("to")
        return final(nxt, seen + (name,)) if nxt and nxt not in seen else name
    targets = {old: final(old) for old in redirects}

    pages = 0
    for old, new in targets.items():
        p = ROOT / old
        if not p.exists() or "kp-redirect" not in read(p):
            p.write_bytes(redirect_page(old, new, redirects[old].get("title", new)).encode("utf-8"))
            pages += 1

    relinked = 0
    pattern = re.compile(r'href="(' + "|".join(re.escape(k) for k in targets) + r')(#[^"]*)?"')
    for p in ROOT.glob("*.html"):
        s = read(p)
        if "kp-redirect" in s:
            continue
        new = pattern.sub(lambda m: f'href="{targets[m.group(1)]}{m.group(2) or ""}"', s)
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            relinked += 1
    print(f"apply_redirects: {len(targets)} redirect(s), wrote {pages} page(s), relinked {relinked} page(s)")


if __name__ == "__main__":
    main()

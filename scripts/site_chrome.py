#!/usr/bin/env python3
"""Give every page the same site header, stylesheet, footer and mobile menu.

The reference is guides.html. Pages built by older generators had no header
(regional articles), a simplified header (region hubs) or a header without the
stylesheet, so their dropdown menu spilled out as a long line of links.
Idempotent: pages that already match are left alone.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"404.html"}
STD_MARK = 'class="nav wrap"'
ADSENSE = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7379462117232471" '
           'crossorigin="anonymous"></script>')
GA_ID = "G-F508WWT8G9"  # Google Analytics 4 measurement ID
ANALYTICS = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>'
             f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
             f"gtag('js',new Date());gtag('config','{GA_ID}');</script>")


def read(p):
    return p.read_bytes().decode("utf-8")


def reference_parts():
    ref = read(ROOT / "guides.html")
    def grab(pattern, required=True):
        m = re.search(pattern, ref, re.S)
        if not m and required:
            raise SystemExit(f"guides.html is missing {pattern}")
        return m.group(0) if m else ""
    return {
        "header": grab(r"<header>.*?</header>"),
        "footer": grab(r"<footer>.*?</footer>"),
        "menu": grab(r"<script>document\.querySelector\('\.menu'\).*?</script>", required=False),
        "css": grab(r'<link rel="stylesheet" href="style\.css[^"]*">'),
    }


def fix(s, parts):
    nl = "\r\n" if "\r\n" in s else "\n"

    if "googletagmanager.com/gtag/js" not in s:  # Google Analytics
        s = re.sub(r"</head>", lambda m: ANALYTICS + nl + m.group(0), s, count=1, flags=re.I)

    if "adsbygoogle.js" not in s:  # Google AdSense, same publisher ID as ads.txt
        s = re.sub(r"</head>", lambda m: ADSENSE + nl + m.group(0), s, count=1, flags=re.I)

    if not re.search(r'<link[^>]+href="style\.css', s, re.I):
        s = re.sub(r"<title>", lambda m: parts["css"] + nl + m.group(0), s, count=1, flags=re.I)

    header = re.search(r"<header\b[^>]*>.*?</header>", s, re.S | re.I)
    if header and STD_MARK not in header.group(0):
        s = s[:header.start()] + parts["header"] + s[header.end():]
    elif not header:
        s = re.sub(r"<body[^>]*>", lambda m: m.group(0) + nl + parts["header"], s, count=1, flags=re.I)

    if not re.search(r"<footer\b", s, re.I):
        s = re.sub(r"</body>", lambda m: parts["footer"] + nl + m.group(0), s, count=1, flags=re.I)

    if parts["menu"] and "querySelector('.menu')" not in s:
        s = re.sub(r"</body>", lambda m: parts["menu"] + nl + m.group(0), s, count=1, flags=re.I)
    return s


def main():
    parts = reference_parts()
    changed = 0
    for p in sorted(ROOT.glob("*.html")):
        if p.name in SKIP or re.fullmatch(r"google[0-9a-f]+\.html", p.name):
            continue
        s = read(p)
        if "kp-redirect" in s:  # merged guides: tiny redirect pages, no site chrome
            continue
        new = fix(s, parts)
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    print(f"site_chrome: updated {changed} page(s)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""FAQPage structured data for every article with a <section class="faq"> block.

Questions are the <h3> headings in the block; the answer is the text (paragraphs, lists) up to the next <h3>.
The JSON-LD lives in <script type="application/ld+json" id="kp-faq-ld"> before </head> and is rewritten
only when it changes, so the step is idempotent. Redirect pages are skipped.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = re.compile(r'<script type="application/ld\+json" id="kp-faq-ld">.*?</script>\n?', re.S)


def text(fragment):
    s = re.sub(r"<(script|style)\b.*?</\1>", "", fragment, flags=re.S)
    s = re.sub(r"</(p|li|h\d)>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def faq_items(page):
    m = re.search(r'<section class="faq"[^>]*>(.*?)</section>', page, re.S)
    if not m:
        return []
    parts = re.split(r"<h3[^>]*>(.*?)</h3>", m.group(1), flags=re.S)
    items = []
    for i in range(1, len(parts) - 1, 2):
        q, a = text(parts[i]), text(parts[i + 1])
        if q and a:
            items.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})
    return items


def main():
    changed = 0
    for p in sorted(ROOT.glob("*.html")):
        raw = p.read_bytes()
        crlf = b"\r\n" in raw
        s = raw.decode("utf-8")
        if "kp-redirect" in s[:4000] or "</head>" not in s:
            continue
        items = faq_items(s)
        block = ""
        if len(items) >= 2:
            data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": items}
            block = ('<script type="application/ld+json" id="kp-faq-ld">'
                     + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>" + ("\r\n" if crlf else "\n"))
        found = TAG.findall(s)
        if block and len(found) == 1 and found[0].strip() == block.strip():
            continue
        if not block and not found:
            continue
        new = TAG.sub("", s)
        if block:
            new = new.replace("</head>", block + "</head>", 1)
        if new != s:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    print(f"FAQ structured data: {changed} pages updated.")


if __name__ == "__main__":
    main()

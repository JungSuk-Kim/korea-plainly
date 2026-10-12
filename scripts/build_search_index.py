#!/usr/bin/env python3
"""Write search-index.json for search.html: every indexable article and hub."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"404.html", "search.html", "privacy.html", "contact.html", "social.html"}


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def main():
    pub = json.loads((ROOT / "content" / "published.json").read_text(encoding="utf-8"))
    region_of = {p["slug"] + ".html": p.get("region", "") for p in pub if isinstance(p, dict) and p.get("slug")}
    items = []
    for p in sorted(ROOT.glob("*.html")):
        if p.name in SKIP or re.fullmatch(r"google[0-9a-f]+\.html", p.name):
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "kp-redirect" in s or re.search(r'name="robots"[^>]*noindex', s):
            continue
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        title = clean(h1.group(1)) if h1 else clean((re.search(r"<title>(.*?)</title>", s, re.S) or [None, p.stem])[1])
        title = re.sub(r"\s*\|\s*Korea Plainly$", "", title)
        desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', s)
        kicker = re.search(r'<p class="kicker">(.*?)</p>', s, re.S)
        items.append({
            "t": title,
            "u": p.name,
            "d": html.unescape(desc.group(1)) if desc else "",
            "k": region_of.get(p.name) or clean(kicker.group(1) if kicker else "").title(),
        })
    (ROOT / "search-index.json").write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"build_search_index: {len(items)} pages")


if __name__ == "__main__":
    main()

from pathlib import Path
from html import escape
import re

ROOT = Path(".")
SKIP = {"index.html", "guides.html", "about.html", "contact.html", "privacy.html"}

pages = []
for p in ROOT.glob("*.html"):
    if p.name in SKIP:
        continue
    s = p.read_text(encoding="utf-8")
    m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.I | re.S)
    if not m:
        continue
    title = re.sub(r"<[^>]+>", "", m.group(1))
    title = re.sub(r"\s+", " ", title).strip()
    pages.append({"file": p.name, "title": title})

def tokens(value):
    return set(re.findall(r"[a-z]{4,}", value.lower()))

for page in pages:
    path = ROOT / page["file"]
    html = path.read_text(encoding="utf-8")

    if 'class="related-guides"' in html:
        continue

    base = tokens(page["title"] + " " + page["file"])
    scored = []

    for other in pages:
        if other["file"] == page["file"]:
            continue
        score = len(base & tokens(other["title"] + " " + other["file"]))
        if score:
            scored.append((score, other))

    scored.sort(key=lambda item: (-item[0], item[1]["title"]))
    related = [item[1] for item in scored[:3]]

    if not related:
        continue

    links = "\n".join(
        f'<li><a href="{escape(item["file"])}">{escape(item["title"])}</a></li>'
        for item in related
    )

    block = f'''
<section class="related-guides">
<h2>Related guides</h2>
<ul>
{links}
</ul>
</section>
'''

    if "</article>" in html:
        html = html.replace("</article>", block + "\n</article>", 1)
    elif "</main>" in html:
        html = html.replace("</main>", block + "\n</main>", 1)
    else:
        continue

    path.write_text(html, encoding="utf-8")
    print("linked:", page["file"])

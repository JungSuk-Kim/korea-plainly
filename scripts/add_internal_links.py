""""Related guides" block at the end of every article and hub page.

A page without the block gets three related articles (most title words in common). A block is rebuilt when it
has gone stale: a link to the page itself, the same page twice, a merged (redirect) page, a hub or a page kept
out of search. Blocks that are still fine are left alone, so the step changes nothing on a healthy site.
article_skin.py later turns the list into photo cards.
"""
from pathlib import Path
from html import escape, unescape
import re

ROOT = Path(".")


def read(p):
    return p.read_bytes().decode("utf-8")   # bytes: keep each file's own line endings


def write(p, text):
    p.write_bytes(text.encode("utf-8"))

SKIP = {"index.html", "guides.html", "about.html", "contact.html", "privacy.html"}
COMMON = set("korea korean guide guides with from your what know tips first visitors time travel that this have "
             "when where things simple easy best plain plainly html".split())
BLOCK = re.compile(r'<section class="related-guides"[^>]*>.*?</section>', re.S)

pages, targets = [], {}
for p in sorted(ROOT.glob("*.html")):
    if p.name in SKIP:
        continue
    s = read(p)
    if "kp-redirect" in s[:4000]:
        continue
    m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.I | re.S)
    if not m:
        continue
    title = unescape(re.sub(r"<[^>]+>", "", m.group(1)))
    title = re.sub(r"\s+", " ", title).strip()
    page = {"file": p.name, "title": title}
    pages.append(page)
    # only real, indexable articles are worth recommending
    if s.count("</article>") == 1 and not re.search(r'name="robots"[^>]*noindex', s):
        targets[p.name] = page


def tokens(value):
    return set(re.findall(r"[a-z]{4,}", value.lower())) - COMMON


def stale(block, name):
    hrefs = re.findall(r'href="([^"#?]+\.html)"', block)
    return (len(hrefs) < 2 or name in hrefs or len(set(hrefs)) < len(hrefs)
            or any(h not in targets for h in hrefs))


for page in pages:
    path = ROOT / page["file"]
    html = read(path)
    old = BLOCK.search(html)
    if old and not stale(old.group(0), page["file"]):
        continue

    base = tokens(page["title"] + " " + page["file"])
    scored = []
    for other in targets.values():
        if other["file"] == page["file"]:
            continue
        score = len(base & tokens(other["title"] + " " + other["file"]))
        if score:
            scored.append((score, other))
    scored.sort(key=lambda item: (-item[0], item[1]["title"]))
    related = [item[1] for item in scored[:3]]
    if len(related) < 2:
        if old:   # nothing good to offer: no block is better than a stale one
            write(path, html[:old.start()] + html[old.end():])
        continue

    links = "\n".join(
        f'<li><a href="{escape(item["file"])}">{escape(item["title"])}</a></li>'
        for item in related
    )
    block = f'''<section class="related-guides">
<h2>Related guides</h2>
<ul>
{links}
</ul>
</section>'''

    if "\r\n" in html:
        block = block.replace("\n", "\r\n")
    if old:
        html = html[:old.start()] + block + html[old.end():]
    elif html.count("</article>") == 1:
        # Only article pages (one <article>) get the block inside the article;
        # hub pages full of <article> cards get it at the end of <main>.
        html = html.replace("</article>", "\n" + block + "\n\n</article>", 1)
    elif "</main>" in html:
        html = html.replace("</main>", "\n" + block + "\n\n</main>", 1)
    else:
        continue

    write(path, html)
    print("linked:", page["file"])

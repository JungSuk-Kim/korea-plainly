from pathlib import Path
import re

DOMAIN = "https://korea-plainly.com"
SKIP = {"index.html", "guides.html", "privacy.html", "about.html", "contact.html"}

for p in sorted(Path(".").glob("*.html")):
    if p.name in SKIP:
        continue
    s = p.read_text(encoding="utf-8")
    if re.search(r'<link[^>]+rel=["\']canonical["\']', s, re.I):
        continue
    m = re.search(r"<title>(.*?)</title>", s, re.I | re.S)
    if not m:
        continue
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    if not title.endswith("| Korea Plainly"):
        title += " | Korea Plainly"
    short = title[:-len(" | Korea Plainly")] if title.endswith(" | Korea Plainly") else title
    desc = short + ". Practical tips and simple advice for foreign visitors traveling in Korea."
    url = DOMAIN + "/" + p.name
    tags = '''<meta name="description" content="__DESC__">
<link rel="canonical" href="__URL__">
<meta property="og:type" content="article">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="__URL__">
<meta property="og:image" content="https://korea-plainly.com/street.jpg">
<meta property="og:site_name" content="Korea Plainly">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="__TITLE__">
<meta name="twitter:description" content="__DESC__">
<meta name="twitter:image" content="https://korea-plainly.com/street.jpg">
'''.replace("__DESC__", desc).replace("__URL__", url).replace("__TITLE__", title)
    s = re.sub(r"</title>", "</title>\n" + tags, s, count=1, flags=re.I)
    p.write_text(s, encoding="utf-8")

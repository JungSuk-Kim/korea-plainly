import json
import os
import re
from pathlib import Path
from html import escape

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]

TOPICS_FILE = ROOT / "content" / "topics.json"
PUBLISHED_FILE = ROOT / "content" / "published.json"
GUIDES_FILE = ROOT / "guides.html"

topics = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
published = json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))

published_slugs = {item["slug"] for item in published}

topic = next(
    (item for item in topics if item["slug"] not in published_slugs),
    None
)

if topic is None:
    print("No unpublished topics.")
    raise SystemExit(0)

slug = topic["slug"]
filename = f"{slug}.html"

if (ROOT / filename).exists():
    raise RuntimeError(
        f"Refusing to overwrite existing file: {filename}"
    )

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

prompt = f"""
You write for Korea Plainly, an English-language website
for foreign visitors to Korea.

Topic:
{topic["title"]}

Category:
{topic["category"]}

Return ONLY valid JSON containing:

title
description
body_html
thumbnail_alt

Requirements:
- 700-1000 words.
- Simple, natural English.
- Practical and useful for foreign visitors.
- Avoid invented prices, opening hours, statistics, laws,
  or uncertain facts.
- No Markdown.
- body_html may use only:
  p, h2, h3, ul, ol, li, strong
- Do not include h1.
- Use clear sections and practical advice.
- Write in the same editorial tone as Korea Plainly.
"""

response = client.responses.create(
    model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
    input=prompt
)

result = response.output_text.strip()

result = re.sub(
    r"^```json\s*|\s*```$",
    "",
    result,
    flags=re.IGNORECASE
).strip()

article = json.loads(result)

title = escape(article["title"])
description = escape(article["description"])
category = escape(topic["category"])
body_html = article["body_html"]

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>{title} | Korea Plainly</title>

<meta name="description" content="{description}">

<style>
*{{box-sizing:border-box}}

body{{
  margin:0;
  background:#f7f2e8;
  color:#17233b;
  font-family:Arial,Helvetica,sans-serif;
  line-height:1.75;
}}

a{{
  color:inherit;
  text-decoration:none;
}}

.site-header{{
  border-bottom:1px solid #ddd4c5;
  background:#f7f2e8;
}}

.nav{{
  max-width:1100px;
  margin:auto;
  padding:22px 24px;
  display:flex;
  justify-content:space-between;
  align-items:center;
}}

.brand{{
  font-weight:900;
  font-size:22px;
  letter-spacing:-.04em;
}}

.back{{
  font-size:13px;
  font-weight:700;
}}

main{{
  max-width:820px;
  margin:auto;
  padding:60px 24px 90px;
}}

.eyebrow{{
  font-size:12px;
  font-weight:900;
  letter-spacing:.14em;
  text-transform:uppercase;
  color:#c9362b;
}}

h1{{
  font-size:clamp(38px,7vw,68px);
  line-height:1.02;
  letter-spacing:-.055em;
  margin:14px 0 22px;
}}

.dek{{
  font-size:19px;
  color:#5b6270;
  max-width:680px;
  margin-bottom:38px;
}}

article h2{{
  font-size:28px;
  line-height:1.2;
  letter-spacing:-.035em;
  margin:48px 0 12px;
}}

article h3{{
  font-size:21px;
  line-height:1.3;
  margin:32px 0 10px;
}}

article p{{
  font-size:17px;
  margin:0 0 18px;
}}

article ul,
article ol{{
  padding-left:24px;
  margin:10px 0 24px;
}}

article li{{
  font-size:17px;
  margin-bottom:8px;
}}

.tip{{
  border-left:4px solid #c9362b;
  background:#eee7d9;
  padding:18px 20px;
  margin:28px 0;
  font-size:15px;
}}

footer{{
  border-top:1px solid #ddd4c5;
  padding:30px 24px;
  color:#737985;
  text-align:center;
  font-size:12px;
}}

@media(max-width:600px){{
  main{{padding:42px 18px 70px}}
  .nav{{padding:18px}}
  article p,
  article li{{font-size:16px}}
  article h2{{font-size:24px}}
}}
</style>
</head>

<body>

<header class="site-header">
<nav class="nav">
<a class="brand" href="index.html">KOREA PLAINLY</a>
<a class="back" href="guides.html">ALL GUIDES →</a>
</nav>
</header>

<main>

<div class="eyebrow">
{category.upper()} · KOREA GUIDE
</div>

<h1>{title}</h1>

<p class="dek">{description}</p>

<article>

{body_html}

<div class="tip">
<strong>Bottom line:</strong>
A little preparation can make your time in Korea much easier.
Keep this guide handy and enjoy exploring at your own pace.
</div>

</article>

</main>

<footer>
© Korea Plainly · Korea, Made Easy for Everyone.
</footer>

</body>
</html>
"""

(ROOT / filename).write_text(
    html,
    encoding="utf-8"
)

published.append({
    "slug": slug,
    "filename": filename,
    "title": article["title"],
    "category": topic["category"]
})

PUBLISHED_FILE.write_text(
    json.dumps(
        published,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

guides = GUIDES_FILE.read_text(encoding="utf-8")

if f'href="{filename}"' not in guides:

    card_number = len(
        re.findall(r'<a class="guide-card"', guides)
    ) + 1

    thumb = f"thumb-auto-{slug}.svg"

    card = f"""<a class="guide-card" href="{filename}">
<div class="guide-image" style="background-image:url('{thumb}')">
<span>{card_number:02d}</span>
</div>
<div class="guide-copy">
<small>{escape(topic["category"]).upper()} · NEW</small>
<h2>{title}</h2>
<p>{description}</p>
<span class="guide-arrow">Read guide →</span>
</div>
</a>"""

    marker = "\n</section>\n</main>"

    if marker not in guides:
        raise RuntimeError(
            "Could not find Guides insertion point."
        )

    guides = guides.replace(
        marker,
        card + marker,
        1
    )

    GUIDES_FILE.write_text(
        guides,
        encoding="utf-8"
    )

svg_title = (
    article["title"]
    .replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
)

line1 = escape(svg_title[:42])
line2 = escape(svg_title[42:84])

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
viewBox="0 0 1200 700">

<rect width="1200" height="700" fill="#f4eee4"/>

<rect x="70" y="70"
width="1060" height="560"
fill="#102033"/>

<text x="110" y="180"
fill="#f4eee4"
font-family="Arial, sans-serif"
font-size="30"
font-weight="700">
{escape(topic["category"]).upper()}
</text>

<text x="110" y="300"
fill="#ffffff"
font-family="Arial, sans-serif"
font-size="58"
font-weight="700">
{line1}
</text>

<text x="110" y="375"
fill="#ffffff"
font-family="Arial, sans-serif"
font-size="58"
font-weight="700">
{line2}
</text>

<text x="110" y="555"
fill="#d33b3b"
font-family="Arial, sans-serif"
font-size="28"
font-weight="700">
KOREA PLAINLY
</text>

</svg>
"""

(ROOT / thumb).write_text(
    svg,
    encoding="utf-8"
)

print(f"Created: {filename}")
print(f"Created: {thumb}")
print("Updated guides.html")

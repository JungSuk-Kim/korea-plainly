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

topics = json.loads(
    TOPICS_FILE.read_text(encoding="utf-8")
)

published = json.loads(
    PUBLISHED_FILE.read_text(encoding="utf-8")
)

published_slugs = {
    item["slug"] for item in published
}

topic = next(
    (
        item for item in topics
        if item["slug"] not in published_slugs
    ),
    None
)

if topic is None:
    print("No unpublished topics.")
    raise SystemExit(0)

slug = topic["slug"]
filename = f"{slug}.html"

# 기존 파일을 절대 덮어쓰지 않음
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

Write a practical guide about:

{topic["title"]}

Category:

{topic["category"]}

Return ONLY valid JSON with:

title
description
body_html
thumbnail_alt

Requirements:

- 700-1000 words.
- Simple, natural English.
- Useful for foreign visitors.
- Avoid invented prices, opening hours, laws,
  statistics, or uncertain facts.
- No Markdown.
- body_html may use only:
  p, h2, h3, ul, ol, li, strong
- Do not include h1.
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

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{title} | Korea Plainly</title>

<meta name="description" content="{description}">

<link rel="stylesheet" href="style.css">
</head>

<body>

<main class="article-page">

<a href="guides.html">← Guides</a>

<h1>{title}</h1>

<p class="article-category">{category}</p>

{body_html}

</main>

</body>
</html>
"""

(ROOT / filename).write_text(
    html,
    encoding="utf-8"
)

# 발행 기록 저장
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

# Guides 페이지 자동 업데이트
guides = GUIDES_FILE.read_text(
    encoding="utf-8"
)

if f'href="{filename}"' not in guides:

    card_number = len(
        re.findall(
            r'<a class="guide-card"',
            guides
        )
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

# 자동 썸네일 생성
svg_text = (
    article["title"]
    .replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
)

line1 = escape(svg_text[:42])
line2 = escape(svg_text[42:84])

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
viewBox="0 0 1200 700">

<rect width="1200" height="700"
fill="#f4eee4"/>

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

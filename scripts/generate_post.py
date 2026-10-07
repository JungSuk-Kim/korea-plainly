import json
import os
import re
from pathlib import Path
from html import escape

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]

TOPICS_FILE = ROOT / "content" / "topics.json"
PUBLISHED_FILE = ROOT / "content" / "published.json"

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

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

prompt = f"""
You write for Korea Plainly, an English-language website for foreign visitors to Korea.

Write a practical, useful guide about:

{topic["title"]}

Category:
{topic["category"]}

Return ONLY valid JSON with these fields:

title
description
slug
category
body_html
thumbnail_alt

Requirements:

- Write 700-1000 words.
- Use simple, natural English.
- Make the article genuinely useful for foreign visitors.
- Avoid invented prices, opening hours, laws, statistics, or uncertain facts.
- Do not use Markdown.
- body_html must use only:
  p, h2, h3, ul, ol, li, strong
- Do not include HTML, CSS, JavaScript, or scripts outside body_html.
- Do not repeat the title as an H1.
- Keep the tone editorial, friendly and practical.
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
slug = re.sub(r"[^a-z0-9-]", "", article["slug"].lower())
category = escape(article["category"])
body_html = article["body_html"]

filename = f"{slug}.html"

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

published.append({
    "slug": slug,
    "filename": filename,
    "title": article["title"]
})

PUBLISHED_FILE.write_text(
    json.dumps(
        published,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print(f"Created: {filename}")

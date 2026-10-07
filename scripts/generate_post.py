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

# --------------------------------------------------
# 1. 기본 데이터 불러오기
# --------------------------------------------------

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
        item
        for item in topics
        if item["slug"] not in published_slugs
    ),
    None
)

if topic is None:
    print("No unpublished topics.")
    raise SystemExit(0)

slug = topic["slug"]
filename = f"{slug}.html"

# --------------------------------------------------
# 2. 기존 파일 덮어쓰기 방지
# --------------------------------------------------

if (ROOT / filename).exists():
    raise RuntimeError(
        f"Refusing to overwrite existing file: {filename}"
    )

# --------------------------------------------------
# 3. 카테고리별 실제 이미지 선택
# --------------------------------------------------

photo_map = {
    "Food": "food.jpg",
    "Travel": "seoul.jpg",
    "Seoul": "seoul.jpg",
    "Daily Korea": "store.jpg",
    "Shopping": "store.jpg",
    "Lifestyle": "street.jpg",
    "Culture": "street.jpg",
}

photo = photo_map.get(
    topic["category"],
    "street.jpg"
)

# --------------------------------------------------
# 4. OpenAI 연결
# --------------------------------------------------

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
- Editorial, clean and easy-to-read tone.
- Avoid invented prices, opening hours, statistics,
  laws, or uncertain facts.
- No Markdown.
- body_html may use only:
  p, h2, h3, ul, ol, li, strong
- Do not include h1.
- Use clear sections.
- Give practical advice.
- Do not repeat the title unnecessarily.
"""

response = client.responses.create(
    model=os.getenv(
        "OPENAI_MODEL",
        "gpt-6-luna"
    ),
    input=prompt
)

result = response.output_text.strip()

# --------------------------------------------------
# 5. JSON 코드블록 제거
# --------------------------------------------------

result = re.sub(
    r"^```json\s*|\s*```$",
    "",
    result,
    flags=re.IGNORECASE
).strip()

article = json.loads(result)

title = escape(
    article["title"]
)

description = escape(
    article["description"]
)

category = escape(
    topic["category"]
)

thumbnail_alt = escape(
    article["thumbnail_alt"]
)

body_html = article["body_html"]

# --------------------------------------------------
# 6. V5 스타일 자동 글 생성
# --------------------------------------------------

html = f"""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
  name="viewport"
  content="width=device-width, initial-scale=1.0"
>

<title>
{title} | Korea Plainly
</title>

<meta
  name="description"
  content="{description}"
>

<style>

* {{
  box-sizing: border-box;
}}

body {{
  margin: 0;
  background: #f7f2e8;
  color: #17233b;
  font-family:
    Arial,
    Helvetica,
    sans-serif;
  line-height: 1.75;
}}

a {{
  color: inherit;
  text-decoration: none;
}}

.site-header {{
  border-bottom:
    1px solid #ddd4c5;
  background: #f7f2e8;
}}

.nav {{
  max-width: 1100px;
  margin: auto;
  padding: 22px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.brand {{
  font-weight: 900;
  font-size: 22px;
  letter-spacing: -0.04em;
}}

.back {{
  font-size: 13px;
  font-weight: 700;
}}

main {{
  max-width: 820px;
  margin: auto;
  padding: 60px 24px 90px;
}}

.eyebrow {{
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #c9362b;
}}

h1 {{
  font-size:
    clamp(38px, 7vw, 68px);
  line-height: 1.02;
  letter-spacing: -0.055em;
  margin: 14px 0 22px;
}}

.dek {{
  font-size: 19px;
  color: #5b6270;
  max-width: 680px;
  margin-bottom: 34px;
}}

.cover {{
  width: 100%;
  height: auto;
  display: block;
  border-radius: 8px;
  margin: 0 0 42px;
  object-fit: cover;
}}

article h2 {{
  font-size: 28px;
  line-height: 1.2;
  letter-spacing: -0.035em;
  margin: 48px 0 12px;
}}

article h3 {{
  font-size: 21px;
  line-height: 1.3;
  margin: 32px 0 10px;
}}

article p {{
  font-size: 17px;
  margin: 0 0 18px;
}}

article ul,
article ol {{
  padding-left: 24px;
  margin: 10px 0 24px;
}}

article li {{
  font-size: 17px;
  margin-bottom: 8px;
}}

.tip {{
  border-left:
    4px solid #c9362b;
  background: #eee7d9;
  padding: 18px 20px;
  margin: 28px 0;
  font-size: 15px;
}}

footer {{
  border-top:
    1px solid #ddd4c5;
  padding: 30px 24px;
  color: #737985;
  text-align: center;
  font-size: 12px;
}}

@media (max-width: 600px) {{

  main {{
    padding:
      42px 18px 70px;
  }}

  .nav {{
    padding: 18px;
  }}

  .brand {{
    font-size: 19px;
  }}

  .back {{
    font-size: 11px;
  }}

  article p,
  article li {{
    font-size: 16px;
  }}

  article h2 {{
    font-size: 24px;
  }}

  .dek {{
    font-size: 17px;
  }}

}}

</style>

</head>

<body>

<header class="site-header">

<nav class="nav">

<a
  class="brand"
  href="index.html"
>
KOREA PLAINLY
</a>

<a
  class="back"
  href="guides.html"
>
ALL GUIDES →
</a>

</nav>

</header>

<main>

<div class="eyebrow">
{category.upper()} · KOREA GUIDE
</div>

<h1>
{title}
</h1>

<p class="dek">
{description}
</p>

<img
  class="cover"
  src="{photo}"
  alt="{thumbnail_alt}"
>

<article>

{body_html}

<div class="tip">

<strong>
Bottom line:
</strong>

A little preparation can make your
time in Korea much easier.
Keep this guide handy and enjoy
exploring at your own pace.

</div>

</article>

</main>

<footer>

© Korea Plainly ·
Korea, Made Easy for Everyone.

</footer>

</body>

</html>
"""

# --------------------------------------------------
# 7. 새 글 저장
# --------------------------------------------------

(ROOT / filename).write_text(
    html,
    encoding="utf-8"
)

# --------------------------------------------------
# 8. 발행 기록 저장
# --------------------------------------------------

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

# --------------------------------------------------
# 9. Guides 페이지 자동 업데이트
# --------------------------------------------------

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

    card = f"""<a
class="guide-card"
href="{filename}"
>

<div
class="guide-image"
style="background-image:url('{photo}')"
>

<span>
{card_number:02d}
</span>

</div>

<div class="guide-copy">

<small>
{escape(topic["category"]).upper()} · NEW
</small>

<h2>
{title}
</h2>

<p>
{description}
</p>

<span class="guide-arrow">
Read guide →
</span>

</div>

</a>
"""

    marker = """
</section>
</main>
"""

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

# --------------------------------------------------
# 10. 완료 메시지
# --------------------------------------------------

print(
    f"Created: {filename}"
)

print(
    f"Used photo: {photo}"
)

print(
    "Updated guides.html"
)

print(
    "Published successfully."
)

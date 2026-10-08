import json, os, re
from pathlib import Path
from html import escape
from openai import OpenAI

ROOT=Path(".")
published=json.loads((ROOT/"content/published.json").read_text(encoding="utf-8"))
if not published:
    raise SystemExit("No published articles.")

filename=published[-1]["filename"]
path=ROOT/filename
html=path.read_text(encoding="utf-8")

if 'class="faq"' in html:
    print("FAQ already exists:", filename)
    raise SystemExit(0)

title=re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I|re.S)
title=re.sub(r"<[^>]+>","",title.group(1)).strip() if title else published[-1]["title"]

article=re.search(r"<article[^>]*>(.*?)</article>", html, re.I|re.S)
body=article.group(1) if article else html

client=OpenAI(api_key=os.environ["OPENAI_API_KEY"])
prompt=f"""
You write practical English guides for foreign visitors to Korea.

Article title: {title}

Create exactly 3 useful FAQ items that a traveler might genuinely ask after reading this article.
Return ONLY valid JSON:
{{"faqs":[{{"question":"...","answer":"..."}}]}}

Rules:
- Answers: 35-70 words each.
- Simple, natural English.
- Do not invent prices, hours, laws, statistics, or uncertain facts.
- Use only information reasonably supported by the article topic.
- Avoid repeating the article verbatim.
"""

response=client.responses.create(
    model=os.getenv("OPENAI_MODEL","gpt-6-luna"),
    input=prompt
)
raw=re.sub(r"^```json\s*|\s*```$","",response.output_text.strip(),flags=re.I).strip()
data=json.loads(raw)

items=[]
for faq in data["faqs"][:3]:
    q=escape(str(faq["question"]).strip())
    a=escape(str(faq["answer"]).strip())
    items.append(f"<h3>{q}</h3>\n<p>{a}</p>")

faq_block='\n<section class="faq">\n<h2>Frequently Asked Questions</h2>\n'+"\n".join(items)+"\n</section>\n"

if "</article>" in html:
    html=html.replace("</article>",faq_block+"</article>",1)
else:
    html += faq_block

path.write_text(html,encoding="utf-8")
print("FAQ added:",filename)

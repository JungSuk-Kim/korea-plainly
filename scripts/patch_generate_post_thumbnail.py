from pathlib import Path

p = Path("scripts/generate_post.py")
s = p.read_text(encoding="utf-8")

if "import hashlib" not in s:
    s = s.replace("import json\n", "import hashlib\nimport json\n", 1)

start = s.find('thumbnail_alt = escape(')
end = s.find('body_html = article["body_html"]', start)

if start == -1 or end == -1:
    raise SystemExit("Could not find thumbnail insertion point.")

replacement = '''thumbnail_alt = escape(
    article["thumbnail_alt"]
)

# --------------------------------------------------
# 5-1. Create a unique Guides thumbnail per article
# --------------------------------------------------

thumbnail = f"thumb-auto-{slug}.svg"
thumbnail_path = ROOT / thumbnail

if not thumbnail_path.exists():
    palette = [
        ("#17233b", "#c9362b"),
        ("#24324a", "#d08a3a"),
        ("#263b36", "#b34f3f"),
        ("#3a2f45", "#c76b9a"),
        ("#283b4d", "#8b6fb8"),
        ("#3d3528", "#6d8c7a"),
    ]

    index = int(
        hashlib.sha256(slug.encode("utf-8")).hexdigest()[:8],
        16
    ) % len(palette)

    bg, accent = palette[index]

    safe_category = escape(
        topic["category"].upper(),
        quote=False
    )

    safe_title = escape(
        article["title"],
        quote=False
    )

    words = safe_title.split()
    line1 = ""
    line2 = ""

    for word in words:
        candidate = (line1 + " " + word).strip()
        if len(candidate) <= 28 and not line2:
            line1 = candidate
        else:
            line2 = (line2 + " " + word).strip()

    if not line1:
        line1 = safe_title

    svg_lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700">',
        f'<rect width="1200" height="700" fill="{bg}"/>',
        f'<circle cx="1040" cy="120" r="190" fill="{accent}" opacity="0.88"/>',
        f'<circle cx="1080" cy="570" r="260" fill="{accent}" opacity="0.18"/>',
        f'<rect x="70" y="70" width="9" height="120" fill="{accent}"/>',
        f'<text x="110" y="105" fill="#f7f2e8" font-family="Arial, Helvetica, sans-serif" font-size="25" font-weight="700" letter-spacing="4">{safe_category}</text>',
        f'<text x="110" y="330" fill="#f7f2e8" font-family="Arial, Helvetica, sans-serif" font-size="58" font-weight="700">{line1}</text>',
        f'<text x="110" y="405" fill="#f7f2e8" font-family="Arial, Helvetica, sans-serif" font-size="58" font-weight="700">{line2}</text>',
        '<text x="110" y="615" fill="#f7f2e8" opacity="0.72" font-family="Arial, Helvetica, sans-serif" font-size="22" letter-spacing="3">KOREA PLAINLY</text>',
        '</svg>',
    ]

    thumbnail_path.write_text(
        "\\n".join(svg_lines),
        encoding="utf-8"
    )

'''

s = s[:start] + replacement + s[end:]

old = 'style="background-image:url(\'{photo}\')"'
new = 'style="background-image:url(\'{thumbnail}\')"'

if old not in s:
    raise SystemExit("Could not find Guides thumbnail reference.")

s = s.replace(old, new, 1)

old_print = '''print(
    f"Used photo: {photo}"
)
'''

new_print = '''print(
    f"Used article photo: {photo}"
)

print(
    f"Used Guides thumbnail: {thumbnail}"
)
'''

if old_print in s:
    s = s.replace(old_print, new_print, 1)

p.write_text(s, encoding="utf-8")
print("Thumbnail automation patch applied successfully.")

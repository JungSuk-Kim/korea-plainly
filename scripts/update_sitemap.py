from pathlib import Path

base = "https://korea-plainly.com"
html_files = sorted(Path(".").glob("*.html"))
urls = [f"  <url><loc>{base}/{p.name}</loc></url>" for p in html_files]

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "\n".join(urls)
    + '\n</urlset>\n'
)

Path("sitemap.xml").write_text(xml, encoding="utf-8")
print(f"Updated sitemap with {len(urls)} URLs.")

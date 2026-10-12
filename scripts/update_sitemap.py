from pathlib import Path
import re

base = "https://korea-plainly.com"


def skip(path):
    # Search Console verification file
    if re.fullmatch(r"google[0-9a-f]+\.html", path.name):
        return True
    s = path.read_text(encoding="utf-8", errors="ignore")
    # noindex pages (thin hubs, 404) do not belong in the sitemap
    return re.search(r'<meta[^>]+name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', s, re.I) is not None


html_files = [p for p in sorted(Path(".").glob("*.html")) if not skip(p)]
urls = [f"  <url><loc>{base}/{p.name}</loc></url>" for p in html_files]

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "\n".join(urls)
    + '\n</urlset>\n'
)

Path("sitemap.xml").write_text(xml, encoding="utf-8")
print(f"Updated sitemap with {len(urls)} URLs.")

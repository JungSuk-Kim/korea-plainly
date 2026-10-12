# Korea Plainly

Practical, plain-English guides for people travelling to Korea for the first time.
Live site: https://korea-plainly.com (GitHub Pages, custom domain in `CNAME`).

## How the site is built

The site is plain HTML in the repository root. There is no build step: GitHub Pages
serves the files as they are.

| Path | What it is |
| --- | --- |
| `*.html` | Every page: home, guides, regional articles, region and category hubs |
| `style.css` | Shared stylesheet |
| `content/published.json` | Record of every auto-published article (slug, title, category, region, image) |
| `content/topics.json`, `region_rotation.json`, `regional_queries.json` | Inputs for the publishing bots |
| `scripts/` | Python scripts the GitHub Actions run |
| `.github/workflows/` | Scheduled and manual automation |
| `favicon.svg`, `og-default.jpg` | Site icon and default social-share image |
| `404.html` | Page shown for broken links |

## Automation

- **Auto Publish** (`auto-publish.yml`, daily): writes one general guide with
  `scripts/generate_post.py`, adds an FAQ, then runs the SEO and sitemap steps.
- **Regional Day** (`regional-day.yml`, daily): writes one regional article, rebuilds the
  region hubs, shrinks new photos, then runs the SEO and sitemap steps.

Both bots commit straight to `main`. **Always run `git pull` before editing locally**, or
your push will be rejected.

## SEO rules (enforced automatically)

`scripts/seo_basics.py` runs before every sitemap update and is safe to re-run:

- every page gets the favicon and Open Graph / Twitter tags (default image `og-default.jpg`);
- a hub page with fewer than 3 guides and almost no text is marked `noindex,follow`, and the
  mark is removed automatically once the hub fills up;
- `scripts/update_sitemap.py` leaves out `noindex` pages and the Google verification file.

`scripts/optimize_images.py` resizes photos wider than 1600px and recompresses large JPEGs.

## Do not delete

- `googlee6ee1fd6d2b284d0.html`: Google Search Console verification
- `ads.txt`, `CNAME`, `robots.txt`

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

Two workflows, both in `.github/workflows/`:

- **Daily Publish** (`daily-publish.yml`, 08:30 Korea time, or run by hand): writes one
  general guide (`generate_post.py` + `add_article_faq.py`) and one regional day
  (`generate_regional_day.py`, one article per category for the next region), then runs
  `scripts/maintain_site.py` and commits everything once. If a writing step fails, the run
  still commits the rest and is marked failed so you notice.
- **Site Maintenance** (`site-maintenance.yml`): runs `scripts/maintain_site.py` whenever you
  push changes to pages, `style.css`, `scripts/` or `content/`, or by hand.

`scripts/maintain_site.py` runs these steps in order; each is safe to repeat:

| Step | What it does |
| --- | --- |
| `generate_region_pages.py`, `fix_navigation_and_regions.py`, `build_category_region_hubs.py` | Rebuild region and category hubs from `content/published.json` |
| `add_internal_links.py` | Adds "Related guides" blocks |
| `site_chrome.py` | Same header, stylesheet, footer and mobile menu on every page (copied from `guides.html`) |
| `site_integrity_fix.py` | Dropdown menu markup and CSS, canonical tags |
| `article_enhance.py` | "Published" date and Article structured data on every article (dates in `content/page_dates.json`) |
| `optimize_images.py` | Shrinks large photos once (tagged so they are never recompressed) |
| `seo_basics.py` | Favicon, og tags, `noindex` on thin hubs (removed automatically once a hub has 3+ guides) |
| `update_sitemap.py` | Sitemap without `noindex` pages or the Google verification file |
| `site_audit.py` | Fails the run on broken links or missing basics |

The bots commit straight to `main`. **Always run `git pull` before editing locally.**

## Photo credits

New regional articles show a credit line under the cover photo. Wikimedia Commons photos
are only used when their licence allows reuse with credit (CC0, public domain, CC BY,
CC BY-SA). Google Maps photos are credited to their author.

## Do not delete

- `googlee6ee1fd6d2b284d0.html`: Google Search Console verification
- `ads.txt`, `CNAME`, `robots.txt`

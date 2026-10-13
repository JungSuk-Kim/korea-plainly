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
| `article.css` | Article design shared by every guide and regional article |
| `content/published.json` | Record of every auto-published article (slug, title, category, region, image) |
| `content/topics.json`, `region_rotation.json`, `regional_queries.json` | Inputs for the publishing bots |
| `content/region_intros.json` | The introduction shown on each region hub and on the Regions page |
| `scripts/` | Python scripts the GitHub Actions run |
| `.github/workflows/` | Scheduled and manual automation |
| `favicon.svg`, `og-default.jpg` | Site icon and default social-share image |
| `404.html` | Page shown for broken links |

## Automation

Two workflows, both in `.github/workflows/`:

- **Daily Publish** (`daily-publish.yml`, 08:17 Korea time, or run by hand): writes one
  general guide (`generate_post.py` + `add_article_faq.py`) and one regional day
  (`generate_regional_day.py`, one article per category for the next region), then runs
  `scripts/maintain_site.py` and commits everything once. If a writing step fails, the run
  still commits the rest and is marked failed so you notice.
- **Rewrite regional articles** (`rewrite-regional.yml`, run by hand): rewrites existing regional
  articles with the current writing rules (`scripts/rewrite_regional.py`); `--flagged` picks the ones that talk
  about their sources.
- **Site Maintenance** (`site-maintenance.yml`): runs `scripts/maintain_site.py` whenever you
  push changes to pages, `style.css`, `scripts/` or `content/`, or by hand.

`scripts/maintain_site.py` runs these steps in order; each is safe to repeat:

| Step | What it does |
| --- | --- |
| `apply_redirects.py` | Merged articles: old pages become noindex redirects and every link points to the article that replaced them (`content/redirects.json`) |
| `lazy_cards.py` | Guide cards on guides.html: real `<img loading="lazy">` thumbnails and a category on every card |
| `regional_photos.py` | Regional articles: credited cover photo (Wikimedia Commons first, else the place's Google Maps photo) and a Naver Map link; choices in `content/regional_photos.json` |
| `generate_region_pages.py`, `fix_navigation_and_regions.py`, `build_category_region_hubs.py` | Rebuild region hubs and the four group hubs per region (See & Do = travel/culture/leisure/local guide, Eat & Drink = food/cafe, Shop, Stay) plus nationwide group hubs; old 8-category hub URLs redirect to their group |
| `add_internal_links.py` | Adds "Related guides" blocks |
| `site_chrome.py` | Same header, stylesheet, footer, mobile menu, AdSense and Google Analytics (G-F508WWT8G9) on every page (copied from `guides.html`) |
| `site_integrity_fix.py` | Main menu (defined once in `scripts/kp_nav.py`), its CSS, canonical tags |
| `guide_photos.py` | Credited Wikimedia Commons photo for each guide that still has a text-card thumbnail (see below) |
| `article_enhance.py` | "Published" date, Article and breadcrumb structured data on every article (dates in `content/page_dates.json`) |
| `home_latest.py` | Home page "Latest guides" (two newest guides and two newest regional articles) and the "Find Korea by place" photo grid of every region with a hub |
| `article_skin.py` | One article design for every article (`article.css`): visible breadcrumb path (Home › Region › Group, or Home › Guides › Category; trail defined in `kp_nav.crumb_trail`), "On this page" contents box on articles with 4+ sections, headline block, cover photo (older guides get their own image), related guides as photo cards, and on regional articles a "Visiting" card (region, address, Google rating with its date, Naver Map / Google Maps / website buttons) |
| `responsive_images.py` | Small WebP copies (480/800/1200px, in `img/`) of every large photo, with `srcset` so phones download only what they need; cover photos load first; `image-set()` overrides for the background photos in `style.css`; unused copies are deleted |
| `optimize_images.py` | Shrinks large photos once (tagged so they are never recompressed) |
| `seo_basics.py` | Favicon, og tags, `noindex` on thin hubs (removed automatically once a hub has 3+ guides) |
| `make_pins.py` | Pinterest pin images (1000x1500, photo + title) for guides and regional articles in `pins/`, `pins/pins.csv` (guides, uploaded once with "Bulk create Pins"), and RSS feeds Pinterest auto-publishes from: `pins/places.xml` (regional articles) and `pins/guides.xml` (guides from 14 Oct 2026); redrawn only when a guide's title or photo changes (`content/pins.json`) |
| `build_search_index.py` | `search-index.json` used by `search.html` |
| `update_sitemap.py` | Sitemap (with publish dates) without `noindex` pages or the Google verification file |
| `site_audit.py` | Fails the run on broken links or missing basics |

The bots commit straight to `main`. **Always run `git pull` before editing locally.**

## Photo credits

New regional articles show a credit line under the cover photo. Wikimedia Commons photos
are only used when their licence allows reuse with credit (CC0, public domain, CC BY,
CC BY-SA). Google Maps photos are credited to their author.

General guides get their photo from `scripts/guide_photos.py`. Every choice is listed in
`content/guide_photos.json` with its source page. To get a different photo, add
`"retry": true` to that guide's entry (optionally with a new `"query"`); the rejected photo
is remembered and the current one stays until a better one is found. To keep the text card,
use `{"skip": true}`. The next run applies the change.

## Merging articles

To merge an article into another, copy any useful sections across, delete the old page and its
`content/published.json` entry, and add `"old.html": {"to": "new.html", "title": "New title"}` to
`content/redirects.json`. The next maintenance run writes the redirect page and fixes every link.

## Do not delete

- `googlee6ee1fd6d2b284d0.html`: Google Search Console verification
- `ads.txt`, `CNAME`, `robots.txt`
- `e2c6381e679c35f682125f233010d0ec.txt`: IndexNow key (proves the site is ours when `scripts/indexnow_ping.py` tells Bing, Naver and others about changed pages after each workflow run)

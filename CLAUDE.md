# Working on Korea Plainly

English travel guides for first-time foreign visitors to Korea. Owner: 김중석 (Jungsuk Kim), who writes to Claude in Korean;
reply in Korean and address him as "주인님" (not "사장님"), keep site content in plain British-leaning English. README.md explains the whole system; read it first.

## Ground rules

- **Always `git pull` (or `git fetch origin main && git rebase origin/main`) before editing.** Bots commit to `main` every day
  (Daily Publish at 08:17 KST, Site Maintenance on every push), and both share the concurrency group `site-bot`.
- Never force-push, never delete articles outright. To retire an article, merge it (see "Merging articles" in README.md):
  `content/redirects.json` + delete the page and its `content/published.json` entry.
- Do not touch `googlee6ee1fd6d2b284d0.html`, `ads.txt`, `CNAME`, `robots.txt`, `e2c6381e679c35f682125f233010d0ec.txt` (IndexNow key), and the `naver-site-verification` meta tag in `index.html` (Naver Search Advisor), and the `p:domain_verify` meta tag in `index.html` (Pinterest).
- Commit as `git -c user.name="JungSuk-Kim" -c user.email="richardjs0718@gmail.com" commit`.

## Making changes

- Pages are plain HTML, but most of their shared parts are written by `scripts/` steps run by `scripts/maintain_site.py`
  (header/footer, nav, cards, hubs, dates, structured data, breadcrumbs, TOC, related guides, sitemap). Change the
  script, not just the page, or the next run will undo or duplicate your edit.
- Every step must be idempotent. After a change:
  ```
  python3 scripts/maintain_site.py && rm -rf scripts/__pycache__ && git add -A
  python3 scripts/maintain_site.py && rm -rf scripts/__pycache__ && git diff --name-only   # must print nothing
  ```
  and `site_audit.py` must say `SITE AUDIT PASSED`.
- Some files use CRLF line endings. Preserve them (read bytes / `newline=""`); don't let a rewrite flip a whole file.
- Redirect pages contain the marker `kp-redirect`; anything that lists articles (hubs, cards, search) must skip them.
- Preview with `python3 -m http.server` and Playwright Chromium; check desktop (1280px) and mobile (390px).

## Content and photos

- Facts that change (opening hours, prices, closing days, routes) must be stated cautiously and point readers to
  Naver Map / KakaoMap. Opening hours are never stored (Google Places terms; they go stale).
- Photos: Wikimedia Commons only with a reusable licence (CC0, public domain, CC BY, CC BY-SA) and a credit line;
  Google Places photos credited to their author. Choices live in `content/guide_photos.json` and
  `content/regional_photos.json`; use `"retry": true` (optionally a new `"query"`) to get a different photo. Photo
  searches only run in GitHub Actions (`KP_FETCH_PHOTOS=1`), so push and let Site Maintenance fetch them.
- Regional articles: a local-guide voice that never narrates sources ("search results", "not confirmed").
  Fix bad ones with the "Rewrite regional articles" workflow rather than by hand.
- One article per place. The regional generator skips places already in `content/published.json`.
- AdSense quality work (Oct 2026, after a "low value content" review): regional place articles are paused while
  `content/regional_paused` exists; `content/noindex.json` lists pages kept out of search (link-only hubs, hotel/shop
  listings, and since 18 Oct every generated regional place article without the owner's photos; re-index one only after
  improving it) and `seo_basics.py` marks them noindex; region hubs get a "Planning a trip to …" section from
  `content/region_overviews.json`; articles are bylined "Jungsuk Kim" (Person in the Article JSON-LD, about.html#author).
  The owner's own photos are `photo-own-*.jpg` (EXIF stripped), credited "Photo: Jungsuk Kim, Korea Plainly".

## Short videos

`scripts/make_short.py` renders a vertical short from `content/shorts/<name>.json` (workflow "Make short video"; output
in `_shorts/`, not published). Slides use a site photo (`image`) or a Commons search for the exact place named
(`photo_query`, logged in `content/shorts/photos.json`). Once the owner uploads a short, add it to `content/videos.json`
with a poster frame in `img/`; `scripts/embed_videos.py` then shows it in its article.
The "Shorts (automatic)" workflow does all of this: `write_short.py` writes the script from the next article in
`content/shorts/queue.json`, `make_short.py` renders it (narration, subtitles, Kevin MacLeod music, CC BY 4.0),
`youtube_shorts.py upload` uploads it as private (log: `content/shorts/uploads.json`), the owner makes it public,
and `youtube_shorts.py check` (every hour) adds it to the article. Videos are not committed (`_shorts/*.mp4`
is ignored); each run keeps its video as a 30-day artifact. Never use Google Maps photos in videos.
Long-form (16:9, 5-6 min; first sentence = the promise, route map within 15 s): "Long-form video (weekly)" runs Tuesdays: `write_longform.py` (script from the next article in
`content/longform/queue.json`, map stops geocoded with OSM Nominatim) → `make_longform.py` (OSM maps, chapters, subtitles,
Kkachi) → `youtube_upload.py` (private) → `youtube_shorts.py record-long`; the hourly check embeds it at the top of the
article once public (a Short for the same article moves to the end). Kkachi the magpie mascot lives in `scripts/mascot/`;
`site_mascot.py` puts Kkachi on the site (article sign-off, About, 404) and `video_hub.py` builds videos.html and the
home page "Watch" section from `content/videos.json`.
Interactive pages (learn-hangul, packing list, cost calculator, city quiz) keep their logic in root `*.js` files;
`home_tools.py` lists them in the home page "Try it" section.
`faq_schema.py` adds FAQPage structured data from each `<section class="faq">` (h3 questions).
`rss_feed.py` writes feed.xml (newest 40 articles, dates from content/page_dates.json) and links it from index/guides.
Festivals: "Festivals (weekly)" runs `fetch_festivals.py` (KTO English TourAPI, secret `TOURAPI_KEY`) into
`content/festivals.json`; `festival_pages.py` fills korea-festivals.html and "Festivals coming up" on region hubs.
Meta: "Social posts" also runs `post_meta.py` (public videos → Instagram Reels, Facebook Page video, Threads link;
articles → Page and Threads link posts; state in `content/social_posted.json`). Reels are created from a public `video_url` (Instagram Login has no resumable upload): the Short is put on the
`reels` GitHub release and Instagram downloads it from there. "Meta token refresh" renews the 60-day
Instagram/Threads tokens into Secrets (`GH_SECRETS_TOKEN`); "Meta check" tests all tokens read-only.
Shorts are numbered episodes of "KOREA BEFORE YOU GO #n" (first slide; number from uploads.json), show a
"Follow for Korea tips" pill on the middle slide, and end with a subscribe ask and a SUBSCRIBE end card (`video_text.SHORT_OUTRO`, `make_short.end_card`); `youtube_playlists.py`
(run by the hourly check) sorts every upload into playlists (state: `content/youtube_playlists.json`). Subscribe buttons
(`.kp-sub`, `?sub_confirmation=1`) come from site_mascot.py, embed_videos.py and video_hub.py.
"YouTube stats" (daily 08:53 KST) runs `youtube_stats.py` → `content/youtube_stats.json`: views/likes/comments, channel subscriber count (same day), and with the
`yt-analytics.readonly` scope also average % viewed, subscribers gained and a retention summary per video.
Analytics calls retry on 5xx/429; if they still fail, the last good numbers are kept with `analytics_stale_since`.
"Keyword ideas (weekly)" runs `keyword_ideas.py` (Google autocomplete for travel seeds, compared with page titles) →
`content/keyword_ideas.json`: "gaps" (common searches with no page) feed new topics, "retitle" feeds title fixes.
Daily Publish runs `refill_topics.py` before the guide: under 7 unused topics, it asks the model to choose new ones
from the gaps (plus a seasonal one) and appends them to `content/topics.json` (searched phrase kept as `"query"`).
Every description starts with the link to the free guide (`scripts/video_text.py`); to retitle videos already on
YouTube, list them in `content/shorts/retitle.json` and run the "YouTube titles" workflow (`youtube_meta.py`).

## Checking the bots

`gh` works through the REST API only (`gh run list` fails):
```
gh api "repos/JungSuk-Kim/korea-plainly/actions/runs?per_page=5" --jq '.workflow_runs[]|[.name,.status,.conclusion,.created_at]|@tsv'
gh api -X POST repos/JungSuk-Kim/korea-plainly/actions/workflows/daily-publish.yml/dispatches -f ref=main   # add -F 'inputs[guide_only]=true' to rerun only the guide
```

## Analytics and ads

Google Analytics 4 `G-F508WWT8G9`, AdSense `ca-pub-7379462117232471` (both added by `scripts/site_chrome.py`).

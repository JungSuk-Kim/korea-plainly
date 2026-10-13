# Working on Korea Plainly

English travel guides for first-time foreign visitors to Korea. Owner: 김중석 (Jungsuk Kim), who writes to Claude in Korean;
reply in Korean, keep site content in plain British-leaning English. README.md explains the whole system; read it first.

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

## Checking the bots

`gh` works through the REST API only (`gh run list` fails):
```
gh api "repos/JungSuk-Kim/korea-plainly/actions/runs?per_page=5" --jq '.workflow_runs[]|[.name,.status,.conclusion,.created_at]|@tsv'
gh api -X POST repos/JungSuk-Kim/korea-plainly/actions/workflows/daily-publish.yml/dispatches -f ref=main   # add -F 'inputs[guide_only]=true' to rerun only the guide
```

## Analytics and ads

Google Analytics 4 `G-F508WWT8G9`, AdSense `ca-pub-7379462117232471` (both added by `scripts/site_chrome.py`).

# Korea Plainly Regional Day V2

This is the actual publishing layer for the regional-day system.

## Schedule
The workflow runs daily at 00:00 UTC (09:00 KST, subject to GitHub Actions scheduling delay).

The existing Guides automation remains separate.

## One regional day
For the current region, the script publishes 8 articles:
1. Travel
2. Food
3. Cafe
4. Shopping
5. Culture
6. Leisure
7. Stay
8. Local Guide

After all 8 succeed, the region rotation advances. When the last region is completed, the round increments.

## Verification
Google Places API (New) is used for current place identity, rating, review count, address, website, Maps URL and opening-hours data where returned.

Naver Search APIs are used as a second Korean-source signal through Local and Blog search. The public Naver Search API does not expose a numeric Naver Place rating, so the automation must never invent one.

## Images
Each article searches Wikimedia Commons for a place-specific image and fails rather than publishing a generic repeated thumbnail when no usable image is found.

## Required GitHub Secrets
- OPENAI_API_KEY
- GOOGLE_PLACES_API_KEY
- NAVER_CLIENT_ID
- NAVER_CLIENT_SECRET

Do not put any of these keys in repository files.

## Important
Google Places API requires a Google Cloud project with billing and Places API (New) enabled.

# Korea Plainly Regional Day — V1

This package adds the planning/state layer for the new regional publishing system.

## Target behavior

One day = one region.

For the selected region, publish:
- Travel
- Food
- Cafe
- Shopping
- Culture
- Leisure
- Stay
- Local Guide

Then move to the next region.

When the full region rotation finishes, start the next round and choose new places/topics instead of duplicating earlier content.

## Important rules

- Guides automation remains separate.
- Food recommendations must use both Naver Place and Google Maps evidence when available.
- Place information must be checked for current status before publication.
- Prefer official websites for operational information.
- Add Google Maps and booking/ticket links when available.
- Do not recommend the same place twice unless a later round has a clearly different reason.
- Every article needs a distinct visual/thumbnail.
- This V1 package is intentionally a planning/state layer. The existing publisher is not replaced yet.

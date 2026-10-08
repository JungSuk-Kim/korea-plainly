# Korea Plainly — Site Integrity Fix #5

Fixes the false audit failures from Fix #4.

1. Google Search Console verification HTML is excluded from canonical/nav checks and is never modified.
2. `social.html` is normalized to the full dropdown navigation.
3. All normal HTML pages receive canonical URLs.
4. Existing navigation, Guides filters, image paths, and placeholder-link checks remain active.

Upload the files preserving paths, then run:
Actions → Korea Plainly Site Integrity Fix → Run workflow.

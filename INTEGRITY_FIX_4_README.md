# Korea Plainly Site Integrity Fix #4

Fixes the #3 audit failure and two additional functional issues.

- Homepage social placeholder links now go to `social.html`
- Guides filter now uses the actual `data-filter` buttons correctly
- Canonical tags are added when missing
- Navigation is rebuilt consistently
- Legacy `images/*.jpg` paths are corrected
- Site integrity workflow also runs on changes to the repair scripts/workflow

## Upload
Replace the existing files with the files in this package, then run:
GitHub → Actions → Korea Plainly Site Integrity Fix → Run workflow.

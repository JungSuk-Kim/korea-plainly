FINAL REGIONAL DAY WORKFLOW FIX

The previous uploaded workflow had malformed newline quoting inside the sitemap Python block.
This replacement fixes that and keeps the safe `git add -A` commit step.

Replace:
.github/workflows/regional-day.yml

Then run manually:
Actions -> Korea Plainly Regional Day -> Run workflow

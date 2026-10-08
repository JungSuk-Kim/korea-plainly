FINAL WORKFLOW FIX

Replace:
.github/workflows/regional-day.yml

Add:
scripts/update_sitemap.py

The sitemap Python code is now outside YAML, so the previous quoting/line-break failure cannot happen.

Then run:
Actions -> Korea Plainly Regional Day -> Run workflow

Korea Plainly Sitemap Fix

1. Unzip this archive.
2. Upload .github/workflows/site-integrity-fix.yml to the same path in the repository, replacing the existing file.
3. Open GitHub Actions > Korea Plainly Site Integrity Fix > Run workflow.

This adds a sitemap refresh step before the existing site audit. It regenerates sitemap.xml from all root-level HTML pages, then runs the audit and commits the result.

The previous Regional Day run generated the articles successfully but failed at git add because '*.png' did not exist.
This workflow replaces the fragile wildcard staging with `git add -A`.
Upload this file to `.github/workflows/regional-day.yml`, replacing the existing file, then run Regional Day again.

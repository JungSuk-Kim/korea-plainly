from pathlib import Path

# Keep the old workflow entry point, but route it through the single canonical
# site-integrity builder so the two workflows can no longer overwrite each other.
code = Path('scripts/fix_navigation_and_regions.py').read_text(encoding='utf-8')
exec(compile(code, 'scripts/fix_navigation_and_regions.py', 'exec'))

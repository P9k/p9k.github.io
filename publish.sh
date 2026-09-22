#!/usr/bin/env bash
# Rebuild the website from the vault and push the result to GitHub Pages.
set -euo pipefail
cd "$(dirname "$0")"
./update.sh "$@"
git add -A
if git diff --cached --quiet; then
  echo "Nothing changed -- nothing to publish."
else
  git commit -m "Update site $(date +%Y-%m-%d)"
  git push
fi

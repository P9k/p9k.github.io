#!/usr/bin/env bash
# Rebuild the website from the Obsidian vault.
set -euo pipefail
cd "$(dirname "$0")"
python3 _build/build.py "$@"

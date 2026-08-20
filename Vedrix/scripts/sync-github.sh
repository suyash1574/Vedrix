#!/usr/bin/env bash
# Safe recurring synchronization for a persistent runner or deployment host.
# It never pushes directly to main and refuses known credential patterns.
set -Eeuo pipefail

REPO_DIR=${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}
SYNC_BRANCH=${SYNC_BRANCH:-autergo/production-hardening}
REMOTE=${REMOTE:-origin}

cd "$REPO_DIR"
git fetch "$REMOTE" "$SYNC_BRANCH"
git switch "$SYNC_BRANCH"
git pull --ff-only "$REMOTE" "$SYNC_BRANCH"

if git grep -nE 'AIza[0-9A-Za-z_-]{20,}|nvapi-[0-9A-Za-z_-]{20,}|gsk_[0-9A-Za-z_-]{20,}|sk-or-v1-[0-9A-Za-z_-]{20,}|AVNS_[0-9A-Za-z_-]{20,}|pkcs[[:space:]]' -- ':!Vedrix/backend/.env'; then
  echo "Refusing to push: credential pattern detected in tracked files." >&2
  exit 1
fi

git diff --check
if [[ -x /home/ubuntu/validate_vedrix_production.py ]]; then
  python3 /home/ubuntu/validate_vedrix_production.py
fi

if git diff --quiet && [[ -z "$(git ls-files --others --exclude-standard)" ]]; then
  echo "No changes to synchronize."
  exit 0
fi

git add -A
if git diff --cached --quiet; then
  echo "No staged changes to synchronize."
  exit 0
fi

git commit -m "chore: synchronize validated production changes"
git push "$REMOTE" "$SYNC_BRANCH"

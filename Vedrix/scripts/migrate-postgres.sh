#!/usr/bin/env bash
set -Eeuo pipefail

# PostgreSQL-only schema deployment. This script intentionally does not import
# the retired SQLite database or call SQLModel create_all.
: "${DATABASE_URL:?DATABASE_URL must be set to a PostgreSQL URL}"

case "$DATABASE_URL" in
  postgresql+asyncpg://*|postgresql://*) ;;
  *) echo "DATABASE_URL must use PostgreSQL" >&2; exit 2 ;;
esac

cd "$(dirname "$0")/../backend"
python -m alembic upgrade head
printf '%s\n' "Alembic migrations applied successfully."

#!/usr/bin/env bash
# PostgreSQL backup script for Vedrix.
# Usage: DATABASE_URL=postgresql://... ./backup.sh production
set -Eeuo pipefail

ENVIRONMENT=${1:-production}
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

if [[ -n "${DATABASE_URL:-}" ]]; then
    case "$DATABASE_URL" in
        postgresql://*|postgresql+asyncpg://*) ;;
        *) echo "DATABASE_URL must be PostgreSQL" >&2; exit 2 ;;
    esac
    BACKUP_FILE="$BACKUP_DIR/vedrix_${ENVIRONMENT}_${DATE}.dump"
    echo "Creating external PostgreSQL backup: $BACKUP_FILE"
    pg_dump --format=custom --file="$BACKUP_FILE" "$DATABASE_URL"
else
    if [[ "$ENVIRONMENT" == "production" ]]; then
        CONTAINER_NAME="vedrix-db-prod"
        DB_NAME="vedrix_prod"
    else
        CONTAINER_NAME="vedrix-db-staging"
        DB_NAME="vedrix_staging"
    fi
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "Set DATABASE_URL for an external PostgreSQL service or start $CONTAINER_NAME." >&2
        exit 1
    fi
    BACKUP_FILE="$BACKUP_DIR/vedrix_${ENVIRONMENT}_${DATE}.dump"
    echo "Creating container PostgreSQL backup: $BACKUP_FILE"
    docker exec "$CONTAINER_NAME" pg_dump -U postgres -d "$DB_NAME" --format=custom > "$BACKUP_FILE"
fi

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
printf '%s\n' "$BACKUP_FILE" > "$BACKUP_DIR/latest_backup"
echo "Backup completed: $BACKUP_FILE ($SIZE)"

# Keep only the seven most recent backups for this environment.
ls -t "$BACKUP_DIR"/vedrix_${ENVIRONMENT}_*.dump 2>/dev/null | tail -n +8 | xargs -r rm -f

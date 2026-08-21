#!/bin/bash
# Encrypted database backup script for Autergo
# Usage: ./backup-encrypted.sh [production|staging] [encrypt]

set -e

ENVIRONMENT=${1:-production}
ENCRYPT=${2:-false}
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
TIMESTAMP_FILE="$BACKUP_DIR/latest_backup"
ENCRYPTION_PASSWORD_FILE="$BACKUP_DIR/.backup_key"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

echo "=== Autergo Encrypted Backup ==="
echo "Environment: $ENVIRONMENT"
echo "Encryption: $ENCRYPT"
echo ""

# Determine container name based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    CONTAINER_NAME="vedrix-db-prod"
    DB_NAME="vedrix_prod"
else
    CONTAINER_NAME="vedrix-db-staging"
    DB_NAME="vedrix_staging"
fi

# Check if container exists
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container $CONTAINER_NAME is not running"
    exit 1
fi

# Create backup filename
BACKUP_FILE="$BACKUP_DIR/vedrix_${ENVIRONMENT}_${DATE}.sql"

echo "Creating database backup..."
docker exec -i "$CONTAINER_NAME" pg_dump -U postgres -d "$DB_NAME" -F c -b > "$BACKUP_FILE"

# Encrypt if requested
if [ "$ENCRYPT" = "true" ]; then
    # Generate or load encryption password
    if [ ! -f "$ENCRYPTION_PASSWORD_FILE" ]; then
        openssl rand -base64 32 > "$ENCRYPTION_PASSWORD_FILE"
        chmod 600 "$ENCRYPTION_PASSWORD_FILE"
        echo "Generated new encryption password"
    fi

    ENCRYPTED_FILE="${BACKUP_FILE}.enc"
    openssl enc -aes-256-cbc -salt -pbkdf2 -in "$BACKUP_FILE" -out "$ENCRYPTED_FILE" -pass file:"$ENCRYPTION_PASSWORD_FILE"

    # Remove unencrypted backup
    rm "$BACKUP_FILE"
    BACKUP_FILE="$ENCRYPTED_FILE"

    echo "Backup encrypted successfully"
fi

# Get file size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

# Update latest backup symlink
echo "$BACKUP_FILE" > "$TIMESTAMP_FILE"

echo ""
echo "Backup completed!"
echo "  File: $BACKUP_FILE"
echo "  Size: $SIZE"

# Keep only last 7 backups
echo ""
echo "Cleaning up old backups (keeping last 7)..."
if [ "$ENCRYPT" = "true" ]; then
    ls -t "$BACKUP_DIR"/vedrix_${ENVIRONMENT}_*.sql.enc 2>/dev/null | tail -n +8 | xargs -r rm -f
else
    ls -t "$BACKUP_DIR"/vedrix_${ENVIRONMENT}_*.sql 2>/dev/null | tail -n +8 | xargs -r rm -f
fi

echo "Done!"

# ── Restore Command Examples ───────────────────────────────────────────────
echo ""
echo "To restore this backup:"
if [ "$ENCRYPT" = "true" ]; then
    echo "  # Decrypt first"
    echo "  openssl enc -aes-256-cbc -d -pbkdf2 -in backup.sql.enc -out backup.sql -pass file:$ENCRYPTION_PASSWORD_FILE"
    echo "  # Then restore"
    echo "  docker exec -i vedrix-db-prod pg_restore -U postgres -d vedrix_prod < backup.sql"
else
    echo "  docker exec -i vedrix-db-prod pg_restore -U postgres -d vedrix_prod < $BACKUP_FILE"
fi
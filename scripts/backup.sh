#!/usr/bin/env bash
# Nightly compressed backup of the database. Keeps 14 days.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

BACKUP_DIR="$HOME/backups"
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y-%m-%d_%H%M)

docker exec hospital-db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
    > "$BACKUP_DIR/hospital_$STAMP.dump"
find "$BACKUP_DIR" -name 'hospital_*.dump' -mtime +14 -delete
echo "$(date -Is) backup written: hospital_$STAMP.dump"

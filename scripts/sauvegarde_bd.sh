#!/usr/bin/env bash
# Sauvegarde quotidienne de la base PostgreSQL RedAfrik.
#
# Usage : scripts/sauvegarde_bd.sh            (valeurs par défaut)
# Cron suggéré (production) :
#   30 2 * * * /chemin/vers/redafrik/scripts/sauvegarde_bd.sh >> /var/log/redafrik-sauvegarde.log 2>&1
#
# Les sauvegardes sont conservées 30 jours dans backups/ (hors git).

set -euo pipefail

export PGPASSWORD="${DB_PASSWORD:-redafrik}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-redafrik}"
DB_NAME="${DB_NAME:-redafrik}"
DEST="${BACKUP_DIR:-$(cd "$(dirname "$0")/.." && pwd)/backups}"

mkdir -p "$DEST"

FICHIER="$DEST/redafrik_$(date +%F_%H%M).dump"

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -Fc \
  -f "$FICHIER"

# Rétention : conserver 30 jours seulement
find "$DEST" -name "redafrik_*.dump" -mtime +30 -delete

echo "Sauvegarde terminée : $FICHIER"
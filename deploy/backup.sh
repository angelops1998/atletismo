#!/usr/bin/env bash
# Backup diario de Atletismo: solo la base de datos (no hay adjuntos subidos,
# los gráficos se generan en el servidor como SVG).
# Guarda en /opt/atletismo/backups y conserva los últimos 14 días.
#
# Uso manual:   sudo -u atletismo bash deploy/backup.sh
# Automatizar (crontab del usuario atletismo, todos los días 3:20 AM):
#   sudo crontab -u atletismo -e
#   20 3 * * * /opt/atletismo/deploy/backup.sh >> /opt/atletismo/backups/backup.log 2>&1
set -euo pipefail

APP_DIR=/opt/atletismo
BACKUP_DIR="$APP_DIR/backups"
STAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"

# Lee DATABASE_URL del .env (pg_dump entiende la URL directamente).
DB_URL=$(grep -E '^DATABASE_URL=' "$APP_DIR/.env" | cut -d= -f2-)
pg_dump "$DB_URL" -Fc -f "$BACKUP_DIR/atletismo_db_$STAMP.dump"

find "$BACKUP_DIR" -name 'atletismo_db_*.dump' -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Backup OK: atletismo_db_$STAMP.dump"

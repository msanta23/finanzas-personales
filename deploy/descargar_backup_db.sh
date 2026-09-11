#!/bin/bash
set -e

SERVER_IP="143.47.48.164"
KEY_FILE="oracle_finanzas.key"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="data/backups"

mkdir -p "$BACKUP_DIR"

echo "📥 Descargando copia de seguridad de la base de datos de Oracle Cloud..."
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" ubuntu@"$SERVER_IP":~/PF/data/finance.db ./data/finance.db

# Guardar también una copia con fecha
cp ./data/finance.db "$BACKUP_DIR/finance_backup_$TIMESTAMP.db"

echo "✅ Base de datos local actualizada con los datos reales de Oracle Cloud."
echo "💾 Copia histórica guardada en: $BACKUP_DIR/finance_backup_$TIMESTAMP.db"

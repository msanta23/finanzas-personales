#!/bin/bash
set -e

# Cargar variables locales desde .env si existe
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

SERVER_IP="${SERVER_IP:-tu_ip_servidor}"
KEY_FILE="${KEY_FILE:-oracle_finanzas.key}"
COMMIT_MSG="${1:-Actualización de código y mejoras}"

echo "=========================================="
echo "🚀 INICIANDO ACTUALIZACIÓN COMPLETA"
echo "=========================================="

# 1. Guardar y subir a GitHub (si es un repositorio git con remoto)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "🐙 1/3 Guardando cambios y subiendo a GitHub..."
    git add .
    if ! git diff-index --quiet HEAD --; then
        git commit -m "$COMMIT_MSG" || true
    fi
    if git remote | grep -q 'origin'; then
        git push origin $(git rev-parse --abbrev-ref HEAD) || echo "⚠️ No se pudo hacer push a GitHub (comprueba conexión o credenciales)."
    fi
fi

# 2. Empaquetar y enviar a Oracle Cloud
echo "📦 2/3 Empaquetando y enviando a Oracle Cloud ($SERVER_IP)..."
tar --exclude='.venv' --exclude='__pycache__' --exclude='vendor' --exclude='.git' --exclude='*.key' --exclude='.pytest_cache' --exclude='data/finance.db' --exclude='*.tar.gz' --exclude='*.log' -czf finanzas_update.tar.gz . || true
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" finanzas_update.tar.gz ubuntu@"$SERVER_IP":~/


# 3. Aplicar en el servidor y reiniciar
echo "⚙️ 3/3 Aplicando cambios y reiniciando servicios en Oracle..."
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" ubuntu@"$SERVER_IP" << 'ENDSSH'
tar -xzf ~/finanzas_update.tar.gz -C ~/PF/
rm ~/finanzas_update.tar.gz
~/PF/.venv/bin/pip install -r ~/PF/requirements.txt --quiet
sudo systemctl restart finanzas-bot finanzas-web
echo "✅ ¡Servicios reiniciados correctamente en la nube!"
sudo systemctl status finanzas-bot --no-pager | head -n 12
ENDSSH

rm finanzas_update.tar.gz

echo "=========================================="
echo "🎉 ¡TODO ACTUALIZADO EN GITHUB Y ORACLE CLOUD!"
echo "=========================================="

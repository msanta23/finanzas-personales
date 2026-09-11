#!/bin/bash
set -e

echo "🚀 Iniciando configuración en Oracle Cloud VM..."

export DEBIAN_FRONTEND=noninteractive

# Actualizar paquetes e instalar dependencias del sistema
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv git curl iptables-persistent

# Configurar firewall interno para Streamlit (puerto 8501)
echo "🔓 Configurando reglas de firewall iptables/ufw para Streamlit (puerto 8501)..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 8501/tcp || true
fi

# Regla para iptables (típico en imágenes de Oracle Cloud Ubuntu)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8501 -j ACCEPT || true
sudo netfilter-persistent save || true

# Configurar entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "📦 Creando entorno virtual de Python..."
    python3 -m venv .venv
fi

echo "📥 Instalando dependencias de Python..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "⚙️ Configurando servicios systemd..."
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

sed -i "s|User=ubuntu|User=$CURRENT_USER|g" deploy/finanzas-bot.service
sed -i "s|/home/ubuntu/PF|$CURRENT_DIR|g" deploy/finanzas-bot.service

sed -i "s|User=ubuntu|User=$CURRENT_USER|g" deploy/finanzas-web.service
sed -i "s|/home/ubuntu/PF|$CURRENT_DIR|g" deploy/finanzas-web.service

sudo cp deploy/finanzas-bot.service /etc/systemd/system/
sudo cp deploy/finanzas-web.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable finanzas-bot
sudo systemctl restart finanzas-bot

sudo systemctl enable finanzas-web
sudo systemctl restart finanzas-web

echo "✅ ¡Despliegue completado con éxito!"
echo "📊 Estado del Bot:"
sudo systemctl status finanzas-bot --no-pager

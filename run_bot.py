#!/usr/bin/env python3
"""
Script de inicio para el Bot de Telegram de Finanzas Personales.
Permite registrar gastos, ingresos y traspasos directamente desde Telegram.
"""
import sys
from pathlib import Path

# Añadir vendor y directorio raíz
BASE_DIR = Path(__file__).resolve().parent
VENDOR_DIR = BASE_DIR / "vendor"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.bot.telegram_bot import TelegramFinanceBot

if __name__ == "__main__":
    try:
        bot = TelegramFinanceBot()
        print("🤖 Bot de Telegram de Finanzas iniciado con éxito.")
        print("📱 Escribe a tu bot en Telegram (ej: '15.50 Mercadona', '/saldo', '/ayuda').")
        print("🛑 Pulsa Ctrl+C para detenerlo.")
        bot.run()
    except Exception as e:
        print(f"❌ Error al iniciar el bot: {e}")
        sys.exit(1)

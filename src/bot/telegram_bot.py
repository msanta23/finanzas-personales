import os
import sys
import re
import json
import time
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

# Asegurar imports del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
VENDOR_DIR = BASE_DIR / "vendor"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from src.database.connection import DB_PATH, get_connection
from src.services.transaction_service import (
    add_transaction, add_transfer, get_transactions, get_categories, get_accounts
)
from src.services.portfolio_service import get_net_worth_summary
from src.services.budget_service import get_50_30_20_analysis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TelegramFinanceBot")

def load_env_file(env_path: Optional[Path] = None):
    """Carga variables desde archivo .env si existen sin dependencias externas."""
    if env_path is None:
        env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

class TelegramFinanceBot:
    def __init__(
        self,
        token: Optional[str] = None,
        allowed_user_id: Optional[str] = None,
        currency_symbol: str = "€",
        db_path: Path = DB_PATH
    ):
        load_env_file()
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.allowed_user_id = str(allowed_user_id or os.environ.get("TELEGRAM_ALLOWED_USER_ID", "")).strip()
        self.currency_symbol = currency_symbol
        self.db_path = db_path

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN no configurado. Añádelo en .env o pásalo al constructor.")

        self.api_base = f"https://api.telegram.org/bot{self.token}"

        # Mapeo de palabras clave para autocategorización inteligente
        self.keyword_category_map = {
            # Supermercado y Alimentación
            "Supermercado y Alimentación": [
                "mercadona", "carrefour", "lidl", "dia", "aldi", "eroski", "alcampo",
                "super", "supermercado", "hipercor", "fruta", "fruteria", "pan", "panaderia",
                "pescaderia", "carniceria", "compra", "comestibles"
            ],
            # Restaurantes y Bares
            "Restaurantes y Bares": [
                "restaurante", "bar", "cafe", "cafeteria", "cerveza", "cervezas", "copa", "copas",
                "cena", "almuerzo", "desayuno", "merienda", "tapas", "vermu", "mcdonalds", "burger",
                "pizza", "telepizza", "dominos", "glovo", "uber eats", "just eat", "starbucks"
            ],
            # Transporte y Combustible
            "Transporte y Combustible": [
                "gasolina", "gasoil", "diesel", "combustible", "repsol", "cepsa", "bp", "galp",
                "parking", "aparcamiento", "peaje", "uber", "cabify", "taxi", "freenow", "metro",
                "bus", "autobus", "tren", "renfe", "ave", "vuelo", "billete", "taller", "coche", "itv"
            ],
            # Suscripciones
            "Suscripciones (Netflix, Spotify, etc.)": [
                "netflix", "spotify", "hbo", "max", "disney", "prime", "amazon prime", "youtube",
                "apple", "icloud", "chatgpt", "openai", "patreon", "twitch", "suscripcion"
            ],
            # Suministros
            "Suministros (Luz, Agua, Gas, Internet)": [
                "luz", "electricidad", "agua", "gas", "internet", "fibra", "telefono", "movil",
                "vodafone", "movistar", "orange", "digi", "yoigo", "iberdrola", "endesa", "naturgy", "totalenergies"
            ],
            # Ocio y Eventos
            "Ocio, Cine y Eventos": [
                "cine", "teatro", "concierto", "festival", "fiesta", "evento", "museo", "entrada",
                "entradas", "steam", "playstation", "nintendo", "juego", "videojuego", "ocio"
            ],
            # Compras y Ropa
            "Compras y Ropa": [
                "zara", "pull", "bershka", "stradivarius", "mango", "h&m", "ropa", "zapatos",
                "zapatillas", "corte ingles", "shein", "aliexpress", "amazon", "compras", "tienda"
            ],
            # Deporte
            "Deporte": [
                "gimnasio", "gym", "padel", "crossfit", "deporte", "decathlon", "running",
                "futbol", "piscina", "entrenamiento", "suplemento", "proteina"
            ],
            # Salud y Seguros
            "Salud y Seguros": [
                "farmacia", "medico", "dentista", "optica", "gafas", "seguro", "sanitas",
                "adeslas", "mapfre", "psicologo", "medicamento", "medicina", "hospital", "clinica"
            ],
            # Viajes y Vacaciones
            "Viajes y Vacaciones": [
                "viaje", "viajes", "hotel", "airbnb", "booking", "vuelo", "ryanair", "vueling",
                "iberia", "vacaciones", "escapada", "maleta", "alojamiento"
            ],
            # Vivienda
            "Vivienda (Alquiler/Hipoteca)": [
                "alquiler", "hipoteca", "comunidad", "piso", "casa", "ibi", "seguro hogar"
            ],
            # Inversiones y Ahorro
            "Fondos Indexados / ETFs": [
                "fondo", "indexado", "etf", "msci", "world", "sp500", "s&p", "vanguard", "amundi", "inversion", "aportacion"
            ],
            "Criptomonedas": [
                "crypto", "cripto", "bitcoin", "btc", "eth", "ethereum", "binance", "kraken"
            ],
            "Planes de Pensiones": [
                "pension", "pensiones", "plan pension"
            ],
            "Fondo de Emergencia": [
                "emergencia", "colchon", "fondo emergencia", "ahorro"
            ],
            # Ingresos
            "Nómina": [
                "nomina", "sueldo", "salario", "paga", "bonus", "empresa", "trabajo"
            ],
            "Dividendos e Intereses": [
                "dividendo", "dividendos", "interes", "intereses", "cuenta remunerada", "rendimiento"
            ],
            "Ventas / Freelance": [
                "freelance", "factura", "cliente", "venta", "ventas", "wallapop", "vinted"
            ]
        }

    # ----------------------------------------------------
    # CLIENTE HTTP TELEGRAM
    # ----------------------------------------------------
    def _make_request(self, method: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Realiza una llamada POST a la API de Telegram."""
        url = f"{self.api_base}/{method}"
        headers = {"Content-Type": "application/json"}
        payload = json.dumps(data or {}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=35) as response:
            res_data = response.read().decode("utf-8")
            return json.loads(res_data)

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
        """Envía un mensaje de texto formateado a Telegram."""
        try:
            self._make_request("sendMessage", {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            })
            return True
        except Exception as e:
            logger.error(f"Error al enviar mensaje a Telegram: {e}")
            return False

    # ----------------------------------------------------
    # PARSER INTELIGENTE DE TEXTO
    # ----------------------------------------------------
    def match_category(self, text: str, tx_type: str, df_cats) -> Tuple[int, str, str]:
        """Identifica la categoría más adecuada según el texto."""
        text_lower = text.lower()
        
        # 1. Buscar por palabras clave en nuestro diccionario
        for cat_name, keywords in self.keyword_category_map.items():
            for kw in keywords:
                # Búsqueda por palabra completa o contenida
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    cat_row = df_cats[df_cats['name'].str.lower() == cat_name.lower()]
                    if not cat_row.empty:
                        r = cat_row.iloc[0]
                        return int(r['id']), str(r['name']), str(r['icon'])

        # 2. Buscar si el nombre de la categoría está directamente en el texto
        for _, r in df_cats.iterrows():
            if r['name'].lower() in text_lower:
                return int(r['id']), str(r['name']), str(r['icon'])

        # 3. Categoría por defecto según tipo
        subset = df_cats[df_cats['type'] == tx_type]
        if not subset.empty:
            r = subset.iloc[0]
            return int(r['id']), str(r['name']), str(r['icon'])
        
        # Fallback general
        first_r = df_cats.iloc[0]
        return int(first_r['id']), str(first_r['name']), str(first_r['icon'])

    def match_account(self, text: str, df_accs) -> Tuple[Optional[int], str]:
        """Identifica la cuenta bancaria mencionada o devuelve la principal."""
        text_lower = text.lower()
        if df_accs.empty:
            return None, "Sin cuenta"

        # 1. Buscar mención explícita o coincidencia de palabras clave
        for _, r in df_accs.iterrows():
            acc_name = r['name'].lower()
            clean_acc = re.sub(r'[^\w\s]', ' ', acc_name)
            words = [w for w in clean_acc.split() if len(w) >= 3]
            keywords = [acc_name] + words
            if "my investor" in acc_name or "myinvestor" in acc_name:
                keywords.extend(["my investor", "myinvestor", "investor", "inversion", "fondos"])
            if "trade republic" in acc_name:
                keywords.extend(["trade", "trade republic", "tr"])
            if "open bank" in acc_name or "openbank" in acc_name:
                keywords.extend(["openbank", "open bank", "open"])
            if "revolut" in acc_name:
                keywords.append("revolut")
            if "abanca" in acc_name:
                keywords.append("abanca")
            if "pension" in acc_name:
                keywords.append("pension")
            if "remunerada" in acc_name or "ahorro" in acc_name:
                keywords.extend(["ahorro", "remunerada"])
            if "nómina" in acc_name or "nomina" in acc_name or "principal" in acc_name:
                keywords.extend(["nomina", "nómina", "principal", "corriente"])

            for kw in set(keywords):
                if kw in text_lower:
                    return int(r['id']), str(r['name'])

        # 2. Cuenta por defecto: buscar cuenta corriente ('checking') o la primera cuenta activo
        checking = df_accs[df_accs['type'] == 'checking']
        if not checking.empty:
            r = checking.iloc[0]
            return int(r['id']), str(r['name'])
        
        first_r = df_accs.iloc[0]
        return int(first_r['id']), str(first_r['name'])

    # ----------------------------------------------------
    # PROCESAMIENTO DE MENSAJES Y COMANDOS
    # ----------------------------------------------------
    def handle_message(self, user_id: int, text: str) -> str:
        """Procesa el mensaje del usuario y devuelve la respuesta formateada."""
        # 1. Verificación de Seguridad
        if self.allowed_user_id and str(user_id) != self.allowed_user_id:
            logger.warning(f"Acceso no autorizado rechazado para user_id: {user_id}")
            return "⛔ *Acceso no autorizado.*\nEste bot de finanzas es privado y está restringido a su propietario."

        clean_text = text.strip()
        if not clean_text:
            return "Por favor, escribe un comando o registra un movimiento (ej: `15.50 Mercadona`)."

        lower = clean_text.lower()
        df_cats = get_categories(db_path=self.db_path)
        df_accs = get_accounts(db_path=self.db_path)
        today_str = datetime.today().strftime("%Y-%m-%d")

        # Comandos de Ayuda
        if lower in ["/start", "/help", "/ayuda", "ayuda", "help"]:
            return (
                "👋 *¡Hola! Soy tu asistente de Finanzas Personales.*\n\n"
                "Puedo registrar tus gastos, ingresos y traspasos al instante.\n\n"
                "📝 *Formas rápidas de registrar movimientos:*\n"
                "• `15.50 Mercadona compra` ➔ _Gasto en Supermercado_\n"
                "• `32.00 Cena restaurante la mafia` ➔ _Gasto en Restaurantes_\n"
                "• `50 Gasolina en Abanca` ➔ _Gasto asignado a cuenta Abanca_\n"
                "• `+2100 Nómina mes` ➔ _Ingreso en Nómina_\n"
                "• `traspaso 300 a My Investor` ➔ _Traspaso a cuenta de Inversión_\n\n"
                "📊 *Comandos disponibles:*\n"
                "• `/saldo` o `/resumen` : Resumen patrimonial y de cuentas\n"
                "• `/ultimos` : Últimos 5 movimientos registrados\n"
                "• `/cuentas` : Lista de cuentas y saldos actuales\n"
                "• `/categorias` : Categorías configuradas\n"
            )

        # Comando: /saldo o /resumen
        if lower in ["/saldo", "/resumen", "saldo", "resumen"]:
            nw = get_net_worth_summary(db_path=self.db_path)
            now = datetime.now()
            b_50 = get_50_30_20_analysis(now.year, now.month, db_path=self.db_path)

            savings_actual = b_50['savings']['actual']
            savings_pct = b_50['savings']['pct']

            msg = (
                f"🏦 *Resumen Patrimonial y Flujo de Caja*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Patrimonio Neto:* `{nw['net_worth']:,.2f} {self.currency_symbol}`\n"
                f"📈 *Activos Totales:* `{nw['total_assets']:,.2f} {self.currency_symbol}`\n"
                f"📉 *Deudas / Pasivos:* `{nw['total_liabilities']:,.2f} {self.currency_symbol}`\n\n"
                f"📅 *Mes actual ({now.strftime('%B %Y')}):*\n"
                f"• Ingresos: `+{b_50['total_income']:,.2f} {self.currency_symbol}`\n"
                f"• Gastos totales: `-{b_50['total_expenses']:,.2f} {self.currency_symbol}`\n"
                f"• Flujo neto: `{b_50['net_cash_flow']:,.2f} {self.currency_symbol}`\n"
                f"• Ahorro e Inversión: `{savings_actual:,.2f} {self.currency_symbol}` (`{savings_pct:.1f}%`)\n\n"
                f"🔗 *Cuentas principales:*\n"
            )
            for _, r in df_accs.iterrows():
                msg += f"• *{r['name']}:* `{r['balance']:,.2f} {self.currency_symbol}`\n"
            return msg

        # Comando: /cuentas
        if lower in ["/cuentas", "cuentas"]:
            if df_accs.empty:
                return "ℹ️ No tienes cuentas registradas aún."
            msg = "🏦 *Tus Cuentas y Saldos:*\n━━━━━━━━━━━━━━━━━━\n"
            for _, r in df_accs.iterrows():
                tipo = "Activo" if r['is_asset'] else "Pasivo/Deuda"
                msg += f"• *{r['name']}* ({tipo}): `{r['balance']:,.2f} {self.currency_symbol}`\n"
            return msg

        # Comando: /ultimos
        if lower in ["/ultimos", "/gastos", "ultimos", "gastos"]:
            df_tx = get_transactions(limit=5, db_path=self.db_path)
            if df_tx.empty:
                return "ℹ️ No hay movimientos registrados todavía."
            msg = "📋 *Últimos 5 Movimientos:*\n━━━━━━━━━━━━━━━━━━\n"
            for _, r in df_tx.iterrows():
                sign = "+" if r['type'] == 'income' else "-"
                icon = r['category_icon'] or "📌"
                cat = r['category_name'] or "General"
                msg += f"• `{r['date']}` | *{sign}{r['amount']:,.2f} {self.currency_symbol}* | {icon} {cat}\n  _{r['description'] or 'Sin concepto'}_\n"
            return msg

        # Comando: /categorias
        if lower in ["/categorias", "categorias"]:
            inc_cats = df_cats[df_cats['type'] == 'income']
            exp_cats = df_cats[df_cats['type'] == 'expense']
            msg = "🏷️ *Categorías Disponibles:*\n\n💰 *Ingresos:*\n"
            for _, r in inc_cats.iterrows():
                msg += f"• {r['icon']} {r['name']}\n"
            msg += "\n💸 *Gastos y Ahorro:*\n"
            for _, r in exp_cats.iterrows():
                msg += f"• {r['icon']} {r['name']}\n"
            return msg

        # ----------------------------------------------------
        # DETECCIÓN DE TRASPASO
        # ----------------------------------------------------
        if lower.startswith("traspaso") or lower.startswith("/traspaso"):
            # Ej: traspaso 500 a myinvestor, traspaso 300 abanca a revolut
            match = re.search(r'(?:traspaso|/traspaso)\s+([0-9]+(?:[.,][0-9]{1,2})?)(.*)', clean_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", ".")
                amount = float(amount_str)
                rest_desc = match.group(2).strip()

                # Buscar cuentas origen y destino
                src_acc_id, src_name = None, "Cuenta Origen"
                dst_acc_id, dst_name = None, "Cuenta Destino"

                if " a " in rest_desc.lower():
                    parts = rest_desc.lower().split(" a ", 1)
                    src_acc_id, src_name = self.match_account(parts[0], df_accs)
                    dst_acc_id, dst_name = self.match_account(parts[1], df_accs)
                else:
                    # Default: Origen primera cuenta corriente, Destino primera inversión o cuenta ahorro
                    checkings = df_accs[df_accs['type'] == 'checking']
                    investments = df_accs[df_accs['type'].isin(['investment', 'savings'])]
                    if not checkings.empty:
                        src_acc_id = int(checkings.iloc[0]['id'])
                        src_name = str(checkings.iloc[0]['name'])
                    if not investments.empty:
                        dst_acc_id = int(investments.iloc[0]['id'])
                        dst_name = str(investments.iloc[0]['name'])
                    elif len(df_accs) > 1:
                        dst_acc_id = int(df_accs.iloc[1]['id'])
                        dst_name = str(df_accs.iloc[1]['name'])

                if not src_acc_id or not dst_acc_id or src_acc_id == dst_acc_id:
                    return "⚠️ *Error en traspaso:* Especifica dos cuentas distintas (ej: `traspaso 300 Abanca a My Investor`)."

                cat_id, cat_name, cat_icon = self.match_category(rest_desc or "Fondos Indexados", "expense", df_cats)

                add_transfer(
                    source_account_id=src_acc_id,
                    dest_account_id=dst_acc_id,
                    amount=amount,
                    date=today_str,
                    description=rest_desc or f"Traspaso de {src_name} a {dst_name}",
                    category_id=cat_id,
                    db_path=self.db_path
                )

                return (
                    f"🔄 *¡Traspaso Realizado!*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💸 *Importe:* `{amount:,.2f} {self.currency_symbol}`\n"
                    f"📤 *Origen:* {src_name}\n"
                    f"📥 *Destino:* {dst_name}\n"
                    f"🏷️ *Categoría:* {cat_icon} {cat_name}\n"
                    f"📅 *Fecha:* `{today_str}`\n"
                )

        # ----------------------------------------------------
        # DETECCIÓN DE INGRESO O GASTO DIRECTO
        # Formatos: "15.50 Mercadona", "+2000 Nomina", "/gasto 45 Cena", "/ingreso 500 Venta"
        # ----------------------------------------------------
        is_income = False
        if lower.startswith("+") or lower.startswith("/ingreso") or "nomina" in lower or "sueldo" in lower:
            is_income = True

        # Extraer importe y concepto con regex
        # Admite: "15.50 Mercadona", "+2000 Nomina", "gasto 45.90 cena", "12,50 cafe"
        pattern = r'^[+/]?(?:gasto|ingreso)?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:€|eur|euros)?\s*(.*)$'
        match = re.match(pattern, clean_text, re.IGNORECASE)

        if not match:
            # Intentar buscar importe en cualquier parte del texto (ej. "Mercadona 15.50")
            rev_match = re.search(r'([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:€|eur|euros)?$', clean_text, re.IGNORECASE)
            if rev_match:
                amount_str = rev_match.group(1).replace(",", ".")
                amount = float(amount_str)
                concept = clean_text[:rev_match.start()].strip()
            else:
                return (
                    "❓ No entendí el formato del movimiento.\n\n"
                    "Prueba escribiendo por ejemplo:\n"
                    "• `15.50 Mercadona`\n"
                    "• `35 Cena con amigos en Revolut`\n"
                    "• `+2100 Nómina mes`\n"
                    "• O consulta `/ayuda`"
                )
        else:
            amount_str = match.group(1).replace(",", ".")
            amount = float(amount_str)
            concept = match.group(2).strip()

        tx_type = 'income' if is_income else 'expense'
        cat_id, cat_name, cat_icon = self.match_category(concept, tx_type, df_cats)
        acc_id, acc_name = self.match_account(concept, df_accs)

        # Registrar transacción
        tx_id = add_transaction(
            account_id=acc_id,
            category_id=cat_id,
            date=today_str,
            amount=amount,
            description=concept or ("Ingreso" if is_income else "Gasto"),
            tx_type=tx_type,
            update_balance=True,
            db_path=self.db_path
        )

        tipo_texto = "Ingreso Registrado" if is_income else "Gasto Registrado"
        signo = "+" if is_income else "-"

        # Obtener saldo actualizado de la cuenta
        updated_accs = get_accounts(db_path=self.db_path)
        acc_bal_str = ""
        if acc_id:
            acc_row = updated_accs[updated_accs['id'] == acc_id]
            if not acc_row.empty:
                bal = acc_row.iloc[0]['balance']
                acc_bal_str = f"\n💳 *Saldo en {acc_name}:* `{bal:,.2f} {self.currency_symbol}`"

        return (
            f"✅ *¡{tipo_texto}!* (#{tx_id})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Importe:* `{signo}{amount:,.2f} {self.currency_symbol}`\n"
            f"🏷️ *Categoría:* {cat_icon} {cat_name}\n"
            f"🏦 *Cuenta:* {acc_name}\n"
            f"📝 *Concepto:* {concept or 'Sin descripción'}\n"
            f"📅 *Fecha:* `{today_str}`{acc_bal_str}"
        )

    # ----------------------------------------------------
    # BUCLE PRINCIPAL (LONG POLLING)
    # ----------------------------------------------------
    def run(self):
        """Ejecuta el bot en modo polling continuo."""
        logger.info("Iniciando Bot de Finanzas de Telegram...")
        logger.info(f"Usuario autorizado: {self.allowed_user_id or 'Todos (Abierto)'}")
        logger.info("Esperando mensajes de Telegram...")

        offset = 0
        while True:
            try:
                updates_resp = self._make_request("getUpdates", {
                    "offset": offset,
                    "timeout": 30
                })

                if updates_resp.get("ok"):
                    for item in updates_resp.get("result", []):
                        offset = item["update_id"] + 1
                        message = item.get("message", {})
                        text = message.get("text", "")
                        chat_id = message.get("chat", {}).get("id")
                        user_id = message.get("from", {}).get("id")

                        if text and chat_id and user_id:
                            logger.info(f"Mensaje recibido de {user_id}: {text}")
                            response_text = self.handle_message(user_id, text)
                            self.send_message(chat_id, response_text)

            except KeyboardInterrupt:
                logger.info("Deteniendo Bot de Telegram...")
                break
            except Exception as e:
                logger.error(f"Error en bucle de polling: {e}")
                time.sleep(5)

def run_bot():
    bot = TelegramFinanceBot()
    bot.run()

if __name__ == "__main__":
    run_bot()

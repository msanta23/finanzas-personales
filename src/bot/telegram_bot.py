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

        # Mapeo de palabras clave complementarias por categoría
        # Mapeo de palabras clave complementarias por categoría
        self.keyword_category_map = {
            # Comida / Supermercado y Alimentación
            "Comida": [
                "supermercado", "super", "alimentacion", "comida", "alimentos", "mercadona", "carrefour", "lidl", "dia", "aldi",
                "eroski", "alcampo", "hipercor", "ahorramas", "bonpreu", "consum", "costco", "gadis", "froiz", "alimerka", "coviran",
                "spar", "condis", "bm", "fruta", "fruteria", "pan", "panaderia", "pescaderia", "carniceria", "compra", "comestibles"
            ],
            "Supermercado y Alimentación": [
                "supermercado", "super", "alimentacion", "comida", "alimentos", "mercadona", "carrefour", "lidl", "dia", "aldi",
                "eroski", "alcampo", "hipercor", "ahorramas", "bonpreu", "consum", "costco", "gadis", "froiz", "alimerka", "coviran",
                "spar", "condis", "bm", "fruta", "fruteria", "pan", "panaderia", "pescaderia", "carniceria", "compra", "comestibles"
            ],
            # Restaurantes y Bares
            "Restaurantes y Bares": [
                "restaurante", "restaurantes", "bar", "bares", "cafe", "cafeteria", "cerveza", "cervezas", "copa", "copas",
                "cena", "cenar", "almuerzo", "comer fuera", "desayuno", "merienda", "tapas", "vermu", "mcdonalds", "burger",
                "burger king", "kfc", "pizza", "telepizza", "dominos", "glovo", "uber eats", "just eat", "starbucks",
                "rodilla", "100 montaditos", "vips", "ginos", "fosters", "foster", "goiko", "tagliatella", "la mafia", "honest greens"
            ],
            # Transporte y Combustible
            "Transporte y Combustible": [
                "transporte", "combustible", "gasolina", "gasoil", "diesel", "repsol", "cepsa", "bp", "galp", "shell",
                "plenoil", "ballenoil", "parking", "aparcamiento", "peaje", "uber", "cabify", "taxi", "freenow", "bolt", "metro",
                "bus", "autobus", "tren", "renfe", "ave", "ouigo", "iryo", "vuelo", "billete", "taller", "coche", "itv", "bici"
            ],
            # Suscripciones
            "Suscripciones (Netflix, Spotify, etc.)": [
                "suscripcion", "suscripciones", "netflix", "spotify", "hbo", "max", "disney", "prime", "amazon prime", "youtube",
                "apple", "icloud", "chatgpt", "openai", "claude", "patreon", "twitch", "dazn", "movistar plus", "filmin"
            ],
            # Suministros
            "Suministros (Luz, Agua, Gas, Internet)": [
                "suministros", "luz", "electricidad", "agua", "gas", "internet", "fibra", "telefono", "movil",
                "vodafone", "movistar", "orange", "digi", "yoigo", "iberdrola", "endesa", "naturgy", "totalenergies"
            ],
            # Ocio y Eventos
            "Ocio, Cine y Eventos": [
                "ocio", "cine", "teatro", "concierto", "festival", "fiesta", "evento", "museo", "entrada",
                "entradas", "steam", "playstation", "nintendo", "juego", "videojuego"
            ],
            # Compras y Ropa
            "Compras y Ropa": [
                "ropa", "compras", "zara", "pull", "bershka", "stradivarius", "mango", "h&m", "massimo dutti", "oysho",
                "primark", "zapatos", "zapatillas", "corte ingles", "el corte ingles", "shein", "aliexpress", "amazon", "tienda",
                "nike", "adidas", "ikea", "leroy merlin", "mediamarkt"
            ],
            # Deporte (palabras estrictas deportivas)
            "Deporte": [
                "deporte", "deportes", "gimnasio", "gym", "padel", "crossfit", "decathlon", "running",
                "futbol", "piscina", "entrenamiento", "suplemento", "proteina", "fitness", "basic fit"
            ],
            # Salud y Seguros
            "Salud y Seguros": [
                "salud", "seguro", "seguros", "farmacia", "medico", "dentista", "optica", "gafas", "sanitas",
                "adeslas", "mapfre", "psicologo", "medicamento", "medicina", "hospital", "clinica"
            ],
            # Viajes y Vacaciones
            "Viajes y Vacaciones": [
                "viaje", "viajes", "vacaciones", "hotel", "airbnb", "booking", "ryanair", "vueling",
                "iberia", "escapada", "maleta", "alojamiento"
            ],
            # Vivienda
            "Vivienda (Alquiler/Hipoteca)": [
                "vivienda", "alquiler", "hipoteca", "comunidad", "piso", "casa", "ibi", "seguro hogar"
            ],
            # Inversiones y Ahorro
            "Fondos Indexados / ETFs": [
                "fondo", "fondos", "indexado", "indexados", "etf", "etfs", "msci", "world", "sp500", "s&p", "vanguard", "amundi", "inversion", "inversiones", "aportacion"
            ],
            "Criptomonedas": [
                "crypto", "cripto", "criptomonedas", "bitcoin", "btc", "eth", "ethereum", "binance", "kraken"
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
            ],
            # Otras categorías directas
            "Caprichos": ["capricho", "caprichos"],
            "Necesidades": ["necesidad", "necesidades"],
            "Bodas": ["boda", "bodas"]
        }

        # Etiquetas genéricas de categorías que pueden ser descartadas del concepto si queda un comercio o detalle
        self.generic_category_tags = {
            "Comida": ["supermercado", "super", "alimentacion", "comida", "alimentos", "comestibles", "compra", "compras"],
            "Supermercado y Alimentación": ["supermercado", "super", "alimentacion", "comida", "alimentos", "comestibles", "compra", "compras"],
            "Restaurantes y Bares": ["restaurantes", "restaurante", "bares", "bar", "comer fuera", "cafeteria", "cafe", "cenar", "cena", "almuerzo", "desayuno", "merienda", "tapas", "copas", "copa", "cervezas", "cerveza"],
            "Transporte y Combustible": ["transporte", "combustible", "gasolina", "gasoil", "diesel", "parking", "aparcamiento", "peaje", "billete"],
            "Suscripciones (Netflix, Spotify, etc.)": ["suscripciones", "suscripcion", "suscripcion mensual"],
            "Suministros (Luz, Agua, Gas, Internet)": ["suministros", "suministro", "factura", "recibo", "electricidad", "luz", "agua", "gas", "internet", "fibra"],
            "Ocio, Cine y Eventos": ["ocio", "eventos", "evento", "entradas", "entrada"],
            "Compras y Ropa": ["compras", "compra", "ropa", "tienda"],
            "Deporte": ["deportes", "deporte", "entrenamiento", "fitness", "gimnasio", "gym"],
            "Salud y Seguros": ["seguros", "seguro", "salud", "medicina", "medicamento", "farmacia"],
            "Viajes y Vacaciones": ["vacaciones", "viajes", "viaje", "escapada", "alojamiento", "hotel"],
            "Vivienda (Alquiler/Hipoteca)": ["vivienda", "alquiler", "hipoteca", "comunidad"],
            "Fondos Indexados / ETFs": ["inversiones", "inversion", "aportacion", "fondos", "fondo", "indexado", "indexados", "etf", "etfs"],
            "Criptomonedas": ["criptomonedas", "criptomoneda", "cripto", "crypto"],
            "Planes de Pensiones": ["planes de pensiones", "plan de pensiones", "plan pensiones", "plan pension", "pensiones", "pension"],
            "Fondo de Emergencia": ["fondo de emergencia", "fondo emergencia", "emergencia", "colchon", "ahorro"],
            "Nómina": ["nomina", "sueldo", "salario", "paga extra", "paga"],
            "Dividendos e Intereses": ["dividendos", "dividendo", "intereses", "interes", "rendimiento"],
            "Ventas / Freelance": ["freelance", "factura", "ventas", "venta"],
            "Caprichos": ["caprichos", "capricho"],
            "Necesidades": ["necesidades", "necesidad"],
            "Bodas": ["bodas", "boda"],
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
    # PARSER INTELIGENTE DE TEXTO, CUENTAS Y CATEGORÍAS
    # ----------------------------------------------------
    @staticmethod
    def _normalize(text: str) -> str:
        """Elimina acentos, signos de puntuación y pasa a minúsculas."""
        import unicodedata
        if not text:
            return ""
        norm = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')
        return re.sub(r'[^a-z0-9\s]', ' ', norm)

    def _get_keywords_for_category(self, cat_name: str) -> List[str]:
        """Obtiene palabras clave por nombre exacto o por coincidencia parcial si la categoría fue renombrada."""
        if cat_name in self.keyword_category_map:
            return self.keyword_category_map[cat_name]
        
        norm_name = self._normalize(cat_name)
        for key, kws in self.keyword_category_map.items():
            norm_key = self._normalize(key)
            if norm_key in norm_name or norm_name in norm_key:
                return kws
        return []

    def _get_generic_tags_for_category(self, cat_name: str) -> List[str]:
        """Obtiene etiquetas genéricas por nombre exacto o coincidencia parcial."""
        if cat_name in self.generic_category_tags:
            return self.generic_category_tags[cat_name]
        
        norm_name = self._normalize(cat_name)
        for key, tags in self.generic_category_tags.items():
            norm_key = self._normalize(key)
            if norm_key in norm_name or norm_name in norm_key:
                return tags
        return []

    def match_category(self, text: str, tx_type: str, df_cats) -> Tuple[int, str, str]:
        """
        Identifica la categoría buscando coincidencias directas con el nombre de la categoría
        o palabras clave de forma estricta.
        """
        if df_cats.empty:
            return 1, "General", "📌"

        norm_text = self._normalize(text)
        user_words = set(w for w in norm_text.split() if len(w) >= 3)
        stop_words = {"para", "con", "del", "por", "una", "uno", "los", "las", "mes", "ano", "hoy", "pago"}
        user_words = user_words - stop_words

        # Filtrar categorías candidatas por tipo (expense / income)
        cats_type = df_cats[df_cats['type'] == tx_type]
        if cats_type.empty:
            cats_type = df_cats

        best_cat = None
        highest_score = 0

        for _, r in cats_type.iterrows():
            cat_name = str(r['name'])
            cat_id = int(r['id'])
            cat_icon = str(r['icon'] or "📌")
            norm_cat_name = self._normalize(cat_name)
            cat_name_words = set(w for w in norm_cat_name.split() if len(w) >= 3) - stop_words

            score = 0

            # 1. ¿El nombre completo de la categoría está dentro del texto del usuario?
            if norm_cat_name in norm_text:
                score += 1000

            # 2. ¿Alguna palabra del nombre de la categoría está escrita por el usuario?
            common_words = user_words.intersection(cat_name_words)
            if common_words:
                score += len(common_words) * 300

            # 3. ¿Alguna palabra clave asociada coincide?
            kw_list = self._get_keywords_for_category(cat_name)
            for kw in kw_list:
                norm_kw = self._normalize(kw)
                if " " in norm_kw:
                    if norm_kw in norm_text:
                        score += 250
                elif norm_kw in user_words:
                    score += 150

            if score > highest_score:
                highest_score = score
                best_cat = (cat_id, cat_name, cat_icon)

        if best_cat and highest_score > 0:
            return best_cat

        # 4. Fallback si no hay ninguna coincidencia:
        fallback_names = ["otros gastos", "general", "otros", "otros ingresos"]
        for _, r in cats_type.iterrows():
            if str(r['name']).lower() in fallback_names:
                return int(r['id']), str(r['name']), str(r['icon'] or "📌")

        first_r = cats_type.iloc[0]
        return int(first_r['id']), str(first_r['name']), str(first_r['icon'] or "📌")

    def get_default_account(self, df_accs) -> Tuple[Optional[int], str]:
        """Devuelve la cuenta por defecto: Revolut si existe, si no checking o primera de activo."""
        if df_accs.empty:
            return None, "Sin cuenta"

        # 1. Prioridad: Cuenta con 'revolut' en el nombre
        for _, r in df_accs.iterrows():
            if "revolut" in str(r['name']).lower():
                return int(r['id']), str(r['name'])

        # 2. Prioridad: Cuenta corriente ('checking')
        checking = df_accs[df_accs['type'] == 'checking']
        if not checking.empty:
            r = checking.iloc[0]
            return int(r['id']), str(r['name'])

        # 3. Prioridad: Primera cuenta de activo
        assets = df_accs[df_accs['is_asset'] == 1]
        if not assets.empty:
            r = assets.iloc[0]
            return int(r['id']), str(r['name'])

        # 4. Fallback: Primera cuenta disponible
        first_r = df_accs.iloc[0]
        return int(first_r['id']), str(first_r['name'])

    def extract_account(self, text: str, df_accs) -> Tuple[Optional[int], str, str, bool]:
        """
        Detecta si se menciona explícitamente una cuenta bancaria en el texto.
        Si se menciona, la elimina del texto y la devuelve.
        Si no se menciona, devuelve la cuenta por defecto (Revolut) sin modificar el texto.
        Retorna: (account_id, account_name, text_without_account, was_explicit)
        """
        if df_accs.empty:
            return None, "Sin cuenta", text, False

        alias_map = {
            "revolut": ["revolut"],
            "abanca": ["abanca"],
            "my investor": ["my investor", "myinvestor", "my_investor"],
            "myinvestor": ["my investor", "myinvestor", "my_investor"],
            "trade republic": ["trade republic", "traderepublic", "trade_republic"],
            "traderepublic": ["trade republic", "traderepublic", "trade_republic"],
            "open bank": ["open bank", "openbank"],
            "openbank": ["open bank", "openbank"],
            "ibkr": ["ibkr", "interactive brokers"],
            "bbva": ["bbva"],
            "santander": ["santander", "banco santander"],
            "caixabank": ["caixabank", "caixa", "la caixa"],
            "caixa": ["caixabank", "caixa", "la caixa"],
            "ing": ["ing direct", "ing"],
            "n26": ["n26"],
            "sabadell": ["sabadell", "banco sabadell"],
            "bankinter": ["bankinter"],
            "imagin": ["imagin", "imaginbank"],
            "kraken": ["kraken"],
            "binance": ["binance"],
            "coinbase": ["coinbase"]
        }

        candidates = []
        for _, r in df_accs.iterrows():
            acc_id = int(r['id'])
            acc_name = str(r['name'])
            acc_name_lower = acc_name.lower()

            keywords = [acc_name_lower]
            for key, aliases in alias_map.items():
                if key in acc_name_lower:
                    keywords.extend(aliases)

            # Palabras del nombre de la cuenta (>= 4 letras)
            words = [w for w in re.sub(r'[^\w\s]', ' ', acc_name_lower).split() if len(w) >= 4]
            stopwords_acc = {"cuenta", "corriente", "tarjeta", "fondo", "cartera", "principal", "ahorro", "inversion"}
            keywords.extend([w for w in words if w not in stopwords_acc])

            for kw in set(keywords):
                if not kw.strip():
                    continue
                # Patrón que captura opcionalmente preposiciones: 'en revolut', 'con revolut', 'de abanca', 'cuenta revolut'
                pattern = r'(?i)\b(?:(?:en|con|de|desde|por|a)\s+)?(?:cuenta\s+(?:de\s+)?)?' + re.escape(kw.strip()) + r'\b'
                for m in re.finditer(pattern, text):
                    candidates.append((m.span(), acc_id, acc_name, m.group(0)))

        # Si hubo coincidencias explícitas en el texto
        if candidates:
            # Ordenar por longitud de coincidencia descendente
            candidates.sort(key=lambda c: (c[0][1] - c[0][0]), reverse=True)
            best_span, best_id, best_name, _ = candidates[0]
            start, end = best_span
            cleaned_text = (text[:start] + " " + text[end:]).strip()
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            return best_id, best_name, cleaned_text, True

        # Si no se mencionó ninguna cuenta explícita, usar la cuenta por defecto (Revolut)
        def_id, def_name = self.get_default_account(df_accs)
        return def_id, def_name, text, False

    def match_account(self, text: str, df_accs) -> Tuple[Optional[int], str]:
        """Identifica la cuenta bancaria mencionada o devuelve la principal/defecto."""
        acc_id, acc_name, _, _ = self.extract_account(text, df_accs)
        return acc_id, acc_name

    def clean_concept(self, text: str, cat_name: str) -> str:
        """
        Limpia el concepto eliminando palabras redundantes de la categoría
        si queda una descripción/comercio sustancial.
        """
        if not text:
            return ""

        raw_clean = re.sub(r'\s+', ' ', text).strip()
        cleaned = raw_clean

        # Obtener tags genéricos para la categoría detectada
        tags = self._get_generic_tags_for_category(cat_name)
        sorted_tags = sorted(tags, key=len, reverse=True)

        for tag in sorted_tags:
            tag_pattern = r'(?i)\b(?:(?:de|para|en|del|la|el|los|las)\s+)?' + re.escape(tag) + r'\b'
            candidate = re.sub(tag_pattern, ' ', cleaned)
            candidate = re.sub(r'\s+', ' ', candidate).strip()
            candidate_clean = re.sub(r'(?i)^(?:en|de|del|para|por|con|a)\s+', '', candidate).strip()
            candidate_clean = re.sub(r'(?i)\s+(?:en|de|del|para|por|con|a)$', '', candidate_clean).strip()

            # Verificar si lo que queda tiene contenido sustancial
            rem_words = [w for w in self._normalize(candidate_clean).split() if len(w) >= 2]
            stop_words = {"en", "de", "del", "para", "por", "con", "a", "el", "la", "los", "las", "un", "una"}
            meaningful_words = [w for w in rem_words if w not in stop_words]

            if meaningful_words:
                cleaned = candidate_clean

        # Limpieza final de preposiciones sueltas al borde
        cleaned = re.sub(r'(?i)^(?:en|de|del|para|por|con|a)\s+', '', cleaned).strip()
        cleaned = re.sub(r'(?i)\s+(?:en|de|del|para|por|con|a)$', '', cleaned).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Si quedó vacío o sin palabras con significado, usar el texto original
        if not cleaned:
            cleaned = raw_clean

        # Formatear adecuadamente si es minúscula
        if cleaned.islower():
            cleaned = cleaned.capitalize()

        return cleaned

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
                    # Default: Origen cuenta por defecto (Revolut/checking), Destino primera inversión o cuenta ahorro
                    def_id, def_name = self.get_default_account(df_accs)
                    src_acc_id, src_name = def_id, def_name
                    investments = df_accs[df_accs['type'].isin(['investment', 'savings'])]
                    if not investments.empty:
                        other_inv = investments[investments['id'] != src_acc_id]
                        if not other_inv.empty:
                            dst_acc_id = int(other_inv.iloc[0]['id'])
                            dst_name = str(other_inv.iloc[0]['name'])
                        else:
                            dst_acc_id = int(investments.iloc[0]['id'])
                            dst_name = str(investments.iloc[0]['name'])
                    elif len(df_accs) > 1:
                        other_accs = df_accs[df_accs['id'] != src_acc_id]
                        if not other_accs.empty:
                            dst_acc_id = int(other_accs.iloc[0]['id'])
                            dst_name = str(other_accs.iloc[0]['name'])

                if not src_acc_id or not dst_acc_id or src_acc_id == dst_acc_id:
                    return "⚠️ *Error en traspaso:* Especifica dos cuentas distintas (ej: `traspaso 300 Abanca a My Investor`)."

                cat_id, cat_name, cat_icon = self.match_category(rest_desc or "Fondos Indexados", "expense", df_cats)

                add_transfer(
                    source_account_id=src_acc_id,
                    dest_account_id=dst_acc_id,
                    amount=amount,
                    date=today_str,
                    description=f"Traspaso de {src_name} a {dst_name}",
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
                raw_concept = clean_text[:rev_match.start()].strip()
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
            raw_concept = match.group(2).strip()

        tx_type = 'income' if is_income else 'expense'
        
        # 1. Identificar categoría
        cat_id, cat_name, cat_icon = self.match_category(raw_concept, tx_type, df_cats)
        
        # 2. Identificar y extraer cuenta (o asignar cuenta por defecto Revolut)
        acc_id, acc_name, text_without_acc, was_explicit = self.extract_account(raw_concept, df_accs)
        
        # 3. Limpiar concepto de palabras redundantes de categoría si queda comercio/descripción
        final_concept = self.clean_concept(text_without_acc, cat_name)
        if not final_concept:
            final_concept = "Ingreso" if is_income else "Gasto"

        # Registrar transacción
        tx_id = add_transaction(
            account_id=acc_id,
            category_id=cat_id,
            date=today_str,
            amount=amount,
            description=final_concept,
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
            f"📝 *Concepto:* {final_concept}\n"
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

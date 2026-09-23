# 💰 FinanzasPro - Contexto del Proyecto y Registro de Sesiones (`gemini.md`)

Este documento sirve como **fuente única de verdad y memoria del proyecto** para que cualquier nueva sesión de Gemini / Antigravity comprenda de inmediato la arquitectura, funcionalidades implementadas, historial de decisiones de diseño, despliegues y convenciones de trabajo.

---

## 1. 📌 Visión General del Proyecto

**FinanzasPro** es una plataforma integral de finanzas personales, análisis de flujo de caja, presupuestación 50/30/20, seguimiento patrimonial e independencia financiera (FIRE), complementada con un asistente en tiempo real vía Telegram Bot.

### 🛠️ Stack Tecnológico
- **Lenguaje**: Python 3.10+ (probado y optimizado en Python 3.12).
- **Frontend / Dashboard**: [Streamlit](https://streamlit.io/) con componentes visuales interactivos construidos en [Plotly](https://plotly.com/python/).
- **Base de Datos**: SQLite relacional (`data/finance.db`) con esquema modularizado en SQL.
- **Bot Móvil**: Telegram Bot con polling asíncrono y parser de lenguaje natural desarrollado con librerías nativas (`urllib`), sin dependencias pesadas innecesarias.
- **Despliegue & Nube**: Servidor VPS en Oracle Cloud Infrastructure (Ubuntu), gestionado mediante `systemd`, con firewall y soporte Docker / Compose.
- **Control de Versiones**: Git & GitHub (`https://github.com/msanta23/finanzas-personales.git`).
- **Tests**: Suite automatizada con `pytest` (19 tests unitarios y de integración).

---

## 2. 🗣️ Historial de Conversaciones y Trabajo Realizado

### 💬 Conversación 1: "Personal Finance Optimization"
* **Objetivo**: Creación desde cero de la aplicación completa de finanzas personales.
* **Lo que se implementó**:
  1. **Base de Datos Relacional**: Tablas `accounts`, `categories`, `transactions`, `budgets`, `financial_goals` y `portfolio_snapshots`.
  2. **Capa de Servicios**:
     - `transaction_service.py`: CRUD de transacciones, cuentas, categorías, traspasos entre cuentas y motor de importación de extractos bancarios en CSV (compatible con BBVA, Santander, CaixaBank, Revolut, N26, etc.).
     - `budget_service.py`: Lógica de asignación 50/30/20 (Necesidades, Deseos, Ahorro/Inversión), límites mensuales y calculadora de fondo de emergencia.
     - `portfolio_service.py`: Cálculo de Patrimonio Neto (*Net Worth*), balance de activos vs pasivos, metas financieras y registro de *snapshots* históricos.
     - `optimizer_service.py`: Motor matemático con calculadora FIRE (regla del 4%, proyecciones de retiro e interés compuesto real ajustado por inflación) y simulador comparativo de amortización de deudas (**Método Avalancha** vs **Método Bola de Nieve** vs Pagos Mínimos).
  3. **Vistas de Interfaz Web (Streamlit)**:
     - `dashboard.py`: Panel principal con KPIs en tiempo real, gráficos de ingresos vs gastos, distribución mensual y alertas de sobrecostes.
     - `cashflow.py`: Historial con filtros múltiples, formularios de registro, traspasos y gestión de cuentas.
     - `budgets.py`: Seguimiento visual de presupuestos por categoría con semáforos de alerta.
     - `portfolio.py`: Distribución patrimonial, deudas y metas.
     - `optimizer.py`: Herramientas interactivas de simulación patrimonial y jubilación.
  4. **Bot de Telegram**: Asistente para registrar gastos/ingresos en lenguaje natural (ej. `15.50 Mercadona compra`, `+2300 Nómina`), consultar `/saldo`, `/resumen`, `/cuentas` y realizar transferencias.

### 💬 Conversación 2: "Estrategia De Asignación De Capital"
* **Objetivo**: Refinar la gestión patrimonial, seguimiento de inversiones y compromisos mensuales.
* **Lo que se implementó**:
  1. **Pestaña Exclusiva "Solo Inversiones" en Portfolio**: Separación estricta entre capital líquido en cuentas corrientes/efectivo y activos invertidos (Fondos indexados, ETFs, Cripto, Planes de Pensiones).
  2. **Métricas de Rentabilidad**: Cálculo del rendimiento anual ponderado (%) y retorno anual estimado en euros sobre las posiciones de inversión.
  3. **Panel de Compromisos Recurrentes y Gastos Fijos**: Vista en acordeón con ingresos fijos, suscripciones recurrentes y cálculo del *Margen Fijo Disponible*.
  4. **Filtros Temporales por Año y Mes**: Navegación ágil por períodos en el historial de transacciones y en el panel central.
  5. **Gestión Dinámica de Categorías**: Posibilidad de renombrar categorías y cambiar sus iconos emoji directamente desde la interfaz.
  6. **Mejora del Parser de Telegram**: Reconocimiento inteligente ampliado de palabras clave para autocategorizar gastos e ingresos con mayor precisión.

### 💬 Conversación 3: "Oracle"
* **Objetivo**: Despliegue en producción en la nube de Oracle Cloud Infrastructure.
* **Lo que se implementó**:
  1. **Infraestructura Cloud**:
     - Servidor Ubuntu en Oracle Cloud (IP pública: `143.47.48.164`).
     - Acceso seguro mediante clave SSH privada: `oracle_finanzas.key`.
  2. **Servicios Systemd en Producción**:
     - `deploy/finanzas-web.service`: Mantiene la interfaz de Streamlit activa en el puerto `8501`.
     - `deploy/finanzas-bot.service`: Mantiene el bot de Telegram escuchando mensajes de forma continua 24/7.
  3. **Scripts de Automatización en `deploy/`**:
     - `setup_oracle_cloud.sh`: Configura paquetes del sistema, entorno virtual `.venv`, reglas de firewall (`iptables`/`ufw`) y registra los servicios systemd.
     - `actualizar_servidor.sh`: Empaqueta el código local (excluyendo la DB de desarrollo, llaves y venv), lo sube por SCP/SSH a la máquina Oracle, actualiza dependencias y reinicia ambos servicios automáticamente.
     - `descargar_backup_db.sh`: Descarga la base de datos de producción `finance.db` desde el servidor Oracle a local y guarda un snapshot con fecha y hora en `data/backups/`.
  4. **Seguridad Web**:
     - Módulo `src/utils/auth.py` con pantalla de login protegida por contraseña (`WEB_PASSWORD` en `.env`).
     - Protección de rutas para evitar accesos no autorizados al dashboard en la nube.

### 💬 Conversación 4: "GitHub"
* **Objetivo**: Configuración del repositorio remoto, control de versiones y sincronización automática.
* **Lo que se implementó**:
  1. **Repositorio Remoto**: Conectado a `https://github.com/msanta23/finanzas-personales.git` en la rama `main`.
  2. **Pipeline Integrado de Despliegue**: El script `deploy/actualizar_servidor.sh` realiza automáticamente:
     `git add` ➔ `git commit` ➔ `git push origin main` ➔ Empaquetado ➔ `scp` / `ssh` a Oracle Cloud ➔ Reinicio de servicios.
  3. **Protección de Datos Sensibles**: `.gitignore` configurado para no versionar `.env`, claves privadas `*.key`, backups de base de datos ni bases de datos activas (`data/finance.db`).

---

## 3. 📂 Estructura del Proyecto

```
PF/
├── app.py                         # Entrada principal de Streamlit con autenticación y enrutado
├── run_bot.py                     # Script independiente para arrancar el bot de Telegram
├── requirements.txt               # Dependencias de Python
├── Dockerfile                     # Contenedorización de la app
├── docker-compose.yml             # Orquestación de servicios web y bot
├── oracle_finanzas.key            # Llave privada SSH para conectar con Oracle Cloud (NO versionar)
├── .env                           # Variables de entorno y secretos (NO versionar)
│
├── src/
│   ├── bot/
│   │   └── telegram_bot.py        # Lógica del bot, parser NLP y cliente HTTP nativo
│   ├── database/
│   │   ├── connection.py          # Conexión SQLite, funciones init_db, seed y clean
│   │   └── schema.sql             # Esquema DDL de todas las tablas
│   ├── services/
│   │   ├── transaction_service.py # Lógica de transacciones, cuentas, categorías, CSV
│   │   ├── budget_service.py      # Análisis 50/30/20 y fondo de emergencia
│   │   ├── portfolio_service.py   # Patrimonio neto, activos, deudas y metas
│   │   └── optimizer_service.py   # Algoritmos FIRE, interés compuesto y deudas
│   ├── ui/
│   │   ├── components.py          # Widgets visuales y gráficos Plotly
│   │   └── views/
│   │       ├── dashboard.py       # Panel central de gastos y flujo
│   │       ├── cashflow.py        # Flujo de caja, transferencias e importación CSV
│   │       ├── budgets.py         # Presupuestos por categoría y 50/30/20
│   │       ├── portfolio.py       # Inversiones, activos, deudas y metas
│   │       └── optimizer.py       # Simuladores FIRE y deudas
│   └── utils/
│       ├── auth.py                # Pantalla de login y validación de contraseña
│       └── formatting.py          # Formateo de moneda y porcentajes
│
├── deploy/
│   ├── setup_oracle_cloud.sh      # Script de aprovisionamiento inicial en la VM
│   ├── actualizar_servidor.sh     # Script unificado Git Push + Despliegue en Oracle
│   ├── descargar_backup_db.sh     # Script para sincronizar DB de producción a local
│   ├── finanzas-web.service       # Definición del servicio systemd para la web
│   └── finanzas-bot.service       # Definición del servicio systemd para el bot
│
├── data/
│   ├── finance.db                 # Base de datos SQLite activa local
│   └── backups/                   # Copias de seguridad históricas descargadas de la nube
│
└── tests/
    ├── conftest.py                # Fixtures y base de datos de pruebas en memoria/temporal
    ├── test_optimizer.py          # Tests del motor financiero (FIRE, deudas, interés)
    ├── test_services.py           # Tests de servicios de base de datos y negocio
    └── test_telegram_bot.py       # Tests del bot de Telegram y parser de texto
```

---

## 4. 🚀 Comandos y Flujo de Trabajo Frecuente

### Ejecutar en Local
```bash
# 1. Ejecutar la aplicación Web (Streamlit)
python3 -m streamlit run app.py

# 2. Ejecutar el Bot de Telegram (en otra terminal)
python3 run_bot.py

# 3. Pasar la suite de tests
PYTHONPATH="vendor:." python3 -m pytest tests/ -v
```

### Actualización a Producción (Oracle Cloud + GitHub)
Para subir cualquier cambio de código a GitHub y desplegarlo en el servidor de Oracle en un solo paso:
```bash
bash deploy/actualizar_servidor.sh "Descripción del cambio"
```

### Sincronizar Base de Datos de Producción
Para descargar a local las transacciones y cambios reales creados en el bot o la web en la nube:
```bash
bash deploy/descargar_backup_db.sh
```

---

## 5. 🤖 Formatos del Bot de Telegram

El bot escucha mensajes del usuario autorizado (`TELEGRAM_ALLOWED_USER_ID`) y reconoce:

* **Gastos**: `14.50 Mercadona compra`, `30 Cena en Revolut`, `5.20 Cafe con amigos`
* **Ingresos**: `+2200 Nómina mensual`, `+50 Venta Wallapop`
* **Traspasos**: `traspaso 300 Abanca a My Investor`, `transferir 50 de Cuenta Corriente a Ahorro`
* **Comandos**:
  - `/saldo` o `/cuentas`: Muestra el saldo de todas las cuentas y patrimonio neto.
  - `/resumen`: Resumen del mes actual con desglose 50/30/20 y ahorro.
  - `/ultimos`: Lista de los últimos 5 movimientos registrados.
  - `/categorias`: Lista de categorías disponibles para gastos e ingresos.
  - `/ayuda`: Guía de uso y ejemplos de sintaxis.

---

## 6. 🔐 Variables de Entorno (`.env`)

| Variable | Descripción | Ejemplo / Uso |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Token del bot generado por @BotFather en Telegram | `123456789:ABC...` |
| `TELEGRAM_ALLOWED_USER_ID` | ID numérico del usuario de Telegram permitido | `12345678` |
| `WEB_PASSWORD` | Contraseña para desbloquear la web en Streamlit | `tu_password_segura` |

---

## 7. 🎯 Directrices y Convenciones para Nuevas Sesiones

1. **Arquitectura por capas**: Mantener la separación estricta entre la capa de UI (`src/ui/`), servicios de negocio (`src/services/`) y acceso a datos (`src/database/`).
2. **Cero regresiones**: Siempre ejecutar los tests unitarios (`pytest tests/ -v`) tras realizar modificaciones en servicios, base de datos o el bot.
3. **Seguridad y privacidad**: Nunca incluir claves SSH, tokens de Telegram ni contraseñas en los commits de Git.
4. **Despliegue atómico**: Las actualizaciones en el servidor de Oracle deben hacerse siempre a través del script `deploy/actualizar_servidor.sh`.

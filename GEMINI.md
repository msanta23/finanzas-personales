# 💰 FinanzasPro - Contexto del Proyecto y Arquitectura (`GEMINI.md`)

Este documento sirve como **fuente única de verdad y contexto técnico** para que cualquier sesión de desarrollo comprenda de inmediato la arquitectura, funcionalidades implementadas, estructura del código, despliegue y convenciones de trabajo.

---

## 1. 📌 Visión General del Proyecto

**FinanzasPro** es una plataforma integral de finanzas personales, análisis de flujo de caja, seguimiento patrimonial, presupuestación e independencia financiera (FIRE), complementada con un asistente en tiempo real vía Telegram Bot.

### 🛠️ Stack Tecnológico
- **Lenguaje**: Python 3.10+ (probado y optimizado en Python 3.12).
- **Frontend / Dashboard**: [Streamlit](https://streamlit.io/) con componentes visuales interactivos en [Plotly](https://plotly.com/python/).
- **Base de Datos**: SQLite relacional (`data/finance.db`) con esquema modularizado en SQL.
- **Bot Móvil**: Telegram Bot con polling asíncrono y parser de lenguaje natural desarrollado con librerías nativas (`urllib`), sin dependencias pesadas innecesarias.
- **Despliegue & Nube**: Compatible con Linux VPS (systemd) y contenedores Docker / Docker Compose.
- **Control de Versiones**: Git & GitHub.
- **Tests**: Suite automatizada con `pytest` (tests unitarios y de integración).

---

## 2. ⚡ Módulos y Funcionalidades

### 📊 1. Panel Central (Dashboard)
- **5 KPIs principales**: Gastos del período (consumo puro), Inversiones/Ahorro, Margen Libre disponible, Tasa de Ahorro e Inversión (%) e Ingresos totales.
- **Selector Temporal**: Navegación por meses individuales o visualización de **"Todo el año"** con métricas y promedios acumulados.
- **Visualización Gráfica**:
  - Gráfico de evolución mensual (desglose de ingresos, gastos e inversiones).
  - Gráfico Donut de distribución de gastos reales por categoría.
  - Tabla de desglose de gastos ordenada de mayor a menor importe con porcentaje y número de movimientos.
- **Diagnóstico Financiero**: Cálculo de gasto medio diario y mensual.

### 💸 2. Flujo de Caja y Transacciones
- **Filtros Independientes**: Filtrado por tipo (`💸 Gastos`, `📈 Ahorro / Inversión`, `💰 Ingresos`), categorías dinámicas, cuentas y fechas.
- **Registro de Movimientos**: Formularios para transacciones simples y traspasos directos entre cuentas.
- **Importación de Extractos Bancarios (CSV)**: Motor de detección y parseo automático compatible con los principales bancos.
- **Gestión de Cuentas y Categorías**: Edición dinámica de nombres, tipos de cuenta, iconos emoji y clasificación.

### 🎯 3. Presupuestos y Compromisos
- **Límites Presupuestarios**: Asignación de límites mensuales por categoría con semáforos visuales de alerta.
- **Panel de Gastos Fijos y Recurrentes**: Acordeón con compromisos mensuales, suscripciones e ingresos recurrentes para calcular el *Margen Fijo Disponible*.
- **Calculadora de Fondo de Emergencia**: Diagnóstico de tasa de consumo mensual (*burn rate*) y cobertura en meses de seguridad.

### 📈 4. Patrimonio Neto e Inversiones (Portfolio)
- **Balance Patrimonial**: Cálculo automático de Patrimonio Neto (*Net Worth*), Activos vs Pasivos.
- **Pestaña Exclusiva "Solo Inversiones"**: Separación entre liquidez corriente y activos invertidos (Fondos indexados, ETFs, Cripto, Planes de Pensiones) con rentabilidad anual ponderada (%) y retorno estimado en euros.
- **Metas Financieras**: Objetivos de ahorro con seguimiento de progreso y fechas objetivo.
- **Histórico Patrimonial**: Registro de snapshots temporales para seguir la evolución del patrimonio.

### 🚀 5. Motor de Optimización Financiera
- **Calculadora FIRE (Financial Independence, Retire Early)**:
  - Edad estimada de retiro e importe objetivo según la regla del 4% (Standard, Lean y Fat FIRE).
  - Proyección de interés compuesto real ajustado por inflación.
- **Optimizador de Deudas**:
  - Comparativa exacta entre el **Método Avalancha** (máximo ahorro en intereses) vs **Método Bola de Nieve** (victorias psicológicas rápidas) vs Pagos Mínimos.

### 📱 6. Asistente Bot de Telegram
- **Registro en Lenguaje Natural**: Parser NLP que reconoce importes, comercios, categorías y cuentas (ej: `14.50 Mercadona compra`, `30 Cena en Revolut`, `+2200 Nómina`).
- **Cuenta por Defecto**: Asignación automática inteligente (Revolut por defecto si no se indica otra).
- **Comandos Rápidos**: `/saldo`, `/cuentas`, `/resumen`, `/ultimos`, `/categorias` y `/ayuda`.
- **Traspasos**: Reconocimiento de comandos de transferencia (ej: `traspaso 300 Abanca a My Investor`).
- **Seguridad**: Autenticación estricta por ID numérico de Telegram (`TELEGRAM_ALLOWED_USER_ID`).

---

## 3. 📂 Estructura del Proyecto

```
PF/
├── app.py                         # Entrada principal de Streamlit con autenticación y enrutado
├── run_bot.py                     # Script independiente para arrancar el bot de Telegram
├── requirements.txt               # Dependencias de Python
├── Dockerfile                     # Contenedorización de la app
├── docker-compose.yml             # Orquestación de servicios web y bot
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
│   │   ├── budget_service.py      # Análisis de presupuestos y fondo de emergencia
│   │   ├── portfolio_service.py   # Patrimonio neto, activos, deudas y metas
│   │   └── optimizer_service.py   # Algoritmos FIRE, interés compuesto y deudas
│   ├── ui/
│   │   ├── components.py          # Widgets visuales y gráficos Plotly
│   │   └── views/
│   │       ├── dashboard.py       # Panel central de gastos y flujo
│   │       ├── cashflow.py        # Flujo de caja, transferencias e importación CSV
│   │       ├── budgets.py         # Presupuestos por categoría
│   │       ├── portfolio.py       # Inversiones, activos, deudas y metas
│   │       └── optimizer.py       # Simuladores FIRE y deudas
│   └── utils/
│       ├── auth.py                # Pantalla de login y validación de contraseña
│       └── formatting.py          # Formateo de moneda y porcentajes
│
├── deploy/
│   ├── setup_oracle_cloud.sh      # Script de aprovisionamiento inicial en servidor VPS
│   ├── actualizar_servidor.sh     # Script unificado Git Push + Despliegue en servidor
│   ├── descargar_backup_db.sh     # Script para sincronizar DB de producción a local
│   ├── finanzas-web.service       # Definición del servicio systemd para la web
│   └── finanzas-bot.service       # Definición del servicio systemd para el bot
│
├── data/
│   ├── finance.db                 # Base de datos SQLite activa (NO versionar)
│   └── backups/                   # Copias de seguridad históricas locales (NO versionar)
│
└── tests/
    ├── conftest.py                # Fixtures y base de datos de pruebas en memoria
    ├── test_optimizer.py          # Tests del motor financiero (FIRE, deudas, interés)
    ├── test_services.py           # Tests de servicios de base de datos y negocio
    └── test_telegram_bot.py       # Tests del bot de Telegram y parser de texto
```

---

## 4. 🚀 Comandos y Flujo de Trabajo

### Ejecución en Local
```bash
# 1. Ejecutar la aplicación Web (Streamlit)
python3 -m streamlit run app.py

# 2. Ejecutar el Bot de Telegram (en otra terminal)
python3 run_bot.py

# 3. Ejecutar la suite de tests
PYTHONPATH="vendor:." python3 -m pytest tests/ -v
```

### Actualización a Producción y GitHub
Para versionar los cambios y desplegar en el servidor VPS:
```bash
bash deploy/actualizar_servidor.sh "Descripción del cambio"
```

### Sincronización de Base de Datos
Para descargar a local la base de datos de producción con los movimientos reales:
```bash
bash deploy/descargar_backup_db.sh
```

---

## 5. 🤖 Formatos del Bot de Telegram

* **Gastos**: `14.50 Mercadona compra`, `30 Cena en Revolut`, `5.20 Cafe con amigos`
* **Ingresos**: `+2200 Nómina mensual`, `+50 Venta Wallapop`
* **Traspasos**: `traspaso 300 Abanca a My Investor`, `transferir 50 de Cuenta Corriente a Ahorro`
* **Comandos**:
  - `/saldo` o `/cuentas`: Muestra saldos y patrimonio neto.
  - `/resumen`: Resumen del mes actual con desglose de gastos y ahorro.
  - `/ultimos`: Lista de las últimas 5 transacciones registradas.
  - `/categorias`: Lista de categorías disponibles.
  - `/ayuda`: Guía de sintaxis y ejemplos.

---

## 6. 🔐 Variables de Entorno (`.env`)

Crea un archivo `.env` en la raíz del proyecto con la siguiente estructura:

```env
TELEGRAM_BOT_TOKEN=tu_token_de_bot_aqui
TELEGRAM_ALLOWED_USER_ID=tu_id_numerico_de_telegram
WEB_PASSWORD=tu_password_segura_aqui
```

---

## 7. 🎯 Directrices y Buenas Prácticas

1. **Arquitectura por Capas**: Mantener la separación estricta entre UI (`src/ui/`), servicios de negocio (`src/services/`) y acceso a base de datos (`src/database/`).
2. **Cero Regresiones**: Ejecutar siempre los tests automatizados (`pytest tests/ -v`) tras cualquier cambio en la lógica o esquema.
3. **Seguridad y Privacidad**: Nunca versionar bases de datos (`*.db`), archivos de entorno (`.env`) ni claves privadas (`*.key`).
4. **Despliegue Atómico**: Utilizar los scripts automatizados en `deploy/` para garantizar despliegues seguros y consistentes.

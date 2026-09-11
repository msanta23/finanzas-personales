# 💰 FinanzasPro - Plataforma de Optimización de Finanzas Personales

Aplicación integral para el control, análisis y optimización matemática de finanzas personales, construida con **Python**, **Streamlit**, **SQLite** y **Plotly**.

---

## 🚀 Funcionalidades Principales

### 1. 📊 Panel Central (Dashboard)
- **KPIs en tiempo real**: Patrimonio Neto (*Net Worth*), Ingresos del mes, Gastos del mes y Tasa de Ahorro/Inversión.
- **Gráficos interactivos**: Flujo de caja comparativo mensual y distribución de gastos por categoría.
- **Diagnóstico rápido y alertas**: Notificaciones sobre sobrecostes presupuestarios y estado del fondo de emergencia.

### 2. 💸 Flujo de Caja y Transacciones
- **Historial y filtros**: Búsqueda avanzada por fecha, categoría, cuenta y tipo de movimiento.
- **Registro de movimientos**: Formulario para ingresos y gastos con impacto directo en saldos.
- **Importación de extractos bancarios (CSV)**: Carga masiva compatible con cualquier banco (BBVA, Santander, CaixaBank, Revolut, N26, etc.).
- **Gestión de cuentas y categorías**: Cuentas corrientes, cuentas de ahorro remuneradas, fondos indexados, préstamos e hipotecas.

### 3. 🎯 Presupuestos y Regla 50/30/20
- **Análisis 50/30/20**: Seguimiento en tiempo real de 50% Necesidades, 30% Deseos y 20% Ahorro/Inversión.
- **Límites por categoría**: Barras de progreso visual con semáforo de alerta (verde, amarillo, rojo).
- **Calculadora de Fondo de Emergencia**: Diagnóstico de tasa de consumo mensual (*burn rate*) y cobertura de seguridad en meses.

### 4. 📈 Patrimonio Neto e Inversiones
- **Desglose de activos y pasivos**: Cartera de fondos indexados, depósitos, cripto y deuda.
- **Seguimiento de objetivos financieros**: Metas de ahorro con barras de progreso y fechas límite.
- **Histórico patrimonial**: Registro de *snapshots* temporales para visualizar el crecimiento neto a largo plazo.

### 5. 🚀 Motor de Optimización Financiera
- **🔥 Calculadora FIRE (Financial Independence, Retire Early)**:
  - Cálculo de la edad de retiro e importe objetivo según la regla del 4% (Standard, Lean y Fat FIRE).
  - Curva de cruce de capitalización acumulada.
- **📈 Calculadora de Interés Compuesto**:
  - Proyección de aportaciones periódicas, rendimiento nominal y poder adquisitivo real ajustado por inflación.
- **⚡ Optimizador de Deudas**:
  - Comparativa exacta entre el **Método Avalancha** (máximo ahorro en intereses) vs **Método Bola de Nieve** (victorias psicológicas rápidas) vs Pagos Mínimos.
- **🩺 Diagnóstico de Salud Financiera**:
  - Evaluación integral con recomendaciones priorizadas de ahorro y reducción de fugas de capital.

### 6. 📱 Asistente Bot de Telegram
- **Registro instantáneo desde el móvil**: Envío de gastos e ingresos en texto natural (ej: `15.50 Mercadona compra`, `35 Cena en Revolut`, `+2300 Nómina`).
- **Autocategorización inteligente**: Detección automática por palabras clave y asignación a cuentas bancarias.
- **Consultas en tiempo real**: Comandos `/saldo`, `/resumen`, `/cuentas`, `/ultimos` y `/categorias`.
- **Traspasos de fondos**: Ej. `traspaso 300 Abanca a My Investor`.
- **Seguridad y privacidad**: Restringido exclusivamente al ID de Telegram del propietario.

---

## 🛠️ Instalación y Ejecución

### Requisitos
- Python 3.10 o superior

### Paso a Paso

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecutar la aplicación Web:**
   ```bash
   python3 -m streamlit run app.py
   ```
   *La base de datos SQLite y los datos de demostración iniciales se generarán automáticamente en el primer arranque.*

3. **Ejecutar el Bot de Telegram (Opcional):**
   ```bash
   python3 run_bot.py
   ```

4. **Ejecutar tests automatizados:**
   ```bash
   PYTHONPATH="vendor:." python3 -m pytest tests/ -v
   ```

---

## 📂 Estructura del Código

```
PF/
├── src/
│   ├── database/
│   │   ├── connection.py        # Conexión SQLite y generación de datos demo
│   │   └── schema.sql           # Esquema relacional de tablas
│   ├── services/
│   │   ├── transaction_service.py # Lógica de transacciones, cuentas y CSV
│   │   ├── budget_service.py      # Análisis de presupuestos y fondo de emergencia
│   │   ├── portfolio_service.py   # Patrimonio neto, activos y metas
│   │   └── optimizer_service.py   # Algoritmos FIRE, interés compuesto y deudas
│   ├── ui/
│   │   ├── components.py          # KPIs y gráficos Plotly reutilizables
│   │   └── views/                 # Vistas individuales de la interfaz
│   │       ├── dashboard.py
│   │       ├── cashflow.py
│   │       ├── budgets.py
│   │       ├── portfolio.py
│   │       └── optimizer.py
│   └── utils/
│       └── formatting.py          # Formateo monetario y porcentual
├── tests/
│   ├── test_optimizer.py          # Tests de fórmulas financieras
│   └── test_services.py           # Tests de base de datos y lógica de negocio
├── app.py                         # Entrada principal de la aplicación Streamlit
├── requirements.txt               # Dependencias de Python
└── README.md
```

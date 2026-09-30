import sys
from pathlib import Path

# Añadir raíz y dependencias vendor a sys.path
ROOT_DIR = Path(__file__).resolve().parent
VENDOR_DIR = ROOT_DIR / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

# Configurar layout de página
st.set_page_config(
    page_title="Optimizador de Finanzas Personales",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ocultar barra lateral y dejar cabecera transparente para mantener los 3 puntos arriba a la derecha
st.markdown(
    """
    <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
        }
        footer {
            visibility: hidden;
        }
        .block-container {
            padding-top: 4.2rem !important;
            padding-bottom: 2rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

from src.utils.auth import check_password, render_logout_button

# Proteger la aplicación con contraseña
check_password()

from src.database.connection import init_db, seed_demo_data, clear_user_data
from src.ui.views.dashboard import render_dashboard_view
from src.ui.views.cashflow import render_cashflow_view
from src.ui.views.budgets import render_budgets_view
from src.ui.views.portfolio import render_portfolio_view
from src.ui.views.optimizer import render_optimizer_view

# Inicializar base de datos y datos demo si está vacía
init_db()
seed_demo_data(force=False)

def main():
    # ----------------------------------------------------
    # BARRA SUPERIOR (MENÚ DE NAVEGACIÓN Y CERRAR SESIÓN)
    # ----------------------------------------------------
    col_nav, col_logout = st.columns([6, 1], vertical_alignment="center")

    with col_nav:
        nav_options = [
            "📊 Panel Central",
            "💸 Flujo de Caja y Gastos",
            "🎯 Presupuestos y 50/30/20",
            "📈 Patrimonio e Inversiones",
            "🚀 Motor de Optimización"
        ]

        page_selection = st.segmented_control(
            "Navegación",
            nav_options,
            default="📊 Panel Central",
            label_visibility="collapsed"
        )
        if not page_selection:
            page_selection = "📊 Panel Central"

    with col_logout:
        render_logout_button()

    st.markdown("---")

    # ----------------------------------------------------
    # RENDERIZADO DE LA VISTA SELECCIONADA
    # ----------------------------------------------------
    currency_symbol = "€"

    if page_selection == "📊 Panel Central":
        render_dashboard_view(currency_symbol=currency_symbol)
    elif page_selection == "💸 Flujo de Caja y Gastos":
        render_cashflow_view(currency_symbol=currency_symbol)
    elif page_selection == "🎯 Presupuestos y 50/30/20":
        render_budgets_view(currency_symbol=currency_symbol)
    elif page_selection == "📈 Patrimonio e Inversiones":
        render_portfolio_view(currency_symbol=currency_symbol)
    elif page_selection == "🚀 Motor de Optimización":
        render_optimizer_view(currency_symbol=currency_symbol)

if __name__ == "__main__":
    main()

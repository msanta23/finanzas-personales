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
    initial_sidebar_state="expanded"
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

@st.dialog("⚠️ Confirmación de Borrado Total")
def confirm_clear_dialog():
    st.warning("⚠️ **Atención:** Esta acción es irreversible. Se borrarán todas las transacciones, cuentas, presupuestos y metas financieras.")
    confirm_check = st.checkbox("Confirmo que deseo borrar todos los datos", value=False)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancelar", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("🗑️ Borrar Definitivamente", type="primary", disabled=not confirm_check, use_container_width=True):
            clear_user_data(keep_categories=True)
            st.toast("¡Base de datos limpia! Lista para empezar de cero.", icon="🗑️")
            st.rerun()

@st.dialog("🔄 Cargar Datos de Demostración")
def confirm_seed_dialog():
    st.info("ℹ️ Esta acción reemplazará los datos actuales con el conjunto completo de datos de demostración de ejemplo.")
    confirm_check = st.checkbox("Confirmo que deseo sobreescribir con datos de prueba", value=False)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancelar", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("🔄 Cargar Demo", type="primary", disabled=not confirm_check, use_container_width=True):
            seed_demo_data(force=True)
            st.toast("¡Datos de demostración restaurados!", icon="🔄")
            st.rerun()

def main():
    # ----------------------------------------------------
    # SIDEBAR / MENÚ DE NAVEGACIÓN
    # ----------------------------------------------------
    with st.sidebar:
        st.markdown("## 💰 **FinanzasPro**")
        st.caption("Sistema de Optimización Financiera")
        st.markdown("---")

        page_selection = st.radio(
            "Navegación",
            [
                "📊 Panel Central",
                "💸 Flujo de Caja y Gastos",
                "🎯 Presupuestos y 50/30/20",
                "📈 Patrimonio e Inversiones",
                "🚀 Motor de Optimización"
            ],
            index=0
        )

        st.markdown("---")
        st.subheader("⚙️ Configuración")
        currency_symbol = st.selectbox("Moneda principal", ["€", "$", "£"], index=0)

        with st.expander("🛠️ Gestión de Datos"):
            if st.button("🗑️ Limpiar Datos (Empezar de Cero)", type="primary", use_container_width=True, help="Borra todos los movimientos, cuentas y presupuestos de ejemplo conservando las categorías para tus finanzas."):
                confirm_clear_dialog()

            if st.button("🔄 Cargar Datos de Demostración", type="secondary", use_container_width=True, help="Restaura un conjunto completo de transacciones, cuentas y metas de ejemplo."):
                confirm_seed_dialog()

        st.markdown("---")
        render_logout_button()
        st.caption("Desarrollado para optimización patrimonial e independencia financiera.")

    # ----------------------------------------------------
    # RENDERIZADO DE LA VISTA SELECCIONADA
    # ----------------------------------------------------
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

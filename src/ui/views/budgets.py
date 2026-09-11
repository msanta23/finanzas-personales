import streamlit as st
import pandas as pd
from datetime import datetime
from ...services.budget_service import get_50_30_20_analysis, get_budget_vs_actual, set_budget, get_emergency_fund_status
from ...services.transaction_service import get_categories
from ...utils.formatting import format_currency, format_percentage
from ..components import plot_50_30_20_gauge

def render_budgets_view(currency_symbol: str = "€"):
    """Vista para gestión de presupuestos, regla 50/30/20 y fondo de emergencia."""
    st.title("🎯 Presupuestos y Fondo de Emergencia")
    st.caption("Planifica tus límites de gasto, equilibra la regla 50/30/20 y asegura tu colchón de seguridad.")

    now = datetime.now()
    col_y, col_m = st.columns([1, 2])
    with col_y:
        selected_year = st.selectbox("Año", [now.year, now.year - 1], index=0, key="bud_year")
    with col_m:
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        selected_month = st.selectbox("Mes de análisis", range(1, 13), index=now.month - 1, format_func=lambda m: month_names[m-1], key="bud_month")

    tab_5020, tab_cats, tab_emergency = st.tabs([
        "⚖️ Regla 50/30/20",
        "📊 Presupuesto por Categoría",
        "🛡️ Fondo de Emergencia"
    ])

    # ----------------------------------------------------
    # TAB 1: REGLA 50/30/20
    # ----------------------------------------------------
    with tab_5020:
        analysis = get_50_30_20_analysis(selected_year, selected_month)
        
        st.subheader("Distribución Presupuestaria Actual vs Objetivo")
        st.plotly_chart(plot_50_30_20_gauge(analysis, currency_symbol), use_container_width=True)

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🏠 Necesidades (50%)")
            st.write(f"**Gasto real:** {format_currency(analysis['needs']['actual'], currency_symbol)} ({analysis['needs']['pct']:.1f}%)")
            st.write(f"**Objetivo (50%):** {format_currency(analysis['needs']['target'], currency_symbol)}")
            diff = analysis['needs']['diff']
            if diff >= 0:
                st.success(f"✅ Dentro del límite (+{format_currency(diff, currency_symbol)} de margen)")
            else:
                st.error(f"⚠️ Excedido en {format_currency(abs(diff), currency_symbol)}")

        with col2:
            st.markdown("### 🎉 Deseos y Ocio (30%)")
            st.write(f"**Gasto real:** {format_currency(analysis['wants']['actual'], currency_symbol)} ({analysis['wants']['pct']:.1f}%)")
            st.write(f"**Objetivo (30%):** {format_currency(analysis['wants']['target'], currency_symbol)}")
            diff = analysis['wants']['diff']
            if diff >= 0:
                st.success(f"✅ Dentro del límite (+{format_currency(diff, currency_symbol)} de margen)")
            else:
                st.warning(f"⚠️ Excedido en {format_currency(abs(diff), currency_symbol)}")

        with col3:
            st.markdown("### 📈 Ahorro / Inversión (20%)")
            st.write(f"**Aportación real:** {format_currency(analysis['savings']['actual'], currency_symbol)} ({analysis['savings']['pct']:.1f}%)")
            st.write(f"**Objetivo (20%):** {format_currency(analysis['savings']['target'], currency_symbol)}")
            diff = analysis['savings']['diff']
            if diff >= 0:
                st.success(f"🎉 Superando objetivo en +{format_currency(diff, currency_symbol)}")
            else:
                st.error(f"🚨 Por debajo del objetivo en {format_currency(abs(diff), currency_symbol)}")

    # ----------------------------------------------------
    # TAB 2: PRESUPUESTO POR CATEGORÍA
    # ----------------------------------------------------
    with tab_cats:
        st.subheader("Seguimiento de Límites Mensuales")
        df_budgets = get_budget_vs_actual(selected_year, selected_month)

        if not df_budgets.empty:
            for _, row in df_budgets.iterrows():
                icon = row['category_icon'] if pd.notna(row['category_icon']) else "📌"
                cat_name = f"{icon} {row['category_name']}"
                spent = row['actual_spent']
                limit = row['budget_limit']
                pct = row['pct_used']
                status = row['status']

                c_left, c_mid, c_right = st.columns([3, 5, 2])
                with c_left:
                    st.write(f"**{cat_name}**")
                    st.caption(f"{format_currency(spent, currency_symbol)} de {format_currency(limit, currency_symbol)}")
                with c_mid:
                    bar_val = min(1.0, spent / limit) if limit > 0 else (1.0 if spent > 0 else 0.0)
                    st.progress(bar_val)
                with c_right:
                    if status == "Excedido":
                        st.markdown(f"🔴 **{pct:.0f}%** (Excedido)")
                    elif status == "En alerta":
                        st.markdown(f"🟡 **{pct:.0f}%** (Alerta)")
                    elif status == "Sin presupuesto":
                        st.markdown("⚪ **Sin límite**")
                    else:
                        st.markdown(f"🟢 **{pct:.0f}%** (OK)")
                st.markdown("<hr style='margin: 4px 0;'/>", unsafe_allow_html=True)

            # Formulario para editar límites
            with st.expander("✏️ Ajustar Límites Presupuestarios"):
                df_cats = get_categories(type_filter="expense")
                cat_choices = [(f"{r['icon']} {r['name']}", r['id']) for _, r in df_cats.iterrows()]
                
                with st.form("form_edit_budget"):
                    sel_cat = st.selectbox("Categoría a modificar", cat_choices, format_func=lambda x: x[0])
                    new_limit = st.number_input("Nuevo límite mensual", min_value=0.0, step=25.0, format="%.2f")
                    is_custom_month = st.checkbox(f"Aplicar solo a {month_names[selected_month-1]} {selected_year} (por defecto aplica a todos)")
                    
                    if st.form_submit_button("Actualizar Límite"):
                        target_m = f"{selected_year:04d}-{selected_month:02d}" if is_custom_month else "default"
                        set_budget(sel_cat[1], new_limit, target_m)
                        st.success("Límite actualizado correctamente.")
                        st.rerun()

    # ----------------------------------------------------
    # TAB 3: FONDO DE EMERGENCIA
    # ----------------------------------------------------
    with tab_emergency:
        st.subheader("Calculadora y Diagnóstico del Fondo de Emergencia")
        
        target_months_input = st.slider("Meses de cobertura deseados", min_value=3, max_value=12, value=6, step=1)
        ef_info = get_emergency_fund_status(months_target=target_months_input)

        col_ef1, col_ef2, col_ef3 = st.columns(3)
        with col_ef1:
            st.metric("Gasto mensual imprescindible (Burn Rate)", format_currency(ef_info["monthly_burn_rate"], currency_symbol))
        with col_ef2:
            st.metric("Liquidez Disponible (Cuentas/Ahorro)", format_currency(ef_info["liquid_savings"], currency_symbol))
        with col_ef3:
            st.metric("Cobertura Actual", f"{ef_info['months_covered']:.1f} meses", delta=f"{ef_info['months_covered'] - target_months_input:.1f} vs objetivo")

        st.markdown("---")

        target_amount = ef_info["target_amount"]
        liquid = ef_info["liquid_savings"]
        progress_ef = min(1.0, liquid / target_amount) if target_amount > 0 else 1.0

        st.write(f"**Progreso hacia el objetivo de {target_months_input} meses ({format_currency(target_amount, currency_symbol)}):**")
        st.progress(progress_ef)

        if ef_info["is_healthy"]:
            st.success(f"🎉 ¡Tu fondo de emergencia está completo! Cubre {ef_info['months_covered']:.1f} meses de gastos fijos. Tienes excedente de {format_currency(abs(ef_info['gap']), currency_symbol)} que puedes destinar a inversión.")
        else:
            st.warning(f"⚠️ Te faltan {format_currency(ef_info['gap'], currency_symbol)} para alcanzar tu objetivo de {target_months_input} meses de seguridad.")

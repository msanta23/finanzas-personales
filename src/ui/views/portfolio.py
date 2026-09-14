import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
from ...services.portfolio_service import (
    get_net_worth_summary, get_asset_allocation, get_investment_allocation, get_liabilities,
    get_historical_snapshots, take_snapshot, get_financial_goals,
    add_financial_goal, update_goal_progress
)
from ...services.transaction_service import update_account_balance, delete_account
from ...utils.formatting import format_currency, format_percentage
from ..components import plot_net_worth_trend

acc_type_map = {
    'investment': 'Fondos / Acciones / ETFs',
    'crypto': 'Criptomonedas',
    'real_estate': 'Bienes Inmuebles',
    'pension': 'Planes de Pensiones',
    'savings': 'Cuenta Ahorro / Remunerada',
    'checking': 'Cuenta Corriente',
    'loan': 'Préstamo',
    'mortgage': 'Hipoteca'
}

def render_portfolio_view(currency_symbol: str = "€"):
    """Vista de seguimiento patrimonial, activos, deudas y objetivos financieros."""
    st.title("📈 Patrimonio Neto e Inversiones")
    st.caption("Gestiona tu cartera de activos, supervisa tus pasivos y avanza hacia tus metas financieras.")

    nw_summary = get_net_worth_summary()

    # Métricas superiores
    col_nw1, col_nw2, col_nw3 = st.columns(3)
    with col_nw1:
        st.metric("Total Activos (Patrimonio Bruto)", format_currency(nw_summary["total_assets"], currency_symbol))
    with col_nw2:
        st.metric("Total Pasivos (Deudas)", format_currency(nw_summary["total_liabilities"], currency_symbol), delta_color="inverse")
    with col_nw3:
        st.metric("Patrimonio Neto (Net Worth)", format_currency(nw_summary["net_worth"], currency_symbol))

    st.markdown("---")

    tab_investments, tab_assets, tab_debts, tab_goals, tab_history = st.tabs([
        "📈 Solo Inversiones",
        "💎 Todos los Activos y Efectivo",
        "📉 Deudas y Pasivos",
        "🏆 Objetivos Financieros",
        "📊 Histórico Patrimonial"
    ])

    # ----------------------------------------------------
    # TAB 1: SOLO INVERSIONES (Excluye cuentas corrientes y efectivo)
    # ----------------------------------------------------
    with tab_investments:
        df_inv = get_investment_allocation()
        if not df_inv.empty:
            total_invested = df_inv['balance'].sum()
            net_worth = nw_summary.get("net_worth", 0.0)
            inv_pct_nw = (total_invested / net_worth * 100) if net_worth > 0 else 0.0
            
            # Cálculo de rendimiento anual ponderado
            weighted_yield = (df_inv['balance'] * df_inv['interest_rate']).sum() / total_invested if total_invested > 0 else 0.0
            annual_estimated_return = (df_inv['balance'] * (df_inv['interest_rate'] / 100.0)).sum()

            col_i1, col_i2, col_i3, col_i4 = st.columns(4)
            with col_i1:
                st.metric("Total Invertido", format_currency(total_invested, currency_symbol))
            with col_i2:
                st.metric("% de tu Patrimonio Neto", f"{inv_pct_nw:.1f}%")
            with col_i3:
                st.metric("Rendimiento Medio Estimado", f"{weighted_yield:.2f}% / año")
            with col_i4:
                st.metric("Retorno Anual Estimado", f"+{format_currency(annual_estimated_return, currency_symbol)}/año")

            st.markdown("---")

            col_inv_chart, col_inv_list = st.columns([1, 1])
            with col_inv_chart:
                st.subheader("Distribución de la Cartera de Inversión")
                fig_inv = px.pie(
                    df_inv,
                    names='name',
                    values='balance',
                    hole=0.5,
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_inv.update_traces(textposition='inside', textinfo='percent+label')
                fig_inv.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
                st.plotly_chart(fig_inv, use_container_width=True)

            with col_inv_list:
                st.subheader("Posiciones de Inversión")
                for _, row in df_inv.iterrows():
                    type_label = acc_type_map.get(row['type'], str(row['type']).capitalize())
                    st.write(f"**{row['name']}** · `{type_label}`")
                    yield_info = f" | Rendimiento: **{row['interest_rate']:.1f}%**" if row['interest_rate'] > 0 else ""
                    st.caption(f"Valor: **{format_currency(row['balance'], currency_symbol)}** — {row['percentage']:.1f}% de tus inversiones{yield_info}")
                    st.markdown("<hr style='margin: 4px 0;'/>", unsafe_allow_html=True)

            with st.expander("🔄 Actualizar Valoración de una Inversión"):
                inv_choices = [(r['name'], r['id'], r['balance']) for _, r in df_inv.iterrows()]
                with st.form("form_update_inv_balance"):
                    sel_inv = st.selectbox(
                        "Selecciona la inversión",
                        inv_choices,
                        format_func=lambda x: f"{x[0]} (Valor actual: {format_currency(x[2], currency_symbol)})"
                    )
                    new_inv_balance = st.number_input(
                        "Nuevo valor total / liquidativo",
                        min_value=0.0,
                        value=float(sel_inv[2]) if sel_inv else 0.0,
                        step=100.0,
                        format="%.2f",
                        help="Actualiza el valor actual de tu fondo, acciones o criptoactivos."
                    )
                    save_snapshot_inv = st.checkbox("Guardar snapshot histórico con la nueva valoración", value=True, key="snap_inv")
                    if st.form_submit_button("Guardar Nueva Valoración", type="primary"):
                        update_account_balance(sel_inv[1], new_inv_balance)
                        if save_snapshot_inv:
                            take_snapshot()
                        st.success(f"Valoración de '{sel_inv[0]}' actualizada a {format_currency(new_inv_balance, currency_symbol)}.")
                        st.rerun()
        else:
            st.info("💡 No tienes cuentas ni activos catalogados como inversión todavía. Puedes dar de alta fondos, acciones, criptoactivos o inmuebles en la pestaña 'Cuentas y Categorías' de Flujo de Caja.")

    # ----------------------------------------------------
    # TAB 2: TODOS LOS ACTIVOS (Incluye cuentas corrientes y ahorro)
    # ----------------------------------------------------
    with tab_assets:
        df_assets = get_asset_allocation()
        if not df_assets.empty:
            col_chart, col_list = st.columns([1, 1])
            with col_chart:
                st.subheader("Distribución Global de Activos")
                fig = px.pie(
                    df_assets,
                    names='name',
                    values='balance',
                    hole=0.5,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with col_list:
                st.subheader("Detalle de Todas las Cuentas")
                for _, row in df_assets.iterrows():
                    type_label = acc_type_map.get(row['type'], str(row['type']).capitalize())
                    st.write(f"**{row['name']}** ({type_label})")
                    st.caption(f"Saldo: **{format_currency(row['balance'], currency_symbol)}** — {row['percentage']:.1f}% del total")
                    st.markdown("<hr style='margin: 4px 0;'/>", unsafe_allow_html=True)

            with st.expander("🔄 Actualizar Valoración / Saldo de un Activo"):
                asset_choices = [(r['name'], r['id'], r['balance']) for _, r in df_assets.iterrows()]
                with st.form("form_update_asset_balance"):
                    sel_asset = st.selectbox(
                        "Selecciona el activo o cuenta",
                        asset_choices,
                        format_func=lambda x: f"{x[0]} (Saldo actual: {format_currency(x[2], currency_symbol)})"
                    )
                    new_asset_balance = st.number_input(
                        "Nuevo valor liquidativo / saldo total",
                        min_value=0.0,
                        value=float(sel_asset[2]) if sel_asset else 0.0,
                        step=100.0,
                        format="%.2f",
                        help="Introduce el valor total actual de tu cartera o cuenta sin registrarlo como flujo de ingresos."
                    )
                    save_snapshot = st.checkbox("Guardar snapshot histórico con la nueva valoración", value=True)
                    if st.form_submit_button("Guardar Nueva Valoración", type="primary"):
                        update_account_balance(sel_asset[1], new_asset_balance)
                        if save_snapshot:
                            take_snapshot()
                        st.success(f"Valoración de '{sel_asset[0]}' actualizada a {format_currency(new_asset_balance, currency_symbol)}.")
                        st.rerun()
        else:
            st.info("No tienes activos registrados aún.")

    # ----------------------------------------------------
    # TAB 2: DEUDAS
    # ----------------------------------------------------
    with tab_debts:
        df_debts = get_liabilities()
        if not df_debts.empty:
            st.subheader("Listado de Deudas y Coste por Intereses")
            
            # Estimación de coste anual de intereses
            df_debts['annual_interest_cost'] = df_debts['balance'] * (df_debts['interest_rate'] / 100.0)
            total_annual_interest = df_debts['annual_interest_cost'].sum()

            st.warning(f"💸 **Coste anual estimado en intereses:** {format_currency(total_annual_interest, currency_symbol)}/año.")

            display_debts = df_debts.copy()
            display_debts['balance_fmt'] = display_debts['balance'].apply(lambda x: format_currency(x, currency_symbol))
            display_debts['rate_fmt'] = display_debts['interest_rate'].apply(lambda x: f"{x:.1f}%")
            display_debts['interest_cost_fmt'] = display_debts['annual_interest_cost'].apply(lambda x: format_currency(x, currency_symbol))

            cols_show = ['id', 'name', 'type', 'balance_fmt', 'rate_fmt', 'interest_cost_fmt']
            renamed = {
                'id': 'ID',
                'name': 'Nombre Deuda',
                'type': 'Tipo',
                'balance_fmt': 'Saldo Pendiente',
                'rate_fmt': 'Interés (TAE)',
                'interest_cost_fmt': 'Interés Anual'
            }
            st.dataframe(display_debts[cols_show].rename(columns=renamed), use_container_width=True, hide_index=True)

            with st.expander("🔄 Actualizar Saldo Pendiente de una Deuda"):
                debt_choices = [(r['name'], r['id'], r['balance']) for _, r in df_debts.iterrows()]
                with st.form("form_update_debt_balance"):
                    sel_debt = st.selectbox(
                        "Selecciona la deuda o pasivo",
                        debt_choices,
                        format_func=lambda x: f"{x[0]} (Saldo pendiente: {format_currency(x[2], currency_symbol)})"
                    )
                    new_debt_balance = st.number_input(
                        "Nuevo saldo pendiente",
                        min_value=0.0,
                        value=float(sel_debt[2]) if sel_debt else 0.0,
                        step=100.0,
                        format="%.2f"
                    )
                    save_snap_debt = st.checkbox("Guardar snapshot histórico con el nuevo saldo", value=True)
                    if st.form_submit_button("Actualizar Saldo Deuda", type="primary"):
                        update_account_balance(sel_debt[1], new_debt_balance)
                        if save_snap_debt:
                            take_snapshot()
                        st.success(f"Saldo de '{sel_debt[0]}' actualizado a {format_currency(new_debt_balance, currency_symbol)}.")
                        st.rerun()
        else:
            st.success("🎉 ¡Felicidades! No tienes deudas ni pasivos pendientes.")

    # ----------------------------------------------------
    # TAB 3: OBJETIVOS FINANCIEROS
    # ----------------------------------------------------
    with tab_goals:
        st.subheader("Metas de Ahorro e Inversión")
        df_goals = get_financial_goals()

        if not df_goals.empty:
            for _, goal in df_goals.iterrows():
                target = goal['target_amount']
                current = goal['current_amount']
                pct = goal['pct_progress']
                completed = goal['is_completed']
                
                col_g1, col_g2, col_g3 = st.columns([3, 4, 2])
                with col_g1:
                    status_icon = "✅" if completed else "🎯"
                    st.write(f"**{status_icon} {goal['title']}**")
                    st.caption(f"{format_currency(current, currency_symbol)} de {format_currency(target, currency_symbol)} | Límite: {goal['target_date'] or 'Sin fecha'}")
                with col_g2:
                    st.progress(min(1.0, current / target) if target > 0 else 1.0)
                with col_g3:
                    st.write(f"**{pct:.1f}%**")
                
                st.markdown("<hr style='margin: 4px 0;'/>", unsafe_allow_html=True)

            with st.expander("🔄 Actualizar Progreso de una Meta"):
                goal_choices = [(g['title'], g['id']) for _, g in df_goals.iterrows()]
                with st.form("form_update_goal"):
                    sel_g = st.selectbox("Meta a actualizar", goal_choices, format_func=lambda x: x[0])
                    new_curr_amt = st.number_input("Nuevo importe acumulado", min_value=0.0, step=100.0, format="%.2f")
                    if st.form_submit_button("Guardar Progreso"):
                        update_goal_progress(sel_g[1], new_curr_amt)
                        st.success("Progreso actualizado.")
                        st.rerun()

        else:
            st.info("No hay metas financieras creadas.")

        with st.expander("➕ Crear Nueva Meta Financiera"):
            with st.form("form_new_goal", clear_on_submit=True):
                g_title = st.text_input("Título de la meta", placeholder="Ej: Compra coche, Viaje a Japón, Invertir 50k...")
                g_target = st.number_input("Importe objetivo", min_value=1.0, step=500.0, format="%.2f")
                g_initial = st.number_input("Importe ya acumulado", min_value=0.0, step=100.0, format="%.2f")
                g_date = st.date_input("Fecha límite deseada")
                g_cat = st.selectbox("Categoría", ["savings_goal", "emergency_fund", "investment", "debt_payoff"], format_func=lambda x: {
                    'savings_goal': 'Ahorro General',
                    'emergency_fund': 'Fondo de Emergencia',
                    'investment': 'Inversión',
                    'debt_payoff': 'Liquidación de Deuda'
                }.get(x, x))

                if st.form_submit_button("Crear Meta"):
                    if g_title.strip():
                        add_financial_goal(g_title, g_target, g_initial, g_date.strftime("%Y-%m-%d"), g_cat)
                        st.success("Meta creada exitosamente.")
                        st.rerun()

    # ----------------------------------------------------
    # TAB 4: HISTÓRICO PATRIMONIAL
    # ----------------------------------------------------
    with tab_history:
        st.subheader("Evolución Temporal del Patrimonio Neto")
        df_hist = get_historical_snapshots()
        if not df_hist.empty:
            st.plotly_chart(plot_net_worth_trend(df_hist, currency_symbol), use_container_width=True)
            
            with st.expander("Ver tabla histórica de snapshots"):
                st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("No hay snapshots registrados.")

        if st.button("📸 Tomar Snapshot del Patrimonio Hoy"):
            take_snapshot()
            st.success("Snapshot registrado.")
            st.rerun()

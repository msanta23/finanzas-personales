import streamlit as st
import pandas as pd
from datetime import datetime
from ...services.transaction_service import get_transactions, get_accounts
from ...services.budget_service import get_50_30_20_analysis, get_budget_vs_actual, get_emergency_fund_status
from ...services.portfolio_service import get_net_worth_summary, get_historical_snapshots, take_snapshot
from ...utils.formatting import format_currency, format_percentage, format_delta_currency
from ..components import render_kpi_card, plot_cashflow_bar, plot_expense_donut, plot_net_worth_trend

def render_dashboard_view(currency_symbol: str = "€"):
    """Renderiza el panel principal con KPIs, gráficos clave y alertas de salud financiera."""
    st.title("📊 Panel Financiero Central")
    st.caption("Visión general en tiempo real de tu salud financiera, flujo de caja y patrimonio neto.")

    # 1. Filtro temporal (Selector de mes actual o previo)
    now = datetime.now()
    col_filter1, col_filter2 = st.columns([2, 1])
    with col_filter1:
        selected_year = st.selectbox("Año", [now.year, now.year - 1], index=0, key="dash_year")
    with col_filter2:
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        selected_month = st.selectbox("Mes", range(1, 13), index=now.month - 1, format_func=lambda m: month_names[m-1], key="dash_month")

    # 2. Métricas Clave (KPIs)
    summary_50_30_20 = get_50_30_20_analysis(selected_year, selected_month)
    net_worth = get_net_worth_summary()
    emergency_fund = get_emergency_fund_status(months_target=6)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        render_kpi_card(
            title="Patrimonio Neto",
            value=format_currency(net_worth["net_worth"], currency_symbol),
            help_text="Total Activos menos Total Deudas/Pasivos"
        )
    with kpi2:
        render_kpi_card(
            title=f"Ingresos ({month_names[selected_month-1]})",
            value=format_currency(summary_50_30_20["total_income"], currency_symbol),
            delta="Flujo positivo" if summary_50_30_20["total_income"] > 0 else None,
            delta_color="normal"
        )
    with kpi3:
        render_kpi_card(
            title=f"Gastos ({month_names[selected_month-1]})",
            value=format_currency(summary_50_30_20["total_expenses"], currency_symbol),
            delta=f"Neto: {format_delta_currency(summary_50_30_20['net_cash_flow'], currency_symbol)}",
            delta_color="normal" if summary_50_30_20["net_cash_flow"] >= 0 else "inverse"
        )
    with kpi4:
        savings_rate = summary_50_30_20["savings"]["pct"]
        render_kpi_card(
            title="Tasa de Ahorro / Inversión",
            value=format_percentage(savings_rate),
            delta="Óptimo (>=20%)" if savings_rate >= 20.0 else "Bajo (<20%)",
            delta_color="normal" if savings_rate >= 20.0 else "inverse",
            help_text="Porcentaje de tus ingresos destinado a ahorro e inversión"
        )

    st.markdown("---")

    # 3. Gráficos de Flujo de Caja y Distribución
    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        st.subheader("💵 Flujo de Caja Mensual")
        # Generar histórico agregado por mes
        df_all_tx = get_transactions(limit=2000)
        if not df_all_tx.empty:
            df_all_tx['month'] = pd.to_datetime(df_all_tx['date']).dt.strftime('%Y-%m')
            df_monthly_inc = df_all_tx[df_all_tx['type'] == 'income'].groupby('month')['amount'].sum().reset_index().rename(columns={'amount': 'income'})
            df_monthly_exp = df_all_tx[df_all_tx['type'] == 'expense'].groupby('month')['amount'].sum().reset_index().rename(columns={'amount': 'expense'})
            df_monthly = pd.merge(df_monthly_inc, df_monthly_exp, on='month', how='outer').fillna(0.0).sort_values('month').tail(6)
            st.plotly_chart(plot_cashflow_bar(df_monthly, currency_symbol), use_container_width=True)
        else:
            st.info("No hay transacciones registradas aún.")

    with col_chart2:
        st.subheader("🍩 Gastos por Categoría")
        month_str = f"{selected_year:04d}-{selected_month:02d}"
        df_month_tx = df_all_tx[(df_all_tx['type'] == 'expense') & (df_all_tx['date'].str.startswith(month_str))] if not df_all_tx.empty else pd.DataFrame()
        if not df_month_tx.empty:
            df_cat_summary = df_month_tx.groupby('category_name')['amount'].sum().reset_index().sort_values('amount', ascending=False)
            st.plotly_chart(plot_expense_donut(df_cat_summary, currency_symbol), use_container_width=True)
        else:
            st.info(f"Sin gastos en {month_names[selected_month-1]} {selected_year}.")

    st.markdown("---")

    # 4. Evolución de Patrimonio y Alertas Rápidas
    col_nw, col_alerts = st.columns([3, 2])

    with col_nw:
        st.subheader("📈 Evolución de Patrimonio Neto")
        df_history = get_historical_snapshots()
        if not df_history.empty:
            st.plotly_chart(plot_net_worth_trend(df_history, currency_symbol), use_container_width=True)
        else:
            st.info("No hay histórico de patrimonio aún.")
        
        if st.button("📸 Registrar snapshot de patrimonio hoy", key="dash_snapshot_btn"):
            take_snapshot()
            st.success("¡Snapshot guardado correctamente!")
            st.rerun()

    with col_alerts:
        st.subheader("⚡ Diagnóstico y Alertas")
        
        # Alerta de fondo de emergencia
        if emergency_fund["months_covered"] >= 6.0:
            st.success(f"🛡️ **Fondo de Emergencia Sólido**: Tienes {emergency_fund['months_covered']:.1f} meses de cobertura ({format_currency(emergency_fund['liquid_savings'], currency_symbol)}).")
        elif emergency_fund["months_covered"] >= 3.0:
            st.warning(f"⚠️ **Fondo de Emergencia Aceptable**: {emergency_fund['months_covered']:.1f} meses cubiertos. Objetivo recomendado: 6 meses ({format_currency(emergency_fund['target_amount'], currency_symbol)}).")
        else:
            st.error(f"🚨 **Fondo de Emergencia Bajo**: Solo {emergency_fund['months_covered']:.1f} meses cubiertos. Te faltan {format_currency(emergency_fund['gap'], currency_symbol)}.")

        # Alerta de presupuestos excedidos en el mes
        df_budgets = get_budget_vs_actual(selected_year, selected_month)
        over_budgets = df_budgets[df_budgets['status'] == 'Excedido']
        if not over_budgets.empty:
            st.error(f"⚠️ Has superado el presupuesto en {len(over_budgets)} categoría(s): " + ", ".join(over_budgets['category_name'].tolist()))
        else:
            st.info("✅ Todos tus presupuestos del mes están dentro de los límites.")

        # Cuentas con mayores saldos
        df_accounts = get_accounts()
        if not df_accounts.empty:
            st.markdown("**Saldos Principales:**")
            for _, acc in df_accounts.head(4).iterrows():
                icon = "🟢" if acc['is_asset'] else "🔴"
                st.write(f"{icon} **{acc['name']}**: {format_currency(acc['balance'], currency_symbol)}")

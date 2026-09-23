import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from ...services.transaction_service import get_transactions, get_accounts
from ...services.budget_service import get_50_30_20_analysis, get_budget_vs_actual, get_emergency_fund_status
from ...utils.formatting import format_currency, format_percentage, format_delta_currency
from ..components import render_kpi_card, plot_cashflow_bar, plot_expense_donut

def render_dashboard_view(currency_symbol: str = "€"):
    """Renderiza el panel principal centrado en gastos, flujo de caja y presupuestos."""
    st.title("💸 Panel Central de Gastos y Flujo")
    st.caption("Control en tiempo real de tus gastos, ingresos, presupuestos y distribución mensual.")

    # 1. Filtro temporal (Selector de mes actual o previo)
    now = datetime.now()
    col_filter1, col_filter2 = st.columns([2, 1])
    with col_filter1:
        selected_year = st.selectbox("Año", [now.year, now.year - 1, now.year - 2], index=0, key="dash_year")
    with col_filter2:
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        selected_month = st.selectbox("Mes", range(1, 13), index=now.month - 1, format_func=lambda m: month_names[m-1], key="dash_month")

    # 2. Métricas Clave (KPIs enfocados en Gastos y Flujo de Caja)
    summary_50_30_20 = get_50_30_20_analysis(selected_year, selected_month)
    emergency_fund = get_emergency_fund_status(months_target=6)
    savings_rate = summary_50_30_20["savings"]["pct"]

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        render_kpi_card(
            title=f"Gastos ({month_names[selected_month-1]})",
            value=format_currency(summary_50_30_20["total_expenses"], currency_symbol),
            delta=f"{summary_50_30_20['needs']['pct'] + summary_50_30_20['wants']['pct']:.1f}% de tus ingresos",
            delta_color="inverse" if summary_50_30_20["total_expenses"] > summary_50_30_20["total_income"] and summary_50_30_20["total_income"] > 0 else "normal",
            help_text="Total de gastos registrados en este mes"
        )
    with kpi2:
        render_kpi_card(
            title=f"Ingresos ({month_names[selected_month-1]})",
            value=format_currency(summary_50_30_20["total_income"], currency_symbol),
            delta="Flujo positivo" if summary_50_30_20["total_income"] > 0 else "Sin ingresos",
            delta_color="normal"
        )
    with kpi3:
        render_kpi_card(
            title="Balance Neto / Margen Libre",
            value=format_delta_currency(summary_50_30_20["net_cash_flow"], currency_symbol),
            delta="Superávit mensual" if summary_50_30_20["net_cash_flow"] >= 0 else "Déficit mensual",
            delta_color="normal" if summary_50_30_20["net_cash_flow"] >= 0 else "inverse",
            help_text="Ingresos del mes menos Gastos del mes"
        )
    with kpi4:
        render_kpi_card(
            title="Tasa de Ahorro e Inversión",
            value=format_percentage(savings_rate),
            delta="Óptimo (>=20%)" if savings_rate >= 20.0 else "Bajo (<20%)",
            delta_color="normal" if savings_rate >= 20.0 else "inverse",
            help_text="Porcentaje de tus ingresos destinado a ahorro e inversión"
        )

    st.markdown("---")

    # 3. Gráficos de Flujo de Caja y Distribución de Gastos
    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        st.subheader("💵 Evolución de Ingresos, Gastos e Inversiones")
        # Generar histórico agregado por mes
        df_all_tx = get_transactions(limit=2000)
        if not df_all_tx.empty:
            df_all_tx['month'] = pd.to_datetime(df_all_tx['date']).dt.strftime('%Y-%m')
            all_months = sorted(df_all_tx['month'].unique())
            df_monthly = pd.DataFrame({'month': all_months})

            # Ingresos
            df_inc = df_all_tx[df_all_tx['type'] == 'income'].groupby('month')['amount'].sum().reset_index().rename(columns={'amount': 'income'})
            # Gastos (excluye ahorro e inversiones: bucket_50_30_20 != 'savings')
            df_exp = df_all_tx[(df_all_tx['type'] == 'expense') & (df_all_tx['bucket_50_30_20'] != 'savings')].groupby('month')['amount'].sum().reset_index().rename(columns={'amount': 'expense'})
            # Inversiones y Ahorro (bucket_50_30_20 == 'savings')
            df_inv = df_all_tx[(df_all_tx['type'] == 'expense') & (df_all_tx['bucket_50_30_20'] == 'savings')].groupby('month')['amount'].sum().reset_index().rename(columns={'amount': 'investment'})

            df_monthly = df_monthly.merge(df_inc, on='month', how='left')
            df_monthly = df_monthly.merge(df_exp, on='month', how='left')
            df_monthly = df_monthly.merge(df_inv, on='month', how='left')
            df_monthly = df_monthly.fillna(0.0).sort_values('month').tail(6)
            st.plotly_chart(plot_cashflow_bar(df_monthly, currency_symbol), use_container_width=True)
        else:
            st.info("No hay transacciones registradas aún.")

    with col_chart2:
        st.subheader("🍩 Distribución de Gastos por Categoría")
        month_str = f"{selected_year:04d}-{selected_month:02d}"
        df_month_tx = df_all_tx[(df_all_tx['type'] == 'expense') & (df_all_tx['date'].str.startswith(month_str))] if not df_all_tx.empty else pd.DataFrame()
        if not df_month_tx.empty:
            df_cat_summary = df_month_tx.groupby('category_name')['amount'].sum().reset_index().sort_values('amount', ascending=False)
            st.plotly_chart(plot_expense_donut(df_cat_summary, currency_symbol), use_container_width=True)
        else:
            st.info(f"Sin gastos registrados en {month_names[selected_month-1]} {selected_year}.")

    st.markdown("---")

    # 4. Detalle de Presupuestos y Diagnóstico de Gastos
    col_budgets, col_alerts = st.columns([3, 2])

    with col_budgets:
        st.subheader("🎯 Estado de Presupuestos del Mes")
        df_budgets = get_budget_vs_actual(selected_year, selected_month)
        if not df_budgets.empty:
            df_b_show = df_budgets.copy()
            df_b_show['cat_display'] = df_b_show['category_icon'].fillna('') + ' ' + df_b_show['category_name']
            df_b_show['spent_fmt'] = df_b_show['actual_spent'].apply(lambda x: format_currency(x, currency_symbol))
            df_b_show['budget_fmt'] = df_b_show['budget_limit'].apply(lambda x: format_currency(x, currency_symbol))
            df_b_show['pct_fmt'] = df_b_show['pct_used'].apply(lambda x: f"{x:.1f}%")

            cols_view = ['cat_display', 'spent_fmt', 'budget_fmt', 'pct_fmt', 'status']
            renamed = {
                'cat_display': 'Categoría',
                'spent_fmt': 'Gastado',
                'budget_fmt': 'Presupuesto',
                'pct_fmt': '% Usado',
                'status': 'Estado'
            }
            st.dataframe(df_b_show[cols_view].rename(columns=renamed), use_container_width=True, hide_index=True)
        else:
            st.info("No hay presupuestos asignados aún para este mes.")

    with col_alerts:
        st.subheader("⚡ Diagnóstico y Hábitos de Gasto")
        
        # Alerta de presupuestos excedidos en el mes
        if not df_budgets.empty:
            over_budgets = df_budgets[df_budgets['status'] == 'Excedido']
            if not over_budgets.empty:
                st.error(f"🚨 **Presupuesto Excedido** en {len(over_budgets)} categoría(s): " + ", ".join(over_budgets['category_name'].tolist()))
            else:
                st.success("✅ **Presupuestos bajo control**: Todos tus gastos del mes se mantienen dentro del límite.")

        # Cálculo de gasto medio diario
        _, total_days_in_month = calendar.monthrange(selected_year, selected_month)
        is_current_month = (selected_year == now.year and selected_month == now.month)
        days_passed = now.day if is_current_month else total_days_in_month
        total_exp = summary_50_30_20["total_expenses"]
        daily_expense = (total_exp / max(1, days_passed)) if total_exp > 0 else 0.0

        st.info(f"📆 **Gasto medio diario este mes:** {format_currency(daily_expense, currency_symbol)}/día (calculado sobre {days_passed} días).")

        # Alerta de fondo de emergencia para imprevistos
        if emergency_fund["months_covered"] >= 6.0:
            st.success(f"🛡️ **Colchón de Seguridad Sólido**: Tienes {emergency_fund['months_covered']:.1f} meses de tus gastos cubiertos ante cualquier imprevisto.")
        elif emergency_fund["months_covered"] >= 3.0:
            st.warning(f"⚠️ **Colchón Aceptable**: Tienes {emergency_fund['months_covered']:.1f} meses de cobertura para gastos.")
        else:
            st.error(f"🚨 **Colchón Bajo**: Solo {emergency_fund['months_covered']:.1f} meses de cobertura. Recomendado: 6 meses de gastos.")


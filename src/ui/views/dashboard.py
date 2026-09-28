import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from ...services.transaction_service import get_transactions
from ...services.budget_service import get_emergency_fund_status
from ...utils.formatting import format_currency, format_percentage, format_delta_currency
from ..components import render_kpi_card, plot_cashflow_bar, plot_expense_donut

def render_dashboard_view(currency_symbol: str = "€"):
    """Renderiza el panel principal centrado en gastos, inversiones y flujo de caja."""
    st.title("💸 Panel Central de Gastos y Flujo")
    st.caption("Control en tiempo real de tus gastos, inversiones, ingresos y distribución mensual.")

    # 1. Filtro temporal (Selector de año y mes)
    now = datetime.now()
    col_filter1, col_filter2 = st.columns([2, 1])
    with col_filter1:
        selected_year = st.selectbox("Año", [now.year, now.year - 1, now.year - 2], index=0, key="dash_year")
    with col_filter2:
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        selected_month = st.selectbox("Mes", range(1, 13), index=now.month - 1, format_func=lambda m: month_names[m-1], key="dash_month")

    # 2. Carga y cálculo de métricas financieras del mes seleccionado
    df_all_tx = get_transactions(limit=2000)
    month_str = f"{selected_year:04d}-{selected_month:02d}"
    df_month_tx = df_all_tx[df_all_tx['date'].str.startswith(month_str)] if not df_all_tx.empty else pd.DataFrame()

    if not df_month_tx.empty:
        total_income = df_month_tx[df_month_tx['type'] == 'income']['amount'].sum()
        # Gastos puros de consumo (excluye ahorro e inversiones: bucket_50_30_20 != 'savings')
        df_pure_exp_month = df_month_tx[(df_month_tx['type'] == 'expense') & (df_month_tx['bucket_50_30_20'] != 'savings')]
        total_pure_expenses = df_pure_exp_month['amount'].sum()
        # Inversiones y Ahorro (bucket_50_30_20 == 'savings')
        df_inv_month = df_month_tx[(df_month_tx['type'] == 'expense') & (df_month_tx['bucket_50_30_20'] == 'savings')]
        total_investments = df_inv_month['amount'].sum()
    else:
        total_income = 0.0
        df_pure_exp_month = pd.DataFrame()
        total_pure_expenses = 0.0
        df_inv_month = pd.DataFrame()
        total_investments = 0.0

    # Margen Libre = Ingresos - Gastos puros - Inversiones
    free_margin = total_income - total_pure_expenses - total_investments
    # Tasa de Ahorro e Inversión = (Inversiones / Ingresos) * 100
    savings_rate = (total_investments / total_income * 100) if total_income > 0 else 0.0

    # 3. Métricas Clave (5 KPIs solicitados: Gastos, Inversiones, Margen Libre, Tasa de Ahorro e Inversión, Ingresos)
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        exp_pct = (total_pure_expenses / total_income * 100) if total_income > 0 else 0.0
        render_kpi_card(
            title=f"Gastos ({month_names[selected_month-1]})",
            value=format_currency(total_pure_expenses, currency_symbol),
            delta=f"{exp_pct:.1f}% de tus ingresos" if total_income > 0 else "Sin ingresos",
            delta_color="inverse" if total_pure_expenses > total_income and total_income > 0 else "normal",
            help_text="Total de gastos reales (consumo y necesidades), sin incluir inversiones"
        )
    with kpi2:
        inv_pct = (total_investments / total_income * 100) if total_income > 0 else 0.0
        render_kpi_card(
            title=f"Inversiones ({month_names[selected_month-1]})",
            value=format_currency(total_investments, currency_symbol),
            delta=f"{inv_pct:.1f}% de tus ingresos" if total_income > 0 else "Aportado al patrimonio",
            delta_color="normal",
            help_text="Capital destinado a inversión, fondos y ahorro durante el mes"
        )
    with kpi3:
        render_kpi_card(
            title="Margen Libre",
            value=format_delta_currency(free_margin, currency_symbol),
            delta="Superávit mensual" if free_margin >= 0 else "Déficit mensual",
            delta_color="normal" if free_margin >= 0 else "inverse",
            help_text="Ingresos del mes menos Gastos puros menos Inversiones"
        )
    with kpi4:
        render_kpi_card(
            title="Tasa de Ahorro e Inversión",
            value=format_percentage(savings_rate),
            delta="Óptimo (>=20%)" if savings_rate >= 20.0 else "Bajo (<20%)",
            delta_color="normal" if savings_rate >= 20.0 else "inverse",
            help_text="Porcentaje de tus ingresos destinado a ahorro e inversión"
        )
    with kpi5:
        render_kpi_card(
            title=f"Ingresos ({month_names[selected_month-1]})",
            value=format_currency(total_income, currency_symbol),
            delta="Flujo positivo" if total_income > 0 else "Sin ingresos",
            delta_color="normal",
            help_text="Total de ingresos percibidos en este mes"
        )

    st.markdown("---")

    # 4. Gráficos de Flujo de Caja y Distribución de Gastos
    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        st.subheader("💵 Evolución de Ingresos, Gastos e Inversiones")
        if not df_all_tx.empty:
            df_all_tx['month'] = pd.to_datetime(df_all_tx['date']).dt.strftime('%Y-%m')
            all_months = sorted(df_all_tx['month'].unique())
            df_monthly = pd.DataFrame({'month': all_months})

            # Ingresos
            df_inc = df_all_tx[df_all_tx['type'] == 'income'].groupby('month')['amount'].sum().reset_index().rename(columns={'amount': 'income'})
            # Gastos puros (excluye ahorro e inversiones)
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
        if not df_pure_exp_month.empty:
            df_cat_summary = df_pure_exp_month.groupby('category_name')['amount'].sum().reset_index().sort_values('amount', ascending=False)
            st.plotly_chart(plot_expense_donut(df_cat_summary, currency_symbol), use_container_width=True)
        else:
            st.info(f"Sin gastos registrados en {month_names[selected_month-1]} {selected_year}.")

    st.markdown("---")

    # 5. Tabla de Gastos por Categoría del Mes (Ordenada de Mayor a Menor) y Diagnóstico
    col_table, col_diag = st.columns([3, 2])

    with col_table:
        st.subheader(f"📑 Gastos de {month_names[selected_month-1]} por Categoría")
        if not df_pure_exp_month.empty:
            df_cat_table = df_pure_exp_month.groupby(['category_icon', 'category_name']).agg(
                total_spent=('amount', 'sum'),
                tx_count=('id', 'count')
            ).reset_index().sort_values('total_spent', ascending=False)

            total_cat_spent = df_cat_table['total_spent'].sum()

            df_cat_table['Categoría'] = df_cat_table['category_icon'].fillna('📌') + ' ' + df_cat_table['category_name']
            df_cat_table['Total Gastado'] = df_cat_table['total_spent'].apply(lambda x: format_currency(x, currency_symbol))
            df_cat_table['% del Total'] = df_cat_table['total_spent'].apply(
                lambda x: f"{(x / total_cat_spent * 100):.1f}%" if total_cat_spent > 0 else "0.0%"
            )
            df_cat_table['Nº Movimientos'] = df_cat_table['tx_count'].astype(int)

            cols_to_show = ['Categoría', 'Total Gastado', '% del Total', 'Nº Movimientos']
            st.dataframe(df_cat_table[cols_to_show], use_container_width=True, hide_index=True)
        else:
            st.info(f"No hay gastos registrados en {month_names[selected_month-1]} {selected_year}.")

    with col_diag:
        st.subheader("⚡ Métricas y Hábitos del Mes")

        # Cálculo de gasto medio diario
        _, total_days_in_month = calendar.monthrange(selected_year, selected_month)
        is_current_month = (selected_year == now.year and selected_month == now.month)
        days_passed = now.day if is_current_month else total_days_in_month
        daily_expense = (total_pure_expenses / max(1, days_passed)) if total_pure_expenses > 0 else 0.0

        st.info(f"📆 **Gasto medio diario este mes:** {format_currency(daily_expense, currency_symbol)}/día (calculado sobre {days_passed} días).")

        # Categoría principal de gasto
        if not df_pure_exp_month.empty:
            top_cat_row = df_pure_exp_month.groupby(['category_icon', 'category_name'])['amount'].sum().reset_index().sort_values('amount', ascending=False).iloc[0]
            top_cat_icon = top_cat_row['category_icon'] or '📌'
            top_cat_name = top_cat_row['category_name']
            top_cat_amount = top_cat_row['amount']
            top_cat_pct = (top_cat_amount / total_pure_expenses * 100) if total_pure_expenses > 0 else 0.0
            st.markdown(f"🏆 **Mayor partida de gasto:** {top_cat_icon} **{top_cat_name}** con {format_currency(top_cat_amount, currency_symbol)} ({top_cat_pct:.1f}% del total).")

        # Colchón de seguridad / Fondo de emergencia
        emergency_fund = get_emergency_fund_status(months_target=6)
        if emergency_fund["months_covered"] >= 6.0:
            st.success(f"🛡️ **Colchón de Seguridad Sólido**: Tienes {emergency_fund['months_covered']:.1f} meses de cobertura ante imprevistos.")
        elif emergency_fund["months_covered"] >= 3.0:
            st.warning(f"⚠️ **Colchón Aceptable**: Tienes {emergency_fund['months_covered']:.1f} meses de cobertura para gastos.")
        else:
            st.error(f"🚨 **Colchón Bajo**: Solo {emergency_fund['months_covered']:.1f} meses de cobertura. Recomendado: 6 meses de gastos.")

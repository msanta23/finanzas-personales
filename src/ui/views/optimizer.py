import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from ...services.optimizer_service import (
    simulate_compound_interest, calculate_fire_projection,
    compare_debt_payoff_strategies, diagnose_financial_health
)
from ...services.portfolio_service import get_net_worth_summary, get_liabilities
from ...utils.formatting import format_currency, format_percentage

def render_optimizer_view(currency_symbol: str = "€"):
    """Vista de optimización financiera, simuladores de interés compuesto, FIRE, deudas y diagnóstico."""
    st.title("🚀 Motor de Optimización Financiera")
    st.caption("Herramientas matemáticas y simuladores para acelerar tu independencia financiera y optimizar cada euro.")

    tab_fire, tab_compound, tab_debts, tab_diag = st.tabs([
        "🔥 Calculadora FIRE (Jubilación Anticipada)",
        "📈 Interés Compuesto",
        "⚡ Estrategias de Deuda (Avalancha vs Bola de Nieve)",
        "🩺 Diagnóstico de Salud Financiera"
    ])

    # ----------------------------------------------------
    # TAB 1: CALCULADORA FIRE
    # ----------------------------------------------------
    with tab_fire:
        st.subheader("Simulador de Independencia Financiera (FIRE)")
        st.write("Calcula cuándo alcanzarás la libertad financiera según tu tasa de ahorro y rentabilidad esperada.")

        nw = get_net_worth_summary()

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            age_input = st.number_input("Edad actual", min_value=18, max_value=85, value=30, step=1)
            invested_input = st.number_input(
                "Patrimonio invertido actual",
                min_value=0.0,
                value=float(nw.get("total_assets", 25000.0)),
                step=1000.0,
                format="%.2f"
            )
            monthly_exp_input = st.number_input("Gastos mensuales estimados", min_value=100.0, value=1500.0, step=50.0, format="%.2f")
        with col_f2:
            monthly_sav_input = st.number_input("Ahorro / Inversión mensual", min_value=0.0, value=700.0, step=50.0, format="%.2f")
            return_pct_input = st.slider("Rentabilidad anual esperada (%)", min_value=1.0, max_value=15.0, value=7.0, step=0.5, help="Histórico MSCI World aprox. 7-8% anualizado antes de inflación.")
            swr_input = st.slider("Tasa de Retirada Segura (SWR %)", min_value=2.5, max_value=5.0, value=4.0, step=0.1, help="Regla del 4% estándar (Estudio Trinity).")

        fire_res = calculate_fire_projection(
            current_invested_assets=invested_input,
            monthly_savings=monthly_sav_input,
            monthly_expenses=monthly_exp_input,
            expected_annual_return_pct=return_pct_input,
            safe_withdrawal_rate_pct=swr_input,
            current_age=age_input
        )

        st.markdown("---")
        kpi_f1, kpi_f2, kpi_f3, kpi_f4 = st.columns(4)
        with kpi_f1:
            st.metric("Objetivo FIRE Estándar", format_currency(fire_res["fire_target_standard"], currency_symbol))
        with kpi_f2:
            st.metric("Años hasta FIRE", f"{fire_res['years_to_fire']} años")
        with kpi_f3:
            st.metric("Edad de Retiro Estimada", f"{fire_res['fire_age']} años" if fire_res['fire_age'] != 'N/A' else 'N/A')
        with kpi_f4:
            st.metric("Progreso Actual", f"{fire_res['current_fire_progress']}%")

        # Gráfico de trayectoria FIRE
        traj_df = fire_res["trajectory_df"]
        if not traj_df.empty:
            fig_fire = go.Figure()
            fig_fire.add_trace(go.Scatter(
                x=traj_df['age'],
                y=traj_df['balance'],
                name='Evolución Patrimonio Invertido',
                line=dict(color='#10B981', width=3),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.1)'
            ))
            fig_fire.add_trace(go.Scatter(
                x=traj_df['age'],
                y=traj_df['fire_target'],
                name='Objetivo FIRE Estándar (100% gastos)',
                line=dict(color='#EF4444', width=2, dash='dash')
            ))
            fig_fire.add_trace(go.Scatter(
                x=traj_df['age'],
                y=traj_df['lean_target'],
                name='Lean FIRE (80% gastos)',
                line=dict(color='#F59E0B', width=1.5, dash='dot')
            ))
            fig_fire.add_trace(go.Scatter(
                x=traj_df['age'],
                y=traj_df['fat_target'],
                name='Fat FIRE (130% gastos)',
                line=dict(color='#8B5CF6', width=1.5, dash='dot')
            ))

            fig_fire.update_layout(
                title="Curva de Acumulación Patrimonial y Cruce FIRE",
                xaxis_title="Edad (Años)",
                yaxis_title=f"Capital ({currency_symbol})",
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_fire, use_container_width=True)

    # ----------------------------------------------------
    # TAB 2: INTERÉS COMPUESTO
    # ----------------------------------------------------
    with tab_compound:
        st.subheader("Calculadora de Crecimiento por Interés Compuesto")
        st.write("Visualiza la fuerza exponencial del interés compuesto a lo largo del tiempo.")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            init_cap = st.number_input("Capital Inicial", min_value=0.0, value=5000.0, step=500.0, format="%.2f", key="ci_init")
            monthly_contrib = st.number_input("Aportación Mensual", min_value=0.0, value=300.0, step=50.0, format="%.2f", key="ci_contrib")
            years_horizon = st.slider("Horizonte de Inversión (Años)", min_value=1, max_value=50, value=25, step=1, key="ci_years")
        with col_c2:
            rate_ci = st.slider("Rentabilidad Anual Nominal (%)", min_value=0.0, max_value=20.0, value=8.0, step=0.5, key="ci_rate")
            inflation_rate = st.slider("Inflación Anual Estimada (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.5, key="ci_inf")

        df_ci = simulate_compound_interest(
            initial_principal=init_cap,
            monthly_contribution=monthly_contrib,
            annual_interest_rate_pct=rate_ci,
            years=years_horizon,
            annual_inflation_pct=inflation_rate
        )

        final_row = df_ci.iloc[-1]
        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        with kpi_c1:
            st.metric("Total Aportado", format_currency(final_row["total_contributed"], currency_symbol))
        with kpi_c2:
            st.metric("Intereses Generados", format_currency(final_row["interest_earned"], currency_symbol), delta=f"{format_currency(final_row['interest_earned'], currency_symbol)} extra")
        with kpi_c3:
            st.metric("Patrimonio Nominal Final", format_currency(final_row["nominal_balance"], currency_symbol))
        with kpi_c4:
            st.metric("Poder Adquisitivo Real", format_currency(final_row["real_balance"], currency_symbol), help="Descontando el efecto acumulado de la inflación.")

        # Gráfico apilado de Aportaciones vs Intereses
        fig_ci = go.Figure()
        fig_ci.add_trace(go.Bar(
            x=df_ci['year'],
            y=df_ci['total_contributed'],
            name='Capital Aportado',
            marker_color='#3B82F6'
        ))
        fig_ci.add_trace(go.Bar(
            x=df_ci['year'],
            y=df_ci['interest_earned'],
            name='Intereses Generados (Plusvalías)',
            marker_color='#10B981'
        ))
        fig_ci.add_trace(go.Scatter(
            x=df_ci['year'],
            y=df_ci['real_balance'],
            name='Valor Real (Ajustado por Inflación)',
            mode='lines+markers',
            line=dict(color='#F59E0B', width=2)
        ))

        fig_ci.update_layout(
            barmode='stack',
            title=f"Proyección a {years_horizon} Años",
            xaxis_title="Años",
            yaxis_title=f"Total ({currency_symbol})",
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_ci, use_container_width=True)

    # ----------------------------------------------------
    # TAB 3: OPTIMIZADOR DE DEUDAS
    # ----------------------------------------------------
    with tab_debts:
        st.subheader("Comparador de Estrategias de Liquidación de Deudas")
        st.write("Descubre cuánto dinero y tiempo ahorras usando el método **Avalancha** (mayor interés) o **Bola de Nieve** (menor saldo).")

        df_db_debts = get_liabilities()
        debts_list = []
        if not df_db_debts.empty:
            for _, r in df_db_debts.iterrows():
                debts_list.append({
                    "name": r['name'],
                    "balance": float(r['balance']),
                    "interest_rate": float(r['interest_rate']),
                    "min_payment": max(25.0, float(r['balance']) * 0.03)
                })

        extra_payment = st.slider("Pago extra mensual destinado a liquidar deuda", min_value=0.0, max_value=1000.0, value=150.0, step=25.0)

        if debts_list:
            res_debts = compare_debt_payoff_strategies(debts_list, extra_monthly_payment=extra_payment)
            
            st.markdown("### Resumen Comparativo")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                st.markdown("#### 🏔️ Método Avalancha (Matemáticamente Óptimo)")
                st.write(f"**Tiempo hasta estar libre de deuda:** {res_debts['avalanche']['months']} meses ({res_debts['avalanche']['years']} años)")
                st.write(f"**Intereses totales pagados:** {format_currency(res_debts['avalanche']['total_interest_paid'], currency_symbol)}")
                st.success(f"💰 **Ahorro en intereses vs pagos mínimos:** {format_currency(res_debts['interest_saved_avalanche'], currency_symbol)}")

            with col_d2:
                st.markdown("#### ⛄ Método Bola de Nieve (Psicológico)")
                st.write(f"**Tiempo hasta estar libre de deuda:** {res_debts['snowball']['months']} meses ({res_debts['snowball']['years']} años)")
                st.write(f"**Intereses totales pagados:** {format_currency(res_debts['snowball']['total_interest_paid'], currency_symbol)}")
                st.info("Prioriza cerrar deudas pequeñas rápido para ganar motivación.")

            with col_d3:
                st.markdown("#### 🐌 Solo Pagos Mínimos")
                st.write(f"**Tiempo:** {res_debts['minimums_only']['months']} meses ({res_debts['minimums_only']['years']} años)")
                st.write(f"**Intereses totales:** {format_currency(res_debts['minimums_only']['total_interest_paid'], currency_symbol)}")
                st.error(f"⚠️ Tardarás {res_debts['months_saved_avalanche']} meses más si no amortizas de forma acelerada.")

        else:
            st.success("🎉 No tienes deudas registradas en la base de datos.")

    # ----------------------------------------------------
    # TAB 4: DIAGNÓSTICO DE SALUD FINANCIERA
    # ----------------------------------------------------
    with tab_diag:
        st.subheader("Diagnóstico Integral de Salud Financiera y Fugas de Ahorro")
        diagnostic = diagnose_financial_health()

        col_diag1, col_diag2, col_diag3 = st.columns(3)
        with col_diag1:
            st.metric("Tasa de Ahorro Global", format_percentage(diagnostic["savings_rate_pct"]), delta=diagnostic["savings_grade"])
        with col_diag2:
            st.metric("Cobertura Fondo de Emergencia", f"{diagnostic['emergency_months']:.1f} meses", delta=diagnostic["emergency_grade"])
        with col_diag3:
            st.metric("Ratio Deuda / Patrimonio", format_percentage(diagnostic["debt_ratio_pct"]), delta="Bajo y controlado" if diagnostic["debt_ratio_pct"] < 30.0 else "Elevado", delta_color="normal" if diagnostic["debt_ratio_pct"] < 30.0 else "inverse")

        st.markdown("---")
        st.subheader("📋 Recomendaciones y Plan de Acción Priorizado")

        for rec in diagnostic["recommendations"]:
            badge_color = "red" if rec["priority"] == "Urgente" else ("orange" if rec["priority"] == "Alta" else "blue")
            with st.container():
                st.markdown(f"**[{rec['priority'].upper()}] {rec['title']}**")
                st.write(rec["description"])
                st.caption(f"💡 **Impacto esperado:** {rec['impact']}")
                st.markdown("<hr style='margin: 8px 0;'/>", unsafe_allow_html=True)

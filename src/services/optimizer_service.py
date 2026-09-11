import math
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from ..database.connection import DB_PATH
from .portfolio_service import get_net_worth_summary, get_liabilities
from .budget_service import get_emergency_fund_status, get_50_30_20_analysis

def simulate_compound_interest(
    initial_principal: float,
    monthly_contribution: float,
    annual_interest_rate_pct: float,
    years: int,
    annual_inflation_pct: float = 2.0
) -> pd.DataFrame:
    """
    Calcula la proyección año a año del interés compuesto con aportaciones mensuales e impacto de inflación.
    """
    monthly_rate = (annual_interest_rate_pct / 100.0) / 12.0
    monthly_inflation = (annual_inflation_pct / 100.0) / 12.0
    total_months = years * 12

    records = []
    current_nominal = initial_principal
    total_contributed = initial_principal

    # Añadir año 0
    records.append({
        "year": 0,
        "total_contributed": round(total_contributed, 2),
        "interest_earned": 0.0,
        "nominal_balance": round(current_nominal, 2),
        "real_balance": round(current_nominal, 2)
    })

    for month in range(1, total_months + 1):
        # Interés generado en el mes
        current_nominal = current_nominal * (1.0 + monthly_rate) + monthly_contribution
        total_contributed += monthly_contribution

        if month % 12 == 0:
            year_num = month // 12
            # Ajuste de poder adquisitivo por inflación acumulada
            inflation_factor = (1.0 + annual_inflation_pct / 100.0) ** year_num
            real_balance = current_nominal / inflation_factor
            interest_earned = current_nominal - total_contributed

            records.append({
                "year": year_num,
                "total_contributed": round(total_contributed, 2),
                "interest_earned": round(max(0.0, interest_earned), 2),
                "nominal_balance": round(current_nominal, 2),
                "real_balance": round(real_balance, 2)
            })

    return pd.DataFrame(records)

def calculate_fire_projection(
    current_invested_assets: float,
    monthly_savings: float,
    monthly_expenses: float,
    expected_annual_return_pct: float = 7.0,
    safe_withdrawal_rate_pct: float = 4.0,
    current_age: int = 30
) -> Dict[str, Any]:
    """
    Calcula la proyección FIRE (Financial Independence, Retire Early):
    - Número FIRE según SWR (Safe Withdrawal Rate, ej. Regla del 4%).
    - Lean FIRE (80%), Standard FIRE (100%), Fat FIRE (130%).
    - Años restantes hasta alcanzar la libertad financiera.
    """
    annual_expenses = monthly_expenses * 12.0
    swr_decimal = safe_withdrawal_rate_pct / 100.0
    
    # Número objetivo FIRE
    fire_target_standard = annual_expenses / swr_decimal if swr_decimal > 0 else 0.0
    fire_target_lean = (annual_expenses * 0.8) / swr_decimal if swr_decimal > 0 else 0.0
    fire_target_fat = (annual_expenses * 1.3) / swr_decimal if swr_decimal > 0 else 0.0

    monthly_rate = (expected_annual_return_pct / 100.0) / 12.0

    # Simular mes a mes hasta alcanzar el objetivo standard o 60 años max
    max_months = 60 * 12
    months_to_fire = None
    balance = current_invested_assets
    trajectory = []

    for m in range(max_months + 1):
        if m % 12 == 0:
            trajectory.append({
                "year": m // 12,
                "age": current_age + (m // 12),
                "balance": round(balance, 2),
                "fire_target": round(fire_target_standard, 2),
                "lean_target": round(fire_target_lean, 2),
                "fat_target": round(fire_target_fat, 2)
            })

        if balance >= fire_target_standard and months_to_fire is None:
            months_to_fire = m

        balance = balance * (1.0 + monthly_rate) + monthly_savings

    years_to_fire = (months_to_fire / 12.0) if months_to_fire is not None else 60.0
    fire_age = current_age + years_to_fire if months_to_fire is not None else None

    # Tasa de ahorro aproximada
    monthly_income = monthly_expenses + monthly_savings
    savings_rate_pct = (monthly_savings / monthly_income * 100.0) if monthly_income > 0 else 0.0

    # Cobertura actual
    current_fire_progress = (current_invested_assets / fire_target_standard * 100.0) if fire_target_standard > 0 else 0.0

    return {
        "fire_target_standard": round(fire_target_standard, 2),
        "fire_target_lean": round(fire_target_lean, 2),
        "fire_target_fat": round(fire_target_fat, 2),
        "current_invested_assets": current_invested_assets,
        "current_fire_progress": round(min(100.0, current_fire_progress), 1),
        "years_to_fire": round(years_to_fire, 1) if months_to_fire is not None else "> 50",
        "fire_age": round(fire_age, 1) if fire_age else "N/A",
        "savings_rate_pct": round(savings_rate_pct, 1),
        "monthly_expenses": monthly_expenses,
        "monthly_savings": monthly_savings,
        "trajectory_df": pd.DataFrame(trajectory)
    }

def compare_debt_payoff_strategies(
    debts: List[Dict[str, Any]],
    extra_monthly_payment: float = 100.0
) -> Dict[str, Any]:
    """
    Compara las dos estrategias principales de aceleración de pago de deuda:
    1. Avalancha (Avalanche): Prioriza la deuda con mayor tasa de interés (ahorra el máximo en intereses).
    2. Bola de nieve (Snowball): Prioriza la deuda con menor saldo pendiente (victorias psicológicas rápidas).
    
    Cada deuda en `debts` debe tener: {'name': str, 'balance': float, 'interest_rate': float, 'min_payment': float}
    """
    if not debts:
        return {"empty": True}

    def simulate_strategy(sort_key, reverse=False):
        # Clonar datos de deudas
        active_debts = [
            {
                "name": d["name"],
                "balance": float(d["balance"]),
                "rate": float(d.get("interest_rate", 0.0)) / 100.0 / 12.0,
                "min_payment": float(d.get("min_payment", max(20.0, d["balance"] * 0.02)))
            }
            for d in debts if d["balance"] > 0
        ]

        total_interest_paid = 0.0
        months = 0
        max_months = 360 # 30 años max
        payoff_history = []

        while active_debts and months < max_months:
            months += 1
            available_extra = extra_monthly_payment
            
            # 1. Aplicar intereses del mes a todas las deudas
            for d in active_debts:
                interest = d["balance"] * d["rate"]
                d["balance"] += interest
                total_interest_paid += interest

            # 2. Pagar el mínimo obligatorio en cada una
            for d in active_debts:
                pay = min(d["balance"], d["min_payment"])
                d["balance"] -= pay

            # 3. Ordenar según la estrategia para asignar el capital extra liberado
            active_debts.sort(key=sort_key, reverse=reverse)

            # 4. Asignar capital extra + mínimos de deudas liquidadas
            for d in active_debts:
                if d["balance"] > 0 and available_extra > 0:
                    pay_extra = min(d["balance"], available_extra)
                    d["balance"] -= pay_extra
                    available_extra -= pay_extra

            # 5. Filtrar deudas pagadas
            active_debts = [d for d in active_debts if d["balance"] > 0.01]

            # Registro de snapshot
            total_remaining = sum(d["balance"] for d in active_debts)
            payoff_history.append({"month": months, "remaining_balance": total_remaining})

        return {
            "months": months,
            "years": round(months / 12.0, 1),
            "total_interest_paid": round(total_interest_paid, 2),
            "history": payoff_history
        }

    # Avalancha: Mayor tasa de interés primero
    avalanche_res = simulate_strategy(lambda d: d["rate"], reverse=True)
    # Bola de nieve: Menor saldo primero
    snowball_res = simulate_strategy(lambda d: d["balance"], reverse=False)
    # Solo pagos mínimos (sin extra)
    baseline_extra = 0.0
    original_extra = extra_monthly_payment
    extra_monthly_payment = 0.0
    min_payments_res = simulate_strategy(lambda d: d["rate"], reverse=True)

    interest_saved_avalanche = max(0.0, min_payments_res["total_interest_paid"] - avalanche_res["total_interest_paid"])
    months_saved_avalanche = max(0, min_payments_res["months"] - avalanche_res["months"])

    return {
        "avalanche": avalanche_res,
        "snowball": snowball_res,
        "minimums_only": min_payments_res,
        "interest_saved_avalanche": round(interest_saved_avalanche, 2),
        "months_saved_avalanche": months_saved_avalanche,
        "debts_count": len(debts)
    }

def diagnose_financial_health(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Analiza la situación financiera global del usuario y emite un diagnóstico con recomendaciones de optimización.
    """
    now = datetime.now()
    analysis_50_30_20 = get_50_30_20_analysis(now.year, now.month, db_path)
    emergency_status = get_emergency_fund_status(months_target=6, db_path=db_path)
    net_worth = get_net_worth_summary(db_path)
    liabilities = get_liabilities(db_path)

    # 1. Calificación de la Tasa de Ahorro
    savings_pct = analysis_50_30_20["savings"]["pct"]
    if savings_pct >= 40.0:
        savings_grade = "A+ (Excelente)"
        savings_badge = "success"
    elif savings_pct >= 20.0:
        savings_grade = "A (Óptima)"
        savings_badge = "success"
    elif savings_pct >= 10.0:
        savings_grade = "B (Mejorable)"
        savings_badge = "warning"
    else:
        savings_grade = "C (Riesgo / Baja)"
        savings_badge = "danger"

    # 2. Calificación del Fondo de Emergencia
    months_cov = emergency_status["months_covered"]
    if months_cov >= 6.0:
        ef_grade = "Totalmente Protegido (>= 6 meses)"
        ef_badge = "success"
    elif months_cov >= 3.0:
        ef_grade = "Fondo Básico (3 a 6 meses)"
        ef_badge = "warning"
    else:
        ef_grade = "Fondo Insuficiente (< 3 meses)"
        ef_badge = "danger"

    # 3. Ratio de Deuda
    total_assets = net_worth["total_assets"]
    total_debt = net_worth["total_liabilities"]
    debt_ratio = (total_debt / total_assets * 100.0) if total_assets > 0 else 0.0

    # 4. Generación de recomendaciones y planes de acción priorizados
    recommendations = []

    if months_cov < 3.0:
        recommendations.append({
            "priority": "Alta",
            "title": "Consolidar Fondo de Emergencia",
            "description": f"Tu cobertura actual es de {months_cov:.1f} meses. Prioriza alcanzar al menos 3 a 6 meses de gastos fijos ({emergency_status['target_amount']:,.2f} €) en cuentas remuneradas o de alta liquidez antes de invertir en activos de mayor volatilidad.",
            "impact": "Tranquilidad financiera y prevención de deuda imprevista."
        })

    # Revisar deudas con alto interés (>8%)
    high_interest_debts = liabilities[liabilities["interest_rate"] > 8.0] if not liabilities.empty else pd.DataFrame()
    if not high_interest_debts.empty:
        total_high_interest = high_interest_debts["balance"].sum()
        names = ", ".join(high_interest_debts["name"].tolist())
        recommendations.append({
            "priority": "Urgente",
            "title": f"Amortizar deudas de alto interés ({names})",
            "description": f"Tienes {total_high_interest:,.2f} € en deudas con tasas elevadas (>8%). La rentabilidad garantizada de liquidar estas deudas supera el retorno esperado del mercado bursátil.",
            "impact": "Ahorro directo inmediato en coste financiero por intereses."
        })

    if analysis_50_30_20["wants"]["pct"] > 35.0:
        recommendations.append({
            "priority": "Media",
            "title": "Optimizar Gastos en Deseos y Ocio",
            "description": f"Actualmente destinas el {analysis_50_30_20['wants']['pct']:.1f}% a gastos no esenciales (el estándar es <= 30%). Revisa suscripciones no utilizadas o salidas recurrentes para aumentar tu capacidad de ahorro.",
            "impact": "Liberar flujo de caja mensual para acelerar metas de inversión."
        })

    if savings_pct < 20.0 and months_cov >= 3.0:
        recommendations.append({
            "priority": "Media",
            "title": "Implementar la técnica 'Págate a ti mismo primero'",
            "description": "Programa una transferencia automática el día 1 de cada mes hacia tu cuenta de inversión o ahorro indexado por el 20% de tus ingresos, antes de empezar a gastar.",
            "impact": "Garantiza el cumplimiento automático de tu presupuesto de ahorro."
        })

    if not recommendations:
        recommendations.append({
            "priority": "Baja",
            "title": "Salud Financiera Excelente",
            "description": "Tus ratios de ahorro, fondo de emergencia y gestión de deuda están en niveles sobresalientes. Puedes explorar optimización fiscal o incremento de aportaciones a fondos indexados globales.",
            "impact": "Acelera tu fecha de jubilación anticipada (FIRE)."
        })

    return {
        "savings_rate_pct": savings_pct,
        "savings_grade": savings_grade,
        "savings_badge": savings_badge,
        "emergency_months": months_cov,
        "emergency_grade": ef_grade,
        "emergency_badge": ef_badge,
        "debt_ratio_pct": debt_ratio,
        "recommendations": recommendations,
        "net_worth": net_worth
    }

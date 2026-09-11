import sqlite3
import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from ..database.connection import get_connection, DB_PATH

def set_budget(category_id: int, monthly_limit: float, month: str = "default", db_path: Path = DB_PATH):
    """Establece o actualiza el límite presupuestario para una categoría."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO budgets (category_id, monthly_limit, month)
        VALUES (?, ?, ?)
        ON CONFLICT(category_id, month) DO UPDATE SET monthly_limit = excluded.monthly_limit
        """,
        (category_id, float(monthly_limit), month)
    )
    conn.commit()
    conn.close()

def get_budget_vs_actual(year: int, month: int, db_path: Path = DB_PATH) -> pd.DataFrame:
    """
    Compara el presupuesto mensual fijado vs el gasto real incurrido en el mes indicado.
    """
    month_str = f"{year:04d}-{month:02d}"
    conn = get_connection(db_path)

    query = """
        SELECT 
            c.id AS category_id,
            c.name AS category_name,
            c.icon AS category_icon,
            c.bucket_50_30_20,
            COALESCE(b_custom.monthly_limit, b_def.monthly_limit, 0.0) AS budget_limit,
            COALESCE(SUM(t.amount), 0.0) AS actual_spent
        FROM categories c
        LEFT JOIN budgets b_custom ON c.id = b_custom.category_id AND b_custom.month = ?
        LEFT JOIN budgets b_def ON c.id = b_def.category_id AND b_def.month = 'default'
        LEFT JOIN transactions t ON c.id = t.category_id 
            AND t.type = 'expense' 
            AND t.date LIKE ?
        WHERE c.type = 'expense'
        GROUP BY c.id
        ORDER BY c.bucket_50_30_20, budget_limit DESC
    """
    df = pd.read_sql_query(query, conn, params=[month_str, f"{month_str}%"])
    conn.close()

    df['remaining'] = df['budget_limit'] - df['actual_spent']
    df['pct_used'] = df.apply(
        lambda r: (r['actual_spent'] / r['budget_limit'] * 100) if r['budget_limit'] > 0 else (100.0 if r['actual_spent'] > 0 else 0.0),
        axis=1
    )
    
    def get_status(row):
        if row['budget_limit'] == 0 and row['actual_spent'] > 0:
            return 'Sin presupuesto'
        if row['pct_used'] > 100:
            return 'Excedido'
        elif row['pct_used'] >= 80:
            return 'En alerta'
        else:
            return 'En objetivo'

    df['status'] = df.apply(get_status, axis=1)
    return df

def get_50_30_20_analysis(year: int, month: int, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Calcula el desglose del mes según la regla 50/30/20:
    - 50% Necesidades (needs)
    - 30% Deseos / Ocio (wants)
    - 20% Ahorro e Inversión (savings)
    """
    month_str = f"{year:04d}-{month:02d}"
    conn = get_connection(db_path)

    # Total Ingresos del mes
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) FROM transactions WHERE type = 'income' AND date LIKE ?",
        (f"{month_str}%",)
    )
    total_income = cursor.fetchone()[0]

    # Gastos por bucket
    cursor.execute(
        """
        SELECT c.bucket_50_30_20, COALESCE(SUM(t.amount), 0.0) AS total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.type = 'expense' AND t.date LIKE ?
        GROUP BY c.bucket_50_30_20
        """,
        (f"{month_str}%",)
    )
    bucket_data = {row['bucket_50_30_20']: row['total'] for row in cursor.fetchall()}
    conn.close()

    needs = bucket_data.get('needs', 0.0)
    wants = bucket_data.get('wants', 0.0)
    savings = bucket_data.get('savings', 0.0)
    total_expenses = needs + wants + savings

    # Si los ingresos son 0 pero hay gastos, usamos el total de gastos como base para evitar división por cero
    base = total_income if total_income > 0 else total_expenses

    needs_pct = (needs / base * 100) if base > 0 else 0.0
    wants_pct = (wants / base * 100) if base > 0 else 0.0
    savings_pct = (savings / base * 100) if base > 0 else 0.0

    target_needs = base * 0.50
    target_wants = base * 0.30
    target_savings = base * 0.20

    return {
        "month": month_str,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_cash_flow": total_income - total_expenses,
        "needs": {"actual": needs, "pct": needs_pct, "target": target_needs, "target_pct": 50.0, "diff": target_needs - needs},
        "wants": {"actual": wants, "pct": wants_pct, "target": target_wants, "target_pct": 30.0, "diff": target_wants - wants},
        "savings": {"actual": savings, "pct": savings_pct, "target": target_savings, "target_pct": 20.0, "diff": savings - target_savings}
    }

def get_emergency_fund_status(months_target: int = 6, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Evalúa la solidez del Fondo de Emergencia:
    - Gastos mensuales promedio de necesidades (últimos 3 meses)
    - Liquidez total disponible en cuentas corrientes y remuneradas/ahorro
    - Meses de cobertura actual y objetivo
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Liquidez disponible (cuentas tipo checking y savings)
    cursor.execute(
        "SELECT COALESCE(SUM(balance), 0.0) FROM accounts WHERE type IN ('checking', 'savings') AND is_asset = 1"
    )
    liquid_savings = cursor.fetchone()[0]

    # Gasto medio mensual en 'needs' en los últimos 90 días
    ninety_days_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    cursor.execute(
        """
        SELECT COALESCE(SUM(t.amount), 0.0)
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.type = 'expense' AND c.bucket_50_30_20 = 'needs' AND t.date >= ?
        """,
        (ninety_days_ago,)
    )
    three_months_needs = cursor.fetchone()[0]
    conn.close()

    monthly_burn_rate = three_months_needs / 3.0 if three_months_needs > 0 else 1200.0 # fallback realista si no hay histórico
    months_covered = (liquid_savings / monthly_burn_rate) if monthly_burn_rate > 0 else 0.0
    target_amount = monthly_burn_rate * months_target
    gap = target_amount - liquid_savings

    return {
        "liquid_savings": liquid_savings,
        "monthly_burn_rate": monthly_burn_rate,
        "months_covered": months_covered,
        "target_months": months_target,
        "target_amount": target_amount,
        "gap": gap,
        "is_healthy": months_covered >= months_target
    }

import sqlite3
import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from ..database.connection import get_connection, DB_PATH

def get_net_worth_summary(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Calcula el total de activos, pasivos y patrimonio neto actual."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT type, balance FROM accounts WHERE is_asset = 1")
    assets_rows = cursor.fetchall()

    cursor.execute("SELECT type, balance, interest_rate, name FROM accounts WHERE is_asset = 0")
    liab_rows = cursor.fetchall()
    conn.close()

    total_assets = sum(row['balance'] for row in assets_rows)
    total_liabilities = sum(row['balance'] for row in liab_rows)
    net_worth = total_assets - total_liabilities

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "assets_count": len(assets_rows),
        "liabilities_count": len(liab_rows)
    }

def get_asset_allocation(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Retorna la distribución de activos por categoría y porcentaje."""
    conn = get_connection(db_path)
    query = """
        SELECT 
            id,
            name,
            type,
            balance,
            currency,
            interest_rate
        FROM accounts
        WHERE is_asset = 1
        ORDER BY balance DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    total = df['balance'].sum() if not df.empty else 0.0
    if total > 0:
        df['percentage'] = (df['balance'] / total) * 100
    else:
        df['percentage'] = 0.0
    return df

def get_liabilities(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Retorna los pasivos / deudas ordenadas por saldo e interés."""
    conn = get_connection(db_path)
    query = """
        SELECT 
            id,
            name,
            type,
            balance,
            interest_rate
        FROM accounts
        WHERE is_asset = 0 AND balance > 0
        ORDER BY interest_rate DESC, balance DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def take_snapshot(snapshot_date: Optional[str] = None, db_path: Path = DB_PATH):
    """Guarda una fotografía del patrimonio neto actual para el histórico."""
    if snapshot_date is None:
        snapshot_date = datetime.now().strftime("%Y-%m-%d")

    summary = get_net_worth_summary(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO portfolio_snapshots (date, total_assets, total_liabilities, net_worth)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET 
            total_assets = excluded.total_assets,
            total_liabilities = excluded.total_liabilities,
            net_worth = excluded.net_worth
        """,
        (snapshot_date, summary['total_assets'], summary['total_liabilities'], summary['net_worth'])
    )
    conn.commit()
    conn.close()

def get_historical_snapshots(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Obtiene el histórico de evolución patrimonial."""
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT date, total_assets, total_liabilities, net_worth FROM portfolio_snapshots ORDER BY date ASC",
        conn
    )
    conn.close()
    return df

def get_financial_goals(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Obtiene las metas financieras activas y completadas."""
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT id, title, target_amount, current_amount, target_date, category, is_completed FROM financial_goals ORDER BY is_completed ASC, target_date ASC",
        conn
    )
    conn.close()
    if not df.empty:
        df['pct_progress'] = (df['current_amount'] / df['target_amount'] * 100).clip(0, 100)
    return df

def add_financial_goal(title: str, target_amount: float, current_amount: float = 0.0, target_date: Optional[str] = None, category: str = "savings_goal", db_path: Path = DB_PATH) -> int:
    """Añade una nueva meta financiera."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO financial_goals (title, target_amount, current_amount, target_date, category)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title.strip(), float(target_amount), float(current_amount), target_date, category)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_goal_progress(goal_id: int, current_amount: float, is_completed: Optional[bool] = None, db_path: Path = DB_PATH):
    """Actualiza el progreso de una meta financiera."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if is_completed is None:
        cursor.execute("SELECT target_amount FROM financial_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        if row and float(current_amount) >= row['target_amount']:
            is_completed = 1
        else:
            is_completed = 0
    else:
        is_completed = 1 if is_completed else 0

    cursor.execute(
        "UPDATE financial_goals SET current_amount = ?, is_completed = ? WHERE id = ?",
        (float(current_amount), is_completed, int(goal_id))
    )
    conn.commit()
    conn.close()

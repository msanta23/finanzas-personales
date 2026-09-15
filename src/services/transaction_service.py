import sqlite3
import pandas as pd
from typing import List, Dict, Optional, Any
from pathlib import Path
from ..database.connection import get_connection, DB_PATH

def get_categories(type_filter: Optional[str] = None, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Obtiene todas las categorías disponibles."""
    conn = get_connection(db_path)
    query = "SELECT id, name, type, bucket_50_30_20, icon, color FROM categories"
    params = []
    if type_filter:
        query += " WHERE type = ?"
        params.append(type_filter)
    query += " ORDER BY bucket_50_30_20, name"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def add_category(name: str, cat_type: str, bucket_50_30_20: str, icon: str = "📌", color: str = "#4F46E5", db_path: Path = DB_PATH) -> int:
    """Crea una nueva categoría."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO categories (name, type, bucket_50_30_20, icon, color) VALUES (?, ?, ?, ?, ?)",
        (name.strip(), cat_type, bucket_50_30_20, icon, color)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_category(category_id: int, name: str, cat_type: str, bucket_50_30_20: str, icon: str = "📌", color: str = "#4F46E5", db_path: Path = DB_PATH) -> bool:
    """Modifica los datos de una categoría existente."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE categories
        SET name = ?, type = ?, bucket_50_30_20 = ?, icon = ?, color = ?
        WHERE id = ?
        """,
        (name.strip(), cat_type, bucket_50_30_20, icon.strip() or "📌", color, int(category_id))
    )
    conn.commit()
    conn.close()
    return True

def delete_category(category_id: int, db_path: Path = DB_PATH) -> bool:
    """Elimina una categoría si no tiene transacciones asociadas."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE category_id = ?", (category_id,))
    tx_count = cursor.fetchone()[0]
    if tx_count > 0:
        conn.close()
        return False
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    return True

def get_accounts(is_asset: Optional[int] = None, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Obtiene el listado de cuentas bancarias y deudas."""
    conn = get_connection(db_path)
    query = "SELECT id, name, type, balance, currency, is_asset, interest_rate, created_at FROM accounts"
    params = []
    if is_asset is not None:
        query += " WHERE is_asset = ?"
        params.append(is_asset)
    query += " ORDER BY is_asset DESC, balance DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def add_account(name: str, acc_type: str, balance: float, currency: str = "EUR", is_asset: int = 1, interest_rate: float = 0.0, db_path: Path = DB_PATH) -> int:
    """Añade una nueva cuenta o producto financiero."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO accounts (name, type, balance, currency, is_asset, interest_rate) VALUES (?, ?, ?, ?, ?, ?)",
        (name.strip(), acc_type, float(balance), currency, int(is_asset), float(interest_rate))
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_account_balance(account_id: int, new_balance: float, db_path: Path = DB_PATH):
    """Actualiza el saldo de una cuenta."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (float(new_balance), int(account_id)))
    conn.commit()
    conn.close()

def update_account_details(account_id: int, name: str, acc_type: str, interest_rate: float, is_asset: Optional[int] = None, db_path: Path = DB_PATH):
    """Actualiza el nombre, tipo de cuenta, interés/rendimiento y condición de activo/pasivo."""
    if is_asset is None:
        is_asset = 0 if acc_type in ['loan', 'mortgage', 'credit_card'] else 1
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE accounts
        SET name = ?, type = ?, interest_rate = ?, is_asset = ?
        WHERE id = ?
        """,
        (name.strip(), acc_type, float(interest_rate), int(is_asset), int(account_id))
    )
    conn.commit()
    conn.close()

def delete_account(account_id: int, db_path: Path = DB_PATH):
    """Elimina una cuenta."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM accounts WHERE id = ?", (int(account_id),))
    conn.commit()
    conn.close()

def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[int] = None,
    account_id: Optional[int] = None,
    tx_type: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    is_recurring: Optional[int] = None,
    limit: int = 1000,
    db_path: Path = DB_PATH
) -> pd.DataFrame:
    """Consulta transacciones con filtros opcionales (incluyendo rango de fechas, año, mes, recurrencia, categoría, cuenta y tipo)."""
    import calendar
    conn = get_connection(db_path)
    query = """
        SELECT 
            t.id,
            t.date,
            t.amount,
            t.description,
            t.type,
            t.is_recurring,
            t.created_at,
            t.account_id,
            a.name AS account_name,
            t.category_id,
            c.name AS category_name,
            c.bucket_50_30_20,
            c.icon AS category_icon,
            c.color AS category_color
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE 1=1
    """
    params = []

    # Ajuste de año y mes si se proporcionan
    if year is not None and month is not None:
        _, last_day = calendar.monthrange(year, month)
        query += " AND t.date >= ? AND t.date <= ?"
        params.extend([f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"])
    elif year is not None:
        query += " AND t.date >= ? AND t.date <= ?"
        params.extend([f"{year:04d}-01-01", f"{year:04d}-12-31"])
    elif month is not None:
        query += " AND CAST(strftime('%m', t.date) AS INTEGER) = ?"
        params.append(month)

    if start_date:
        query += " AND t.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND t.date <= ?"
        params.append(end_date)
    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)
    if account_id:
        query += " AND t.account_id = ?"
        params.append(account_id)
    if tx_type:
        query += " AND t.type = ?"
        params.append(tx_type)
    if is_recurring is not None:
        query += " AND t.is_recurring = ?"
        params.append(1 if is_recurring else 0)

    query += " ORDER BY t.date DESC, t.id DESC LIMIT ?"
    params.append(limit)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_recurring_commitments(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Obtiene el último movimiento activo de cada compromiso recurrente / gasto fijo mensual."""
    conn = get_connection(db_path)
    query = """
        SELECT 
            t.id,
            t.date,
            t.amount,
            t.description,
            t.type,
            a.name AS account_name,
            c.name AS category_name,
            c.icon AS category_icon,
            c.bucket_50_30_20
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY LOWER(TRIM(description)), type 
                    ORDER BY date DESC, id DESC
                ) as rn
                FROM transactions
                WHERE is_recurring = 1
            ) sub WHERE sub.rn = 1
        )
        ORDER BY t.type ASC, t.amount DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df



def add_transaction(
    account_id: Optional[int],
    category_id: int,
    date: str,
    amount: float,
    description: str,
    tx_type: str,
    is_recurring: bool = False,
    update_balance: bool = True,
    db_path: Path = DB_PATH
) -> int:
    """Registra un nuevo movimiento y opcionalmente actualiza el balance de la cuenta."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO transactions (account_id, category_id, date, amount, description, type, is_recurring)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (account_id, category_id, date, float(amount), description, tx_type, 1 if is_recurring else 0)
    )
    new_id = cursor.lastrowid

    if update_balance and account_id:
        delta = float(amount) if tx_type == 'income' else -float(amount)
        cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (delta, account_id))

    conn.commit()
    conn.close()
    return new_id

def add_transfer(
    source_account_id: int,
    dest_account_id: int,
    amount: float,
    date: str,
    description: str = "Traspaso entre cuentas",
    category_id: Optional[int] = None,
    is_recurring: bool = False,
    db_path: Path = DB_PATH
) -> int:
    """
    Registra un traspaso entre cuentas:
    1. Resta el importe de la cuenta origen.
    2. Suma el importe en la cuenta destino.
    3. Registra la transacción para seguimiento presupuestario (ej. ahorro/inversión).
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Si no se indica categoría, asignar por defecto la categoría de ahorro/inversión o Fondos Indexados
    if category_id is None:
        cursor.execute("SELECT id FROM categories WHERE bucket_50_30_20 = 'savings' LIMIT 1")
        cat_row = cursor.fetchone()
        category_id = cat_row[0] if cat_row else 1

    # Actualizar saldos
    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (float(amount), source_account_id))
    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (float(amount), dest_account_id))

    # Registrar el movimiento
    cursor.execute(
        """
        INSERT INTO transactions (account_id, category_id, date, amount, description, type, is_recurring)
        VALUES (?, ?, ?, ?, ?, 'expense', ?)
        """,
        (source_account_id, category_id, date, float(amount), description, 1 if is_recurring else 0)
    )
    new_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return new_id

def get_transaction_by_id(transaction_id: int, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Obtiene el detalle completo de una transacción por su ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT t.id, t.account_id, t.category_id, t.date, t.amount, t.description, t.type, t.is_recurring,
               a.name AS account_name, c.name AS category_name, c.icon AS category_icon
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.id = ?
        """,
        (transaction_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_transaction(
    transaction_id: int,
    account_id: Optional[int],
    category_id: int,
    date: str,
    amount: float,
    description: str,
    tx_type: str,
    is_recurring: bool = False,
    adjust_balance: bool = True,
    db_path: Path = DB_PATH
) -> bool:
    """Modifica una transacción existente y recalcula los saldos de cuenta de forma consistente."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT account_id, amount, type FROM transactions WHERE id = ?", (transaction_id,))
    old = cursor.fetchone()
    if not old:
        conn.close()
        return False

    old_acc_id = old['account_id']
    old_amount = float(old['amount'])
    old_type = old['type']

    new_amount = float(amount)

    if adjust_balance:
        # Revertir saldo anterior
        if old_acc_id:
            revert_delta = -old_amount if old_type == 'income' else old_amount
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (revert_delta, old_acc_id))
        
        # Aplicar nuevo saldo
        if account_id:
            apply_delta = new_amount if tx_type == 'income' else -new_amount
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (apply_delta, account_id))

    cursor.execute(
        """
        UPDATE transactions
        SET account_id = ?, category_id = ?, date = ?, amount = ?, description = ?, type = ?, is_recurring = ?
        WHERE id = ?
        """,
        (account_id, category_id, date, new_amount, description, tx_type, 1 if is_recurring else 0, transaction_id)
    )

    conn.commit()
    conn.close()
    return True

def delete_transaction(transaction_id: int, rollback_balance: bool = True, db_path: Path = DB_PATH):
    """Elimina una transacción y revierte su impacto en balance si se solicita."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if rollback_balance:
        cursor.execute("SELECT account_id, amount, type FROM transactions WHERE id = ?", (transaction_id,))
        row = cursor.fetchone()
        if row and row['account_id']:
            acc_id = row['account_id']
            amt = row['amount']
            ttype = row['type']
            delta = -amt if ttype == 'income' else amt
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (delta, acc_id))

    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()

def import_csv_transactions(
    df: pd.DataFrame,
    col_date: str,
    col_amount: str,
    col_desc: str,
    default_account_id: Optional[int] = None,
    default_category_id: Optional[int] = None,
    default_income_category_id: Optional[int] = None,
    db_path: Path = DB_PATH
) -> int:
    """
    Importa transacciones desde un DataFrame procesado de CSV.
    Detecta automáticamente tipo (income/expense) según signo del importe o columnas.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Si no se provee categoría por defecto de gastos, buscar la primera de gastos
    if default_category_id is None:
        cursor.execute("SELECT id FROM categories WHERE type = 'expense' LIMIT 1")
        cat_row = cursor.fetchone()
        default_category_id = cat_row[0] if cat_row else 1

    # Si no se provee categoría por defecto de ingresos, buscar la categoría de Nómina o la primera de ingresos
    if default_income_category_id is None:
        cursor.execute("SELECT id FROM categories WHERE type = 'income' AND name LIKE '%Nómina%' LIMIT 1")
        income_cat_row = cursor.fetchone()
        if not income_cat_row:
            cursor.execute("SELECT id FROM categories WHERE type = 'income' LIMIT 1")
            income_cat_row = cursor.fetchone()
        default_income_category_id = income_cat_row[0] if income_cat_row else default_category_id

    imported_count = 0
    for _, row in df.iterrows():
        try:
            raw_date = str(row[col_date]).strip()
            # Parsear fecha en formato ISO si es posible
            dt = pd.to_datetime(raw_date, dayfirst=True)
            iso_date = dt.strftime("%Y-%m-%d")

            # Parsear importe (maneja números con comas europeas)
            raw_amt = row[col_amount]
            if isinstance(raw_amt, str):
                cleaned_amt = raw_amt.replace("€", "").replace("$", "").replace(" ", "").replace(".", "").replace(",", ".")
                amt_val = float(cleaned_amt)
            else:
                amt_val = float(raw_amt)

            tx_type = 'income' if amt_val > 0 else 'expense'
            abs_amount = abs(amt_val)
            desc = str(row[col_desc]).strip() if col_desc in row and pd.notna(row[col_desc]) else "Movimiento importado"
            cat_id = default_income_category_id if tx_type == 'income' else default_category_id

            cursor.execute(
                """
                INSERT INTO transactions (account_id, category_id, date, amount, description, type, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (default_account_id, cat_id, iso_date, abs_amount, desc, tx_type)
            )
            imported_count += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    return imported_count

import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "finance.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Retorna una conexión a la base de datos SQLite."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Path = DB_PATH):
    """Crea las tablas según schema.sql si no existen."""
    conn = get_connection(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

def seed_demo_data(db_path: Path = DB_PATH, force: bool = False):
    """Puebla la base de datos con datos realistas de demostración."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM categories;")
    count = cursor.fetchone()[0]
    if count > 0 and not force:
        conn.close()
        return

    if force:
        cursor.execute("DELETE FROM transactions;")
        cursor.execute("DELETE FROM budgets;")
        cursor.execute("DELETE FROM financial_goals;")
        cursor.execute("DELETE FROM portfolio_snapshots;")
        cursor.execute("DELETE FROM accounts;")
        cursor.execute("DELETE FROM categories;")

    # 1. Categorías por defecto
    categories = [
        # Ingresos
        ('Nómina', 'income', 'income', '💼', '#10B981'),
        ('Nómina / Salario', 'income', 'income', '💼', '#10B981'),
        ('Dividendos e Intereses', 'income', 'income', '📈', '#059669'),
        ('Ventas / Freelance', 'income', 'income', '💻', '#34D399'),
        
        # Necesidades (Needs - 50%)
        ('Vivienda (Alquiler/Hipoteca)', 'expense', 'needs', '🏠', '#3B82F6'),
        ('Supermercado y Alimentación', 'expense', 'needs', '🛒', '#60A5FA'),
        ('Suministros (Luz, Agua, Gas, Internet)', 'expense', 'needs', '💡', '#93C5FD'),
        ('Transporte y Combustible', 'expense', 'needs', '🚗', '#2563EB'),
        ('Salud y Seguros', 'expense', 'needs', '🩺', '#1D4ED8'),

        # Deseos / Ocio (Wants - 30%)
        ('Restaurantes y Bares', 'expense', 'wants', '🍽️', '#F59E0B'),
        ('Ocio, Cine y Eventos', 'expense', 'wants', '🎟️', '#FBBF24'),
        ('Suscripciones (Netflix, Spotify, etc.)', 'expense', 'wants', '📺', '#D97706'),
        ('Viajes y Vacaciones', 'expense', 'wants', '✈️', '#B45309'),
        ('Compras y Ropa', 'expense', 'wants', '🛍️', '#FCD34D'),
        ('Deporte', 'expense', 'wants', '🏋️', '#10B981'),

        # Ahorro e Inversión (Savings - 20%)
        ('Fondo de Emergencia', 'expense', 'savings', '🛡️', '#8B5CF6'),
        ('Fondos Indexados / ETFs', 'expense', 'savings', '📊', '#7C3AED'),
        ('Criptomonedas', 'expense', 'savings', '🪙', '#6D28D9'),
        ('Planes de Pensiones', 'expense', 'savings', '👴', '#5B21B6')
    ]

    cursor.executemany(
        "INSERT INTO categories (name, type, bucket_50_30_20, icon, color) VALUES (?, ?, ?, ?, ?);",
        categories
    )

    # 2. Cuentas y Activos / Pasivos
    accounts = [
        ('Cuenta Corriente Principal', 'checking', 3500.0, 'EUR', 1, 0.0),
        ('Cuenta Remunerada Ahorro (3.5%)', 'savings', 12000.0, 'EUR', 1, 3.5),
        ('Cartera Fondos Indexados (MSCI World)', 'investment', 28500.0, 'EUR', 1, 7.5),
        ('Exchange Cripto (BTC / ETH)', 'crypto', 4200.0, 'EUR', 1, 0.0),
        ('Préstamo Coche', 'loan', 6400.0, 'EUR', 0, 5.9),
        ('Tarjeta de Crédito', 'credit_card', 350.0, 'EUR', 0, 18.5)
    ]

    cursor.executemany(
        "INSERT INTO accounts (name, type, balance, currency, is_asset, interest_rate) VALUES (?, ?, ?, ?, ?, ?);",
        accounts
    )

    # 3. Presupuestos mensuales predefinidos
    cursor.execute("SELECT id, name FROM categories;")
    cat_map = {row['name']: row['id'] for row in cursor.fetchall()}

    budgets = [
        (cat_map['Vivienda (Alquiler/Hipoteca)'], 850.0, 'default'),
        (cat_map['Supermercado y Alimentación'], 400.0, 'default'),
        (cat_map['Suministros (Luz, Agua, Gas, Internet)'], 160.0, 'default'),
        (cat_map['Transporte y Combustible'], 120.0, 'default'),
        (cat_map['Salud y Seguros'], 80.0, 'default'),
        (cat_map['Restaurantes y Bares'], 200.0, 'default'),
        (cat_map['Ocio, Cine y Eventos'], 120.0, 'default'),
        (cat_map['Suscripciones (Netflix, Spotify, etc.)'], 45.0, 'default'),
        (cat_map['Compras y Ropa'], 100.0, 'default'),
        (cat_map['Fondos Indexados / ETFs'], 500.0, 'default'),
        (cat_map['Fondo de Emergencia'], 200.0, 'default'),
    ]
    cursor.executemany(
        "INSERT INTO budgets (category_id, monthly_limit, month) VALUES (?, ?, ?);",
        budgets
    )

    # 4. Objetivos Financieros
    goals = [
        ('Fondo de Emergencia (6 meses)', 10000.0, 12000.0, '2026-12-31', 'emergency_fund', 1),
        ('Primeros 50.000 € Invertidos', 50000.0, 28500.0, '2027-12-31', 'investment', 0),
        ('Liquidación Préstamo Coche', 6400.0, 3600.0, '2027-06-30', 'debt_payoff', 0),
        ('Vacaciones en Japón', 3500.0, 1800.0, '2027-04-15', 'savings_goal', 0)
    ]
    cursor.executemany(
        "INSERT INTO financial_goals (title, target_amount, current_amount, target_date, category, is_completed) VALUES (?, ?, ?, ?, ?, ?);",
        goals
    )

    # 5. Generar transacciones históricas realistas para los últimos 3 meses
    today = datetime.now().date()
    tx_list = []

    cursor.execute("SELECT id, name FROM accounts;")
    acc_map = {row['name']: row['id'] for row in cursor.fetchall()}
    main_acc = acc_map.get('Cuenta Corriente Principal', 1)
    inv_acc = acc_map.get('Cartera Fondos Indexados (MSCI World)', 1)

    for months_back in range(3, -1, -1):
        base_date = today - timedelta(days=months_back * 30)
        y_m = base_date.strftime("%Y-%m")
        
        # Ingreso Nómina (día 1)
        tx_list.append((main_acc, cat_map['Nómina / Salario'], f"{y_m}-01", 2650.0, 'Nómina mensual', 'income', 1))
        
        # Gastos Fijos (días 2 al 6)
        tx_list.append((main_acc, cat_map['Vivienda (Alquiler/Hipoteca)'], f"{y_m}-03", 850.0, 'Alquiler vivienda', 'expense', 1))
        tx_list.append((main_acc, cat_map['Suministros (Luz, Agua, Gas, Internet)'], f"{y_m}-05", 145.50, 'Factura luz e internet', 'expense', 1))
        tx_list.append((main_acc, cat_map['Salud y Seguros'], f"{y_m}-06", 65.0, 'Seguro médico', 'expense', 1))

        # Inversión mensual automática (día 5)
        tx_list.append((inv_acc, cat_map['Fondos Indexados / ETFs'], f"{y_m}-05", 500.0, 'Aportación periódica fondos', 'expense', 1))

        # Supermercado semanal
        for day in [4, 11, 18, 25]:
            tx_list.append((main_acc, cat_map['Supermercado y Alimentación'], f"{y_m}-{day:02d}", 85.0 + (day % 15), 'Compra semanal Mercadona', 'expense', 0))

        # Transporte / Gasolina
        tx_list.append((main_acc, cat_map['Transporte y Combustible'], f"{y_m}-10", 60.0, 'Gasolinera Repsol', 'expense', 0))
        tx_list.append((main_acc, cat_map['Transporte y Combustible'], f"{y_m}-24", 55.0, 'Gasolinera Repsol', 'expense', 0))

        # Ocio y Restaurantes
        tx_list.append((main_acc, cat_map['Restaurantes y Bares'], f"{y_m}-08", 45.0, 'Cena fin de semana', 'expense', 0))
        tx_list.append((main_acc, cat_map['Restaurantes y Bares'], f"{y_m}-15", 72.0, 'Comida con amigos', 'expense', 0))
        tx_list.append((main_acc, cat_map['Restaurantes y Bares'], f"{y_m}-22", 50.0, 'Tapas y cervezas', 'expense', 0))
        tx_list.append((main_acc, cat_map['Ocio, Cine y Eventos'], f"{y_m}-17", 32.0, 'Entradas cine y palomitas', 'expense', 0))

        # Suscripciones
        tx_list.append((main_acc, cat_map['Suscripciones (Netflix, Spotify, etc.)'], f"{y_m}-12", 17.99, 'Netflix + Spotify', 'expense', 1))

    cursor.executemany(
        "INSERT INTO transactions (account_id, category_id, date, amount, description, type, is_recurring) VALUES (?, ?, ?, ?, ?, ?, ?);",
        tx_list
    )

    # 6. Histórico de Patrimonio Neto (Snapshots mensuales)
    snapshots = [
        ((today - timedelta(days=90)).strftime("%Y-%m-%d"), 42000.0, 7800.0, 34200.0),
        ((today - timedelta(days=60)).strftime("%Y-%m-%d"), 44300.0, 7400.0, 36900.0),
        ((today - timedelta(days=30)).strftime("%Y-%m-%d"), 46800.0, 7000.0, 39800.0),
        (today.strftime("%Y-%m-%d"), 48200.0, 6750.0, 41450.0),
    ]
    cursor.executemany(
        "INSERT INTO portfolio_snapshots (date, total_assets, total_liabilities, net_worth) VALUES (?, ?, ?, ?);",
        snapshots
    )

    conn.commit()
    conn.close()

def clear_user_data(keep_categories: bool = True, db_path: Path = DB_PATH):
    """Elimina transacciones, cuentas, presupuestos, metas y snapshots para empezar desde cero."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions;")
    cursor.execute("DELETE FROM budgets;")
    cursor.execute("DELETE FROM financial_goals;")
    cursor.execute("DELETE FROM portfolio_snapshots;")
    cursor.execute("DELETE FROM accounts;")
    if not keep_categories:
        cursor.execute("DELETE FROM categories;")
    conn.commit()
    conn.close()


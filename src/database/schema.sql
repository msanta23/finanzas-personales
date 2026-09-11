-- Esquema de base de datos relacional para Finanzas Personales

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'checking', 'savings', 'investment', 'real_estate', 'crypto', 'loan', 'mortgage', 'credit_card'
    balance REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'EUR',
    is_asset INTEGER NOT NULL DEFAULT 1, -- 1 para activo, 0 para pasivo/deuda
    interest_rate REAL DEFAULT 0.0,      -- Tasa de interés anual (%) relevante para deudas o cuentas remuneradas
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL, -- 'income', 'expense'
    bucket_50_30_20 TEXT NOT NULL, -- 'needs' (necesidades), 'wants' (deseos/ocio), 'savings' (ahorro/inversión), 'income'
    icon TEXT DEFAULT '📌',
    color TEXT DEFAULT '#4F46E5'
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    category_id INTEGER NOT NULL,
    date TEXT NOT NULL, -- Formato YYYY-MM-DD
    amount REAL NOT NULL,
    description TEXT,
    type TEXT NOT NULL, -- 'income', 'expense', 'transfer'
    is_recurring INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    monthly_limit REAL NOT NULL,
    month TEXT NOT NULL, -- Formato YYYY-MM o 'default'
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(category_id, month)
);

CREATE TABLE IF NOT EXISTS financial_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL NOT NULL DEFAULT 0.0,
    target_date TEXT,
    category TEXT NOT NULL DEFAULT 'savings_goal', -- 'emergency_fund', 'investment', 'savings_goal', 'debt_payoff'
    is_completed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE, -- YYYY-MM-DD
    total_assets REAL NOT NULL,
    total_liabilities REAL NOT NULL,
    net_worth REAL NOT NULL
);

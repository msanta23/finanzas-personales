import pytest
import tempfile
from pathlib import Path
from src.database.connection import init_db, seed_demo_data, get_connection
from src.services.transaction_service import (
    get_categories, add_category, get_accounts, add_account,
    get_transactions, add_transaction, delete_transaction
)
from src.services.budget_service import set_budget, get_budget_vs_actual, get_50_30_20_analysis, get_emergency_fund_status
from src.services.portfolio_service import get_net_worth_summary, take_snapshot, get_historical_snapshots

@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_finance.db"
        init_db(db_path)
        seed_demo_data(db_path, force=True)
        yield db_path

def test_database_initialization_and_seed(temp_db):
    cats = get_categories(db_path=temp_db)
    assert not cats.empty
    accs = get_accounts(db_path=temp_db)
    assert not accs.empty
    txs = get_transactions(db_path=temp_db)
    assert not txs.empty

def test_add_and_delete_transaction(temp_db):
    accs = get_accounts(db_path=temp_db)
    cats = get_categories(db_path=temp_db)
    acc_id = int(accs.iloc[0]["id"])
    cat_id = int(cats.iloc[0]["id"])
    
    initial_balance = float(accs.iloc[0]["balance"])

    # Añadir gasto
    tx_id = add_transaction(
        account_id=acc_id,
        category_id=cat_id,
        date="2026-09-01",
        amount=50.0,
        description="Test gasto",
        tx_type="expense",
        update_balance=True,
        db_path=temp_db
    )
    assert tx_id > 0

    accs_after = get_accounts(db_path=temp_db)
    updated_acc = accs_after[accs_after["id"] == acc_id].iloc[0]
    assert updated_acc["balance"] == initial_balance - 50.0

    # Eliminar gasto con rollback
    delete_transaction(tx_id, rollback_balance=True, db_path=temp_db)
    accs_final = get_accounts(db_path=temp_db)
    final_acc = accs_final[accs_final["id"] == acc_id].iloc[0]
    assert final_acc["balance"] == initial_balance

def test_50_30_20_and_budgets(temp_db):
    analysis = get_50_30_20_analysis(2026, 9, db_path=temp_db)
    assert "needs" in analysis
    assert "wants" in analysis
    assert "savings" in analysis
    
    ef = get_emergency_fund_status(months_target=6, db_path=temp_db)
    assert "months_covered" in ef
    assert ef["liquid_savings"] > 0

def test_portfolio_summary_and_snapshots(temp_db):
    summary = get_net_worth_summary(db_path=temp_db)
    assert summary["total_assets"] > 0
    assert summary["net_worth"] == summary["total_assets"] - summary["total_liabilities"]

    take_snapshot("2026-09-08", db_path=temp_db)
    hist = get_historical_snapshots(db_path=temp_db)
    assert not hist.empty
    assert "2026-09-08" in hist["date"].values

def test_update_account_details(temp_db):
    from src.services.transaction_service import update_account_details
    accs = get_accounts(db_path=temp_db)
    target_id = int(accs.iloc[0]["id"])
    
    update_account_details(target_id, "Cuenta Modificada", "investment", 7.5, db_path=temp_db)
    
    accs_updated = get_accounts(db_path=temp_db)
    row = accs_updated[accs_updated["id"] == target_id].iloc[0]
    assert row["name"] == "Cuenta Modificada"
    assert row["type"] == "investment"
    assert row["interest_rate"] == 7.5
    assert row["is_asset"] == 1

def test_add_transfer(temp_db):
    from src.services.transaction_service import add_transfer, add_account
    
    acc_src = add_account("Cuenta Nómina Test", "checking", 3000.0, db_path=temp_db)
    acc_dst = add_account("Cartera Inversión Test", "investment", 1000.0, db_path=temp_db)
    
    add_transfer(
        source_account_id=acc_src,
        dest_account_id=acc_dst,
        amount=500.0,
        date="2026-09-10",
        description="Aportación mensual fondos indexados",
        db_path=temp_db
    )
    
    accs = get_accounts(db_path=temp_db)
    src_bal = accs[accs["id"] == acc_src].iloc[0]["balance"]
    dst_bal = accs[accs["id"] == acc_dst].iloc[0]["balance"]
    
    assert src_bal == 2500.0
    assert dst_bal == 1500.0

def test_update_transaction(temp_db):
    from src.services.transaction_service import (
        add_transaction, update_transaction, get_transaction_by_id, add_account, get_categories
    )
    
    acc_id = add_account("Cuenta Gastos", "checking", 1000.0, db_path=temp_db)
    cats = get_categories(db_path=temp_db)
    cat_id = int(cats[cats["type"] == "expense"].iloc[0]["id"])
    
    tx_id = add_transaction(
        account_id=acc_id,
        category_id=cat_id,
        date="2026-09-01",
        amount=50.0,
        description="Gasto inicial",
        tx_type="expense",
        update_balance=True,
        db_path=temp_db
    )
    
    accs = get_accounts(db_path=temp_db)
    assert accs[accs["id"] == acc_id].iloc[0]["balance"] == 950.0
    
    # Modificar el importe a 80.0
    ok = update_transaction(
        transaction_id=tx_id,
        account_id=acc_id,
        category_id=cat_id,
        date="2026-09-02",
        amount=80.0,
        description="Gasto corregido",
        tx_type="expense",
        adjust_balance=True,
        db_path=temp_db
    )
    assert ok is True
    
    tx_updated = get_transaction_by_id(tx_id, db_path=temp_db)
    assert tx_updated["amount"] == 80.0
    assert tx_updated["description"] == "Gasto corregido"
    assert tx_updated["date"] == "2026-09-02"
    
    accs_after = get_accounts(db_path=temp_db)
    assert accs_after[accs_after["id"] == acc_id].iloc[0]["balance"] == 920.0

def test_transactions_year_and_month_filters(temp_db):
    txs_2026_9 = get_transactions(year=2026, month=9, db_path=temp_db)
    assert not txs_2026_9.empty
    # Verificar que todas las fechas son de 2026-09
    for d in txs_2026_9['date']:
        assert d.startswith("2026-09")

    txs_empty_year = get_transactions(year=1990, db_path=temp_db)
    assert txs_empty_year.empty

def test_investment_allocation_excludes_cash(temp_db):
    from src.services.portfolio_service import get_investment_allocation
    inv_df = get_investment_allocation(db_path=temp_db)
    assert not inv_df.empty
    # Ningún tipo de cuenta debe ser checking, savings o cash
    for acc_type in inv_df['type']:
        assert acc_type.lower() not in ['checking', 'savings', 'cash']

def test_recurring_commitments_and_filter(temp_db):
    from src.services.transaction_service import get_recurring_commitments
    rec_df = get_recurring_commitments(db_path=temp_db)
    assert not rec_df.empty
    
    # Probar filtro en get_transactions
    tx_rec = get_transactions(is_recurring=1, db_path=temp_db)
    assert not tx_rec.empty
    for r in tx_rec['is_recurring']:
        assert r == 1

    tx_one_off = get_transactions(is_recurring=0, db_path=temp_db)
    assert not tx_one_off.empty
    for r in tx_one_off['is_recurring']:
        assert r == 0

def test_update_category(temp_db):
    from src.services.transaction_service import get_categories, update_category
    cats = get_categories(db_path=temp_db)
    target_id = int(cats.iloc[0]["id"])

    ok = update_category(
        category_id=target_id,
        name="Supermercado VIP",
        cat_type="expense",
        bucket_50_30_20="needs",
        icon="🛍️",
        color="#10B981",
        db_path=temp_db
    )
    assert ok is True

    cats_after = get_categories(db_path=temp_db)
    cat_row = cats_after[cats_after["id"] == target_id].iloc[0]
    assert cat_row["name"] == "Supermercado VIP"
    assert cat_row["icon"] == "🛍️"
    assert cat_row["type"] == "expense"
    assert cat_row["bucket_50_30_20"] == "needs"

def test_plot_cashflow_bar_with_investments():
    import pandas as pd
    from src.ui.components import plot_cashflow_bar
    
    df_monthly = pd.DataFrame({
        'month': ['2026-07', '2026-08', '2026-09'],
        'income': [2500.0, 2650.0, 2650.0],
        'expense': [1200.0, 1150.0, 1195.56],
        'investment': [500.0, 500.0, 500.0]
    })
    
    fig = plot_cashflow_bar(df_monthly, "€")
    assert fig is not None
    assert len(fig.data) == 3
    names = [trace.name for trace in fig.data]
    assert "Ingresos" in names
    assert "Gastos" in names
    assert "Inversiones" in names

def test_monthly_expenses_and_investments_separation(temp_db):
    txs = get_transactions(year=2026, month=9, db_path=temp_db)
    assert not txs.empty

    income = txs[txs['type'] == 'income']['amount'].sum()
    pure_expenses = txs[(txs['type'] == 'expense') & (txs['bucket_50_30_20'] != 'savings')]['amount'].sum()
    investments = txs[(txs['type'] == 'expense') & (txs['bucket_50_30_20'] == 'savings')]['amount'].sum()

    assert income > 0
    assert pure_expenses > 0
    assert investments > 0
    assert pure_expenses + investments == txs[txs['type'] == 'expense']['amount'].sum()


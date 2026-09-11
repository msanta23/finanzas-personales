import pytest
import pandas as pd
from src.services.optimizer_service import (
    simulate_compound_interest,
    calculate_fire_projection,
    compare_debt_payoff_strategies
)

def test_simulate_compound_interest():
    # Capital inicial 1000, aportación 100/mes, 10% anual, 10 años, 2% inflación
    df = simulate_compound_interest(
        initial_principal=1000.0,
        monthly_contribution=100.0,
        annual_interest_rate_pct=10.0,
        years=10,
        annual_inflation_pct=2.0
    )
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 11 # Año 0 al 10
    assert df.iloc[0]["total_contributed"] == 1000.0
    assert df.iloc[-1]["total_contributed"] == 1000.0 + (100.0 * 12 * 10)
    assert df.iloc[-1]["nominal_balance"] > df.iloc[-1]["total_contributed"]
    assert df.iloc[-1]["real_balance"] < df.iloc[-1]["nominal_balance"]

def test_calculate_fire_projection():
    res = calculate_fire_projection(
        current_invested_assets=20000.0,
        monthly_savings=500.0,
        monthly_expenses=1500.0,
        expected_annual_return_pct=7.0,
        safe_withdrawal_rate_pct=4.0,
        current_age=30
    )
    # Gasto anual = 1500 * 12 = 18.000. Regla 4%: 18.000 / 0.04 = 450.000 €
    assert res["fire_target_standard"] == 450000.0
    assert res["fire_target_lean"] == 450000.0 * 0.8
    assert res["fire_target_fat"] == 450000.0 * 1.3
    assert res["current_fire_progress"] > 0
    assert isinstance(res["years_to_fire"], float)
    assert res["fire_age"] > 30

def test_compare_debt_payoff_strategies():
    debts = [
        {"name": "Tarjeta Crédito", "balance": 1000.0, "interest_rate": 20.0, "min_payment": 50.0},
        {"name": "Préstamo Personal", "balance": 5000.0, "interest_rate": 6.0, "min_payment": 100.0}
    ]
    res = compare_debt_payoff_strategies(debts, extra_monthly_payment=100.0)
    assert "avalanche" in res
    assert "snowball" in res
    assert "minimums_only" in res
    # Método avalancha debe pagar menor o igual interés que bola de nieve
    assert res["avalanche"]["total_interest_paid"] <= res["snowball"]["total_interest_paid"]
    # Método acelerado debe tardar menos que el solo mínimos
    assert res["avalanche"]["months"] <= res["minimums_only"]["months"]

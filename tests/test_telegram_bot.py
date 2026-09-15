import pytest
import sqlite3
from pathlib import Path
from src.bot.telegram_bot import TelegramFinanceBot
from src.database.connection import init_db, seed_demo_data, get_connection
from src.services.transaction_service import get_transactions, get_accounts

@pytest.fixture
def test_bot(temp_db):
    bot = TelegramFinanceBot(
        token="MOCK_TOKEN_12345",
        allowed_user_id="154948717",
        currency_symbol="€",
        db_path=temp_db
    )
    return bot

def test_unauthorized_user(test_bot):
    resp = test_bot.handle_message(user_id=999999999, text="15.50 Mercadona")
    assert "Acceso no autorizado" in resp

def test_commands(test_bot):
    # Test /ayuda
    resp_help = test_bot.handle_message(user_id=154948717, text="/ayuda")
    assert "asistente de Finanzas Personales" in resp_help

    # Test /saldo
    resp_saldo = test_bot.handle_message(user_id=154948717, text="/saldo")
    assert "Patrimonio Neto" in resp_saldo

    # Test /cuentas
    resp_cuentas = test_bot.handle_message(user_id=154948717, text="/cuentas")
    assert "Tus Cuentas y Saldos" in resp_cuentas

    # Test /categorias
    resp_cats = test_bot.handle_message(user_id=154948717, text="/categorias")
    assert "Categorías Disponibles" in resp_cats

def test_record_expense_with_keyword_matching(test_bot, temp_db):
    # Registrar compra de supermercado con "comida supermercado"
    resp = test_bot.handle_message(user_id=154948717, text="14 comida supermercado")
    assert "Gasto Registrado" in resp
    assert "14.00 €" in resp
    assert "Supermercado y Alimentación" in resp

    # Registrar gasto deportivo real
    resp_sport = test_bot.handle_message(user_id=154948717, text="45 gimnasio basic fit")
    assert "Gasto Registrado" in resp_sport
    assert "45.00 €" in resp_sport
    assert "Deporte" in resp_sport

    # Registrar restaurante
    resp_rest = test_bot.handle_message(user_id=154948717, text="28.50 cena restaurante")
    assert "Gasto Registrado" in resp_rest
    assert "28.50 €" in resp_rest
    assert "Restaurantes y Bares" in resp_rest

    # Verificar que se guardó en la base de datos
    df_tx = get_transactions(db_path=temp_db)
    matched = df_tx[df_tx["description"] == "comida supermercado"]
    assert not matched.empty
    assert float(matched.iloc[0]["amount"]) == 14.00
    assert matched.iloc[0]["category_name"] == "Supermercado y Alimentación"

def test_record_income(test_bot, temp_db):
    resp = test_bot.handle_message(user_id=154948717, text="+2450.00 Nómina de la empresa")
    assert "Ingreso Registrado" in resp
    assert "2,450.00 €" in resp
    assert "Nómina" in resp

def test_record_transfer_between_accounts(test_bot, temp_db):
    from src.services.transaction_service import add_account
    add_account("Abanca", "checking", 3000.0, db_path=temp_db)
    add_account("My Investor", "investment", 1000.0, db_path=temp_db)

    # Traspaso de una cuenta a otra
    resp = test_bot.handle_message(user_id=154948717, text="traspaso 400 Abanca a My Investor")
    assert "Traspaso Realizado" in resp
    assert "400.00 €" in resp
    assert "Abanca" in resp
    assert "My Investor" in resp



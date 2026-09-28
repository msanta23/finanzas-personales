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
        allowed_user_id="123456789",
        currency_symbol="€",
        db_path=temp_db
    )
    return bot

def test_unauthorized_user(test_bot):
    resp = test_bot.handle_message(user_id=999999999, text="15.50 Mercadona")
    assert "Acceso no autorizado" in resp

def test_commands(test_bot):
    # Test /ayuda
    resp_help = test_bot.handle_message(user_id=123456789, text="/ayuda")
    assert "asistente de Finanzas Personales" in resp_help

    # Test /saldo
    resp_saldo = test_bot.handle_message(user_id=123456789, text="/saldo")
    assert "Patrimonio Neto" in resp_saldo

    # Test /cuentas
    resp_cuentas = test_bot.handle_message(user_id=123456789, text="/cuentas")
    assert "Tus Cuentas y Saldos" in resp_cuentas

    # Test /categorias
    resp_cats = test_bot.handle_message(user_id=123456789, text="/categorias")
    assert "Categorías Disponibles" in resp_cats

def test_record_expense_with_keyword_matching(test_bot, temp_db):
    # Registrar compra de supermercado con "comida supermercado"
    resp = test_bot.handle_message(user_id=123456789, text="14 comida supermercado")
    assert "Gasto Registrado" in resp
    assert "14.00 €" in resp
    assert "Comida" in resp

    # Registrar gasto deportivo real
    resp_sport = test_bot.handle_message(user_id=123456789, text="45 gimnasio basic fit")
    assert "Gasto Registrado" in resp_sport
    assert "45.00 €" in resp_sport
    assert "Deporte" in resp_sport

    # Registrar restaurante
    resp_rest = test_bot.handle_message(user_id=123456789, text="28.50 cena restaurante la mafia")
    assert "Gasto Registrado" in resp_rest
    assert "28.50 €" in resp_rest
    assert "Restaurantes y Bares" in resp_rest
    assert "La mafia" in resp_rest

    # Verificar que se guardó en la base de datos
    df_tx = get_transactions(db_path=temp_db)
    matched = df_tx[df_tx["description"] == "Comida"]
    assert not matched.empty
    assert float(matched.iloc[0]["amount"]) == 14.00
    assert matched.iloc[0]["category_name"] == "Comida"

def test_concept_cleaning_and_default_revolut_account(test_bot, temp_db):
    from src.services.transaction_service import add_account
    add_account("Abanca", "checking", 2000.0, db_path=temp_db)
    add_account("Revolut", "checking", 1500.0, db_path=temp_db)

    # 1. Caso explícito con comercio, cuenta y categoría: "15 ahorramas revolut comida"
    # El concepto debe ser sólo "Ahorramas", cuenta "Revolut", categoría "Comida"
    resp = test_bot.handle_message(user_id=123456789, text="15 ahorramas revolut comida")
    assert "Gasto Registrado" in resp
    assert "15.00 €" in resp
    assert "Comida" in resp
    assert "Cuenta:* Revolut" in resp
    assert "Concepto:* Ahorramas" in resp

    # 2. Caso sin cuenta especificada: "15.50 ahorramas comida" -> Debe usar Revolut por defecto y concepto "Ahorramas"
    resp_def = test_bot.handle_message(user_id=123456789, text="15.50 ahorramas comida")
    assert "Gasto Registrado" in resp_def
    assert "15.50 €" in resp_def
    assert "Comida" in resp_def
    assert "Cuenta:* Revolut" in resp_def
    assert "Concepto:* Ahorramas" in resp_def

    # 3. Caso sólo comercio: "20 ahorramas" -> Debe usar Revolut por defecto y categoría Comida
    resp_merch = test_bot.handle_message(user_id=123456789, text="20 ahorramas")
    assert "Gasto Registrado" in resp_merch
    assert "20.00 €" in resp_merch
    assert "Comida" in resp_merch
    assert "Cuenta:* Revolut" in resp_merch
    assert "Concepto:* Ahorramas" in resp_merch

    # 4. Caso con cuenta distinta explícita: "50 Gasolina Repsol en Abanca"
    resp_abanca = test_bot.handle_message(user_id=123456789, text="50 Gasolina Repsol en Abanca")
    assert "Gasto Registrado" in resp_abanca
    assert "50.00 €" in resp_abanca
    assert "Transporte y Combustible" in resp_abanca
    assert "Cuenta:* Abanca" in resp_abanca
    assert "Concepto:* Repsol" in resp_abanca

def test_category_renamed_to_comida(test_bot, temp_db):
    from src.services.transaction_service import add_category, add_account
    add_account("Revolut", "checking", 1000.0, db_path=temp_db)
    # Renombrar o añadir categoría llamada "Comida"
    cat_id = add_category("Comida", "expense", "needs", "🛒", "#60A5FA", db_path=temp_db)

    # Probar que reconoce supermercados hacia la categoría "Comida"
    resp_merc = test_bot.handle_message(user_id=123456789, text="25 Mercadona")
    assert "Gasto Registrado" in resp_merc
    assert "25.00 €" in resp_merc
    assert "Comida" in resp_merc
    assert "Concepto:* Mercadona" in resp_merc
    assert "Cuenta:* Revolut" in resp_merc

    # Probar que limpia "comida" del concepto si hay comercio: "18 ahorramas comida"
    resp_ahorr = test_bot.handle_message(user_id=123456789, text="18 ahorramas comida")
    assert "Gasto Registrado" in resp_ahorr
    assert "18.00 €" in resp_ahorr
    assert "Comida" in resp_ahorr
    assert "Concepto:* Ahorramas" in resp_ahorr

def test_record_income(test_bot, temp_db):
    resp = test_bot.handle_message(user_id=123456789, text="+2450.00 Nómina de la empresa")
    assert "Ingreso Registrado" in resp
    assert "2,450.00 €" in resp
    assert "Nómina" in resp

def test_record_transfer_between_accounts(test_bot, temp_db):
    from src.services.transaction_service import add_account
    add_account("Abanca", "checking", 3000.0, db_path=temp_db)
    add_account("My Investor", "investment", 1000.0, db_path=temp_db)

    # Traspaso de una cuenta a otra
    resp = test_bot.handle_message(user_id=123456789, text="traspaso 400 Abanca a My Investor")
    assert "Traspaso Realizado" in resp
    assert "400.00 €" in resp
    assert "Abanca" in resp
    assert "My Investor" in resp



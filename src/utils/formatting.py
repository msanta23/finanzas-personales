"""Utilidades y formateadores para la aplicación de finanzas personales."""

def format_currency(amount: float, currency_symbol: str = "€") -> str:
    """Formatea un número decimal como valor monetario."""
    if amount is None:
        amount = 0.0
    # Formato europeo estándar: 1.234,56 € o $ 1,234.56
    if currency_symbol in ["€", "EUR"]:
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} €"
    else:
        return f"{currency_symbol} {amount:,.2f}"

def format_percentage(value: float, decimals: int = 1) -> str:
    """Formatea un valor decimal como porcentaje."""
    if value is None:
        return "0.0%"
    return f"{value:.{decimals}f}%"

def format_delta_currency(amount: float, currency_symbol: str = "€") -> str:
    """Formatea una variación con signo + o -."""
    if amount is None:
        amount = 0.0
    prefix = "+" if amount > 0 else ""
    return f"{prefix}{format_currency(amount, currency_symbol)}"

import os
import streamlit as st
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_env_file():
    """Carga variables desde archivo .env si existen."""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

def check_password() -> bool:
    """
    Verifica si el usuario ha iniciado sesión.
    Si no es así, muestra un formulario de inicio de sesión y detiene la ejecución.
    """
    load_env_file()
    expected_password = os.environ.get("WEB_PASSWORD", "finanzas2026")

    # Si ya está autenticado en la sesión actual
    if st.session_state.get("authenticated", False):
        return True

    # Pantalla de Login centrada y elegante
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background-color: #1E293B; padding: 2.5rem; border-radius: 12px; border: 1px solid #334155; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <h1 style="color: #38BDF8; margin-bottom: 0.5rem;">🔒 FinanzasPro</h1>
                <p style="color: #94A3B8; font-size: 1.05rem;">Acceso Protegido a Finanzas Personales</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            password_input = st.text_input(
                "Contraseña de Acceso",
                type="password",
                placeholder="Introduce tu contraseña...",
                help="Configurada en el archivo .env"
            )
            submit_button = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True, type="primary")

            if submit_button:
                if password_input == expected_password:
                    st.session_state["authenticated"] = True
                    st.toast("¡Acceso concedido!", icon="✅")
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta. Inténtalo de nuevo.")

    st.stop()
    return False

def render_logout_button():
    """Muestra el botón de cerrar sesión en la barra lateral."""
    if st.session_state.get("authenticated", False):
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

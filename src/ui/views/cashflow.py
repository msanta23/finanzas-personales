import streamlit as st
import pandas as pd
from datetime import datetime
from ...services.transaction_service import (
    get_transactions, get_transaction_by_id, add_transaction, update_transaction, add_transfer, delete_transaction,
    get_categories, add_category, delete_category, get_accounts, add_account,
    update_account_details, delete_account,
    import_csv_transactions
)
from ...utils.formatting import format_currency

def render_cashflow_view(currency_symbol: str = "€"):
    """Vista para gestionar ingresos, gastos, extractos bancarios y categorías/cuentas."""
    st.title("💸 Flujo de Caja y Transacciones")
    st.caption("Registra tus movimientos, importa extractos, edita o traspasa entre cuentas.")

    tab_tx, tab_add, tab_import, tab_cats_accs = st.tabs([
        "📋 Historial y Edición de Transacciones",
        "➕ Registrar Movimiento / Traspaso",
        "📂 Importar CSV Bancario",
        "🏷️ Cuentas y Categorías"
    ])

    df_cats = get_categories()
    df_accs = get_accounts()

    # ----------------------------------------------------
    # TAB 1: HISTORIAL Y EDICIÓN DE TRANSACCIONES
    # ----------------------------------------------------
    with tab_tx:
        st.subheader("Filtros de búsqueda")

        # Obtener años disponibles en la base de datos
        all_tx_dates = get_transactions(limit=5000)
        available_years = []
        if not all_tx_dates.empty and 'date' in all_tx_dates.columns:
            years_found = sorted(list(set(pd.to_datetime(all_tx_dates['date']).dt.year.dropna().astype(int))), reverse=True)
            available_years = years_found
        if not available_years:
            available_years = [datetime.today().year]
        if datetime.today().year not in available_years:
            available_years.insert(0, datetime.today().year)

        year_options = [("Todos los años", None)] + [(str(y), y) for y in available_years]
        month_names = [
            ("Todos los meses", None),
            ("Enero", 1), ("Febrero", 2), ("Marzo", 3), ("Abril", 4),
            ("Mayo", 5), ("Junio", 6), ("Julio", 7), ("Agosto", 8),
            ("Septiembre", 9), ("Octubre", 10), ("Noviembre", 11), ("Diciembre", 12)
        ]

        col_y, col_m, col_f1, col_f2, col_f3 = st.columns([1.2, 1.3, 1.4, 1.6, 1.5])

        with col_y:
            selected_year_tuple = st.selectbox("Año", year_options, format_func=lambda x: x[0], key="tx_filter_year")
            year_param = selected_year_tuple[1]

        with col_m:
            selected_month_tuple = st.selectbox("Mes", month_names, format_func=lambda x: x[0], key="tx_filter_month")
            month_param = selected_month_tuple[1]

        with col_f1:
            type_filter = st.selectbox("Tipo de Movimiento", ["Todos", "expense", "income"], format_func=lambda x: "Todos" if x == "Todos" else ("Gastos / Ahorro" if x == "expense" else "Ingresos"), key="tx_filter_type")
            tx_type_param = None if type_filter == "Todos" else type_filter

        with col_f2:
            cat_options = [("Todas las categorías", None)] + [(f"{row['icon']} {row['name']} ({'Ingreso' if row['type']=='income' else 'Gasto/Ahorro'})", row['id']) for _, row in df_cats.iterrows()]
            selected_cat_tuple = st.selectbox("Categoría", cat_options, format_func=lambda x: x[0], key="tx_filter_cat")
            cat_param = selected_cat_tuple[1]

        with col_f3:
            acc_options = [("Todas las cuentas", None)] + [(row['name'], row['id']) for _, row in df_accs.iterrows()]
            selected_acc_tuple = st.selectbox("Cuenta", acc_options, format_func=lambda x: x[0], key="tx_filter_acc")
            acc_param = selected_acc_tuple[1]

        df_tx = get_transactions(
            category_id=cat_param,
            account_id=acc_param,
            tx_type=tx_type_param,
            year=year_param,
            month=month_param,
            limit=1000
        )

        if not df_tx.empty:
            inc_total = df_tx[df_tx['type'] == 'income']['amount'].sum()
            exp_total = df_tx[df_tx['type'] == 'expense']['amount'].sum()
            net_total = inc_total - exp_total

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Movimientos encontrados", f"{len(df_tx)}")
            with col_m2:
                st.metric("Total Ingresos", f"+{format_currency(inc_total, currency_symbol)}")
            with col_m3:
                st.metric("Total Gastos", f"-{format_currency(exp_total, currency_symbol)}")
            with col_m4:
                st.metric("Balance Neto", format_currency(net_total, currency_symbol))

            st.write("---")
            
            # Formatear para visualización
            display_df = df_tx.copy()
            display_df['amount_formatted'] = display_df.apply(
                lambda r: f"{'+' if r['type'] == 'income' else '-'}{format_currency(r['amount'], currency_symbol)}",
                axis=1
            )
            display_df['category_display'] = display_df['category_icon'].fillna('') + ' ' + display_df['category_name'].fillna('Sin categoría')
            
            cols_to_show = ['id', 'date', 'type', 'category_display', 'description', 'account_name', 'amount_formatted']
            renamed_cols = {
                'id': 'ID',
                'date': 'Fecha',
                'type': 'Tipo',
                'category_display': 'Categoría',
                'description': 'Concepto',
                'account_name': 'Cuenta',
                'amount_formatted': 'Importe'
            }
            st.dataframe(display_df[cols_to_show].rename(columns=renamed_cols), use_container_width=True, hide_index=True)

            st.write("---")
            # Panel interactivo para Modificar o Eliminar Movimientos
            with st.expander("✏️ **Modificar o Eliminar un Movimiento Existente**", expanded=False):
                tx_edit_options = [
                    (
                        f"#{r['id']} | {r['date']} | {'+' if r['type']=='income' else '-'}{r['amount']:.2f} {currency_symbol} | {r['category_name'] or 'Sin cat'} | {r['description'] or ''}",
                        int(r['id'])
                    )
                    for _, r in df_tx.iterrows()
                ]
                selected_tx_tuple = st.selectbox(
                    "Selecciona el movimiento a modificar:",
                    tx_edit_options,
                    format_func=lambda x: x[0],
                    key="select_tx_to_edit"
                )

                if selected_tx_tuple:
                    tx_id_to_edit = selected_tx_tuple[1]
                    tx_data = get_transaction_by_id(tx_id_to_edit)

                    if tx_data:
                        col_e1, col_e2 = st.columns(2)
                        
                        # Parse date
                        try:
                            curr_dt = datetime.strptime(tx_data['date'], "%Y-%m-%d").date()
                        except Exception:
                            curr_dt = datetime.today().date()

                        with col_e1:
                            edit_tx_type = st.radio(
                                "Tipo",
                                ["income", "expense"],
                                index=0 if tx_data['type'] == 'income' else 1,
                                format_func=lambda x: "💰 Ingreso" if x == "income" else "💸 Gasto",
                                horizontal=True,
                                key=f"edit_type_{tx_id_to_edit}"
                            )
                            edit_date = st.date_input("Fecha", value=curr_dt, key=f"edit_date_{tx_id_to_edit}")
                            edit_amount = st.number_input(f"Importe ({currency_symbol})", value=float(tx_data['amount']), min_value=0.01, step=10.0, format="%.2f", key=f"edit_amt_{tx_id_to_edit}")
                        
                        with col_e2:
                            # Cuentas
                            acc_list = [(r['name'], int(r['id'])) for _, r in df_accs.iterrows()]
                            acc_idx = 0
                            for idx, a in enumerate(acc_list):
                                if a[1] == tx_data['account_id']:
                                    acc_idx = idx
                                    break
                            edit_acc = st.selectbox("Cuenta Bancaria", acc_list, index=acc_idx if acc_list else 0, format_func=lambda x: x[0], key=f"edit_acc_{tx_id_to_edit}") if acc_list else None

                            # Categorías según el tipo seleccionado
                            filtered_edit_cats = df_cats[df_cats['type'] == edit_tx_type] if not df_cats.empty else pd.DataFrame()
                            cat_list = [(f"{r['icon']} {r['name']}", int(r['id'])) for _, r in filtered_edit_cats.iterrows()]
                            cat_idx = 0
                            for idx, c in enumerate(cat_list):
                                if c[1] == tx_data['category_id']:
                                    cat_idx = idx
                                    break
                            edit_cat = st.selectbox("Categoría", cat_list, index=cat_idx if cat_list else 0, format_func=lambda x: x[0], key=f"edit_cat_{tx_id_to_edit}") if cat_list else None

                            edit_desc = st.text_input("Concepto / Descripción", value=tx_data['description'] or "", key=f"edit_desc_{tx_id_to_edit}")
                            edit_recurring = st.checkbox("Movimiento recurrente mensual", value=bool(tx_data['is_recurring']), key=f"edit_rec_{tx_id_to_edit}")

                        adjust_bal = st.checkbox("Ajustar automáticamente los saldos de cuenta afectados", value=True, key=f"edit_bal_check_{tx_id_to_edit}")

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("💾 Guardar Cambios del Movimiento", type="primary", use_container_width=True, key=f"btn_save_tx_{tx_id_to_edit}"):
                                if not edit_cat:
                                    st.error("Por favor, selecciona una categoría válida.")
                                else:
                                    update_transaction(
                                        transaction_id=tx_id_to_edit,
                                        account_id=edit_acc[1] if edit_acc else None,
                                        category_id=edit_cat[1],
                                        date=edit_date.strftime("%Y-%m-%d"),
                                        amount=edit_amount,
                                        description=edit_desc,
                                        tx_type=edit_tx_type,
                                        is_recurring=edit_recurring,
                                        adjust_balance=adjust_bal
                                    )
                                    st.success("¡Movimiento actualizado con éxito!")
                                    st.rerun()

                        with col_btn2:
                            if st.button("🗑️ Eliminar este Movimiento", type="secondary", use_container_width=True, key=f"btn_del_tx_{tx_id_to_edit}"):
                                delete_transaction(tx_id_to_edit, rollback_balance=adjust_bal)
                                st.success("Movimiento eliminado.")
                                st.rerun()

        else:
            st.info("No se encontraron movimientos con los filtros seleccionados.")

    # ----------------------------------------------------
    # TAB 2: REGISTRAR MOVIMIENTO MANUAL / TRASPASO
    # ----------------------------------------------------
    with tab_add:
        st.subheader("Nuevo Movimiento o Traspaso")
        
        # Selector de tipo interactivo
        tx_type = st.radio(
            "Selecciona la Operación a Realizar:",
            ["income", "expense", "transfer"],
            format_func=lambda x: {
                "income": "💰 Ingreso (Nómina, Rendimientos...)",
                "expense": "💸 Gasto (Supermercado, Alquiler, Ocio...)",
                "transfer": "🔄 Traspaso entre Cuentas (Nómina ➔ Inversión / Ahorro)"
            }.get(x, x),
            horizontal=True,
            key="add_tx_type_radio"
        )

        acc_choices = [(r['name'], r['id']) for _, r in df_accs.iterrows()]

        if tx_type == "transfer":
            st.info("💡 **Traspaso interno:** Restará saldo de la cuenta de origen (ej. Cuenta Nómina) y lo sumará a la cuenta de destino (ej. Fondos Indexados o Cuenta Remunerada), computando en el 20% de Ahorro/Inversión.")
            
            with st.form("form_add_transfer", clear_on_submit=True):
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    src_acc = st.selectbox("Cuenta de Origen (De donde sale el dinero)", acc_choices, format_func=lambda x: x[0], key="tr_src_acc") if acc_choices else None
                    dest_acc = st.selectbox("Cuenta de Destino (Hacia donde va el dinero)", acc_choices, format_func=lambda x: x[0], index=min(1, len(acc_choices)-1) if len(acc_choices) > 1 else 0, key="tr_dest_acc") if acc_choices else None
                    tr_amount = st.number_input(f"Importe del Traspaso ({currency_symbol})", min_value=0.01, step=50.0, format="%.2f")

                with col_t2:
                    tr_date = st.date_input("Fecha del Traspaso", value=datetime.today(), key="tr_date")
                    
                    # Categorías de ahorro / inversión recomendadas para traspasos
                    savings_cats = df_cats[df_cats['bucket_50_30_20'] == 'savings']
                    if savings_cats.empty:
                        savings_cats = df_cats[df_cats['type'] == 'expense']
                    cat_choices_tr = [(f"{r['icon']} {r['name']}", r['id']) for _, r in savings_cats.iterrows()]
                    
                    selected_cat_tr = st.selectbox(
                        "Categoría de Ahorro / Inversión (Regla 50/30/20)",
                        cat_choices_tr,
                        format_func=lambda x: x[0]
                    ) if cat_choices_tr else None
                    
                    tr_desc = st.text_input("Concepto / Descripción", value="Aportación periódica a inversión / ahorro")
                    tr_recurring = st.checkbox("¿Es un traspaso recurrente mensual automático?", value=True)

                submitted_tr = st.form_submit_button("🚀 Ejecutar Traspaso entre Cuentas", type="primary", use_container_width=True)
                if submitted_tr:
                    if not src_acc or not dest_acc:
                        st.error("Debes tener al menos dos cuentas creadas para hacer un traspaso.")
                    elif src_acc[1] == dest_acc[1]:
                        st.error("La cuenta de origen y destino deben ser distintas.")
                    else:
                        add_transfer(
                            source_account_id=src_acc[1],
                            dest_account_id=dest_acc[1],
                            amount=tr_amount,
                            date=tr_date.strftime("%Y-%m-%d"),
                            description=tr_desc,
                            category_id=selected_cat_tr[1] if selected_cat_tr else None,
                            is_recurring=tr_recurring
                        )
                        st.success(f"¡Traspaso de {format_currency(tr_amount, currency_symbol)} realizado con éxito de '{src_acc[0]}' a '{dest_acc[0]}'!")
                        st.rerun()

        else:
            filtered_cats = df_cats[df_cats['type'] == tx_type] if not df_cats.empty else pd.DataFrame()
            cat_choices = [(f"{r['icon']} {r['name']}", r['id']) for _, r in filtered_cats.iterrows()]

            with st.form("form_add_transaction", clear_on_submit=True):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    tx_date = st.date_input("Fecha", value=datetime.today())
                    tx_amount = st.number_input(f"Importe ({currency_symbol})", min_value=0.01, step=10.0, format="%.2f")
                    selected_acc = st.selectbox("Cuenta Bancaria / Destino u Origen", acc_choices, format_func=lambda x: x[0]) if acc_choices else None

                with col_a2:
                    selected_cat = st.selectbox(
                        f"Categoría de {'Ingreso' if tx_type == 'income' else 'Gasto'}",
                        cat_choices,
                        format_func=lambda x: x[0]
                    ) if cat_choices else None
                    
                    tx_desc = st.text_input(
                        "Concepto / Descripción",
                        placeholder="Ej: Nómina del mes, Compra supermercado, Dividendo..."
                    )
                    is_recurring = st.checkbox("¿Es un movimiento recurrente mensual? (ej. Nómina fija, Alquiler)", value=True if tx_type == 'income' else False)

                update_acc_bal = st.checkbox("Actualizar saldo de la cuenta seleccionada", value=True)

                submitted = st.form_submit_button("💾 Guardar Movimiento", type="primary", use_container_width=True)
                if submitted:
                    if not selected_cat:
                        st.error("Por favor, selecciona una categoría.")
                    else:
                        add_transaction(
                            account_id=selected_acc[1] if selected_acc else None,
                            category_id=selected_cat[1],
                            date=tx_date.strftime("%Y-%m-%d"),
                            amount=tx_amount,
                            description=tx_desc,
                            tx_type=tx_type,
                            is_recurring=is_recurring,
                            update_balance=update_acc_bal
                        )
                        st.success("¡Transacción registrada exitosamente!")
                        st.rerun()

    # ----------------------------------------------------
    # TAB 3: IMPORTAR CSV BANCARIO
    # ----------------------------------------------------
    with tab_import:
        st.subheader("📂 Carga masiva de extractos bancarios en CSV")
        st.write("Sube el archivo CSV descargado de tu entidad bancaria (BBVA, Santander, CaixaBank, Openbank, Revolut, Trade Republic, etc.).")
        
        uploaded_file = st.file_uploader("Seleccionar archivo CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                # Intentar leer con detección de separadores comunes (, o ;)
                sample = uploaded_file.read(2048).decode('utf-8', errors='ignore')
                uploaded_file.seek(0)
                sep = ';' if sample.count(';') > sample.count(',') else ','
                df_upload = pd.read_csv(uploaded_file, sep=sep)

                st.write("Vista previa del archivo (primeras 5 filas):")
                st.dataframe(df_upload.head(5), use_container_width=True)

                st.markdown("### Configuración de Columnas")
                col_i1, col_i2, col_i3 = st.columns(3)
                cols_available = df_upload.columns.tolist()

                with col_i1:
                    col_date = st.selectbox("Columna de Fecha", cols_available)
                with col_i2:
                    col_amount = st.selectbox("Columna de Importe", cols_available)
                with col_i3:
                    col_desc = st.selectbox("Columna de Concepto / Descripción", cols_available)

                col_i4, col_i5, col_i6 = st.columns(3)
                with col_i4:
                    dest_acc = st.selectbox("Asignar a Cuenta", [(r['name'], r['id']) for _, r in df_accs.iterrows()], format_func=lambda x: x[0], key="csv_dest_acc")
                with col_i5:
                    exp_cats = df_cats[df_cats['type'] == 'expense']
                    dest_cat = st.selectbox("Categoría por defecto para gastos (-)", [(f"{r['icon']} {r['name']}", r['id']) for _, r in exp_cats.iterrows()], format_func=lambda x: x[0], key="csv_dest_cat")
                with col_i6:
                    inc_cats = df_cats[df_cats['type'] == 'income']
                    dest_inc_cat = st.selectbox("Categoría por defecto para ingresos (+)", [(f"{r['icon']} {r['name']}", r['id']) for _, r in inc_cats.iterrows()], format_func=lambda x: x[0], key="csv_dest_inc_cat")

                if st.button("🚀 Procesar e Importar Transacciones", type="primary"):
                    imported = import_csv_transactions(
                        df=df_upload,
                        col_date=col_date,
                        col_amount=col_amount,
                        col_desc=col_desc,
                        default_account_id=dest_acc[1] if dest_acc else None,
                        default_category_id=dest_cat[1] if dest_cat else None,
                        default_income_category_id=dest_inc_cat[1] if dest_inc_cat else None
                    )
                    st.success(f"¡Se han importado {imported} movimientos con éxito!")
                    st.rerun()

            except Exception as e:
                st.error(f"Error al procesar el archivo CSV: {e}")

    # ----------------------------------------------------
    # TAB 4: CATEGORÍAS Y CUENTAS
    # ----------------------------------------------------
    with tab_cats_accs:
        col_c_left, col_c_right = st.columns(2)

        with col_c_left:
            st.subheader("🏦 Cuentas y Activos")
            
            acc_tab_choice = st.radio(
                "Gestión de Cuentas",
                ["➕ Añadir Nueva Cuenta", "✏️ Modificar Cuenta Existente"],
                horizontal=True,
                label_visibility="collapsed"
            )

            acc_type_map = {
                'checking': 'Cuenta Corriente',
                'savings': 'Cuenta Ahorro / Remunerada',
                'investment': 'Inversión (Fondos/Acciones)',
                'crypto': 'Criptomonedas',
                'real_estate': 'Bienes Inmuebles',
                'loan': 'Préstamo Personal',
                'mortgage': 'Hipoteca',
                'credit_card': 'Tarjeta de Crédito'
            }

            if acc_tab_choice == "➕ Añadir Nueva Cuenta":
                with st.form("form_add_acc", clear_on_submit=True):
                    acc_name = st.text_input("Nombre de la cuenta", placeholder="Ej: Cuenta Nómina BBVA, Fondos Indexados...")
                    acc_type = st.selectbox(
                        "Tipo de cuenta",
                        list(acc_type_map.keys()),
                        format_func=lambda x: acc_type_map.get(x, x)
                    )
                    acc_balance = st.number_input(f"Saldo inicial ({currency_symbol})", step=100.0, format="%.2f")
                    acc_interest = st.number_input("Interés anual (%)", min_value=0.0, max_value=100.0, step=0.1, help="Rendimiento anual en cuentas remuneradas o TAE en deudas")
                    is_asset = 0 if acc_type in ['loan', 'mortgage', 'credit_card'] else 1
                    
                    if st.form_submit_button("➕ Añadir Cuenta", type="primary"):
                        if acc_name.strip():
                            add_account(acc_name, acc_type, acc_balance, "EUR", is_asset, acc_interest)
                            st.success(f"Cuenta '{acc_name}' añadida con éxito.")
                            st.rerun()

            elif acc_tab_choice == "✏️ Modificar Cuenta Existente":
                df_all_accs = get_accounts()
                if not df_all_accs.empty:
                    acc_options = [(int(r['id']), r['name'], r['type'], float(r['interest_rate'] or 0.0), float(r['balance'])) for _, r in df_all_accs.iterrows()]
                    selected_acc = st.selectbox(
                        "Selecciona la cuenta a modificar",
                        acc_options,
                        format_func=lambda x: f"{x[1]} ({acc_type_map.get(x[2], x[2])}) — Saldo: {x[4]:.2f} {currency_symbol}"
                    )
                    if selected_acc:
                        acc_id_edit, curr_name, curr_type, curr_interest, curr_bal = selected_acc
                        type_keys = list(acc_type_map.keys())
                        default_idx = type_keys.index(curr_type) if curr_type in type_keys else 0

                        with st.form(key=f"form_edit_acc_{acc_id_edit}"):
                            edit_name = st.text_input("Nombre de la cuenta", value=curr_name)
                            edit_type = st.selectbox(
                                "Tipo de cuenta",
                                type_keys,
                                index=default_idx,
                                format_func=lambda x: acc_type_map.get(x, x)
                            )
                            edit_interest = st.number_input(
                                "Interés / Rendimiento anual (%)",
                                min_value=0.0,
                                max_value=100.0,
                                value=float(curr_interest),
                                step=0.1,
                                help="Rendimiento anual estimado o TAE en deudas"
                            )
                            
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                save_btn = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)
                            with col_b2:
                                del_acc_btn = st.form_submit_button("🗑️ Eliminar Cuenta", type="secondary", use_container_width=True)

                            if save_btn:
                                if edit_name.strip():
                                    update_account_details(acc_id_edit, edit_name, edit_type, edit_interest)
                                    st.success(f"Cuenta '{edit_name}' actualizada correctamente.")
                                    st.rerun()
                            if del_acc_btn:
                                delete_account(acc_id_edit)
                                st.success("Cuenta eliminada.")
                                st.rerun()
                else:
                    st.info("No hay cuentas creadas aún para modificar.")

        with col_c_right:
            st.subheader("🏷️ Categorías (Ingresos y Gastos)")
            
            cat_action = st.radio(
                "Categorías",
                ["📋 Ver Categorías", "➕ Nueva Categoría", "🗑️ Eliminar Categoría"],
                horizontal=True,
                label_visibility="collapsed"
            )

            if cat_action == "📋 Ver Categorías":
                st.write("**💰 Categorías de Ingreso:**")
                df_inc = df_cats[df_cats['type'] == 'income']
                if not df_inc.empty:
                    for _, r in df_inc.iterrows():
                        st.write(f"- {r['icon']} **{r['name']}**")
                
                st.write("---")
                st.write("**💸 Categorías de Gasto:**")
                df_exp = df_cats[df_cats['type'] == 'expense']
                if not df_exp.empty:
                    bucket_labels = {'needs': '🏠 Necesidades (50%)', 'wants': '🎉 Deseos (30%)', 'savings': '📈 Ahorro/Inversión (20%)'}
                    for _, r in df_exp.iterrows():
                        st.write(f"- {r['icon']} **{r['name']}** *({bucket_labels.get(r['bucket_50_30_20'], r['bucket_50_30_20'])})*")

            elif cat_action == "➕ Nueva Categoría":
                with st.form("form_add_cat", clear_on_submit=True):
                    cat_name = st.text_input("Nombre de la categoría", placeholder="Ej: Nómina Empresa X, Gimnasio, Mascotas...")
                    cat_type = st.selectbox("Tipo de Categoría", ["income", "expense"], format_func=lambda x: "💰 Ingreso" if x == "income" else "💸 Gasto")
                    cat_bucket = st.selectbox("Asignación Presupuesto", ["income", "needs", "wants", "savings"], format_func=lambda x: {
                        'income': '💰 Ingreso (Nómina, Rendimientos...)',
                        'needs': '🏠 Necesidades Básicas (50%)',
                        'wants': '🎉 Deseos y Ocio (30%)',
                        'savings': '📈 Ahorro e Inversión (20%)'
                    }.get(x, x))
                    cat_icon = st.text_input("Icono (Emoji)", value="💼" if cat_type == "income" else "📌")
                    
                    if st.form_submit_button("➕ Añadir Categoría", type="primary"):
                        if cat_name.strip():
                            add_category(cat_name, cat_type, cat_bucket, cat_icon)
                            st.success(f"Categoría '{cat_name}' añadida con éxito.")
                            st.rerun()

            elif cat_action == "🗑️ Eliminar Categoría":
                cat_del_options = [(f"{r['icon']} {r['name']} ({'Ingreso' if r['type']=='income' else 'Gasto'})", int(r['id'])) for _, r in df_cats.iterrows()]
                selected_cat_to_del = st.selectbox("Selecciona la categoría a eliminar", cat_del_options, format_func=lambda x: x[0])
                if st.button("🗑️ Eliminar Categoría seleccionada", type="secondary"):
                    ok = delete_category(selected_cat_to_del[1])
                    if ok:
                        st.success("Categoría eliminada.")
                        st.rerun()
                    else:
                        st.error("No se puede eliminar la categoría porque tiene movimientos asociados. Elimina o reasigna los movimientos primero.")

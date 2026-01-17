import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import google.generativeai as genai

# ==========================================
# 🔒 LOGIN & SETUP
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    if "APP_PASSWORD" not in st.secrets: return True

    st.text_input("🔒 Password", type="password", on_change=password_entered, key="password_input")
    return False

def password_entered():
    if st.session_state["password_input"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["password_input"]
    else: st.error("Password errata")

st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")
if not check_password(): st.stop()

# AI CONFIG
gemini_ok = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash')
        gemini_ok = True
except: pass

# ==========================================
# 🔗 GESTIONE DATABASE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet):
    try: return conn.read(worksheet=sheet, ttl=0)
    except: return pd.DataFrame()

def save_data(sheet, df):
    conn.update(worksheet=sheet, data=df)
    st.cache_data.clear()

def add_riga_diario(tipo, dati):
    df = get_data("diario")
    if df.empty: df = pd.DataFrame(columns=["data", "tipo", "dettaglio_json"])
    
    nuova = pd.DataFrame([{
        "data": datetime.datetime.now().strftime("%Y-%m-%d"),
        "tipo": tipo,
        "dettaglio_json": json.dumps(dati)
    }])
    save_data("diario", pd.concat([df, nuova], ignore_index=True))

def delete_riga(idx):
    df = get_data("diario")
    save_data("diario", df.drop(idx))

def get_oggi(): return datetime.datetime.now().strftime("%Y-%m-%d")

def get_foto_obiettivo():
    df = get_data("diario")
    if not df.empty:
        settings = df[df['tipo'] == 'settings']
        if not settings.empty:
            try:
                last = settings.iloc[-1]
                d = json.loads(last['dettaglio_json'])
                return d.get('url_foto', '')
            except: pass
    return ''

# ==========================================
# INTERFACCIA UTENTE
# ==========================================
st.title("💪 Fit Tracker AI")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Cibo & Integratori", "🏋️ Workout", "📏 Misure", "🤖 AI"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df = get_data("diario")
    oggi = get_oggi()
    
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    cal = pro = carb = fat = 0
    if not df_oggi.empty:
        for _, r in df_oggi.iterrows():
            if r['tipo'] == 'pasto':
                try:
                    d = json.loads(r['dettaglio_json'])
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
                except: pass

    ultimo_peso = "--"
    if not df.empty:
        df_misure = df[df['tipo'] == 'misure']
        if not df_misure.empty:
            try:
                last_row = df_misure.iloc[-1]
                d_mis = json.loads(last_row['dettaglio_json'])
                ultimo_peso = f"{d_mis['peso']} kg"
            except: pass

    col_metrics = st.columns(5)
    col_metrics[0].metric("🔥 Kcal Oggi", int(cal))
    col_metrics[1].metric("🥩 Proteine", f"{int(pro)}g")
    col_metrics[2].metric("🍚 Carbo", f"{int(carb)}g")
    col_metrics[3].metric("🥑 Grassi", f"{int(fat)}g")
    col_metrics[4].metric("⚖️ Peso", ultimo_peso, delta_color="off")

    st.markdown("---")

    col_left, col_center, col_right = st.columns([1.5, 1.5, 1])

    # COLONNA SINISTRA: DIARIO
    with col_left:
        st.subheader("📅 Oggi")
        
        st.info("🍎 **Alimentazione & Integratori**")
        if not df_oggi.empty:
            found_pasto = False
            for idx, r in df_oggi.iterrows():
                if r['tipo'] == 'pasto':
                    found_pasto = True
                    d = json.loads(r['dettaglio_json'])
                    
                    # Logica Visualizzazione Integratori vs Cibo
                    is_integ = d.get('pasto') == "Integrazione"
                    icona = "💊" if is_integ else "🍽️"
                    
                    # Recupera l'unità di misura salvata (se esiste), altrimenti 'g'
                    unita = d.get('unita', 'g') 
                    qta_display = d.get('gr', 0) # Per retrocompatibilità usiamo 'gr' come quantità generica
                    
                    # Formattazione stringa quantità (es. "2 cps" o "500 mg")
                    qta_str = f"{int(qta_display) if qta_display == int(qta_display) else qta_display} {unita}"

                    c1, c2 = st.columns([4,1])
                    c1.write(f"{icona} **{d['nome']}** ({qta_str}) | {int(d['cal'])} kcal")
                    if c2.button("🗑️", key=f"dash_del_{idx}"): 
                        delete_riga(idx)
                        st.toast("Eliminato!")
                        st.rerun()
            if not found_pasto: st.caption("Vuoto.")
        else: st.caption("Nessun dato.")

        st.write("") 
        st.success("🏋️ **Allenamenti**")
        if not df_oggi.empty:
            found_work = False
            for idx, r in df_oggi.iterrows():
                if r['tipo'] == 'allenamento':
                    found_work = True
                    d = json.loads(r['dettaglio_json'])
                    c1, c2 = st.columns([4,1])
                    c1.write(f"**{d.get('nome_sessione','Workout')}** ({d['durata']} min)")
                    if c2.button("🗑️", key=f"dash_del_w_{idx}"): 
                        delete_riga(idx)
                        st.toast("Eliminato!")
                        st.rerun()
            if not found_work: st.caption("Riposo.")
        else: st.caption("Nessun allenamento.")

    # COLONNA CENTRALE: GRAFICO
    with col_center:
        st.subheader("📉 Peso")
        if not df.empty:
            misure_list = []
            for _, r in df.iterrows():
                if r['tipo'] == 'misure':
                    try:
                        d = json.loads(r['dettaglio_json'])
                        misure_list.append({"Data": r['data'], "Peso (kg)": d['peso']})
                    except: pass
            if misure_list:
                st.line_chart(pd.DataFrame(misure_list).set_index("Data"), color="#0051FF")
            else: st.info("Manca il peso.")

    # COLONNA DESTRA: FOTO
    with col_right:
        st.subheader("🏆 Obiettivo")
        with st.container(border=True):
            saved_url = get_foto_obiettivo()
            if saved_url:
                try: st.image(saved_url, use_container_width=True)
                except: st.error("Errore foto.")

            with st.expander("Cambia"):
                t_link, t_up = st.tabs(["Link", "Upload"])
                with t_link:
                    url_foto = st.text_input("Link (.jpg/.png)")
                    if st.button("Salva"):
                        if url_foto:
                            add_riga_diario("settings", {"url_foto": url_foto})
                            st.rerun()
                with t_up:
                    up_file = st.file_uploader("File", type=['jpg','png'])
                    if up_file: st.image(up_file, width=150)

# --- TAB 2: CIBO & INTEGRATORI ---
with tab2:
    st.header("Diario Alimentare")
    c_in, c_db = st.columns([1,1])
    
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with c_in:
        st.subheader("🍽️ Inserimento")
        
        categorie_pasto = ["Colazione", "Pranzo", "Cena", "Spuntino", "Integrazione"]
        pasto = st.selectbox("Categoria", categorie_pasto)
        
        # === LOGICA DIFFERENZIATA ===
        if pasto == "Integrazione":
            st.markdown("##### 💊 Dettagli Integratore")
            
            # Scelta del tipo di formato
            tipo_int = st.radio("Formato", ["Polvere (g)", "Capsule/Pastiglie (pz)", "Micro-dosaggio (mg)"], horizontal=True)
            
            # Imposta l'unità di misura in base alla scelta
            if "Polvere" in tipo_int: unita = "g"
            elif "Capsule" in tipo_int: unita = "cps/pz"
            else: unita = "mg"
            
            col_i1, col_i2 = st.columns([2, 1])
            nome_int = col_i1.text_input("Nome Integratore", placeholder="es. Omega 3, Creatina...")
            qta_int = col_i2.number_input(f"Quantità ({unita})", min_value=0.0, step=1.0 if unita!="g" else 0.5)

            st.caption("Valori Nutrizionali (Opzionali per vitamine/minerali)")
            c1,c2,c3,c4 = st.columns(4)
            k = c1.number_input("Kcal Totali", 0.0)
            p = c2.number_input("Pro Totali", 0.0)
            c = c3.number_input("Carb Totali", 0.0)
            f = c4.number_input("Fat Totali", 0.0)
            
            if st.button("Aggiungi Integratore", type="primary"):
                if nome_int:
                    # Salviamo 'gr' come quantità generica, ma aggiungiamo 'unita' per la visualizzazione
                    add_riga_diario("pasto", {
                        "pasto": pasto, 
                        "nome": nome_int, 
                        "cal": k, "pro": p, "carb": c, "fat": f, 
                        "gr": qta_int, 
                        "unita": unita # Salviamo l'unità specifica
                    })
                    st.success("Integratore aggiunto!")
                    st.rerun()
                else:
                    st.error("Inserisci il nome!")

        else:
            # === LOGICA STANDARD PER CIBO ===
            sel_cibo = st.selectbox("Cerca Cibo", ["-- Manuale --"] + nomi_cibi)
            gr = st.number_input("Grammi", min_value=0.0, value=100.0, step=10.0)

            v_n, v_k, v_p, v_c, v_f = "", 0.0, 0.0, 0.0, 0.0
            if sel_cibo != "-- Manuale --" and not df_cibi.empty:
                row = df_cibi[df_cibi['nome'] == sel_cibo].iloc[0]
                f = gr/100
                v_n=row['nome']; v_k=row['kcal']*f; v_p=row['pro']*f; v_c=row['carb']*f; v_f=row['fat']*f

            with st.form("f_pasto"):
                st.caption(f"Valori per {gr}g")
                nome = st.text_input("Nome", v_n)
                c1,c2,c3,c4 = st.columns(4)
                k = c1.number_input("Kcal", value=float(v_k))
                p = c2.number_input("Pro", value=float(v_p))
                c = c3.number_input("Carb", value=float(v_c))
                fat = c4.number_input("Fat", value=float(v_f))
                
                if st.form_submit_button("Aggiungi Pasto"):
                    if nome:
                        add_riga_diario("pasto", {"pasto":pasto, "nome":nome, "cal":k, "pro":p, "carb":c, "fat":fat, "gr":gr, "unita": "g"})
                        st.success("Pasto aggiunto!")
                        st.rerun()
                    else: st.error("Nome mancante.")

    with c_db:
        st.subheader("💾 Nuovo Cibo DB (100g)")
        with st.form("f_new_cibo"):
            nn = st.text_input("Nome")
            kk = st.number_input("Kcal"); pp = st.number_input("Pro"); cc = st.number_input("Carb"); ff = st.number_input("Fat")
            if st.form_submit_button("Salva nel DB"):
                if nn: 
                    new = pd.DataFrame([{"nome":nn, "kcal":kk, "pro":pp, "carb":cc, "fat":ff}])
                    save_data("cibi", pd.concat([df_cibi, new], ignore_index=True))
                    st.success("Salvato!"); st.rerun()
    
    st.divider()
    st.subheader("Riepilogo Oggi")
    df = get_data("diario")
    df_oggi = df[df['data'] == get_oggi()] if not df.empty else pd.DataFrame()
    if not df_oggi.empty:
        for idx, r in df_oggi.iterrows():
            if r['tipo'] == 'pasto':
                try:
                    d = json.loads(r['dettaglio_json'])
                    cc1, cc2, cc3 = st.columns([1, 4, 1])
                    
                    # Icona e Unità nel riepilogo in basso
                    ico = "💊" if d.get('pasto') == "Integrazione" else "🍽️"
                    u_mis = d.get('unita', 'g')
                    qty = d.get('gr', 0)
                    qty_s = f"{int(qty) if qty==int(qty) else qty} {u_mis}"

                    cc1.write(f"{ico} **{d['pasto']}**")
                    cc2.write(f"{d['nome']} ({qty_s}) - {int(d['cal'])} kcal")
                    if cc3.button("🗑️", key=f"list_del_{idx}"): delete_riga(idx); st.rerun()
                except: pass

# --- TAB 3: WORKOUT ---
with tab3:
    st.header("🏋️ Registro Allenamenti")
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    col_setup, col_list = st.columns([1, 2])
    with col_setup:
        st.subheader("Impostazioni")
        nome_sessione = st.text_input("Nome Sessione", value="Workout")
        st.markdown("---")
        tipo_ex = st.radio("Tipo Attività", ["🏋️ Pesi", "🏃 Cardio"], horizontal=True)
        df_ex = get_data("esercizi")
        lista_ex = df_ex['nome'].tolist() if not df_ex.empty else []

        if tipo_ex == "🏋️ Pesi":
            ex_sel = st.selectbox("Esercizio", ["-- Nuovo/Manuale --"] + lista_ex)
            nome_ex = ex_sel if ex_sel != "-- Nuovo/Manuale --" else st.text_input("Nome")
            c1, c2, c3 = st.columns(3)
            serie = c1.number_input("Serie", 1, step=1)
            reps = c2.number_input("Reps", 1, step=1)
            kg = c3.number_input("Kg", 0.0, step=0.5)
            if st.button("➕ Aggiungi Pesi", type="primary"):
                if nome_ex: st.session_state['sess_w'].append({"type": "pesi", "nome": nome_ex, "serie": serie, "reps": reps, "kg": kg})
                else: st.error("Inserisci nome")
        else:
            nome_cardio = st.text_input("Attività", "Corsa")
            c1, c2, c3 = st.columns(3)
            km = c1.number_input("Km", 0.0, step=0.1)
            tempo = c2.number_input("Min", 0, step=1)
            kcal_burn = c3.number_input("Kcal", 0, step=10)
            if st.button("➕ Aggiungi Cardio", type="primary"):
                st.session_state['sess_w'].append({"type": "cardio", "nome": nome_cardio, "km": km, "tempo": tempo, "kcal": kcal_burn})
        
        st.markdown("---")
        with st.expander("📝 Crea Esercizio DB"):
            with st.form("new_ex_db"):
                n_new = st.text_input("Nome Esercizio")
                if st.form_submit_button("Salva"):
                    if n_new:
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":n_new}])], ignore_index=True))
                        st.success("OK"); st.rerun()

    with col_list:
        st.subheader(f"In corso: {nome_sessione}")
        if st.session_state['sess_w']:
            for i, item in enumerate(st.session_state['sess_w']):
                with st.container(border=True):
                    cols = st.columns([1, 4, 1])
                    cols[0].title("🏋️" if item['type']=="pesi" else "🏃")
                    with cols[1]:
                        st.write(f"**{item['nome']}**")
                        if item['type'] == "pesi": st.caption(f"{item['serie']}x{item['reps']} @ {item['kg']}kg")
                        else: st.caption(f"{item['km']}km in {item['tempo']}min")
                    if cols[2].button("❌", key=f"d_s_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
            
            durata_tot = st.number_input("Durata Tot (min)", 0, step=5)
            if st.button("💾 SALVA SESSIONE", type="primary", use_container_width=True):
                add_riga_diario("allenamento", {"nome_sessione": nome_sessione, "durata": durata_tot, "esercizi": st.session_state['sess_w']})
                st.session_state['sess_w'] = []; st.success("Salvato!"); st.rerun()

# --- TAB 4: MISURE ---
with tab4:
    st.header("📏 Misure Corporee")
    with st.form("misure_form"):
        col1, col2 = st.columns(2)
        peso = col1.number_input("Peso Corporeo (kg)", 0.0, step=0.1, format="%.1f")
        alt = col2.number_input("Altezza (cm)", 0, step=1)
        c1, c2, c3 = st.columns(3)
        collo = c1.number_input("Collo", 0.0); vita = c2.number_input("Vita", 0.0); fianchi = c3.number_input("Fianchi", 0.0)
        if st.form_submit_button("Salva Misure"):
            add_riga_diario("misure", {"peso":peso, "alt":alt, "collo":collo, "vita":vita, "fianchi":fianchi})
            st.success("Salvato!"); st.rerun()

# --- TAB 5: AI ---
with tab5:
    st.header("🤖 Coach")
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["txt"])
    if p := st.chat_input("Chiedi..."):
        st.session_state.chat.append({"role":"user", "txt":p})
        with st.chat_message("user"): st.markdown(p)
        resp = "Errore AI"
        if gemini_ok:
            try: resp = model.generate_content(f"Sei un PT. Rispondi a: {p}").text
            except Exception as e: resp = str(e)
        st.session_state.chat.append({"role":"assistant", "txt":resp})
        with st.chat_message("assistant"): st.markdown(resp)

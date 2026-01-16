import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import google.generativeai as genai

# ==========================================
# 🔒 SISTEMA DI LOGIN (PROTEZIONE)
# ==========================================
def check_password():
    """Ritorna True se l'utente ha inserito la password corretta."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True
    
    # Se non c'è password nei secrets, entra diretto (per sicurezza in sviluppo)
    if "APP_PASSWORD" not in st.secrets:
        return True

    st.text_input(
        "🔒 Inserisci la Password per accedere", 
        type="password", 
        on_change=password_entered, 
        key="password_input"
    )
    return False

def password_entered():
    """Controlla se la password inserita corrisponde a quella nei Secrets."""
    if st.session_state["password_input"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["password_input"]
    else:
        st.session_state["password_correct"] = False
        st.error("😕 Password errata")

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(page_title="Fit Tracker Cloud", page_icon="☁️", layout="wide")

# BLOCCO DELL'APP SE PASSWORD ERRATA
if not check_password():
    st.stop()

# ==========================================
# 🛑 CONFIGURAZIONE AI
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    gemini_ok = True
except:
    gemini_ok = False

# ==========================================
# 🔗 CONNESSIONE GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data_diario():
    try:
        return conn.read(worksheet="diario", ttl=0)
    except:
        return pd.DataFrame(columns=["data", "tipo", "dettaglio_json"])

def get_data_cibi():
    try:
        return conn.read(worksheet="cibi", ttl=0)
    except:
        return pd.DataFrame(columns=["nome", "kcal", "pro", "carb", "fat"])

def save_riga_diario(data_str, tipo, dettaglio_dict):
    df = get_data_diario()
    nuova_riga = pd.DataFrame([{
        "data": data_str,
        "tipo": tipo,
        "dettaglio_json": json.dumps(dettaglio_dict)
    }])
    df_aggiornato = pd.concat([df, nuova_riga], ignore_index=True)
    conn.update(worksheet="diario", data=df_aggiornato)

def save_nuovo_cibo(nome, k, p, c, f):
    df = get_data_cibi()
    if not df.empty and nome in df['nome'].values:
        st.warning("Cibo già presente!")
        return
    nuova_riga = pd.DataFrame([{ "nome": nome, "kcal": k, "pro": p, "carb": c, "fat": f }])
    df_aggiornato = pd.concat([df, nuova_riga], ignore_index=True)
    conn.update(worksheet="cibi", data=df_aggiornato)

def delete_riga(indice_da_eliminare):
    df = get_data_diario()
    df_aggiornato = df.drop(indice_da_eliminare)
    conn.update(worksheet="diario", data=df_aggiornato)

def get_oggi(): return datetime.datetime.now().strftime("%Y-%m-%d")

# ==========================================
# INTERFACCIA WEB
# ==========================================
st.title("☁️ Fit Tracker - Google Sheets Edition")
st.caption(f"Database: Google Sheets | Data: {get_oggi()}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "💪 Allenamento", "🤖 AI Coach"])

# --- TAB DASHBOARD ---
with tab1:
    st.header("Riepilogo di Oggi")
    df_diario = get_data_diario()
    oggi = get_oggi()
    
    cal = pro = carb = fat = 0
    
    if not df_diario.empty:
        df_oggi = df_diario[df_diario['data'] == oggi]
        # Calcolo Totali
        for index, row in df_oggi.iterrows():
            try:
                dettagli = json.loads(row['dettaglio_json'])
                if row['tipo'] == 'pasto':
                    cal += dettagli['cal']; pro += dettagli['pro']; carb += dettagli['carb']; fat += dettagli['fat']
            except: pass
    else:
        df_oggi = pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kcal", int(cal)); c2.metric("Pro", int(pro)); c3.metric("Carb", int(carb)); c4.metric("Fat", int(fat))
    
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🍎 Pasti Mangiati")
        if not df_oggi.empty:
            for index, row in df_oggi.iterrows():
                if row['tipo'] == 'pasto':
                    dett = json.loads(row['dettaglio_json'])
                    c_txt, c_btn = st.columns([4, 1])
                    with c_txt:
                        st.text(f"🍽️ {dett['pasto']}: {dett['nome']} ({int(dett['cal'])} kcal - {dett.get('grammi','?')}g)")
                    with c_btn:
                        if st.button("🗑️", key=f"del_p_{index}"):
                            delete_riga(index)
                            st.toast("Cancellato!"); st.rerun()

    with col_b:
        st.subheader("💪 Allenamenti Fatti")
        if not df_oggi.empty:
            for index, row in df_oggi.iterrows():
                if row['tipo'] == 'allenamento':
                    dett = json.loads(row['dettaglio_json'])
                    c_txt, c_btn = st.columns([4, 1])
                    with c_txt:
                        st.info(f"Sessione: {dett['durata']} min")
                        for ex in dett['esercizi']: st.caption(f"- {ex['nome']}")
                    with c_btn:
                        if st.button("🗑️", key=f"del_w_{index}"):
                            delete_riga(index)
                            st.toast("Eliminato!"); st.rerun()

# --- TAB ALIMENTAZIONE ---
with tab2:
    st.header("Registra Cibo")
    c_in, c_db = st.columns([1, 1])
    df_cibi = get_data_cibi()
    lista_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with c_in:
        st.subheader("Calcolatore")
        pasto = st.selectbox("Pasto", ["Colazione", "Pranzo", "Cena", "Spuntino"])
        scelta_db = st.selectbox("🔍 Cerca nel DB (100g)", ["-- Manuale --"] + lista_cibi)
        grammi = st.number_input("⚖️ Grammi consumati", min_value=1.0, value=100.0, step=10.0)

        calc_nome, calc_k, calc_p, calc_c, calc_f = "", 0.0, 0.0, 0.0, 0.0
        if scelta_db != "-- Manuale --" and not df_cibi.empty:
            riga = df_cibi[df_cibi['nome'] == scelta_db].iloc[0]
            factor = grammi / 100.0
            calc_nome = riga['nome']
            calc_k = float(riga['kcal']) * factor; calc_p = float(riga['pro']) * factor
            calc_c = float(riga['carb']) * factor; calc_f = float(riga['fat']) * factor

        with st.form("add_food"):
            st.caption(f"Valori per {grammi}g")
            nome = st.text_input("Nome", value=calc_nome)
            c1, c2, c3, c4 = st.columns(4)
            k = c1.number_input("Kcal", value=calc_k); p = c2.number_input("Pro", value=calc_p)
            c = c3.number_input("Carb", value=calc_c); f = c4.number_input("Fat", value=calc_f)
            
            if st.form_submit_button("🍽️ Mangia!"):
                dati_pasto = {"pasto": pasto, "nome": nome, "cal": k, "pro": p, "carb": c, "fat": f, "grammi": grammi}
                save_riga_diario(get_oggi(), "pasto", dati_pasto)
                st.success("Salvato!"); st.rerun()

    with c_db:
        st.subheader("💾 Nuovo Cibo DB (100g)")
        with st.form("new_db"):
            n_n = st.text_input("Nome"); c1, c2 = st.columns(2)
            n_k = c1.number_input("Kcal (100g)"); n_p = c2.number_input("Pro (100g)")
            n_c = c1.number_input("Carb (100g)"); n_f = c2.number_input("Fat (100g)")
            if st.form_submit_button("Salva DB"):
                if n_n: save_nuovo_cibo(n_n, n_k, n_p, n_c, n_f); st.success("Salvato!"); st.rerun()

# --- TAB ALLENAMENTO ---
with tab3:
    st.header("Workout")
    if 'temp_w' not in st.session_state: st.session_state['temp_w'] = []
    c1, c2, c3 = st.columns(3)
    nom_ex = c1.text_input("Esercizio"); det_ex = c2.text_input("Dettagli")
    if c3.button("Aggiungi Ex"):
        st.session_state['temp_w'].append({"nome": nom_ex, "dett": det_ex})
    
    for i, e in enumerate(st.session_state['temp_w']): st.text(f"{i+1}. {e['nome']} ({e['dett']})")
    
    durata = st.number_input("Durata (min)", min_value=0)
    if st.button("💾 SALVA WORKOUT", type="primary"):
        if st.session_state['temp_w']:
            save_riga_diario(get_oggi(), "allenamento", {"durata": durata, "esercizi": st.session_state['temp_w']})
            st.session_state['temp_w'] = []; st.success("Allenamento salvato!"); st.rerun()

# --- TAB AI ---
with tab4:
    st.header("🤖 AI Coach")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Chiedi al coach..."):
        with st.chat_message("user"): st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        if gemini_ok:
            try:
                res = model.generate_content(f"Sei un personal trainer. Rispondi a: {prompt}")
                reply = res.text
            except Exception as e: reply = f"Errore: {e}"
        else: reply = "Errore: Chiave API non trovata."
        
        with st.chat_message("assistant"): st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

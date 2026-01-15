import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import google.generativeai as genai

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(page_title="Fit Tracker Cloud", page_icon="☁️", layout="wide")

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
# Crea la connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data_diario():
    # Legge il foglio 'diario'. Se vuoto, ritorna DataFrame vuoto
    try:
        return conn.read(worksheet="diario", ttl=0) # ttl=0 non usa cache (dati freschi)
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
        "dettaglio_json": json.dumps(dettaglio_dict) # Convertiamo il dict in testo
    }])
    df_aggiornato = pd.concat([df, nuova_riga], ignore_index=True)
    conn.update(worksheet="diario", data=df_aggiornato)

def save_nuovo_cibo(nome, k, p, c, f):
    df = get_data_cibi()
    # Controlla se esiste già
    if nome in df['nome'].values:
        st.warning("Cibo già presente!")
        return
    
    nuova_riga = pd.DataFrame([{ "nome": nome, "kcal": k, "pro": p, "carb": c, "fat": f }])
    df_aggiornato = pd.concat([df, nuova_riga], ignore_index=True)
    conn.update(worksheet="cibi", data=df_aggiornato)

def get_oggi(): return datetime.datetime.now().strftime("%Y-%m-%d")

# ==========================================
# INTERFACCIA WEB
# ==========================================
st.title("☁️ Fit Tracker - Google Sheets Edition")
st.caption(f"Database collegato: Google Sheets (FitTrackerDB) | Data: {get_oggi()}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "💪 Allenamento", "🤖 AI Coach"])

# --- TAB DASHBOARD ---
with tab1:
    st.header("Riepilogo di Oggi")
    
    # Scarica i dati freschi
    df_diario = get_data_diario()
    
    # Filtra solo le righe di oggi
    oggi = get_oggi()
    if not df_diario.empty:
        df_oggi = df_diario[df_diario['data'] == oggi]
    else:
        df_oggi = pd.DataFrame()

    cal = pro = carb = fat = 0
    list_pasti = []
    list_allenamenti = []

    if not df_oggi.empty:
        for index, row in df_oggi.iterrows():
            dettagli = json.loads(row['dettaglio_json']) # Riconverte testo in dict
            
            if row['tipo'] == 'pasto':
                cal += dettagli['cal']; pro += dettagli['pro']; carb += dettagli['carb']; fat += dettagli['fat']
                list_pasti.append(dettagli)
            elif row['tipo'] == 'allenamento':
                list_allenamenti.append(dettagli)

    # Metriche
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kcal", int(cal)); c2.metric("Pro", int(pro)); c3.metric("Carb", int(carb)); c4.metric("Fat", int(fat))
    
    st.divider()
    ca, cb = st.columns(2)
    with ca:
        st.subheader("Pasti Mangiati")
        for p in list_pasti: st.text(f"🍽️ {p['pasto']}: {p['nome']} ({int(p['cal'])} kcal)")
    with cb:
        st.subheader("Allenamenti Fatti")
        for a in list_allenamenti: 
            st.info(f"Durata: {a['durata']} min")
            for ex in a['esercizi']: st.text(f"- {ex['nome']}")

# --- TAB ALIMENTAZIONE ---
with tab2:
    st.header("Registra Cibo")
    c_in, c_db = st.columns([1, 1])
    
    # Carica DB Cibi per il menu a tendina
    df_cibi = get_data_cibi()
    lista_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with c_in:
        with st.form("add_food"):
            pasto = st.selectbox("Pasto", ["Colazione", "Pranzo", "Cena", "Spuntino"])
            
            # Selezione da DB o manuale
            scelta_db = st.selectbox("Cerca nel DB (o lascia vuoto)", [""] + lista_cibi)
            
            # Valori di default se scelgo da DB
            def_n=""; def_k=0.0; def_p=0.0; def_c=0.0; def_f=0.0
            if scelta_db:
                riga = df_cibi[df_cibi['nome'] == scelta_db].iloc[0]
                def_n = riga['nome']; def_k = riga['kcal']; def_p = riga['pro']; def_c = riga['carb']; def_f = riga['fat']

            nome = st.text_input("Nome", value=def_n)
            k = st.number_input("Kcal", value=float(def_k))
            p = st.number_input("Pro", value=float(def_p))
            c = st.number_input("Carb", value=float(def_c))
            f = st.number_input("Fat", value=float(def_f))
            
            if st.form_submit_button("Mangia!"):
                dati_pasto = {"pasto": pasto, "nome": nome, "cal": k, "pro": p, "carb": c, "fat": f}
                save_riga_diario(get_oggi(), "pasto", dati_pasto)
                st.success("Salvato su Google Sheets!")
                st.rerun()

    with c_db:
        st.subheader("Aggiungi Nuovo al DB")
        with st.form("new_db_food"):
            n_n = st.text_input("Nome Nuovo Cibo")
            n_k = st.number_input("Kcal")
            n_p = st.number_input("Pro")
            n_c = st.number_input("Carb")
            n_f = st.number_input("Fat")
            if st.form_submit_button("Salva nel DB"):
                save_nuovo_cibo(n_n, n_k, n_p, n_c, n_f)
                st.success("Cibo aggiunto al database!")
                st.rerun()

# --- TAB ALLENAMENTO ---
with tab3:
    st.header("Workout")
    if 'temp_w' not in st.session_state: st.session_state['temp_w'] = []

    c1, c2, c3 = st.columns(3)
    nom_ex = c1.text_input("Esercizio")
    det_ex = c2.text_input("Dettagli (es. 3x10 50kg)")
    if c3.button("Aggiungi Ex"):
        st.session_state['temp_w'].append({"nome": nom_ex, "dett": det_ex})
    
    st.write("### Lista Corrente:")
    for i, e in enumerate(st.session_state['temp_w']): st.text(f"{i+1}. {e['nome']} - {e['dett']}")
    
    durata = st.number_input("Durata Totale (min)", min_value=0)
    if st.button("💾 SALVA SU CLOUD", type="primary"):
        if st.session_state['temp_w']:
            dati_w = {"durata": durata, "esercizi": st.session_state['temp_w']}
            save_riga_diario(get_oggi(), "allenamento", dati_w)
            st.session_state['temp_w'] = []
            st.success("Allenamento salvato per sempre!")
            st.rerun()

# --- TAB AI ---
with tab4:
    st.header("🤖 AI Coach")
    prompt = st.chat_input("Chiedi al coach...")
    if prompt:
        with st.chat_message("user"): st.write(prompt)
        if gemini_ok:
            try:
                res = model.generate_content(f"Sei un coach sportivo. Rispondi brevemente a: {prompt}")
                with st.chat_message("assistant"): st.write(res.text)
            except Exception as e: st.error(f"Errore: {e}")
        else: st.error("Manca API Key")

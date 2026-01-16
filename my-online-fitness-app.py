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
# 🔒 SISTEMA DI LOGIN (PROTEZIONE)
# ==========================================
def check_password():
    """Ritorna True se l'utente ha inserito la password corretta."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
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
        del st.session_state["password_input"]  # Pulisce il campo per sicurezza
    else:
        st.session_state["password_correct"] = False
        st.error("😕 Password errata")

# BLOCCO DELL'APP: Se la password non è corretta, l'app si ferma qui.
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

def delete_riga(indice_da_eliminare):
    # 1. Scarica tutto il diario
    df = get_data_diario()
    
    # 2. Elimina la riga che ha quell'indice specifico
    # (drop elimina la riga mantenendo intatti gli altri dati)
    df_aggiornato = df.drop(indice_da_eliminare)
    
    # 3. Ricarica il foglio pulito su Google Sheets
    conn.update(worksheet="diario", data=df_aggiornato)

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
    
    cal = pro = carb = fat = 0
    
    # Se il diario non è vuoto, calcoliamo i totali
    if not df_diario.empty:
        # Filtriamo per data
        df_oggi = df_diario[df_diario['data'] == oggi]
        
        # Calcolo Totali (Loop veloce)
        for index, row in df_oggi.iterrows():
            try:
                dettagli = json.loads(row['dettaglio_json'])
                if row['tipo'] == 'pasto':
                    cal += dettagli['cal']; pro += dettagli['pro']; carb += dettagli['carb']; fat += dettagli['fat']
            except:
                pass
    else:
        df_oggi = pd.DataFrame()

    # Metriche in alto
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kcal", int(cal)); c2.metric("Pro", int(pro)); c3.metric("Carb", int(carb)); c4.metric("Fat", int(fat))
    
    st.divider()
    
    # --- LISTA INTERATTIVA CON TASTO ELIMINA ---
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🍎 Pasti Mangiati")
        if not df_oggi.empty:
            # Iteriamo sulle righe per mostrare i bottoni
            for index, row in df_oggi.iterrows():
                if row['tipo'] == 'pasto':
                    dett = json.loads(row['dettaglio_json'])
                    
                    # Creiamo due colonne: una per il testo, una per il bottone
                    c_txt, c_btn = st.columns([4, 1])
                    
                    with c_txt:
                        st.text(f"🍽️ {dett['pasto']}: {dett['nome']} ({int(dett['cal'])} kcal)")
                    
                    with c_btn:
                        # Il "key" deve essere unico per ogni bottone, usiamo l'index della riga
                        if st.button("🗑️", key=f"del_p_{index}"):
                            delete_riga(index)
                            st.toast(f"Cancellato: {dett['nome']}")
                            st.rerun() # Ricarica la pagina subito

    with col_b:
        st.subheader("💪 Allenamenti Fatti")
        if not df_oggi.empty:
            for index, row in df_oggi.iterrows():
                if row['tipo'] == 'allenamento':
                    dett = json.loads(row['dettaglio_json'])
                    
                    c_txt, c_btn = st.columns([4, 1])
                    with c_txt:
                        st.info(f"Sessione: {dett['durata']} min")
                        for ex in dett['esercizi']:
                            st.caption(f"- {ex['nome']}")
                    
                    with c_btn:
                        if st.button("🗑️", key=f"del_w_{index}"):
                            delete_riga(index)
                            st.toast("Allenamento eliminato")
                            st.rerun()

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
        st.subheader("Calcolatore & Diario")
        
        # 1. SELEZIONE E INPUT GRAMMI (Fuori dal form per aggiornare in tempo reale)
        pasto = st.selectbox("Pasto", ["Colazione", "Pranzo", "Cena", "Spuntino"])
        scelta_db = st.selectbox("🔍 Cerca nel DB (100g)", ["-- Manuale --"] + lista_cibi)
        grammi = st.number_input("⚖️ Grammi consumati", min_value=1.0, value=100.0, step=10.0)

        # 2. LOGICA DI CALCOLO (Valori iniziali)
        # Valori di default (manuali)
        calc_nome = ""
        calc_k = 0.0
        calc_p = 0.0
        calc_c = 0.0
        calc_f = 0.0

        # Se abbiamo selezionato un cibo, ricalcoliamo i valori in base ai grammi
        if scelta_db != "-- Manuale --" and not df_cibi.empty:
            # Trova la riga nel DB
            riga = df_cibi[df_cibi['nome'] == scelta_db].iloc[0]
            
            # Calcolo proporzione: (Valore100g * GrammiMangiati) / 100
            factor = grammi / 100.0
            
            calc_nome = riga['nome']
            calc_k = float(riga['kcal']) * factor
            calc_p = float(riga['pro']) * factor
            calc_c = float(riga['carb']) * factor
            calc_f = float(riga['fat']) * factor

        # 3. FORM DI INVIO (Con i valori calcolati pre-compilati)
        with st.form("add_food"):
            st.caption(f"Valori calcolati per {grammi}g di prodotto")
            
            # Usiamo 'value' per pre-compilare. 
            # Nota: Streamlit aggiornerà questi campi quando 'scelta_db' o 'grammi' cambiano.
            nome = st.text_input("Nome", value=calc_nome)
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            k = col_m1.number_input("Kcal", value=calc_k, step=1.0)
            p = col_m2.number_input("Pro", value=calc_p, step=0.1)
            c = col_m3.number_input("Carb", value=calc_c, step=0.1)
            f = col_m4.number_input("Fat", value=calc_f, step=0.1)
            
            if st.form_submit_button("🍽️ Aggiungi al Diario"):
                dati_pasto = {"pasto": pasto, "nome": nome, "cal": k, "pro": p, "carb": c, "fat": f, "grammi": grammi}
                save_riga_diario(get_oggi(), "pasto", dati_pasto)
                st.success(f"Aggiunto: {nome} ({k:.0f} kcal)")
                st.rerun()

    with c_db:
        st.subheader("💾 Aggiungi al Database (su 100g)")
        st.info("Qui inserisci i valori nutrizionali per **100g** di prodotto (come leggi sull'etichetta).")
        
        with st.form("new_db_food"):
            n_n = st.text_input("Nome Nuovo Cibo")
            c1, c2 = st.columns(2)
            n_k = c1.number_input("Kcal (per 100g)", step=1.0)
            n_p = c2.number_input("Pro (per 100g)", step=0.1)
            n_c = c1.number_input("Carb (per 100g)", step=0.1)
            n_f = c2.number_input("Fat (per 100g)", step=0.1)
            
            if st.form_submit_button("Salva nel DB"):
                if n_n:
                    save_nuovo_cibo(n_n, n_k, n_p, n_c, n_f)
                    st.success(f"{n_n} aggiunto al database!")
                    st.rerun()
                else:
                    st.error("Inserisci un nome.")

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

import streamlit as st
import json
import os
import datetime
import google.generativeai as genai

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(page_title="Fit Tracker AI", page_icon="💪", layout="wide")

# ==========================================
# 🛑 CONFIGURAZIONE AI
# ==========================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]  # <--- RIMETTI LA TUA CHIAVE

# Configura Gemini se la chiave è presente
if "INCOLLA_QUI" not in GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        gemini_ok = True
    except:
        gemini_ok = False
else:
    gemini_ok = False

# ==========================================
# 1. BACKEND (Adattato per Streamlit)
# ==========================================
DB_FILE = 'diario_fitness.json'
FOOD_DB_FILE = 'database_cibi.json'

def load_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_data(data, filepath):
    with open(filepath, 'w') as f: json.dump(data, f, indent=4)

# Carichiamo i dati all'avvio
if 'dati' not in st.session_state:
    st.session_state['dati'] = load_data(DB_FILE)
if 'db_cibi' not in st.session_state:
    st.session_state['db_cibi'] = load_data(FOOD_DB_FILE)

def get_oggi(): return datetime.datetime.now().strftime("%Y-%m-%d")

def init_giorno(data_str):
    if data_str not in st.session_state['dati']:
        st.session_state['dati'][data_str] = {
            "pasti": {p: [] for p in ["Colazione", "Pranzo", "Cena", "Spuntino"]},
            "allenamenti": [],
            "misure": None
        }

# ==========================================
# 2. INTERFACCIA WEB
# ==========================================

st.title("💪 Fit Tracker Pro - AI Web Edition")
st.markdown(f"**Data:** {get_oggi()}")

# Creiamo le schede (Tabs) come nella versione desktop
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "💪 Allenamento", "🤖 AI Coach"])

# --- TAB DASHBOARD ---
with tab1:
    st.header("Riepilogo Giornaliero")
    oggi = get_oggi()
    init_giorno(oggi)
    dati_oggi = st.session_state['dati'][oggi]

    # Calcoli
    cal = pro = carb = fat = 0
    for pasto, cibi in dati_oggi["pasti"].items():
        for c in cibi:
            cal += c['cal']; pro += c['pro']; carb += c['carb']; fat += c['fat']

    # Metriche in alto
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Kcal", int(cal))
    col2.metric("Proteine", f"{int(pro)}g")
    col3.metric("Carbo", f"{int(carb)}g")
    col4.metric("Grassi", f"{int(fat)}g")

    st.divider()
    
    # Diario
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🍎 Pasti")
        for pasto, cibi in dati_oggi["pasti"].items():
            if cibi:
                st.markdown(f"**{pasto}**")
                for c in cibi:
                    st.text(f"- {c['nome']} ({c['cal']} kcal)")
    
    with col_b:
        st.subheader("💪 Allenamenti")
        if dati_oggi["allenamenti"]:
            for a in dati_oggi["allenamenti"]:
                st.info(f"Sessione: {a['durata']} min")
                for ex in a['esercizi']:
                    if ex['type'] == 'pesi':
                        st.text(f"🏋️ {ex['nome']}: {ex['serie']}x{ex['reps']} {ex['peso']}kg")
                    else:
                        st.text(f"🏃 {ex['nome']}: {ex['km']}km in {ex['tempo']}min")
        else:
            st.write("Nessun allenamento oggi.")

# --- TAB ALIMENTAZIONE ---
with tab2:
    st.header("Registra Cibo")
    
    col_input, col_db = st.columns([2, 1])
    
    with col_input:
        with st.form("form_cibo"):
            pasto = st.selectbox("Pasto", ["Colazione", "Pranzo", "Cena", "Spuntino"])
            nome = st.text_input("Nome Cibo")
            c1, c2, c3, c4 = st.columns(4)
            kcal = c1.number_input("Kcal", min_value=0.0)
            prot = c2.number_input("Pro", min_value=0.0)
            carbo = c3.number_input("Carb", min_value=0.0)
            grassi = c4.number_input("Fat", min_value=0.0)
            
            submitted = st.form_submit_button("Aggiungi al Diario")
            if submitted and nome:
                init_giorno(oggi)
                st.session_state['dati'][oggi]["pasti"][pasto].append({
                    "nome": nome, "cal": kcal, "pro": prot, "carb": carbo, "fat": grassi
                })
                save_data(st.session_state['dati'], DB_FILE)
                st.success(f"{nome} aggiunto!")
                st.rerun() # Ricarica pagina per aggiornare dashboard

    with col_db:
        st.subheader("Database")
        # Menu a tendina per caricare dati
        cibi_salvati = list(st.session_state['db_cibi'].keys())
        scelta = st.selectbox("Scegli cibo salvato", ["-- Seleziona --"] + cibi_salvati)
        if scelta != "-- Seleziona --":
            info = st.session_state['db_cibi'][scelta]
            st.info(f"Dati per {scelta}:\nKcal: {info['cal']} | P: {info['pro']} | C: {info['carb']} | F: {info['fat']}")
            st.caption("Copia questi valori nel form a sinistra se vuoi aggiungerlo.")

        # Salva nuovo cibo
        if st.button("Salva cibo attuale nel DB"):
             if nome:
                 st.session_state['db_cibi'][nome] = {"cal": kcal, "pro": prot, "carb": carbo, "fat": grassi}
                 save_data(st.session_state['db_cibi'], FOOD_DB_FILE)
                 st.success("Salvato nel Database!")
                 st.rerun()

# --- TAB ALLENAMENTO ---
with tab3:
    st.header("Workout Session")
    
    # Usiamo la session_state per tenere la lista temporanea
    if 'temp_workout' not in st.session_state:
        st.session_state['temp_workout'] = []

    type_ex = st.radio("Tipo", ["Pesi", "Cardio"], horizontal=True)
    
    c1, c2, c3, c4 = st.columns(4)
    if type_ex == "Pesi":
        nome_ex = c1.text_input("Esercizio")
        serie = c2.number_input("Serie", min_value=1, step=1)
        reps = c3.number_input("Reps", min_value=1, step=1)
        peso = c4.number_input("Kg", min_value=0.0, step=0.5)
        if st.button("Aggiungi Esercizio"):
            st.session_state['temp_workout'].append({"type": "pesi", "nome": nome_ex, "serie": serie, "reps": reps, "peso": peso})
            st.success("Aggiunto!")
            
    else:
        nome_cardio = c1.text_input("Attività")
        km = c2.number_input("Km", min_value=0.0)
        tempo = c3.number_input("Minuti", min_value=0.0)
        if st.button("Aggiungi Cardio"):
            st.session_state['temp_workout'].append({"type": "cardio", "nome": nome_cardio, "km": km, "tempo": tempo})
            st.success("Aggiunto!")

    st.divider()
    st.subheader("Lista Corrente")
    for i, ex in enumerate(st.session_state['temp_workout']):
        st.text(f"{i+1}. {ex}")

    durata_tot = st.number_input("Durata Totale (min)", min_value=0)
    if st.button("💾 SALVA ALLENAMENTO COMPLETO", type="primary"):
        if st.session_state['temp_workout']:
            init_giorno(oggi)
            st.session_state['dati'][oggi]["allenamenti"].append({
                "durata": durata_tot,
                "esercizi": st.session_state['temp_workout']
            })
            save_data(st.session_state['dati'], DB_FILE)
            st.session_state['temp_workout'] = [] # Reset
            st.success("Allenamento salvato!")
            st.rerun()

# --- TAB AI COACH ---
with tab4:
    st.header("🤖 AI Coach (Gemini)")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mostra chat passata
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input utente
    if prompt := st.chat_input("Chiedi al coach (es. calorie pizza, scheda massa...)"):
        # Mostra messaggio utente
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Risposta AI
        if gemini_ok:
            try:
                full_prompt = f"Sei un personal trainer esperto. Rispondi brevemente. Domanda: {prompt}"
                response = model.generate_content(full_prompt)
                reply = response.text
            except Exception as e:
                reply = f"Errore AI: {e}"
        else:
            reply = "Chiave API mancante. Inseriscila nel codice."

        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

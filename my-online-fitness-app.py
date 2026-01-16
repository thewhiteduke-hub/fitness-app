import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import google.generativeai as genai

# ==========================================
# 🔒 LOGIN
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

# ==========================================
# CONFIGURAZIONE
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")
if not check_password(): st.stop()

# AI CONFIG
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    gemini_ok = True
except: gemini_ok = False

# ==========================================
# 🔗 DATABASE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet):
    try: return conn.read(worksheet=sheet, ttl=0)
    except: return pd.DataFrame()

def save_data(sheet, df):
    conn.update(worksheet=sheet, data=df)

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

# ==========================================
# UI & TAB
# ==========================================
st.title("💪 Fit Tracker AI")
st.caption(f"📅 Data: {get_oggi()}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Cibo", "🏋️ Workout", "📏 Misure", "🤖 AI"])

# --- DASHBOARD ---
with tab1:
    st.header("Il tuo andamento")
    df = get_data("diario")
    oggi = get_oggi()
    
    # 1. Calcolo Calorie Oggi
    cal = pro = carb = fat = 0
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    if not df_oggi.empty:
        for _, r in df_oggi.iterrows():
            try:
                d = json.loads(r['dettaglio_json'])
                if r['tipo'] == 'pasto':
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
            except: pass

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Kcal", int(cal), delta_color="normal")
    col2.metric("Pro", f"{int(pro)}g")
    col3.metric("Carb", f"{int(carb)}g")
    col4.metric("Fat", f"{int(fat)}g")

    st.divider()

    # 2. Grafico Peso
    st.subheader("📉 Andamento Peso")
    if not df.empty:
        misure_list = []
        for _, r in df.iterrows():
            if r['tipo'] == 'misure':
                try:
                    d = json.loads(r['dettaglio_json'])
                    misure_list.append({"data": r['data'], "peso": d['peso']})
                except: pass
        
        if misure_list:
            chart_data = pd.DataFrame(misure_list).set_index("data")
            st.line_chart(chart_data)
        else:
            st.info("Nessuna misura registrata ancora.")

    st.divider()

    # 3. Diario Odierno (con tasto elimina)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🍎 Pasti Oggi")
        if not df_oggi.empty:
            for idx, r in df_oggi.iterrows():
                if r['tipo'] == 'pasto':
                    d = json.loads(r['dettaglio_json'])
                    cc1, cc2 = st.columns([4,1])
                    cc1.text(f"🍽️ {d['nome']} ({int(d['cal'])} kcal)")
                    if cc2.button("🗑️", key=f"d_p_{idx}"): delete_riga(idx); st.rerun()

    with c2:
        st.subheader("🏋️ Workout Oggi")
        if not df_oggi.empty:
            for idx, r in df_oggi.iterrows():
                if r['tipo'] == 'allenamento':
                    d = json.loads(r['dettaglio_json'])
                    cc1, cc2 = st.columns([4,1])
                    with cc1:
                        st.info(f"⏱️ {d.get('durata',0)} min")
                        for ex in d['esercizi']: st.caption(f"• {ex['nome']}: {ex['serie']}x{ex['reps']} {ex['kg']}kg")
                    if cc2.button("🗑️", key=f"d_w_{idx}"): delete_riga(idx); st.rerun()

# --- CIBO ---
with tab2:
    st.header("Diario Alimentare")
    c_in, c_db = st.columns([1,1])
    
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with c_in:
        st.subheader("Mangia")
        pasto = st.selectbox("Momento", ["Colazione", "Pranzo", "Cena", "Spuntino"])
        sel_cibo = st.selectbox("Cerca Cibo", ["-- Manuale --"] + nomi_cibi)
        gr = st.number_input("Grammi", 100.0, step=10.0)

        # Autocompilazione
        v_n, v_k, v_p, v_c, v_f = "", 0.0, 0.0, 0.0, 0.0
        if sel_cibo != "-- Manuale --" and not df_cibi.empty:
            row = df_cibi[df_cibi['nome'] == sel_cibo].iloc[0]
            f = gr/100
            v_n=row['nome']; v_k=row['kcal']*f; v_p=row['pro']*f; v_c=row['carb']*f; v_f=row['fat']*f

        with st.form("f_pasto"):
            st.caption(f"Valori per {gr}g")
            nome = st.text_input("Nome", v_n)
            k = st.number_input("Kcal", value=float(v_k))
            p = st.number_input("Pro", value=float(v_p))
            c = st.number_input("Carb", value=float(v_c))
            fat = st.number_input("Fat", value=float(v_f))
            if st.form_submit_button("Aggiungi"):
                add_riga_diario("pasto", {"pasto":pasto, "nome":nome, "cal":k, "pro":p, "carb":c, "fat":fat, "gr":gr})
                st.success("Fatto!"); st.rerun()

    with c_db:
        st.subheader("Nuovo Cibo nel DB (100g)")
        with st.form("f_new_cibo"):
            nn = st.text_input("Nome")
            kk = st.number_input("Kcal"); pp = st.number_input("Pro"); cc = st.number_input("Carb"); ff = st.number_input("Fat")
            if st.form_submit_button("Salva Cibo"):
                if nn: 
                    new = pd.DataFrame([{"nome":nn, "kcal":kk, "pro":pp, "carb":cc, "fat":ff}])
                    save_data("cibi", pd.concat([df_cibi, new], ignore_index=True))
                    st.success("Salvato!"); st.rerun()

# --- WORKOUT ---
with tab3:
    st.header("Scheda Allenamento")
    
    # Sessione Temporanea
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    col_run, col_db = st.columns([2,1])
    
    df_ex = get_data("esercizi")
    lista_ex = df_ex['nome'].tolist() if not df_ex.empty else []

    with col_run:
        st.subheader("🔥 Sessione in corso")
        
        # Selezione Esercizio
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        ex_sel = c1.selectbox("Seleziona Esercizio", ["-- Nuovo --"] + lista_ex)
        
        # Se seleziona "-- Nuovo --", appare una casella di testo, altrimenti usa il nome selezionato
        nome_ex_finale = ex_sel if ex_sel != "-- Nuovo --" else c1.text_input("Scrivi nome esercizio")
        
        serie = c2.number_input("Serie", 1, step=1)
        reps = c3.number_input("Reps", 1, step=1)
        kg = c4.number_input("Kg", 0.0, step=0.5)
        
        if st.button("➕ Aggiungi alla scheda", type="primary"):
            if nome_ex_finale:
                st.session_state['sess_w'].append({"nome": nome_ex_finale, "serie": serie, "reps": reps, "kg": kg})
            else:
                st.error("Scegli o scrivi un nome!")

        st.markdown("---")
        # Lista Esercizi Aggiunti
        if st.session_state['sess_w']:
            for i, e in enumerate(st.session_state['sess_w']):
                sc1, sc2 = st.columns([5,1])
                sc1.info(f"**{i+1}. {e['nome']}** | {e['serie']} x {e['reps']} @ {e['kg']}kg")
                if sc2.button("❌", key=f"rem_w_{i}"):
                    st.session_state['sess_w'].pop(i); st.rerun()
            
            durata = st.number_input("Durata Totale (minuti)", 0, step=5)
            if st.button("💾 SALVA SESSIONE COMPLETA"):
                add_riga_diario("allenamento", {"durata":durata, "esercizi":st.session_state['sess_w']})
                st.session_state['sess_w'] = []
                st.success("Workout salvato!"); st.rerun()
        else:
            st.caption("Aggiungi esercizi per iniziare...")

    with col_db:
        st.subheader("📝 Crea Esercizio")
        st.info("Aggiungi qui i tuoi esercizi preferiti per ritrovarli nel menu a tendina.")
        with st.form("new_ex"):
            n_ex = st.text_input("Nome Esercizio (es. Panca)")
            if st.form_submit_button("Salva nel DB"):
                if n_ex:
                    new = pd.DataFrame([{"nome":n_ex}])
                    save_data("esercizi", pd.concat([df_ex, new], ignore_index=True))
                    st.success("Creato!"); st.rerun()

# --- MISURE ---
with tab4:
    st.header("📏 Misure Corporee")
    with st.form("misure_form"):
        col1, col2 = st.columns(2)
        peso = col1.number_input("Peso Corporeo (kg)", 0.0, step=0.1, format="%.1f")
        alt = col2.number_input("Altezza (cm)", 0, step=1)
        
        c1, c2, c3 = st.columns(3)
        collo = c1.number_input("Collo (cm)", 0.0, step=0.5)
        vita = c2.number_input("Vita (cm)", 0.0, step=0.5)
        fianchi = c3.number_input("Fianchi (cm)", 0.0, step=0.5)
        
        if st.form_submit_button("Salva Misure"):
            add_riga_diario("misure", {"peso":peso, "alt":alt, "collo":collo, "vita":vita, "fianchi":fianchi})
            st.success("Misure aggiornate!"); st.rerun()

# --- AI ---
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

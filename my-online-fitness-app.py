import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import time
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V15.1 - FULL DATA ENGINE)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root { --primary: #0051FF; --bg-app: #F8F9FA; --card-bg: #FFFFFF; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: var(--bg-app); }
    .stApp { background-color: var(--bg-app) !important; }
    div[data-testid="stContainer"] { background-color: var(--card-bg); border-radius: 16px; padding: 20px; border: 1px solid #E5E7EB; margin-bottom: 1rem; }
    button[kind="primary"] { background: linear-gradient(135deg, #0051FF 0%, #0030CC 100%) !important; border-radius: 10px !important; border: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
# ==========================================
def check_password():
    if st.session_state.get("password_correct"): return True
    pwd = st.secrets.get("APP_PASSWORD", "admin")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.container(border=True):
            st.markdown("### 🔒 Accesso")
            input_pwd = st.text_input("Password", type="password")
            if input_pwd == pwd:
                st.session_state["password_correct"] = True
                st.rerun()
    return False

if not check_password(): st.stop()

# ==========================================
# 🚀 DATABASE ENGINE & HELPERS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def fetch_data_cached(sheet_name):
    try: return conn.read(worksheet=sheet_name)
    except: return pd.DataFrame()

def get_data(sheet): return fetch_data_cached(sheet)

def save_data(sheet, df):
    df = df.fillna("") 
    conn.update(worksheet=sheet, data=df)
    st.cache_data.clear()

def safe_parse_json(json_str):
    try:
        if pd.isna(json_str) or json_str == "": return {}
        return json.loads(json_str)
    except: return {}

def add_riga_diario(tipo, dati, data_custom=None):
    df = get_data("diario")
    target_date = data_custom if data_custom else datetime.datetime.now().strftime("%Y-%m-%d")
    nuova = pd.DataFrame([{"data": target_date, "tipo": tipo, "dettaglio_json": json.dumps(dati)}])
    save_data("diario", pd.concat([df, nuova], ignore_index=True))

def delete_riga(idx):
    df = get_data("diario")
    save_data("diario", df.drop(idx))
    st.rerun()

# Recupero Dati Core
df_diario = get_data("diario")
df_cibi = get_data("cibi")
df_int = get_data("integratori")
df_ex = get_data("esercizi")

# ==========================================
# 📊 LOGICA CALCOLI
# ==========================================
def get_user_settings(df):
    settings = {"url_foto": "", "target_cal": 2500, "target_pro": 180, "target_carb": 300, "target_fat": 80}
    if not df.empty:
        rows = df[df['tipo'] == 'settings']
        if not rows.empty: settings.update(safe_parse_json(rows.iloc[-1]['dettaglio_json']))
    return settings

user_settings = get_user_settings(df_diario)

# ==========================================
# 📱 SIDEBAR
# ==========================================
with st.sidebar:
    if user_settings.get('url_foto'):
        st.image(user_settings['url_foto'], use_container_width=True)
    
    st.markdown("### 📅 Filtro Data")
    selected_date = st.date_input("Giorno:", datetime.date.today())
    data_filtro = selected_date.strftime("%Y-%m-%d")
    
    with st.expander("🎯 Modifica Target"):
        with st.form("t_form"):
            t_cal = st.number_input("Kcal", value=int(user_settings['target_cal']))
            t_pro = st.number_input("Pro", value=int(user_settings['target_pro']))
            if st.form_submit_button("Salva"):
                user_settings.update({"target_cal": t_cal, "target_pro": t_pro})
                add_riga_diario("settings", user_settings, data_filtro)
                st.rerun()

# ==========================================
# 🏠 MAIN DASHBOARD
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "💾 Gestione DB"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df_oggi = df_diario[df_diario['data'] == data_filtro]
    cal = pro = carb = fat = 0
    
    for i, r in df_oggi.iterrows():
        d = safe_parse_json(r['dettaglio_json'])
        if r['tipo'] == 'pasto':
            cal += d.get('cal', 0); pro += d.get('pro', 0)
            carb += d.get('carb', 0); fat += d.get('fat', 0)
    
    c1, c2 = st.columns(2)
    c1.metric("Calorie", f"{int(cal)} kcal", f"{int(user_settings['target_cal']-cal)} residui")
    c2.metric("Proteine", f"{int(pro)}g", f"{int(user_settings['target_pro']-pro)} residui")
    
    st.divider()
    st.subheader("📝 Log di oggi")
    for i, r in df_oggi.iterrows():
        d = safe_parse_json(r['dettaglio_json'])
        with st.container():
            col_a, col_b = st.columns([5,1])
            if r['tipo'] == 'pasto':
                col_a.write(f"🍎 **{d.get('nome')}**: {d.get('cal')} kcal (P:{d.get('pro')} C:{d.get('carb')} F:{d.get('fat')})")
            elif r['tipo'] == 'allenamento':
                col_a.write(f"🏋️ **Workout**: {d.get('nome_sessione')} ({d.get('durata')} min)")
            
            if col_b.button("🗑️", key=f"del_{i}"): delete_riga(i)

# --- TAB 2: ALIMENTAZIONE (CON AUTO-DB) ---
with tab2:
    st.subheader("Inserisci Pasto")
    
    # CALLBACK PER AUTO-COMPLETAMENTO
    def update_macros():
        if st.session_state.f_sel != "-- Manuale --":
            row = df_cibi[df_cibi['nome'] == st.session_state.f_sel].iloc[0]
            factor = st.session_state.f_gr / 100
            st.session_state.f_k = row['kcal'] * factor
            st.session_state.f_p = row['pro'] * factor
            st.session_state.f_c = row['carb'] * factor
            st.session_state.f_f = row['fat'] * factor

    nomi_cibi = ["-- Manuale --"] + (df_cibi['nome'].tolist() if not df_cibi.empty else [])
    sel_cibo = st.selectbox("Cerca nel DB", nomi_cibi, key="f_sel", on_change=update_macros)
    
    with st.form("pasto_form"):
        nome = st.text_input("Nome", value=sel_cibo if sel_cibo != "-- Manuale --" else "")
        gr = st.number_input("Grammi", value=100, key="f_gr")
        c1, c2, c3, c4 = st.columns(4)
        k = c1.number_input("Kcal", key="f_k")
        p = c2.number_input("Pro", key="f_p")
        c = c3.number_input("Carb", key="f_c")
        f = c4.number_input("Fat", key="f_f")
        
        if st.form_submit_button("Aggiungi al diario"):
            add_riga_diario("pasto", {"nome":nome, "cal":k, "pro":p, "carb":c, "fat":f, "gr":gr}, data_filtro)
            st.rerun()

# --- TAB 4: GESTIONE DB (I TUOI DATI SONO QUI) ---
with tab4:
    st.subheader("I tuoi Database")
    
    t_c, t_e = st.tabs(["Cibi Salvati", "Esercizi"])
    
    with t_c:
        st.dataframe(df_cibi, use_container_width=True)
        with st.expander("Aggiungi nuovo cibo al DB"):
            with st.form("new_db_cibo"):
                n = st.text_input("Nome Alimento")
                c1,c2,c3,c4 = st.columns(4)
                kcal = c1.number_input("Kcal/100g")
                prot = c2.number_input("Pro/100g")
                carb = c3.number_input("Carb/100g")
                fats = c4.number_input("Fat/100g")
                if st.form_submit_button("Salva nel Database"):
                    new_row = pd.DataFrame([{"nome":n, "kcal":kcal, "pro":prot, "carb":carb, "fat":fats}])
                    save_data("cibi", pd.concat([df_cibi, new_row], ignore_index=True))
                    st.rerun()
                    
    with t_e:
        st.dataframe(df_ex, use_container_width=True)

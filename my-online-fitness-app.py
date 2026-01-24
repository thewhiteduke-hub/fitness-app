import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import time
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V15.0 - TITANIUM LIGHT)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* 1. IMPORT FONT INTER & SETUP VARS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --primary: #0051FF;
        --primary-hover: #0039B3;
        --bg-app: #F8F9FA;
        --card-bg: #FFFFFF;
        --text-main: #1F2937;
        --text-sub: #6B7280;
        --border-light: #E5E7EB;
        --success: #10B981;
        --danger: #EF4444;
    }

    html, body, .stApp {
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-app);
        color: var(--text-main);
    }

    /* 2. CONTAINER & CARD SYSTEM */
    div[data-testid="stContainer"], div[data-testid="stExpander"] {
        background-color: var(--card-bg);
        border-radius: 16px;
        border: 1px solid var(--border-light);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="stContainer"]:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-color: #BFDBFE;
        transform: translateY(-2px);
    }

    /* 3. INPUT FIELDS */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        background-color: #F9FAFB;
    }

    /* 4. BUTTONS */
    button[kind="primary"] {
        background: linear-gradient(145deg, var(--primary) 0%, var(--primary-hover) 100%) !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0, 81, 255, 0.25);
    }

    /* 5. TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        border-bottom: 1px solid #E5E7EB;
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary) !important;
    }

    /* 6. METRICS */
    div[data-testid="stMetricValue"] {
        font-weight: 800 !important;
        color: var(--primary) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN SYSTEM
# ==========================================
def check_password():
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    
    pwd = st.secrets["APP_PASSWORD"] if "APP_PASSWORD" in st.secrets else "admin"
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("")
        with st.container(border=True):
            st.markdown("### 🔒 Accesso FitPro")
            input_pwd = st.text_input("Inserisci Password", type="password", key="pwd_login_15")
            if input_pwd == pwd:
                st.session_state["password_correct"] = True
                st.rerun()
            elif input_pwd:
                st.error("Password errata")
    return False

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
# 🚀 DATABASE ENGINE (OPTIMIZED)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def fetch_data_cached(sheet_name):
    try: 
        return conn.read(worksheet=sheet_name)
    except:
        return pd.DataFrame()

def get_data(sheet): return fetch_data_cached(sheet)

def save_data(sheet, df):
    with st.spinner(f"💾 Salvataggio {sheet}..."):
        df = df.fillna("") 
        conn.update(worksheet=sheet, data=df)
        fetch_data_cached.clear()
        st.cache_data.clear()

def safe_parse_json(json_str):
    try:
        if pd.isna(json_str) or json_str == "": return {}
        return json.loads(json_str)
    except: return {}

def add_riga_diario(tipo, dati, data_custom=None):
    df = get_data("diario")
    if df.empty: df = pd.DataFrame(columns=["data", "tipo", "dettaglio_json"])
    target_date = data_custom if data_custom else datetime.datetime.now().strftime("%Y-%m-%d")
    nuova = pd.DataFrame([{"data": target_date, "tipo": tipo, "dettaglio_json": json.dumps(dati)}])
    df_totale = pd.concat([df, nuova], ignore_index=True)
    save_data("diario", df_totale)

def delete_riga(idx):
    df = get_data("diario")
    if idx in df.index:
        save_data("diario", df.drop(idx))
        st.rerun()

def get_user_settings():
    df = get_data("diario")
    settings = {"url_foto": "", "target_cal": 2500, "target_pro": 180, "target_carb": 300, "target_fat": 80}
    if not df.empty:
        rows = df[df['tipo'] == 'settings']
        if not rows.empty:
            settings.update(safe_parse_json(rows.iloc[-1]['dettaglio_json']))
    return settings

def calculate_user_status(df):
    if df.empty: return 1, 0, 0.0, 100, 0
    xp = len(df[df['tipo'] == 'pasto']) * 5 + len(df[df['tipo'] == 'allenamento']) * 20 + \
         len(df[df['tipo'] == 'misure']) * 10 + len(df[df['tipo'] == 'acqua']) * 2
    level = 1 + (xp // 500)
    current_xp = xp % 500
    progress = current_xp / 500
    
    streak = 0
    try:
        dates = sorted(pd.to_datetime(df['data']).dt.date.unique(), reverse=True)
        today = datetime.date.today()
        if dates and (dates[0] == today or dates[0] == today - datetime.timedelta(days=1)):
            streak = 1
            for i in range(len(dates)-1):
                if dates[i] - datetime.timedelta(days=1) == dates[i+1]: streak += 1
                else: break
    except: pass
    return level, xp, progress, int(current_xp), streak

def clear_form_state(keys):
    for k in keys:
        if k in st.session_state: del st.session_state[k]

# Load Data
df = get_data("diario")
user_settings = get_user_settings()
lvl, tot_xp, prog, curr_xp, streak_count = calculate_user_status(df)

# ==========================================
# 📱 SIDEBAR
# ==========================================
with st.sidebar:
    url_avatar = user_settings.get('url_foto', '').strip()
    if url_avatar:
        st.markdown(f"""<div style="display:flex; justify-content:center; margin-bottom: 15px;">
            <div style="width: 180px; height: 230px; background-image: url('{url_avatar}'); 
            background-size: cover; background-position: center; border-radius: 12px; border: 2px solid #E5E7EB;"></div>
            </div>""", unsafe_allow_html=True)
    
    col_lvl, col_info = st.columns([1, 2])
    col_lvl.markdown(f"<h1 style='color:#0051FF; text-align:center;'>{lvl}</h1>", unsafe_allow_html=True)
    col_info.markdown(f"**Atleta**\n\n🔥 Streak: {streak_count}")
    st.progress(prog)
    st.caption(f"🚀 XP: {curr_xp} / 500")

    st.markdown("---")
    selected_date = st.date_input("Data Diario:", datetime.date.today())
    data_filtro = selected_date.strftime("%Y-%m-%d")
    
    with st.expander("🎯 Target & Foto"):
        nu_url = st.text_input("URL Foto Profilo", value=url_avatar)
        tc = st.number_input("Kcal", value=int(user_settings['target_cal']))
        if st.button("Salva Impostazioni"):
            ns = user_settings.copy()
            ns.update({"url_foto": nu_url, "target_cal": tc})
            add_riga_diario("settings", ns, data_filtro); st.rerun()

    st.markdown("---")
    q_ai = st.text_input("Coach AI...")
    if st.button("Chiedi all'AI"):
        if gemini_ok:
            ans = model.generate_content(f"Sei un PT esperto. Rispondi brevemente: {q_ai}").text
            st.info(ans)

# ==========================================
# 🏠 MAIN DASHBOARD
# ==========================================
st.title("Fit Tracker Pro")
st.caption(f"Visualizzazione per il giorno: {data_filtro}")

misure_list = []
if not df.empty:
    for _, r in df[df['tipo'] == 'misure'].iterrows():
        d = safe_parse_json(r['dettaglio_json'])
        if 'peso' in d: misure_list.append({"Data": r['data'], "Peso": float(d['peso'])})

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Calisthenics"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df_oggi = df[df['data'] == data_filtro]
    cal = pro = carb = fat = water = 0
    meal_groups = {"Colazione":[], "Pranzo":[], "Cena":[], "Spuntino":[], "Integrazione":[]}
    allenamenti = []

    for i, r in df_oggi.iterrows():
        d = safe_parse_json(r['dettaglio_json']); d['idx'] = i
        if r['tipo'] == 'pasto':
            cal += d.get('cal',0); pro += d.get('pro',0); carb += d.get('carb',0); fat += d.get('fat',0)
            meal_groups[d.get('pasto', 'Spuntino')].append(d)
        elif r['tipo'] == 'allenamento': allenamenti.append(d)
        elif r['tipo'] == 'acqua': water += d.get('ml', 0)

    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        with st.container(border=True):
            st.metric("Calorie", f"{int(cal)}", f"{int(user_settings['target_cal']-cal)} left")
            st.progress(min(cal/user_settings['target_cal'], 1.0))
    with c2:
        with st.container(border=True):
            st.metric("Proteine", f"{int(pro)}g", f"{int(user_settings['target_pro']-pro)}g left")
            st.progress(min(pro/user_settings['target_pro'], 1.0))
    with c3:
        with st.container(border=True):
            if st.button("💧 +250ml"): add_riga_diario("acqua", {"ml": 250}, data_filtro); st.rerun()
            st.caption(f"Acqua: {water} / 2500 ml")

    st.divider()
    if misure_list:
        df_chart = pd.DataFrame(misure_list).sort_values("Data")
        chart = alt.Chart(df_chart).mark_line(point=True, color='#0051FF').encode(
            x='Data:T', y=alt.Y('Peso:Q', scale=alt.Scale(zero=False))
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🍎 Pasti")
        for cat, items in meal_groups.items():
            if items:
                with st.expander(f"{cat}"):
                    for p in items:
                        c_t, c_b = st.columns([4,1])
                        c_t.write(f"**{p['nome']}** ({p['cal']} kcal)")
                        if c_b.button("🗑️", key=f"del_{p['idx']}"): delete_riga(p['idx'])
    with col_r:
        st.subheader("🏋️ Allenamenti")
        for w in allenamenti:
            with st.container(border=True):
                st.write(f"**{w['nome_sessione']}** ({w['durata']} min)")
                for ex in w.get('esercizi', []):
                    st.caption(f"• {ex['nome']}")

# --- TAB 2: ALIMENTAZIONE ---
with tab2:
    c_in, c_db = st.columns([2,1])
    df_cibi = get_data("cibi")
    with c_in:
        st.subheader("Inserimento")
        cat_p = st.selectbox("Pasto", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"])
        with st.container(border=True):
            nome_f = st.text_input("Alimento")
            gr_f = st.number_input("Grammi", value=100)
            c1,c2,c3,c4 = st.columns(4)
            kf=c1.number_input("Kcal", 0); pf=c2.number_input("Pro", 0.0); cf=c3.number_input("Carb", 0.0); ff=c4.number_input("Fat", 0.0)
            if st.button("Aggiungi Pasto", type="primary"):
                add_riga_diario("pasto", {"pasto":cat_p, "nome":nome_f, "gr":gr_f, "cal":kf, "pro":pf, "carb":cf, "fat":ff}, data_filtro)
                st.rerun()
    with c_db:
        st.subheader("Database")
        with st.form("new_food"):
            nf = st.text_input("Nome Cibo")
            if st.form_submit_button("Salva nel DB"):
                new_df = pd.concat([df_cibi, pd.DataFrame([{"nome":nf, "kcal":0, "pro":0, "carb":0, "fat":0}])])
                save_data("cibi", new_df); st.rerun()

# --- TAB 3: WORKOUT ---
with tab3:
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    c1, c2 = st.columns([1,2])
    with c1:
        st.subheader("Nuovo Set")
        nome_ex = st.text_input("Esercizio")
        s = st.number_input("Set", 1); r = st.number_input("Rep", 1); k = st.number_input("Kg", 0.0)
        if st.button("Aggiungi Esercizio"):
            st.session_state['sess_w'].append({"nome":nome_ex, "serie":s, "reps":r, "kg":k, "type":"pesi"})
    with c2:
        st.subheader("Sessione in corso")
        for i, ex in enumerate(st.session_state['sess_w']):
            st.write(f"{ex['nome']} - {ex['serie']}x{ex['reps']} @ {ex['kg']}kg")
        durata = st.number_input("Durata min", 60)
        if st.button("Salva Allenamento", type="primary"):
            add_riga_diario("allenamento", {"nome_sessione":"Workout", "durata":durata, "esercizi":st.session_state['sess_w']}, data_filtro)
            st.session_state['sess_w'] = []
            st.rerun()

# --- TAB 4 & 5 (STORICO & SKILLS) ---
with tab4:
    st.subheader("Misure")
    p_m = st.number_input("Peso Corporeo", 0.0)
    if st.button("Salva Pesata"):
        add_riga_diario("misure", {"peso":p_m}, data_filtro); st.rerun()
    if misure_list: st.table(pd.DataFrame(misure_list).sort_values("Data", ascending=False))

with tab5:
    st.subheader("🤸 Skills Calisthenics")
    n_sk = st.text_input("Skill")
    d_sk = st.text_area("Note")
    if st.button("Salva Skill"):
        add_riga_diario("calisthenics", {"nome":n_sk, "desc":d_sk}, data_filtro); st.rerun()

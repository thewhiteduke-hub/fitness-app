import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import time
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V14.5 - FINAL FORCE LIGHT THEME)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* 1. IMPORT FONT INTER */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --primary: #0051FF;
        --primary-soft: #E5F0FF;
        --text-main: #111827;
        --text-sub: #6B7280;
        --bg-app: #F3F4F6;
        --card-bg: #FFFFFF;
        --success: #10B981;
        --danger: #EF4444;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-app);
        color: var(--text-main);
    }

    /* PULIZIA UI STREAMLIT */
    .stApp { background-color: var(--bg-app) !important; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
        box-shadow: 4px 0 24px rgba(0,0,0,0.02);
    }

    /* CARD SYSTEM & HOVER EFFECTS */
    div[data-testid="stContainer"] {
        background-color: var(--card-bg);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #F3F4F6;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    div[data-testid="stContainer"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
        border-color: var(--primary-soft);
    }

    /* INPUT STYLING */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 12px !important;
        border: 1px solid #E5E7EB !important;
        padding-left: 12px;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px var(--primary-soft) !important;
    }

    /* BUTTONS */
    button[kind="primary"] {
        background: linear-gradient(135deg, #0051FF 0%, #0030CC 100%) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0, 81, 255, 0.2);
        border: none !important;
        transition: all 0.3s ease;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 6px 16px rgba(0, 81, 255, 0.4);
        transform: scale(1.02);
    }
    button[kind="secondary"] {
        border-radius: 12px !important;
        border: 1px solid #E5E7EB !important;
        color: var(--text-main) !important;
        background: transparent !important;
    }

    /* CUSTOM METRICS */
    div[data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif;
        font-weight: 800 !important;
        color: var(--primary) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: var(--text-sub) !important;
        font-weight: 500;
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #ffffff;
        padding: 8px;
        border-radius: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border: none !important;
        border-radius: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-soft) !important;
        color: var(--primary) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
# ==========================================
def check_password():
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    # Default password fallback
    pwd = st.secrets["APP_PASSWORD"] if "APP_PASSWORD" in st.secrets else "admin"
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("")
        with st.container(border=True):
            st.markdown("### 🔒 Accesso")
            input_pwd = st.text_input("Password", type="password", key="pwd_login_14")
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
# 🚀 DATABASE ENGINE & HELPERS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def fetch_data_cached(sheet_name):
    try: 
        return conn.read(worksheet=sheet_name)
    except Exception as e:
        return pd.DataFrame()

def get_data(sheet): return fetch_data_cached(sheet)

def save_data(sheet, df):
    df = df.fillna("") 
    conn.update(worksheet=sheet, data=df)
    fetch_data_cached.clear()
    st.cache_data.clear()

def safe_parse_json(json_str):
    """Helper per evitare crash su JSON corrotti"""
    try:
        if pd.isna(json_str) or json_str == "": return {}
        return json.loads(json_str)
    except: return {}

# [FIX] Aggiunta parametro data_custom per back-logging
def add_riga_diario(tipo, dati, data_custom=None):
    df = get_data("diario")
    if df.empty: df = pd.DataFrame(columns=["data", "tipo", "dettaglio_json"])
    
    # Se passata una data specifica (es. dal calendario), usiamo quella
    target_date = data_custom if data_custom else datetime.datetime.now().strftime("%Y-%m-%d")
    
    nuova = pd.DataFrame([{"data": target_date, "tipo": tipo, "dettaglio_json": json.dumps(dati)}])
    df_totale = pd.concat([df, nuova], ignore_index=True)
    save_data("diario", df_totale)

def delete_riga(idx):
    df = get_data("diario")
    if idx in df.index:
        save_data("diario", df.drop(idx))
    else:
        st.warning("Impossibile trovare la riga. Ricarico...")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

def get_user_settings():
    df = get_data("diario")
    settings = {"url_foto": "", "target_cal": 2500, "target_pro": 180, "target_carb": 300, "target_fat": 80}
    if not df.empty:
        rows = df[df['tipo'] == 'settings']
        if not rows.empty:
            try: settings.update(safe_parse_json(rows.iloc[-1]['dettaglio_json']))
            except: pass
    return settings

# [UPDATED] Funzione Livello Aggiornata con XP Acqua
def calculate_user_level(df):
    if df.empty: return 1, 0, 0.0, 100
    xp = 0
    xp += len(df[df['tipo'] == 'pasto']) * 5
    xp += len(df[df['tipo'] == 'allenamento']) * 20
    xp += len(df[df['tipo'] == 'misure']) * 10
    # Nuovo: 2 XP per ogni inserimento acqua
    xp += len(df[df['tipo'] == 'acqua']) * 2
    
    level = 1 + (xp // 500)
    current_xp = xp % 500
    next_level_xp = 500
    progress = current_xp / next_level_xp
    return level, xp, progress, int(current_xp)

def clear_form_state(keys_to_clear):
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

df = get_data("diario")
user_settings = get_user_settings()

# ==========================================
# 📱 SIDEBAR (VERSIONE NATIVE - STABILE)
# ==========================================
with st.sidebar:
    # 1. CALCOLO DATI
    lvl, tot_xp, prog, curr_xp = calculate_user_level(df)
    
    # 2. SEZIONE PROFILO (Semplificata)
    url_avatar = user_settings.get('url_foto', '').strip()
    
    col_av, col_info = st.columns([1, 2])
    
    with col_av:
        if url_avatar:
            st.image(url_avatar, width=80)
        else:
            # Emoji semplice se non c'è foto
            st.markdown("# 👤")

    with col_info:
        st.metric(label="Livello", value=f"{lvl}", delta="Elite Athlete")
    
    # Barra XP Standard
    st.write("")
    st.progress(prog)
    st.caption(f"🚀 XP: {curr_xp} / 500")

    # --- RESTO DELLA SIDEBAR (Funzionalità invariate) ---
    st.markdown("---")
    st.markdown("**📅 Seleziona Data**")
    selected_date = st.date_input("Visualizza diario del:", datetime.date.today())
    data_filtro = selected_date.strftime("%Y-%m-%d")
    
    st.markdown("---")
    with st.expander("🎯 Target"):
        with st.form("target_form"):
            tc = st.number_input("Target Kcal", value=int(user_settings['target_cal']))
            tp = st.number_input("Target Pro", value=int(user_settings['target_pro']))
            tca = st.number_input("Target Carb", value=int(user_settings['target_carb']))
            tf = st.number_input("Target Fat", value=int(user_settings['target_fat']))
            if st.form_submit_button("Salva"):
                ns = user_settings.copy(); ns.update({"target_cal":tc,"target_pro":tp,"target_carb":tca,"target_fat":tf})
                add_riga_diario("settings", ns, data_filtro); st.rerun()

    st.markdown("---")
    with st.expander("📸 Cambia Foto"):
        nu = st.text_input("Link Foto", key="s_url")
        if st.button("Salva", key="s_btn"):
            if nu:
                ns = user_settings.copy(); ns['url_foto'] = nu
                add_riga_diario("settings", ns, data_filtro); st.rerun()

    st.markdown("---")
    w_fast = st.number_input("Peso Rapido (kg)", 0.0, format="%.1f", key="side_w_f")
    if st.button("Salva Peso", key="side_btn_w"):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast}, data_filtro)
            st.toast("Salvato!"); st.rerun()

    st.markdown("---")
    q_ai = st.text_input("Coach AI...", key="s_ai")
    if st.button("Invia", key="s_aibtn"):
        if "chat" not in st.session_state: st.session_state.chat = []
        st.session_state.chat.append({"role":"user","txt":q_ai})
        ans="Errore AI"; 
        if gemini_ok:
            try: ans=model.generate_content(f"Sei un PT esperto. Sii breve e motivante. Rispondi: {q_ai}").text
            except: pass
        st.session_state.chat.append({"role":"assistant","txt":ans}); st.rerun()
    
    if "chat" in st.session_state and st.session_state.chat:
        st.info(st.session_state.chat[-1]['txt'])

# ==========================================
# 🏠 MAIN DASHBOARD
# ==========================================

# 1. Recupero URL Foto sicuro
url_avatar = user_settings.get('url_foto', '').strip()

# 2. Layout Header
c_header_txt, c_header_img = st.columns([4, 1])

with c_header_txt:
    st.title(f"Bentornato, Atleta.")
    st.caption(f"📅 Riepilogo del: {data_filtro}")

with c_header_img:
    if url_avatar:
        st.markdown(f"""
        <div style="display:flex; justify-content:flex-end;">
            <div style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid #0051FF; 
                background-image: url('{url_avatar}'); background-size: cover; background-position: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);"></div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display:flex; justify-content:flex-end;">
            <div style="width: 80px; height: 80px; border-radius: 50%; background-color: #E5F0FF; color: #0051FF;
                display:flex; align-items:center; justify-content:center; font-size: 30px; border: 3px solid #0051FF;">👤</div>
        </div>""", unsafe_allow_html=True)

st.write("") 

st.write("") 

# ==========================================
# 📊 PREPARAZIONE DATI GLOBALI (Mancava questo pezzo!)
# ==========================================
misure_list = []
if not df.empty:
    for _, r in df.iterrows():
        if r['tipo'] == 'misure':
            try:
                # Usiamo la funzione safe_parse_json definita in alto
                d = safe_parse_json(r['dettaglio_json'])
                if d and 'peso' in d:
                    misure_list.append({"Data": r['data'], "Peso": float(d['peso'])})
            except: pass


tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Calisthenics"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df_oggi = df[df['data'] == data_filtro] if not df.empty else pd.DataFrame()
    
    cal = pro = carb = fat = 0
    meal_groups = {"Colazione": [], "Pranzo": [], "Cena": [], "Spuntino": [], "Integrazione": []}
    allenamenti = []
    water_today = 0 # [NEW] Variabile accumulo acqua
    
    if not df_oggi.empty:
        for i, r in df_oggi.iterrows():
            d = safe_parse_json(r['dettaglio_json'])
            if not d: continue
            d['idx'] = i 
            
            if r['tipo'] == 'pasto':
                cal += d.get('cal',0); pro += d.get('pro',0); carb += d.get('carb',0); fat += d.get('fat',0)
                cat = d.get('pasto', 'Spuntino')
                if cat in meal_groups: meal_groups[cat].append(d)
                else: meal_groups["Spuntino"].append(d)
            elif r['tipo'] == 'allenamento':
                allenamenti.append(d)
            elif r['tipo'] == 'acqua':
                water_today += d.get('ml', 0)

    # --- HERO DASHBOARD ---
    TC = user_settings['target_cal']
    perc_cal = min(cal / TC, 1.0) if TC > 0 else 0
    delta_cal = TC - cal
    
    c_hero_1, c_hero_2, c_hero_3 = st.columns([1.5, 1, 1])
    
    with c_hero_1:
        with st.container(border=True):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#6B7280; font-size:14px; font-weight:600;">CALORIE GIORNALIERE</span>
                    <h1 style="margin:0; font-size:36px; color:#111827;">{int(cal)} <span style="font-size:18px; color:#9CA3AF;">/ {TC}</span></h1>
                </div>
                <div style="background:{'#E5F0FF' if delta_cal > 0 else '#FEE2E2'}; padding:8px 16px; border-radius:20px;">
                    <span style="color:{'#0051FF' if delta_cal > 0 else '#EF4444'}; font-weight:700;">
                        {f'{int(delta_cal)} left' if delta_cal >= 0 else f'{abs(int(delta_cal))} over'}
                    </span>
                </div>
            </div>
            <div style="margin-top:15px; width:100%; background:#F3F4F6; height:12px; border-radius:10px;">
                <div style="width:{perc_cal*100}%; background:linear-gradient(90deg, #0051FF, #00C6FF); height:12px; border-radius:10px; transition:width 1s ease;"></div>
            </div>
            """, unsafe_allow_html=True)
    
    with c_hero_2:
        with st.container(border=True):
            TP = user_settings['target_pro']
            prog_p = min(pro/TP, 1.0) if TP > 0 else 0
            st.metric("Proteine", f"{int(pro)}g", f"{int(TP - pro)}g left", delta_color="normal")
            st.progress(prog_p)
            
    with c_hero_3:
        with st.container(border=True):
            st.markdown("**💧 Idratazione**")
            cols_w = st.columns(3)
            # [FIX] Pulsante acqua funzionante
            if cols_w[1].button("➕ 250", key="btn_water_real"):
                add_riga_diario("acqua", {"ml": 250}, data_filtro)
                st.toast("Idratazione registrata! 💧")
                time.sleep(0.5)
                st.rerun()
                
            target_water = 2500
            prog_w = min(water_today / target_water, 1.0) if target_water > 0 else 0
            st.caption(f"{water_today} / {target_water} ml")
            st.progress(prog_w) 

    st.markdown("---")
    
    col_vis, col_kpi = st.columns([1, 1])
    with col_vis:
         st.markdown("##### 🍰 Carboidrati")
         TCA = user_settings['target_carb']
         pc = min(carb/TCA, 1.0) if TCA > 0 else 0
         st.progress(pc)
         st.caption(f"{int(carb)} / {TCA}g")

    with col_kpi:
         st.markdown("##### 🥑 Grassi")
         TF = user_settings['target_fat']
         pf = min(fat/TF, 1.0) if TF > 0 else 0
         st.progress(pf)
         st.caption(f"{int(fat)} / {TF}g")
    
    st.markdown("---")
    st.subheader("🔥 La tua Costanza (Workout)")
    
    today = datetime.date.today()
    last_7 = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    
    active_dates = set()
    if not df.empty:
        workout_days = df[df['tipo'] == 'allenamento']['data'].tolist()
        active_dates = set(workout_days)

    cols = st.columns(7)
    for idx, day in enumerate(last_7):
        d_str = day.strftime("%Y-%m-%d")
        lbl = day.strftime("%a")
        is_active = d_str in active_dates
        bg = "#0051FF" if is_active else "#f0f0f0"
        txt = "#ffffff" if is_active else "#999"
        bdr = "2px solid #0051FF" if day == today else "1px solid #ddd"
        
        with cols[idx]:
            st.markdown(f"""
            <div style="background-color:{bg}; color:{txt}; border-radius:6px; 
            text-align:center; padding:5px; border:{bdr}; font-size:12px;">
                <b>{lbl}</b><br>{day.day}
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📉 Andamento Peso")

    if misure_list:
        df_w = pd.DataFrame(misure_list)
        df_w['Data'] = pd.to_datetime(df_w['Data'])
        df_w = df_w.sort_values('Data')

        chart_w = alt.Chart(df_w).mark_line(
            point=True, color='#0051FF', strokeWidth=3
        ).encode(
            x=alt.X('Data:T', axis=alt.Axis(format='%d/%m', title='', tickCount=5)),
            y=alt.Y('Peso:Q', scale=alt.Scale(zero=False, padding=10), title='Kg'),
            tooltip=[alt.Tooltip('Data:T', format='%d %B'), alt.Tooltip('Peso:Q')]
        ).properties(height=250, background='transparent')

        with st.container(border=True):
            st.altair_chart(chart_w.interactive(), use_container_width=True)
            if len(df_w) >= 2:
                delta = df_w.iloc[-1]['Peso'] - df_w.iloc[-2]['Peso']
                sym = "⬆" if delta > 0 else "⬇"
                st.caption(f"Variazione: **{sym} {abs(delta):.1f} kg** rispetto alla pesata precedente.")
    else:
        st.info("Nessuna misurazione trovata.")

    st.markdown("---")
    cl1, cl2 = st.columns(2)
    with cl1:
        st.subheader("🍎 Diario Oggi")
        found_meals = False
        order = ["Colazione", "Pranzo", "Cena", "Spuntino", "Integrazione"]
        for cat in order:
            items = meal_groups[cat]
            if items:
                found_meals = True
                sub_cal = sum(x['cal'] for x in items)
                with st.expander(f"**{cat}** • {int(sub_cal)} kcal", expanded=True):
                    for p in items:
                        r1, r2, r3 = st.columns([3, 2, 1])
                        qty = f"{int(p.get('gr',0))}{p.get('unita','g')}"
                        r1.markdown(f"**{p['nome']}**")
                        r1.caption(qty)
                        r2.markdown(f"<small>P:{int(p['pro'])} C:{int(p['carb'])} F:{int(p['fat'])}</small>", unsafe_allow_html=True)
                        if r3.button("🗑️", key=f"del_p_{p['idx']}"): 
                            delete_riga(p['idx']); st.rerun()
        if not found_meals: st.info("Nessun pasto registrato oggi.")

    # --- TAB 1 ---
    with cl2:
        st.subheader("🏋️ Allenamento")
        if allenamenti:
            for w in allenamenti:
                with st.container(border=True):
                    h1, h2 = st.columns([4,1])
                    h1.markdown(f"**{w.get('nome_sessione','Workout')}**")
                    h1.caption(f"⏱️ {w['durata']} min")
                    if h2.button("✖️", key=f"del_w_{w['idx']}"): delete_riga(w['idx']); st.rerun()
                    if 'esercizi' in w and w['esercizi']:
                        for ex in w['esercizi']:
                            t = ex.get('type', 'pesi')
                            # --- LOGICA VISUALIZZAZIONE AGGIORNATA ---
                            if t == "pesi": 
                                det = f"**{ex['kg']}kg** x {ex['serie']}x{ex['reps']}"
                            elif t == "isometria": 
                                det = f"⏱️ **{ex['tempo']}s** x {ex['serie']}"
                            elif t == "abs": 
                                det = f"🔥 {ex['serie']}x{ex['reps']}"
                            elif t == "calisthenics": 
                                det = f"bw+{ex.get('kg',0)}kg x {ex['serie']}x{ex['reps']}"
                            else: # Cardio
                                det = f"{ex['km']}km"
                            
                            st.markdown(f"• {ex['nome']} ({det})")
        else: st.info("Riposo o nessun dato.")

# --- TAB 2: ALIMENTAZIONE ---
with tab2:
    c_in, c_db = st.columns([2,1])
    
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []
    df_int = get_data("integratori")
    nomi_int = df_int['nome'].tolist() if not df_int.empty else []

    with c_in:
        st.subheader("Inserimento")
        cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
        
        if cat == "Integrazione":
            sel_i = st.selectbox("Cerca Integratore", ["-- Manuale --"] + nomi_int, key="search_int")
            if "last_sel_int" not in st.session_state: st.session_state.last_sel_int = None
            if sel_i != st.session_state.last_sel_int:
                st.session_state.last_sel_int = sel_i
                if sel_i != "-- Manuale --" and not df_int.empty:
                    try:
                        row = df_int[df_int['nome'] == sel_i].iloc[0]
                        st.session_state['i_nm'] = str(row['nome']) 
                        st.session_state['base_int'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                    except: pass
                else: st.session_state['base_int'] = {'k':0,'p':0,'c':0,'f':0}

            base = st.session_state.get('base_int', {'k':0,'p':0,'c':0,'f':0})
            tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], horizontal=True, key="i_rad")
            u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
            
            with st.container(border=True):
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", key="i_nm")
                q = c2.number_input(f"Qta ({u})", step=1.0, key="i_q") 
                
                val_k = base['k'] * q; val_p = base['p'] * q; val_c = base['c'] * q; val_f = base['f'] * q
                st.caption(f"Totale: {int(val_k)} kcal | P:{int(val_p)} C:{int(val_c)} F:{int(val_f)}")

                if st.button("Aggiungi", type="primary", use_container_width=True, key="bi"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":q,"unita":u,"cal":val_k,"pro":val_p,"carb":val_c,"fat":val_f}, data_filtro)
                        clear_form_state(["i_nm", "i_q"])
                        st.rerun()
        else:
            st.info("💡 Compila i dati qui sotto per aggiungere un pasto.")
            with st.container(border=True):
                sel = st.selectbox("🔍 Cerca Cibo", ["-- Manuale --"]+nomi_cibi, key="f_sel")
                if "last_sel_food" not in st.session_state: st.session_state.last_sel_food = None
                if sel != st.session_state.last_sel_food:
                    st.session_state.last_sel_food = sel
                    if sel != "-- Manuale --" and not df_cibi.empty:
                        try:
                            row = df_cibi[df_cibi['nome'] == sel].iloc[0]
                            st.session_state['f_nm'] = str(row['nome']) 
                            st.session_state['base_food'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                        except: pass
                
                base_f = st.session_state.get('base_food', {'k':0,'p':0,'c':0,'f':0})
                c1, c2 = st.columns([2,1])
                nom = c1.text_input("Nome Alimento", key="f_nm")
                gr = c2.number_input("Quantità (g)", step=10.0, key="f_gr")
                
                fac = gr / 100
                k_t = base_f['k']*fac; p_t = base_f['p']*fac
                c_t = base_f['c']*fac; f_t = base_f['f']*fac
                
                st.markdown("###### 📊 Valori Nutrizionali")
                m1,m2,m3,m4 = st.columns(4)
                k=m1.number_input("Kcal", value=float(k_t), key="fk"); p=m2.number_input("Pro", value=float(p_t), key="fp")
                c=m3.number_input("Carb", value=float(c_t), key="fc"); f=m4.number_input("Fat", value=float(f_t), key="ff")
                st.write("")
                if st.button("🍽️ Aggiungi al Diario", type="primary", use_container_width=True, key="bf"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f}, data_filtro)
                        st.success("Pasto aggiunto!")
                        clear_form_state(["f_nm", "f_gr", "fk", "fp", "fc", "ff"])
                        st.rerun()

    with c_db:
        st.subheader("💾 Gestione DB")
        df_ex_gestione = get_data("esercizi") 
        if df_ex_gestione.empty: df_ex_gestione = pd.DataFrame(columns=["nome", "categoria"])

        t_cibo, t_int, t_ex = st.tabs(["Cibo", "Int", "Ex"])
        
        with t_cibo:
            with st.form("dbf"):
                n=st.text_input("Nome", key="dbn")
                r1, r2 = st.columns(2)
                k=r1.number_input("K/100", key="dbk"); p=r2.number_input("P", key="dbp")
                c=r1.number_input("C", key="dbc"); f=r2.number_input("F", key="dbf")
                if st.form_submit_button("Salva"):
                    if n: 
                        save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True))
                        st.rerun()
            
            with st.expander("🗑️ Elimina Cibi"):
                if not df_cibi.empty:
                    to_del = st.multiselect("Seleziona", df_cibi['nome'].tolist(), key="del_food_m")
                    if st.button("Elimina", key="btn_del_f"):
                        save_data("cibi", df_cibi[~df_cibi['nome'].isin(to_del)])
                        st.rerun()

        with t_int:
            with st.form("dbi"):
                ni=st.text_input("Nome", key="dbi_n")
                r1, r2 = st.columns(2)
                ki=r1.number_input("K", key="dbi_k"); pi=r2.number_input("P", key="dbi_p")
                ci=r1.number_input("C", key="dbi_c"); fi=r2.number_input("F", key="dbi_f")
                if st.form_submit_button("Salva"):
                    if ni: 
                        save_data("integratori", pd.concat([df_int, pd.DataFrame([{"nome":ni,"tipo":"g","kcal":ki,"pro":pi,"carb":ci,"fat":fi}])], ignore_index=True))
                        st.rerun()

        with t_ex:
            st.markdown("**➕ Aggiungi Bulk**")
            bulk_text = st.text_area("Lista (uno per riga)", height=100, key="bulk_ex")
            cat_bulk = st.selectbox("Categoria", ["Pesi", "Calisthenics", "Isometria", "Cardio"], key="cat_bulk")
            if st.button("Salva Lista"):
                if bulk_text:
                    lista = [x.strip() for x in bulk_text.split('\n') if x.strip()]
                    if lista:
                        new_rows = pd.DataFrame({'nome': lista, 'categoria': cat_bulk})
                        save_data("esercizi", pd.concat([df_ex_gestione, new_rows], ignore_index=True))
                        st.rerun()

# --- TAB 3: WORKOUT (AGGIORNATO CON ISOMETRIA E ABS) ---
with tab3:
    st.subheader("Workout")
    df_ex = get_data("esercizi")
    if df_ex.empty: df_ex = pd.DataFrame(columns=["nome", "categoria"])
    elif "categoria" not in df_ex.columns: df_ex["categoria"] = "Pesi"
    
    # 1. Caricamento Liste per Categoria
    ls_pesi = sorted(df_ex[df_ex['categoria'] == 'Pesi']['nome'].unique().tolist())
    ls_cali = sorted(df_ex[df_ex['categoria'] == 'Calisthenics']['nome'].unique().tolist())
    ls_iso  = sorted(df_ex[df_ex['categoria'] == 'Isometria']['nome'].unique().tolist())
    ls_abs  = sorted(df_ex[df_ex['categoria'] == 'Abs']['nome'].unique().tolist())
    
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    c1, c2 = st.columns([1,2])
    with c1:
        st.caption("Setup Sessione")
        ses = st.text_input("Nome Sessione", "Workout", key="w_ses")
        # UPDATED: Aggiunte nuove modalità
        mod = st.radio("Modo", ["Pesi", "Calisthenics", "Isometria", "Abs", "Cardio"], horizontal=True, key="w_mod")
        
        # --- MODO PESI ---
        if mod == "Pesi":
            def clear_w_in(): 
                if 'ws' in st.session_state: st.session_state.ws = 1
                if 'ww' in st.session_state: st.session_state.ww = 0.0

            sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_pesi, key="w_sl", on_change=clear_w_in)
            nm = st.text_input("Nome", key="w_nm") if sl == "-- Nuovo --" else sl
            s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
            if st.button("Aggiungi Set", key="wb"): 
                st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
            
            with st.expander("Salva nel DB"):
                if st.button("Salva Pesi", key="wds"): 
                    save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Pesi"}])], ignore_index=True))
                    st.rerun()

        # --- MODO CALISTHENICS ---
        elif mod == "Calisthenics":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_cali, key="w_cali_sl")
            nm = st.text_input("Nome", key="w_cali_nm") if sl == "-- Nuovo --" else sl
            s = st.number_input("Set", 1, key="wcs"); r = st.number_input("Rep", 1, key="wcr"); w = st.number_input("Kg", 0.0, key="wcw")
            if st.button("Aggiungi Set", key="w_cali_b"): 
                st.session_state['sess_w'].append({"type":"calisthenics","nome":nm,"serie":s,"reps":r,"kg":w})

        # --- MODO ISOMETRIA (NEW) ---
        elif mod == "Isometria":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_iso, key="w_iso_sl")
            nm = st.text_input("Nome", key="w_iso_nm") if sl == "-- Nuovo --" else sl
            
            c_i1, c_i2 = st.columns(2)
            s = c_i1.number_input("Set", 1, key="wis")
            t = c_i2.number_input("Tempo (sec)", 10, step=5, key="wit")
            
            if st.button("Aggiungi Iso", key="w_iso_b"): 
                st.session_state['sess_w'].append({"type":"isometria","nome":nm,"serie":s,"tempo":t})
            
            with st.expander("Salva nel DB"):
                if st.button("Salva Iso", key="wds_iso"): 
                    save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Isometria"}])], ignore_index=True))
                    st.rerun()

        # --- MODO ABS (NEW) ---
        elif mod == "Abs":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_abs, key="w_abs_sl")
            nm = st.text_input("Nome", key="w_abs_nm") if sl == "-- Nuovo --" else sl
            
            s = st.number_input("Set", 3, key="was")
            r = st.number_input("Reps", 15, step=5, key="war")
            
            if st.button("Aggiungi Abs", key="w_abs_b"): 
                st.session_state['sess_w'].append({"type":"abs","nome":nm,"serie":s,"reps":r})
            
            with st.expander("Salva nel DB"):
                if st.button("Salva Abs", key="wds_abs"): 
                    save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Abs"}])], ignore_index=True))
                    st.rerun()

        # --- MODO CARDIO ---
        else: 
            nm = st.text_input("Nome", "Corsa", key="ca_nm")
            km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
            if st.button("Aggiungi Cardio", key="cb"): 
                st.session_state['sess_w'].append({"type":"cardio","nome":nm,"km":km,"tempo":mi,"kcal":kc})

    with c2:
        st.subheader(f"In Corso: {ses}")
        if st.session_state['sess_w']:
            for i,e in enumerate(st.session_state['sess_w']):
                # --- LOGICA DISPLAY IN SESSIONE ---
                typ = e.get('type', 'pesi')
                if typ == 'cardio': 
                    det = f"{e.get('km')}km in {e.get('tempo')}min"
                elif typ == 'isometria':
                    det = f"{e.get('serie')} set x {e.get('tempo')} sec"
                elif typ == 'abs':
                    det = f"{e.get('serie')} set x {e.get('reps')} reps"
                else:
                    det = f"{e.get('serie',0)}x{e.get('reps',0)} @ {e.get('kg',0)}kg"
                
                c_txt, c_del = st.columns([5,1])
                c_txt.markdown(f"**{e['nome']}** : {det}")
                if c_del.button("❌", key=f"del_w_sess_{i}"): 
                    st.session_state['sess_w'].pop(i)
                    st.rerun()
            
            st.divider()
            du = st.number_input("Durata (min)", 0, step=5, key="wdur")
            
            if st.button("TERMINA & SALVA", type="primary", use_container_width=True):
                add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']}, data_filtro)
                st.session_state['sess_w'] = []
                st.toast("Workout Salvato! 💪", icon="🔥")
                time.sleep(1.5) 
                st.rerun()
        else: 
            st.info("Aggiungi il primo esercizio.")

# --- TAB 4: STORICO ---
with tab4:
    if misure_list: st.dataframe(pd.DataFrame(misure_list), use_container_width=True)
    else: st.info("Nessuna misurazione.")
    
    with st.expander("Misure Complete"):
        c1,c2 = st.columns(2)
        p=c1.number_input("Peso", key="ms_p"); a=c2.number_input("Altezza", key="ms_a")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="ms_co"); vi=c4.number_input("Vita", key="ms_vi"); fi=c5.number_input("Fianchi", key="ms_fi")
        if st.button("Salva Misure", key="fs"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi}, data_filtro)
            st.success("Misure salvate")
            st.rerun()

# --- TAB 5: SKILLS ---
with tab5:
    st.subheader("🤸 Skills")
    with st.expander("➕ Nuova Skill", expanded=True):
        with st.form("f_cali"):
            c1, c2 = st.columns([2, 1])
            n_sk = c1.text_input("Skill")
            u_sk = c2.text_input("Link Foto")
            d_sk = st.text_area("Note")
            if st.form_submit_button("Salva"):
                if n_sk: 
                    add_riga_diario("calisthenics", {"nome": n_sk, "desc": d_sk, "url": u_sk}, data_filtro)
                    st.rerun()
    
    skills = []
    if not df.empty:
        for i, r in df.iterrows():
            if r['tipo'] == 'calisthenics':
                try:
                    d = safe_parse_json(r['dettaglio_json'])
                    d['idx'] = i; d['dt'] = r['data']
                    skills.append(d)
                except: pass
    
    if skills:
        for s in reversed(skills):
            with st.container(border=True):
                ci, ct = st.columns([1, 3])
                with ci:
                    if s.get('url'): st.image(s['url'], use_container_width=True)
                with ct:
                    c_h, c_d = st.columns([5, 1])
                    c_h.markdown(f"### {s['nome']}")
                    if c_d.button("🗑️", key=f"dc_{s['idx']}"): delete_riga(s['idx']); st.rerun()
                    st.caption(f"📅 {s['dt']}")
                    st.write(s['desc'])
    else: st.info("Nessuna skill registrata.")

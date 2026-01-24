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

    /* 2. CONTAINER & CARD SYSTEM (GLASS EFFECT) */
    div[data-testid="stContainer"], div[data-testid="stExpander"] {
        background-color: var(--card-bg);
        border-radius: 16px;
        border: 1px solid var(--border-light);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="stContainer"]:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-color: #BFDBFE; /* Light Blue Border on Hover */
        transform: translateY(-2px);
    }

    /* 3. INPUT FIELDS - MODERN & CLEAN */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        padding-left: 12px;
        background-color: #F9FAFB;
        transition: all 0.2s ease;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
        border-color: var(--primary) !important;
        background-color: #FFFFFF;
        box-shadow: 0 0 0 3px rgba(0, 81, 255, 0.1) !important;
    }

    /* 4. BUTTONS - HIGH PERFORMANCE LOOK */
    button[kind="primary"] {
        background: linear-gradient(145deg, var(--primary) 0%, var(--primary-hover) 100%) !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        padding: 0.5rem 1rem !important;
        box-shadow: 0 4px 12px rgba(0, 81, 255, 0.25);
        transition: transform 0.1s ease, box-shadow 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 6px 16px rgba(0, 81, 255, 0.4);
        transform: translateY(-1px);
    }
    button[kind="primary"]:active { transform: scale(0.97) !important; }
    
    button[kind="secondary"] {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        background: transparent !important;
        color: var(--text-main) !important;
    }

    /* 5. TABS RESTYLING */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        gap: 16px;
        border-bottom: 1px solid #E5E7EB;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border: none !important;
        background: transparent !important;
        padding: 8px 16px;
        font-weight: 600;
        color: #9CA3AF;
        transition: color 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary) !important;
    }

    /* 6. METRICS & PROGRESS */
    div[data-testid="stMetricValue"] {
        font-weight: 800 !important;
        color: var(--primary) !important;
        font-size: 1.8rem !important;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(90deg, #0051FF, #60A5FA);
        border-radius: 10px;
    }
    
    /* SIDEBAR POLISH */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
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
    except Exception as e:
        return pd.DataFrame()

def get_data(sheet): return fetch_data_cached(sheet)

def save_data(sheet, df):
    # UX: Feedback di caricamento per evitare click multipli
    with st.spinner(f"💾 Salvataggio in corso su {sheet}..."):
        df = df.fillna("") 
        try:
            conn.update(worksheet=sheet, data=df)
            fetch_data_cached.clear()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Errore DB: {e}")

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
    with st.spinner("🗑️ Eliminazione riga..."):
        df = get_data("diario")
        if idx in df.index:
            save_data("diario", df.drop(idx))
        else:
            st.warning("Impossibile trovare la riga. Ricarico...")
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

# === GAMIFICATION ENGINE V2 (LEVEL + STREAK) ===
def calculate_user_status(df):
    if df.empty: return 1, 0, 0.0, 100, 0
    
    # XP Calc
    xp = 0
    xp += len(df[df['tipo'] == 'pasto']) * 5
    xp += len(df[df['tipo'] == 'allenamento']) * 20
    xp += len(df[df['tipo'] == 'misure']) * 10
    xp += len(df[df['tipo'] == 'acqua']) * 2
    
    level = 1 + (xp // 500)
    current_xp = xp % 500
    progress = current_xp / 500
    
    # Streak Calc
    streak = 0
    try:
        unique_dates = sorted(pd.to_datetime(df['data']).dt.date.unique(), reverse=True)
        today = datetime.date.today()
        
        if unique_dates:
            # Se l'ultimo inserimento è oggi o ieri, la streak è attiva
            if unique_dates[0] == today:
                streak = 1
                check_idx = 1
            elif unique_dates[0] == today - datetime.timedelta(days=1):
                streak = 1
                check_idx = 1 # Inizia a controllare da ieri in giù
            else:
                streak = 0
                check_idx = 0
                
            # Conta all'indietro
            if streak > 0 and len(unique_dates) > 1:
                current_check = unique_dates[0] 
                for prev_date in unique_dates[1:]:
                    if prev_date == current_check - datetime.timedelta(days=1):
                        streak += 1
                        current_check = prev_date
                    else:
                        break
    except:
        streak = 0

    return level, xp, progress, int(current_xp), streak

def clear_form_state(keys_to_clear):
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

# Caricamento Dati Iniziale
df = get_data("diario")
user_settings = get_user_settings()

# --- 1. SEZIONE FOTO PROFILO (SOLO FOTO) ---
    if url_avatar:
        # Foto Grande Verticale Pulita
        st.markdown(f"""
        <div style="display:flex; justify-content:center; margin-bottom: 15px;">
            <div style="
                width: 180px; 
                height: 250px; 
                background-image: url('{url_avatar}'); 
                background-size: cover; 
                background-position: center top; 
                border-radius: 12px; 
                border: 2px solid #E5E7EB;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            "></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tasto Full Screen
        if st.button("🔍 Ingrandisci", use_container_width=True):
            @st.dialog("Target Physique", width="large")
            def show_full_image():
                st.image(url_avatar, use_container_width=True)
            show_full_image()
            
    else:
        # Placeholder se non c'è foto
        st.markdown("""
        <div style="text-align:center; padding: 20px; border: 2px dashed #E5E7EB; border-radius: 12px; color: #9CA3AF; margin-bottom: 15px;">
            <div style="font-size: 40px; margin-bottom: 10px;">👤</div>
            <div style="font-size: 12px; font-weight: 600;">Nessuna Foto</div>
        </div>
        """, unsafe_allow_html=True)

    # --- 2. STATISTICHE LIVELLO (Sotto la foto) ---
    st.write("") # Spaziatore
    
    col_lvl, col_info = st.columns([1, 2])
    with col_lvl:
        st.markdown(f"<h1 style='margin:0; text-align:center; color:#0051FF; font-size:36px;'>{lvl}</h1>", unsafe_allow_html=True)
    with col_info:
        st.markdown("**Livello Atleta**")
        st.caption("Elite Performance")
    
    st.progress(prog)
    
    c_xp, c_fire = st.columns([2,1])
    c_xp.caption(f"🚀 XP: {curr_xp} / 500")
    if streak_count > 0:
        c_fire.markdown(f"🔥 **{streak_count}**")

    st.markdown("---")
    st.markdown("**📅 Calendario**")
    selected_date = st.date_input("Seleziona data:", datetime.date.today(), label_visibility="collapsed")
    data_filtro = selected_date.strftime("%Y-%m-%d")
    
    with st.expander("🎯 Modifica Target"):
        with st.form("target_form"):
            tc = st.number_input("Kcal", value=int(user_settings['target_cal']))
            tp = st.number_input("Pro", value=int(user_settings['target_pro']))
            tca = st.number_input("Carb", value=int(user_settings['target_carb']))
            tf = st.number_input("Fat", value=int(user_settings['target_fat']))
            if st.form_submit_button("Salva Target"):
                ns = user_settings.copy(); ns.update({"target_cal":tc,"target_pro":tp,"target_carb":tca,"target_fat":tf})
                add_riga_diario("settings", ns, data_filtro); st.rerun()

    with st.expander("📸 Foto Profilo"):
        nu = st.text_input("URL Immagine", key="s_url")
        if st.button("Aggiorna Foto"):
            if nu:
                ns = user_settings.copy(); ns['url_foto'] = nu
                add_riga_diario("settings", ns, data_filtro); st.rerun()

    st.markdown("---")
    w_fast = st.number_input("Peso Rapido (kg)", 0.0, format="%.1f", key="side_w_f")
    if st.button("Salva Peso", key="side_btn_w", type="primary", use_container_width=True):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast}, data_filtro)
            st.toast("Peso salvato!"); st.rerun()

    st.markdown("---")
    q_ai = st.text_input("Coach AI...", key="s_ai")
    if st.button("Chiedi", key="s_aibtn"):
        if "chat" not in st.session_state: st.session_state.chat = []
        st.session_state.chat.append({"role":"user","txt":q_ai})
        ans="Errore AI"; 
        if gemini_ok:
            try: ans=model.generate_content(f"Sei un PT esperto. Rispondi brevemente a: {q_ai}").text
            except: pass
        st.session_state.chat.append({"role":"assistant","txt":ans}); st.rerun()
    
    if "chat" in st.session_state and st.session_state.chat:
        st.info(st.session_state.chat[-1]['txt'])

# ==========================================
# 🏠 MAIN DASHBOARD
# ==========================================
c_header_txt, c_header_img = st.columns([4, 1])
with c_header_txt:
    st.title(f"Bentornato, Atleta.")
    st.caption(f"📅 Riepilogo del: {data_filtro}")

# Preparazione Dati
misure_list = []
if not df.empty:
    for _, r in df.iterrows():
        if r['tipo'] == 'misure':
            try:
                d = safe_parse_json(r['dettaglio_json'])
                if d and 'peso' in d: misure_list.append({"Data": r['data'], "Peso": float(d['peso'])})
            except: pass

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Calisthenics"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df_oggi = df[df['data'] == data_filtro] if not df.empty else pd.DataFrame()
    cal = pro = carb = fat = 0
    meal_groups = {"Colazione": [], "Pranzo": [], "Cena": [], "Spuntino": [], "Integrazione": []}
    allenamenti = []
    water_today = 0
    
    if not df_oggi.empty:
        for i, r in df_oggi.iterrows():
            try:
                d = safe_parse_json(r['dettaglio_json'])
                d['idx'] = i 
                if r['tipo'] == 'pasto':
                    cal += d.get('cal',0); pro += d.get('pro',0); carb += d.get('carb',0); fat += d.get('fat',0)
                    cat = d.get('pasto', 'Spuntino')
                    if cat in meal_groups: meal_groups[cat].append(d)
                    else: meal_groups["Spuntino"].append(d)
                elif r['tipo'] == 'allenamento': allenamenti.append(d)
                elif r['tipo'] == 'acqua': water_today += d.get('ml', 0)
            except: pass

    # HERO SECTION
    TC = user_settings['target_cal']
    perc_cal = min(cal / TC, 1.0) if TC > 0 else 0
    delta_cal = TC - cal
    state_color = "#0051FF" if delta_cal >= 0 else "#EF4444"
    bg_state = "#E5F0FF" if delta_cal >= 0 else "#FEE2E2"

    c_hero_1, c_hero_2, c_hero_3 = st.columns([1.5, 1, 1])
    
    with c_hero_1:
        with st.container(border=True):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
                <div>
                    <span style="color:#6B7280; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:1px;">Daily Calories</span>
                    <div style="display:flex; align-items:baseline; gap:8px;">
                        <h1 style="margin:0; font-size:32px; font-weight:800; color:#1F2937;">{int(cal)}</h1>
                        <span style="font-size:16px; color:#9CA3AF; font-weight:500;">/ {int(TC)}</span>
                    </div>
                </div>
                <div style="background:{bg_state}; padding:6px 14px; border-radius:20px; border:1px solid {state_color}20;">
                    <span style="color:{state_color}; font-weight:700; font-size:14px;">{int(delta_cal)} left</span>
                </div>
            </div>
            <div style="width:100%; background:#F3F4F6; height:8px; border-radius:10px; overflow:hidden;">
                <div style="width:{perc_cal*100}%; background:linear-gradient(90deg, #0051FF, #00C6FF); height:100%; border-radius:10px;"></div>
            </div>
            """, unsafe_allow_html=True)

    with c_hero_2:
        with st.container(border=True):
            TP = user_settings['target_pro']
            st.metric("Proteine", f"{int(pro)}g", f"{int(TP - pro)}g left", delta_color="normal")
            st.progress(min(pro/TP, 1.0) if TP > 0 else 0)
            
    with c_hero_3:
        with st.container(border=True):
            st.markdown("**💧 Acqua**")
            cw1, cw2 = st.columns([1, 2])
            with cw1:
                if st.button("➕", key="btn_w_quick", help="Aggiungi 250ml"):
                    add_riga_diario("acqua", {"ml": 250}, data_filtro)
                    st.toast("Idratazione +250ml"); time.sleep(0.5); st.rerun()
            with cw2: st.caption(f"{int(water_today)} / 2500 ml")
            st.progress(min(water_today / 2500, 1.0))

    col_vis, col_kpi = st.columns([1, 1])
    with col_vis:
         st.caption("Carboidrati")
         st.progress(min(carb/user_settings['target_carb'], 1.0) if user_settings['target_carb'] > 0 else 0)
         st.caption(f"{int(carb)} / {user_settings['target_carb']}g")
    with col_kpi:
         st.caption("Grassi")
         st.progress(min(fat/user_settings['target_fat'], 1.0) if user_settings['target_fat'] > 0 else 0)
         st.caption(f"{int(fat)} / {user_settings['target_fat']}g")
    
    st.divider()
    
    # CHART SECTION (CLEANER)
    if misure_list:
        df_w = pd.DataFrame(misure_list)
        df_w['Data'] = pd.to_datetime(df_w['Data'])
        df_w = df_w.sort_values('Data')
        
        base = alt.Chart(df_w).encode(x=alt.X('Data:T', axis=alt.Axis(format='%d/%m', title='', grid=False)))
        line = base.mark_line(color='#0051FF', strokeWidth=3).encode(y=alt.Y('Peso:Q', scale=alt.Scale(zero=False, padding=5), title='Kg'))
        area = base.mark_area(opacity=0.1, color='#0051FF').encode(y=alt.Y('Peso:Q', scale=alt.Scale(zero=False, padding=5)))
        points = base.mark_circle(size=60, color='white', stroke='#0051FF', strokeWidth=2).encode(
            y=alt.Y('Peso:Q'), tooltip=[alt.Tooltip('Data:T', format='%d %B'), alt.Tooltip('Peso:Q', format='.1f')]
        )
        chart_w = (area + line + points).properties(height=280, background='transparent').interactive()
        
        st.subheader("📉 Trend Peso")
        with st.container(border=True):
            st.altair_chart(chart_w, use_container_width=True)
    
    st.divider()
    
    # DIARY LISTS
    cl1, cl2 = st.columns(2)
    with cl1:
        st.subheader("🍎 Diario Oggi")
        found_meals = False
        for cat in ["Colazione", "Pranzo", "Cena", "Spuntino", "Integrazione"]:
            items = meal_groups[cat]
            if items:
                found_meals = True
                sub_cal = sum(x['cal'] for x in items)
                with st.expander(f"**{cat}** • {int(sub_cal)} kcal", expanded=True):
                    for p in items:
                        r1, r2 = st.columns([4, 1])
                        r1.markdown(f"**{p['nome']}** • <span style='color:#6B7280'>{int(p.get('gr',0))}{p.get('unita','g')}</span>", unsafe_allow_html=True)
                        r1.caption(f"P:{int(p['pro'])} C:{int(p['carb'])} F:{int(p['fat'])}")
                        if r2.button("✖️", key=f"del_p_{p['idx']}"): delete_riga(p['idx']); st.rerun()
        if not found_meals: st.info("Nessun pasto registrato oggi.")

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
                            if t == "pesi": det = f"**{ex['kg']}kg** x {ex['serie']}x{ex['reps']}"
                            elif t == "isometria": 
                                zav = f" +**{ex.get('kg',0)}kg**" if ex.get('kg',0) > 0 else ""
                                det = f"⏱️ {ex['tempo']}s{zav} x {ex['serie']}"
                            elif t == "abs": 
                                zav = f" +**{ex.get('kg',0)}kg**" if ex.get('kg',0) > 0 else ""
                                det = f"🔥 {ex['serie']}x{ex['reps']}{zav}"
                            elif t == "calisthenics": det = f"bw+{ex.get('kg',0)}kg x {ex['serie']}x{ex['reps']}"
                            else: det = f"{ex['km']}km"
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
        st.subheader("🍽️ Inserimento Pasti")
        cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
        
        def update_macro_values():
            base = st.session_state.get('base_food', {'k':0,'p':0,'c':0,'f':0})
            factor = st.session_state.get('f_gr', 0.0) / 100
            st.session_state['fk'] = base['k'] * factor
            st.session_state['fp'] = base['p'] * factor
            st.session_state['fc'] = base['c'] * factor
            st.session_state['ff'] = base['f'] * factor

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
            
            base = st.session_state.get('base_int', {'k':0,'p':0,'c':0,'f':0})
            tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], horizontal=True, key="i_rad")
            u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
            
            with st.container(border=True):
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", key="i_nm")
                q = c2.number_input(f"Qta ({u})", step=1.0, key="i_q") 
                val_k = base['k'] * q; val_p = base['p'] * q; val_c = base['c'] * q; val_f = base['f'] * q
                st.caption(f"Totale: {int(val_k)} kcal | P:{int(val_p)} C:{int(val_c)} F:{int(val_f)}")
                
                if st.button("Aggiungi Integratore", type="primary", use_container_width=True, key="bi"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":q,"unita":u,"cal":val_k,"pro":val_p,"carb":val_c,"fat":val_f}, data_filtro)
                        clear_form_state(["i_nm", "i_q"]); st.rerun()

        else:
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
                            if st.session_state.get('f_gr', 0) > 0: update_macro_values()
                        except: pass
                
                c1, c2 = st.columns([2,1])
                nom = c1.text_input("Nome Alimento", key="f_nm")
                gr = c2.number_input("Quantità (g)", step=10.0, key="f_gr", on_change=update_macro_values)
                
                st.divider()
                st.caption("Valori Nutrizionali Calcolati")
                m1,m2,m3,m4 = st.columns(4)
                k=m1.number_input("Kcal", key="fk", step=1.0)
                p=m2.number_input("Pro", key="fp", step=0.1)
                c=m3.number_input("Carb", key="fc", step=0.1)
                f=m4.number_input("Fat", key="ff", step=0.1)
                
                st.write("")
                if st.button("🍽️ Aggiungi Pasto", type="primary", use_container_width=True, key="bf"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f}, data_filtro)
                        st.success("Aggiunto!"); clear_form_state(["f_nm", "f_gr", "fk", "fp", "fc", "ff"]); st.rerun()

    with c_db:
        st.subheader("💾 Database")
        df_ex_gestione = get_data("esercizi") 
        if df_ex_gestione.empty: df_ex_gestione = pd.DataFrame(columns=["nome", "categoria"])
        
        t_cibo, t_int, t_ex = st.tabs(["Cibo", "Int", "Ex"])
        
        with t_cibo:
            with st.form("dbf"):
                n=st.text_input("Nome", key="dbn")
                r1, r2 = st.columns(2)
                k=r1.number_input("K/100", key="dbk"); p=r2.number_input("P", key="dbp")
                c=r1.number_input("C", key="dbc"); f=r2.number_input("F", key="dbf")
                if st.form_submit_button("Salva Cibo"):
                    if n: save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()
            
            with st.expander("🗑️ Elimina"):
                if not df_cibi.empty:
                    to_del = st.multiselect("Seleziona", df_cibi['nome'].tolist(), key="del_food_m")
                    if st.button("Elimina", key="btn_del_f"):
                        save_data("cibi", df_cibi[~df_cibi['nome'].isin(to_del)]); st.rerun()

        with t_int:
            with st.form("dbi"):
                ni=st.text_input("Nome", key="dbi_n")
                r1, r2 = st.columns(2)
                ki=r1.number_input("K", key="dbi_k"); pi=r2.number_input("P", key="dbi_p")
                ci=r1.number_input("C", key="dbi_c"); fi=r2.number_input("F", key="dbi_f")
                if st.form_submit_button("Salva Int"):
                    if ni: save_data("integratori", pd.concat([df_int, pd.DataFrame([{"nome":ni,"tipo":"g","kcal":ki,"pro":pi,"carb":ci,"fat":fi}])], ignore_index=True)); st.rerun()

        with t_ex:
            st.caption("Aggiungi Esercizi (Bulk)")
            bulk_text = st.text_area("Lista (uno per riga)", height=100, key="bulk_ex")
            cat_bulk = st.selectbox("Categoria", ["Pesi", "Calisthenics", "Isometria", "Cardio"], key="cat_bulk")
            if st.button("Salva Lista"):
                if bulk_text:
                    lista = [x.strip() for x in bulk_text.split('\n') if x.strip()]
                    if lista:
                        new_rows = pd.DataFrame({'nome': lista, 'categoria': cat_bulk})
                        save_data("esercizi", pd.concat([df_ex_gestione, new_rows], ignore_index=True)); st.rerun()

# --- TAB 3: WORKOUT ---
with tab3:
    st.subheader("🏋️ Workout Session")
    df_ex = get_data("esercizi")
    if df_ex.empty: df_ex = pd.DataFrame(columns=["nome", "categoria"])
    elif "categoria" not in df_ex.columns: df_ex["categoria"] = "Pesi"
    
    ls_pesi = sorted(df_ex[df_ex['categoria'] == 'Pesi']['nome'].unique().tolist())
    ls_cali = sorted(df_ex[df_ex['categoria'] == 'Calisthenics']['nome'].unique().tolist())
    ls_iso  = sorted(df_ex[df_ex['categoria'] == 'Isometria']['nome'].unique().tolist())
    ls_abs  = sorted(df_ex[df_ex['categoria'] == 'Abs']['nome'].unique().tolist())
    
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    c1, c2 = st.columns([1,2])
    with c1:
        with st.container(border=True):
            st.markdown("#### Configurazione")
            ses = st.text_input("Nome Sessione", "Workout", key="w_ses")
            mod = st.radio("Tipologia", ["Pesi", "Calisthenics", "Isometria", "Abs", "Cardio"], horizontal=True, key="w_mod")
            st.divider()
            
            if mod == "Pesi":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_pesi, key="w_sl")
                nm = st.text_input("Nome", key="w_nm") if sl == "-- Nuovo --" else sl
                c_set, c_rep, c_kg = st.columns(3)
                s=c_set.number_input("Set",1,key="ws"); r=c_rep.number_input("Rep",1,key="wr"); w=c_kg.number_input("Kg",0.0,key="ww")
                if st.button("Aggiungi Set", key="wb", type="primary", use_container_width=True): 
                    st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
                
                with st.expander("Salva nuovo esercizio"):
                    if st.button("Salva nel DB", key="wds"): 
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Pesi"}])], ignore_index=True)); st.rerun()

            elif mod == "Calisthenics":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_cali, key="w_cali_sl")
                nm = st.text_input("Nome", key="w_cali_nm") if sl == "-- Nuovo --" else sl
                s = st.number_input("Set", 1, key="wcs"); r = st.number_input("Rep", 1, key="wcr"); w = st.number_input("Kg", 0.0, key="wcw")
                if st.button("Aggiungi Set", key="w_cali_b", type="primary", use_container_width=True): 
                    st.session_state['sess_w'].append({"type":"calisthenics","nome":nm,"serie":s,"reps":r,"kg":w})

            elif mod == "Isometria":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_iso, key="w_iso_sl")
                nm = st.text_input("Nome", key="w_iso_nm") if sl == "-- Nuovo --" else sl
                c_i1, c_i2, c_i3 = st.columns(3)
                s = c_i1.number_input("Set", 1, key="wis"); t = c_i2.number_input("Sec", 10, step=5, key="wit"); z = c_i3.number_input("Kg", 0.0, step=0.5, key="wiz")
                if st.button("Aggiungi Iso", key="w_iso_b", type="primary", use_container_width=True): 
                    st.session_state['sess_w'].append({"type":"isometria","nome":nm,"serie":s,"tempo":t,"kg":z})
                
                with st.expander("Salva nuovo esercizio"):
                    if st.button("Salva nel DB", key="wds_iso"): 
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Isometria"}])], ignore_index=True)); st.rerun()

            elif mod == "Abs":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_abs, key="w_abs_sl")
                nm = st.text_input("Nome", key="w_abs_nm") if sl == "-- Nuovo --" else sl
                c_a1, c_a2, c_a3 = st.columns(3)
                s = c_a1.number_input("Set", 3, key="was"); r = c_a2.number_input("Reps", 15, step=5, key="war"); z = c_a3.number_input("Kg", 0.0, step=1.0, key="waz")
                if st.button("Aggiungi Abs", key="w_abs_b", type="primary", use_container_width=True): 
                    st.session_state['sess_w'].append({"type":"abs","nome":nm,"serie":s,"reps":r,"kg":z})
                
                with st.expander("Salva nuovo esercizio"):
                    if st.button("Salva nel DB", key="wds_abs"): 
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Abs"}])], ignore_index=True)); st.rerun()

            else: 
                nm = st.text_input("Nome", "Corsa", key="ca_nm")
                km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
                if st.button("Aggiungi Cardio", key="cb", type="primary", use_container_width=True): 
                    st.session_state['sess_w'].append({"type":"cardio","nome":nm,"km":km,"tempo":mi,"kcal":kc})

    with c2:
        st.info(f"⚡ In Corso: {ses}")
        if st.session_state['sess_w']:
            for i,e in enumerate(st.session_state['sess_w']):
                typ = e.get('type', 'pesi')
                kg_val = e.get('kg', 0)
                zav_str = f" +{kg_val}kg" if kg_val > 0 else ""
                
                if typ == 'cardio': det = f"{e.get('km')}km in {e.get('tempo')}min"
                elif typ == 'isometria': det = f"{e.get('serie')} set x {e.get('tempo')}s{zav_str}"
                elif typ == 'abs': det = f"{e.get('serie')} set x {e.get('reps')} reps{zav_str}"
                else: det = f"{e.get('serie',0)}x{e.get('reps',0)} @ {kg_val}kg"
                
                with st.container(border=True):
                    c_txt, c_del = st.columns([5,1])
                    c_txt.markdown(f"**{e['nome']}** : {det}")
                    if c_del.button("❌", key=f"del_w_sess_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
            
            st.divider()
            du = st.number_input("Durata Totale (min)", 0, step=5, key="wdur")
            if st.button("💾 TERMINA & SALVA WORKOUT", type="primary", use_container_width=True):
                add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']}, data_filtro)
                st.session_state['sess_w'] = []
                st.toast("Workout Salvato! 💪", icon="🔥"); time.sleep(1.5); st.rerun()
        else: 
            st.write("Nessun esercizio aggiunto.")

# --- TAB 4: STORICO (IMPROVED) ---
with tab4:
    st.subheader("📏 Storico e Misure")
    
    if misure_list:
        df_history = pd.DataFrame(misure_list)
        df_history['Data'] = pd.to_datetime(df_history['Data']).dt.date
        df_history = df_history.sort_values('Data', ascending=False)
        
        st.dataframe(
            df_history,
            use_container_width=True,
            column_config={
                "Data": st.column_config.DateColumn("Data Pesata", format="DD/MM/YYYY"),
                "Peso": st.column_config.ProgressColumn(
                    "Peso Corporeo",
                    help="Il tuo peso attuale",
                    format="%.1f kg",
                    min_value=40,
                    max_value=120,
                ),
            },
            hide_index=True
        )
    else: 
        st.info("Nessuna misurazione trovata.")

    with st.expander("📝 Registra Misure Complete"):
        c1,c2 = st.columns(2)
        p=c1.number_input("Peso", key="ms_p"); a=c2.number_input("Altezza", key="ms_a")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="ms_co"); vi=c4.number_input("Vita", key="ms_vi"); fi=c5.number_input("Fianchi", key="ms_fi")
        if st.button("Salva Misure", key="fs"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi}, data_filtro)
            st.success("Misure salvate"); st.rerun()

# --- TAB 5: SKILLS ---
with tab5:
    st.subheader("🤸 Skills & Progressioni")
    with st.expander("➕ Nuova Skill", expanded=True):
        with st.form("f_cali"):
            c1, c2 = st.columns([2, 1])
            n_sk = c1.text_input("Nome Skill")
            u_sk = c2.text_input("Link Foto/Video")
            d_sk = st.text_area("Note e Progressione")
            if st.form_submit_button("Salva Skill"):
                if n_sk: add_riga_diario("calisthenics", {"nome": n_sk, "desc": d_sk, "url": u_sk}, data_filtro); st.rerun()
    
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

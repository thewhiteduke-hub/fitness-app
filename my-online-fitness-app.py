import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V14.5 - PREMIUM UI)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* 1. RESET GENERALE & FONTS */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #F0F2F6; /* Grigio leggermente più freddo */
        color: #171717;
    }

    /* 2. TITOLI E TESTI */
    h1, h2, h3 {
        color: #111827 !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    h4, h5, h6, p, div, span, label {
        color: #374151 !important;
    }
    
    /* 3. CARD DESIGN (Sostituisce il container standard) */
    div[data-testid="stContainer"] {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #E5E7EB; /* Bordo sottile grigio */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    
    /* Rimuove stile card dai container interni non necessari */
    div[data-testid="stContainer"] div[data-testid="stContainer"] {
        box-shadow: none;
        border: none;
        padding: 0;
    }

    /* 4. SIDEBAR PIÙ PULITA */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #E5E7EB;
    }
    section[data-testid="stSidebar"] div[data-testid="stContainer"] {
        box-shadow: none; 
        border: none;
    }

    /* 5. FIX CRITICO INPUT & SELECTBOX (Leggibilità) */
    /* Forza sfondo bianco e testo scuro per tutti gli input */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #111827 !important;
        border-radius: 8px;
        border: 1px solid #D1D5DB !important;
    }
    
    /* Menu a tendina (Dropdown) */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul {
        background-color: #ffffff !important;
    }
    li[role="option"], div[role="option"] {
        color: #111827 !important; 
        background-color: #ffffff !important;
    }
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: #EFF6FF !important; /* Azzurro chiarissimo hover */
        color: #0051FF !important;
        font-weight: 600;
    }
    
    /* Labels degli input */
    div[data-testid="stWidgetLabel"] p {
        font-weight: 600;
        font-size: 0.9rem;
        color: #4B5563 !important;
    }

    /* 6. METRICHE & KPI */
    div[data-testid="stMetricValue"] {
        color: #0051FF !important; /* Blu Elettrico */
        font-weight: 800;
        font-size: 1.8rem !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #6B7280 !important;
        font-size: 0.9rem;
    }

    /* 7. BOTTONI */
    /* Primary */
    button[kind="primary"] {
        background-color: #0051FF !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    button[kind="primary"]:hover {
        background-color: #003ECC !important;
        box-shadow: 0 4px 12px rgba(0, 81, 255, 0.3);
    }
    /* Secondary */
    button[kind="secondary"] {
        border: 1px solid #D1D5DB;
        color: #374151;
        border-radius: 8px;
    }

    /* 8. TAB NAVIGATION */
    div[data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    div[data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px 8px 0 0;
        border: 1px solid #E5E7EB;
        padding: 10px 20px;
    }
    div[aria-selected="true"] {
        background-color: #0051FF !important;
        color: white !important;
    }
    
    img { border-radius: 12px; }
    
    /* Separatore */
    hr { margin: 1.5em 0; border-color: #E5E7EB; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
# ==========================================
def check_password():
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    if "APP_PASSWORD" not in st.secrets: return True
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown("### 🔒 Accesso Atleta")
            st.text_input("Password", type="password", on_change=password_entered, key="pwd_login_14")
    return False

def password_entered():
    if st.session_state["pwd_login_14"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["pwd_login_14"]
    else: st.error("Password errata")

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
# 🚀 DATABASE ENGINE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def fetch_data_cached(sheet_name):
    try: return conn.read(worksheet=sheet_name)
    except: return pd.DataFrame()

def get_data(sheet): return fetch_data_cached(sheet)

def save_data(sheet, df):
    df = df.fillna("") 
    conn.update(worksheet=sheet, data=df)
    fetch_data_cached.clear()
    st.cache_data.clear()

def add_riga_diario(tipo, dati):
    df = get_data("diario")
    if df.empty: df = pd.DataFrame(columns=["data", "tipo", "dettaglio_json"])
    data_oggi = datetime.datetime.now().strftime("%Y-%m-%d")
    nuova = pd.DataFrame([{"data": data_oggi, "tipo": tipo, "dettaglio_json": json.dumps(dati)}])
    df_totale = pd.concat([df, nuova], ignore_index=True)
    save_data("diario", df_totale)

def delete_riga(idx):
    df = get_data("diario")
    save_data("diario", df.drop(idx))

def get_oggi(): return datetime.datetime.now().strftime("%Y-%m-%d")

def get_user_settings():
    df = get_data("diario")
    settings = {"url_foto": "", "target_cal": 2500, "target_pro": 180, "target_carb": 300, "target_fat": 80}
    if not df.empty:
        rows = df[df['tipo'] == 'settings']
        if not rows.empty:
            try: settings.update(json.loads(rows.iloc[-1]['dettaglio_json']))
            except: pass
    return settings

# ==========================================
# 📱 SIDEBAR
# ==========================================
user_settings = get_user_settings()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=50)
    st.markdown("### Fit Tracker Pro")
    st.caption("v14.5 - Premium UI")
    
    st.markdown("---")
    st.markdown("#### 📅 Calendario")
    selected_date = st.date_input("Seleziona data", datetime.date.today(), label_visibility="collapsed")
    data_filtro = selected_date.strftime("%Y-%m-%d")
    
    st.markdown("---")
    st.markdown("#### 🎯 Obiettivi Macro")
    with st.expander("Modifica Target"):
        with st.form("target_form"):
            tc = st.number_input("Kcal", value=int(user_settings['target_cal']))
            tp = st.number_input("Pro (g)", value=int(user_settings['target_pro']))
            tca = st.number_input("Carb (g)", value=int(user_settings['target_carb']))
            tf = st.number_input("Fat (g)", value=int(user_settings['target_fat']))
            if st.form_submit_button("Salva Target"):
                ns = user_settings.copy(); ns.update({"target_cal":tc,"target_pro":tp,"target_carb":tca,"target_fat":tf})
                add_riga_diario("settings", ns); st.rerun()

    if user_settings['url_foto']:
        st.markdown("---")
        try: st.image(user_settings['url_foto'], use_container_width=True)
        except: st.error("Link foto errato")
    
    with st.expander("📷 Avatar"):
        nu = st.text_input("URL Immagine", key="s_url")
        if st.button("Aggiorna", key="s_btn"):
            if nu:
                ns = user_settings.copy(); ns['url_foto'] = nu
                add_riga_diario("settings", ns); st.rerun()

    st.markdown("---")
    st.markdown("#### ⚖️ Check-in Peso")
    w_fast = st.number_input("Peso (kg)", 0.0, format="%.1f", key="side_w_f", label_visibility="collapsed")
    if st.button("Salva Peso Rapido", key="side_btn_w", use_container_width=True):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast})
            st.toast("✅ Peso salvato correttamente!"); st.rerun()

    st.markdown("---")
    st.markdown("#### 🤖 AI Coach")
    q_ai = st.text_input("Chiedi al coach...", key="s_ai")
    if st.button("Invia", key="s_aibtn", type="primary", use_container_width=True):
        st.session_state.chat.append({"role":"user","txt":q_ai})
        ans="Errore AI"; 
        if gemini_ok:
            try: ans=model.generate_content(f"Sei un Personal Trainer esperto e motivante. Rispondi brevemente: {q_ai}").text
            except: pass
        st.session_state.chat.append({"role":"assistant","txt":ans}); st.rerun()
    if "chat" not in st.session_state: st.session_state.chat = []
    if st.session_state.chat: 
        st.info(st.session_state.chat[-1]['txt'], icon="🤖")

# ==========================================
# 🏠 MAIN DASHBOARD
# ==========================================
col_header_1, col_header_2 = st.columns([3,1])
with col_header_1:
    st.title(f"Dashboard Atleta")
    st.markdown(f"**Riepilogo giornaliero:** {selected_date.strftime('%d %B %Y')}")

with col_header_2:
    st.write("") # Spacer

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Calisthenics"])

# --- DASHBOARD ---
with tab1:
    df = get_data("diario")
    df_oggi = df[df['data'] == data_filtro] if not df.empty else pd.DataFrame()
    
    cal = pro = carb = fat = 0
    meal_groups = {"Colazione": [], "Pranzo": [], "Cena": [], "Spuntino": [], "Integrazione": []}
    allenamenti = []
    
    if not df_oggi.empty:
        for i, r in df_oggi.iterrows():
            try:
                d = json.loads(r['dettaglio_json']); d['idx'] = i
                if r['tipo'] == 'pasto':
                    cal += d['cal']; pro += d['pro']; carb += d['carb']; fat += d['fat']
                    cat = d.get('pasto', 'Spuntino')
                    if cat in meal_groups: meal_groups[cat].append(d)
                    else: meal_groups["Spuntino"].append(d)
                elif r['tipo'] == 'allenamento':
                    allenamenti.append(d)
            except: pass

    misure_list = []
    curr_peso = "--"
    if not df.empty:
        for _, r in df.iterrows():
            if r['tipo'] == 'misure':
                try:
                    d = json.loads(r['dettaglio_json'])
                    misure_list.append({"Data": r['data'], "Peso": d['peso']})
                    if r['data'] == data_filtro: curr_peso = f"{d['peso']} kg"
                except: pass
    if curr_peso == "--" and misure_list: curr_peso = f"{misure_list[-1]['Peso']} kg"

    # KPI CARDS
    TC = user_settings['target_cal']; TP = user_settings['target_pro']
    
    st.markdown("### 🔥 Daily Stats")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: 
        st.metric("Kcal", int(cal), f"{int(cal-TC)}", delta_color="inverse" if cal > TC else "normal")
        st.progress(min(cal/TC, 1.0) if TC > 0 else 0)
    with k2: 
        st.metric("Proteine", f"{int(pro)}g", f"{int(pro-TP)}", delta_color="normal")
        st.progress(min(pro/TP, 1.0) if TP > 0 else 0)
    with k3: st.metric("Carboidrati", f"{int(carb)}g")
    with k4: st.metric("Grassi", f"{int(fat)}g")
    with k5: st.metric("Peso", curr_peso)

    st.markdown("---")

    # CONTENUTO PRINCIPALE
    c_main_1, c_main_2 = st.columns([1,1])
    
    with c_main_1:
        st.subheader("🍎 Diario Alimentare")
        found_meals = False
        order = ["Colazione", "Pranzo", "Cena", "Spuntino", "Integrazione"]
        
        for cat in order:
            items = meal_groups[cat]
            if items:
                found_meals = True
                sub_cal = sum(x['cal'] for x in items)
                with st.expander(f"**{cat}** — {int(sub_cal)} kcal", expanded=True):
                    for p in items:
                        col_txt, col_act = st.columns([6, 1])
                        qty = f"{int(p.get('gr',0))} {p.get('unita','g')}"
                        col_txt.markdown(f"**{p['nome']}** <span style='color:#6B7280; font-size:0.9em'>({qty})</span>", unsafe_allow_html=True)
                        if col_act.button("🗑️", key=f"del_p_{p['idx']}"): 
                            delete_riga(p['idx']); st.rerun()
        if not found_meals: st.info(f"Nessun pasto registrato per {data_filtro}.")

    with c_main_2:
        st.subheader("🏋️ Scheda Allenamento")
        if allenamenti:
            for w in allenamenti:
                with st.container(border=True):
                    h1, h2 = st.columns([4,1])
                    h1.markdown(f"#### {w.get('nome_sessione','Workout')}")
                    h1.caption(f"⏱️ {w['durata']} min")
                    if h2.button("Elimina", key=f"del_w_{w['idx']}"):
                        delete_riga(w['idx']); st.rerun()
                    
                    if 'esercizi' in w and w['esercizi']:
                        for ex in w['esercizi']:
                            t = ex.get('type', 'pesi')
                            if t == "pesi": det = f"**{ex['serie']}x{ex['reps']}** @ {ex['kg']}kg"
                            elif t == "isometria": det = f"**{ex['serie']}x {ex['tempo']}s** (+{ex.get('kg',0)}kg)"
                            elif t == "calisthenics": det = f"**{ex['serie']}x{ex['reps']}** (+{ex.get('kg',0)}kg)"
                            else: det = f"{ex['km']}km in {ex['tempo']}m"
                            st.markdown(f"🔹 {ex['nome']}: {det}")
                    else: st.caption("Nessun dato esercizi.")
        else:
            st.info(f"Rest day o nessun allenamento il {data_filtro}.")
            
    # GRAFICO PESO (Full Width sotto)
    st.markdown("---")
    st.subheader("📉 Trend Peso Corporeo")
    if misure_list:
        chart = alt.Chart(pd.DataFrame(misure_list)).mark_area(
            line={'color':'#0051FF', 'size':3},
            color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='rgba(0, 81, 255, 0.5)', offset=0), alt.GradientStop(color='rgba(255, 255, 255, 0)', offset=1)], x1=1, x2=1, y1=1, y2=0)
        ).encode(
            x=alt.X('Data:T', axis=alt.Axis(format='%d/%m', title='')),
            y=alt.Y('Peso:Q', scale=alt.Scale(zero=False), title='Kg'),
            tooltip=['Data', 'Peso']
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)

# --- ALIMENTAZIONE ---
with tab2:
    c_in, c_db = st.columns([2,1])
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []
    df_int = get_data("integratori")
    nomi_int = df_int['nome'].tolist() if not df_int.empty else []

    with c_in:
        st.subheader("🍽️ Aggiungi Pasto")
        with st.container(border=True):
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
            
            if cat == "Integrazione":
                sel_i = st.selectbox("Seleziona Integratore", ["-- Manuale --"] + nomi_int, key="search_int")
                if "last_sel_int" not in st.session_state: st.session_state.last_sel_int = None
                if sel_i != st.session_state.last_sel_int:
                    st.session_state.last_sel_int = sel_i
                    if sel_i != "-- Manuale --" and not df_int.empty:
                        try:
                            row = df_int[df_int['nome'] == sel_i].iloc[0]
                            st.session_state['i_nm'] = str(row['nome']) 
                            d_val = row.get('descrizione', '')
                            st.session_state['i_desc_f'] = str(d_val) if pd.notna(d_val) else ""
                            st.session_state['i_q'] = 1.0 
                            st.session_state['base_int'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                            map_tipo = {"g": 0, "cps": 1, "mg": 2}
                            st.session_state['temp_tipo_idx'] = map_tipo.get(row.get('tipo', 'g'), 0)
                        except: pass
                    else: st.session_state['base_int'] = {'k':0,'p':0,'c':0,'f':0}
                
                base = st.session_state.get('base_int', {'k':0,'p':0,'c':0,'f':0})
                tip_idx = st.session_state.get('temp_tipo_idx', 0)
                tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], index=tip_idx, horizontal=True, key="i_rad")
                u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome Integratore", key="i_nm")
                q = c2.number_input(f"Quantità ({u})", step=1.0, key="i_q") 
                desc = st.text_area("Note / Timing", key="i_desc_f", height=80)
                
                val_k = base['k'] * q; val_p = base['p'] * q; val_c = base['c'] * q; val_f = base['f'] * q
                st.session_state['ik'], st.session_state['ip'], st.session_state['ic'], st.session_state['if'] = float(val_k), float(val_p), float(val_c), float(val_f)

                with st.expander("Dettagli Macro"):
                    m1,m2,m3,m4=st.columns(4)
                    k=m1.number_input("Kcal", key="ik"); p=m2.number_input("Pro", key="ip")
                    c=m3.number_input("Carb", key="ic"); f=m4.number_input("Fat", key="if")
                
                if st.button("➕ Aggiungi al Diario", type="primary", use_container_width=True, key="bi"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"desc":desc,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.toast(f"Aggiunto: {nom}"); st.rerun()

            else:
                sel = st.selectbox("Cerca Cibo", ["-- Manuale --"]+nomi_cibi, key="f_sel")
                if "last_sel_food" not in st.session_state: st.session_state.last_sel_food = None
                if sel != st.session_state.last_sel_food:
                    st.session_state.last_sel_food = sel
                    if sel != "-- Manuale --" and not df_cibi.empty:
                        try:
                            row = df_cibi[df_cibi['nome'] == sel].iloc[0]
                            st.session_state['f_nm'] = str(row['nome']) 
                            st.session_state['f_gr'] = 100.0 
                            st.session_state['base_food'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                        except: pass
                    else: st.session_state['base_food'] = {'k':0,'p':0,'c':0,'f':0}
                
                base_f = st.session_state.get('base_food', {'k':0,'p':0,'c':0,'f':0})
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome Alimento", key="f_nm")
                gr = c2.number_input("Grammi", step=10.0, key="f_gr")
                
                fac = gr / 100
                st.session_state['fk'], st.session_state['fp'], st.session_state['fc'], st.session_state['ff'] = base_f['k']*fac, base_f['p']*fac, base_f['c']*fac, base_f['f']*fac
                
                m1,m2,m3,m4=st.columns(4)
                k=m1.number_input("Kcal",key="fk"); p=m2.number_input("Pro",key="fp"); c=m3.number_input("Carb",key="fc"); f=m4.number_input("Fat",key="ff")
                
                if st.button("🍴 Mangia", type="primary", use_container_width=True, key="bf"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.toast(f"Gnam! Hai mangiato {nom}"); st.rerun()

    with c_db:
        st.subheader("💾 Database")
        t_cibo, t_int, t_ex = st.tabs(["Cibo", "Integr", "Bulk Ex"])
        
        with t_cibo:
            st.caption("Valori per 100g")
            with st.form("dbf"):
                n=st.text_input("Nome", key="dbn"); k=st.number_input("Kcal", key="dbk"); p=st.number_input("Pro", key="dbp"); c=st.number_input("Carb", key="dbc"); f=st.number_input("Fat", key="dbf")
                if st.form_submit_button("Salva Cibo"):
                    if n: save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()
        
        with t_int:
            st.caption("Valori per 1 dose/g")
            with st.form("dbi"):
                ni=st.text_input("Nome", key="dbi_n"); di=st.text_area("Desc.", key="dbi_d", height=80)
                ti_sel = st.radio("Tipo", ["Polvere", "Capsula", "Mg"], key="dbi_t")
                c1,c2=st.columns(2)
                ki=c1.number_input("K", key="dbi_k"); pi=c2.number_input("P", key="dbi_p"); ci=c1.number_input("C", key="dbi_c"); fi=c2.number_input("F", key="dbi_f")
                if st.form_submit_button("Salva Integratore"):
                    if ni: save_data("integratori", pd.concat([df_int, pd.DataFrame([{"nome":ni, "tipo":ti_sel, "descrizione":di, "kcal":ki, "pro":pi, "carb":ci, "fat":fi}])], ignore_index=True)); st.rerun()
        
        with t_ex:
            st.caption("Incolla lista esercizi (uno per riga)")
            bulk_text = st.text_area("Lista", height=200, key="bulk_ex_area")
            if st.button("Salva Bulk"):
                if bulk_text:
                    df_current_ex = get_data("esercizi")
                    lista = [x.strip() for x in bulk_text.split('\n') if x.strip()]
                    if lista:
                        new_df = pd.DataFrame({'nome': lista, 'categoria': 'Pesi'})
                        save_data("esercizi", pd.concat([df_current_ex, new_df], ignore_index=True))
                        st.success(f"{len(lista)} Esercizi caricati!"); st.rerun()

# --- WORKOUT ---
with tab3:
    st.subheader("💪 Workout Logger")
    df_ex = get_data("esercizi")
    if df_ex.empty: df_ex = pd.DataFrame(columns=["nome", "categoria"])
    elif "categoria" not in df_ex.columns: df_ex["categoria"] = "Pesi"
    
    ls_pesi = sorted(df_ex[df_ex['categoria'] == 'Pesi']['nome'].tolist())
    ls_cali = sorted(df_ex[df_ex['categoria'] == 'Calisthenics']['nome'].tolist())
    ls_iso = sorted(df_ex[df_ex['categoria'] == 'Isometria']['nome'].tolist())
    ls_cardio = sorted(df_ex[df_ex['categoria'] == 'Cardio']['nome'].tolist())

    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    c1, c2 = st.columns([1, 2])

    with c1:
        with st.container(border=True):
            st.markdown("#### Configurazione")
            ses = st.text_input("Nome Sessione", "Full Body", key="w_ses")
            mod = st.radio("Tipologia", ["Pesi", "Calisthenics", "Isometria", "Cardio"], key="w_mod")
            st.divider()

            if mod == "Pesi":
                sl = st.selectbox("Scegli Esercizio", ["-- Nuovo --"] + ls_pesi, key="w_sl")
                nm = st.text_input("Nome", key="w_nm") if sl == "-- Nuovo --" else sl
                c_a, c_b, c_c = st.columns(3)
                s=c_a.number_input("Set",1,key="ws"); r=c_b.number_input("Rep",1,key="wr"); w=c_c.number_input("Kg",0.0,key="ww")
                
                if st.button("Aggiungi Set", key="wb", type="primary", use_container_width=True): 
                    st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
                
                if st.button("💾 Salva in DB", key="wds", use_container_width=True): 
                    save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Pesi"}])], ignore_index=True)); st.toast("Esercizio salvato!"); st.rerun()

            elif mod == "Calisthenics":
                sl = st.selectbox("Skill / Esercizio", ["-- Nuovo --"] + ls_cali, key="w_cali_sl")
                nm = st.text_input("Nome", key="w_cali_nm") if sl == "-- Nuovo --" else sl
                c_a,c_b,c_c = st.columns(3)
                s = c_a.number_input("Set", 1, key="wcs"); r = c_b.number_input("Rep", 1, key="wcr"); w = c_c.number_input("Kg (+/-)", 0.0, key="wcw")
                if st.button("Aggiungi Set", key="w_cali_b", type="primary", use_container_width=True):
                    st.session_state['sess_w'].append({"type":"calisthenics","nome":nm,"serie":s,"reps":r,"kg":w})
                if st.button("💾 Salva in DB", key="wds_cali", use_container_width=True): 
                     save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Calisthenics"}])], ignore_index=True)); st.rerun()

            elif mod == "Isometria":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + ls_iso, key="w_iso_sl")
                nm = st.text_input("Nome", key="w_iso_nm") if sl == "-- Nuovo --" else sl
                c_a,c_b,c_c = st.columns(3)
                s = c_a.number_input("Set", 1, key="wis_s"); t = c_b.number_input("Sec", 10, step=5, key="wis_t"); w = c_c.number_input("Kg", 0.0, key="wis_w")
                if st.button("Aggiungi Set", key="w_iso_b", type="primary", use_container_width=True):
                    st.session_state['sess_w'].append({"type":"isometria","nome":nm,"serie":s,"tempo":t,"kg":w})
                if st.button("💾 Salva in DB", key="wds_iso", use_container_width=True): 
                     save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Isometria"}])], ignore_index=True)); st.rerun()

            else:
                sl = st.selectbox("Attività", ["-- Nuovo --"] + ls_cardio, key="w_cardio_sl")
                nm = st.text_input("Nome", key="ca_nm") if sl == "-- Nuovo --" else sl
                c_a,c_b,c_c = st.columns(3)
                km=c_a.number_input("Km",0.0,key="ck"); mi=c_b.number_input("Min",0,key="cm"); kc=c_c.number_input("Kcal",0,key="cc")
                if st.button("Aggiungi Cardio", key="cb", type="primary", use_container_width=True): 
                    st.session_state['sess_w'].append({"type":"cardio","nome":nm,"km":km,"tempo":mi,"kcal":kc})
                if st.button("💾 Salva in DB", key="wds_cardio", use_container_width=True): 
                     save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Cardio"}])], ignore_index=True)); st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown(f"#### 🔥 Live: {ses}")
            if st.session_state['sess_w']:
                for i,e in enumerate(st.session_state['sess_w']):
                    t = e.get('type','pesi')
                    if t == "pesi": det = f"{e['serie']}x{e['reps']} @ **{e['kg']}kg**"
                    elif t == "calisthenics": det = f"{e['serie']}x{e['reps']} (**{e['kg']}kg**)"
                    elif t == "isometria": det = f"{e['serie']}x {e['tempo']}s (**{e['kg']}kg**)"
                    else: det = f"{e['km']}km in {e['tempo']}m ({e['kcal']} kcal)"
                    
                    c_txt, c_del = st.columns([6,1])
                    c_txt.markdown(f"{i+1}. **{e['nome']}** : {det}")
                    if c_del.button("❌", key=f"del_w_{i}"):
                        st.session_state['sess_w'].pop(i)
                        st.rerun()
                
                st.divider()
                du = st.number_input("Durata Totale (min)", 0, step=5, key="wdur")
                if st.button("✅ TERMINA & SALVA WORKOUT", type="primary", use_container_width=True):
                    add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']})
                    st.session_state['sess_w'] = []
                    st.balloons()
                    st.success("Allenamento Salvato con successo!")
                    st.rerun()
            else:
                st.info("La sessione è vuota. Aggiungi esercizi dal pannello laterale.")

# --- STORICO ---
with tab4:
    st.subheader("📏 Misure Corporee")
    with st.container(border=True):
        if misure_list: st.dataframe(pd.DataFrame(misure_list), use_container_width=True)
        else: st.info("Nessun dato registrato.")
    
    with st.expander("➕ Aggiungi Misurazione Completa"):
        c1,c2 = st.columns(2)
        p=c1.number_input("Peso", key="ms_p"); a=c2.number_input("Altezza", key="ms_a")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="ms_co"); vi=c4.number_input("Vita", key="ms_vi"); fi=c5.number_input("Fianchi", key="ms_fi")
        if st.button("Salva Misure", key="fs"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi}); st.success("Misure Salvate!")

# --- CALISTHENICS ---
with tab5:
    st.subheader("🤸 Calisthenics Skills Journey")
    with st.expander("➕ Nuova Skill / Progetto", expanded=True):
        with st.form("f_cali"):
            c1, c2 = st.columns([2, 1])
            n_sk = c1.text_input("Nome Skill (es. Front Lever)")
            u_sk = c2.text_input("URL Foto (Opzionale)")
            d_sk = st.text_area("Note / Progressione / Obiettivo")
            if st.form_submit_button("Salva Skill"):
                if n_sk:
                    add_riga_diario("calisthenics", {"nome": n_sk, "desc": d_sk, "url": u_sk})
                    st.success("Skill creata!"); st.rerun()
    
    st.markdown("---")
    skills = []
    if not df.empty:
        for i, r in df.iterrows():
            if r['tipo'] == 'calisthenics':
                try:
                    d = json.loads(r['dettaglio_json']); d['idx'] = i; d['dt'] = r['data']
                    skills.append(d)
                except: pass
    
    if skills:
        for s in reversed(skills):
            with st.container(border=True):
                ci, ct = st.columns([1, 4])
                with ci:
                    if s.get('url'): st.image(s['url'], use_container_width=True)
                    else: st.image("https://cdn-icons-png.flaticon.com/512/2548/2548532.png", width=80)
                with ct:
                    c_h, c_d = st.columns([5, 1])
                    c_h.markdown(f"### {s['nome']}")
                    if c_d.button("🗑️", key=f"dc_{s['idx']}"): delete_riga(s['idx']); st.rerun()
                    st.caption(f"📅 Aggiornato il: {s['dt']}")
                    st.markdown(s['desc'])
    else: st.info("Ancora nessuna skill tracciata.")

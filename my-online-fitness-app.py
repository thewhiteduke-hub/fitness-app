import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V14.3 - FINAL FORCE LIGHT THEME)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* 1. IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* 2. FORZATURA GLOBALE TEMA CHIARO (Sovrascrive Dark Mode di Streamlit) */
    :root {
        --primary-color: #0051FF;
        --background-color: #F8F9FB;
        --secondary-background-color: #ffffff;
        --text-color: #1f1f1f;
        --font: 'Inter', sans-serif;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1f1f1f;
    }

    /* Sfondo Generale App */
    .stApp {
        background-color: #F8F9FB !important;
    }

    /* Sidebar Forzata Bianca */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Testi nella sidebar e main */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, p, span, div {
        color: #1f1f1f !important;
    }
    
    /* 3. FIX INPUT FIELDS (Date, Text, Number) - Risolve il nero su nero */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #d0d0d0 !important;
        caret-color: #0051FF; /* Cursore blu */
    }
    /* Sfondo dei menu a tendina */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul {
        background-color: #ffffff !important;
    }
    /* Opzioni menu a tendina */
    li[role="option"] {
        color: #000000 !important;
    }

    /* 4. CARD CONTENITORI */
    div[data-testid="stContainer"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* 5. TABS STYLE */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 8px;
        color: #555555;
        border: 1px solid #e0e0e0;
        padding: 6px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0051FF !important;
        color: #ffffff !important;
        border: none;
    }

    /* 6. GRAFICI ALTAIR */
    /* Rimuove sfondo dai grafici per evitare il riquadro grigio/nero */
    canvas {
        background-color: transparent !important;
    }

    /* 7. BOTTONI E METRICHE */
    div[data-testid="stMetricValue"] { color: #0051FF !important; }
    
    button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #d0d0d0 !important;
    }
    button[kind="primary"] {
        background-color: #0051FF !important;
        color: #ffffff !important;
        border: none !important;
    }
    
    /* Fix specifico per il calendario scuro */
    div[data-baseweb="calendar"] {
        background-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
# ==========================================
def check_password():
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    if "APP_PASSWORD" not in st.secrets: return True
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("")
        with st.container(border=True):
            st.markdown("### 🔒 Accesso")
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
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=60)
    st.markdown("### Fit Tracker Pro")
    st.caption("v14.3 - Stable Light")
    
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
                add_riga_diario("settings", ns); st.rerun()

    st.markdown("---")
    if user_settings['url_foto']:
        try: st.image(user_settings['url_foto'], use_container_width=True)
        except: pass
    
    with st.expander("📸 Cambia Foto"):
        nu = st.text_input("Link Foto", key="s_url")
        if st.button("Salva", key="s_btn"):
            if nu:
                ns = user_settings.copy(); ns['url_foto'] = nu
                add_riga_diario("settings", ns); st.rerun()

    st.markdown("---")
    w_fast = st.number_input("Peso Rapido (kg)", 0.0, format="%.1f", key="side_w_f")
    if st.button("Salva Peso", key="side_btn_w"):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast})
            st.toast("Salvato!"); st.rerun()

    st.markdown("---")
    q_ai = st.text_input("Coach AI...", key="s_ai")
    if st.button("Invia", key="s_aibtn"):
        st.session_state.chat.append({"role":"user","txt":q_ai})
        ans="Errore AI"; 
        if gemini_ok:
            try: ans=model.generate_content(f"Sei un PT. Rispondi: {q_ai}").text
            except: pass
        st.session_state.chat.append({"role":"assistant","txt":ans}); st.rerun()
    if "chat" not in st.session_state: st.session_state.chat = []
    if st.session_state.chat: st.info(st.session_state.chat[-1]['txt'])

# ==========================================
# 🏠 MAIN - (FIX SCOPE & COLORI)
# ==========================================
st.title(f"Bentornato, Atleta.")
st.caption(f"📅 Riepilogo del: {data_filtro}")

# 1. SCARICO I DATI UNA VOLTA SOLA QUI (GLOBALMENTE)
df = get_data("diario")
misure_list = []

# 2. PREPARO LA LISTA PESO PER TUTTE LE SCHEDE
# Questo risolve il NameError dello screenshot 1
if not df.empty:
    for _, r in df.iterrows():
        if r['tipo'] == 'misure':
            try:
                d = json.loads(r['dettaglio_json'])
                misure_list.append({"Data": r['data'], "Peso": d['peso']})
            except: pass

# 3. CREAZIONE TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Calisthenics"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df_oggi = df[df['data'] == data_filtro] if not df.empty else pd.DataFrame()
    
    cal = pro = carb = fat = 0
    meal_groups = {
        "Colazione": [], "Pranzo": [], "Cena": [], 
        "Spuntino": [], "Integrazione": []
    }
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

    # KPI & VISUALIZZAZIONE GRAFICA
    TC = user_settings['target_cal']
    
    col_vis, col_kpi = st.columns([1, 2])
    
    with col_vis:
        # 🍩 DONUT CHART CALORIE (FIX TRASPARENZA)
        rimanenti = max(0, TC - cal)
        source = pd.DataFrame([
            {"category": "Consumate", "value": cal, "color": "#0051FF"},
            {"category": "Rimanenti", "value": rimanenti, "color": "#E0E0E0"}
        ])
        base = alt.Chart(source).encode(theta=alt.Theta("value", stack=True))
        pie = base.mark_arc(innerRadius=60).encode(
            color=alt.Color("color", scale=None),
            tooltip=["category", "value"]
        )
        text = base.mark_text(radius=0, size=24, color="#0051FF").encode(
            text=alt.value(f"{int(cal)}")
        )
        # Background transparent risolve il riquadro nero/grigio
        st.altair_chart((pie + text).properties(background='transparent'), use_container_width=True)
        st.caption(f"Target: {int(TC)} kcal")

    with col_kpi:
        # MACROS
        TP = user_settings['target_pro']
        TCA = user_settings['target_carb']
        TF = user_settings['target_fat']
        
        st.markdown("##### 🥗 Macro Breakdown")
        def macro_bar(label, val, target, color):
            perc = min(val/target, 1.0) if target > 0 else 0
            st.markdown(f"""
            <div style="margin-bottom: 8px;">
                <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:4px; color:#333;">
                    <strong>{label}</strong>
                    <span>{int(val)} / {target}g</span>
                </div>
                <div style="width:100%; background-color:#e0e0e0; border-radius:10px; height:8px;">
                    <div style="width:{perc*100}%; background-color:{color}; border-radius:10px; height:8px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        macro_bar("Proteine", pro, TP, "#0051FF")
        macro_bar("Carboidrati", carb, TCA, "#33C1FF")
        macro_bar("Grassi", fat, TF, "#FFB033")

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
                            elif t == "isometria": det = f"**{ex['tempo']}s** x {ex['serie']}"
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
        st.subheader("Inserimento")
        cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
        
        if cat == "Integrazione":
            # === INTEGRATORE ===
            sel_i = st.selectbox("Cerca Integratore", ["-- Manuale --"] + nomi_int, key="search_int")
            if "last_sel_int" not in st.session_state: st.session_state.last_sel_int = None
            if sel_i != st.session_state.last_sel_int:
                st.session_state.last_sel_int = sel_i
                if sel_i != "-- Manuale --" and not df_int.empty:
                    try:
                        row = df_int[df_int['nome'] == sel_i].iloc[0]
                        st.session_state['i_nm'] = str(row['nome']) 
                        d_val = row.get('descrizione', '')
                        st.session_state['i_desc_f'] = str(d_val) if pd.notna(d_val) else ""
                        st.session_state['base_int'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                        st.session_state['temp_tipo_idx'] = {"g":0,"cps":1,"mg":2}.get(row.get('tipo','g'),0)
                    except: pass
                else: st.session_state['base_int'] = {'k':0,'p':0,'c':0,'f':0}

            base = st.session_state.get('base_int', {'k':0,'p':0,'c':0,'f':0})
            tip_idx = st.session_state.get('temp_tipo_idx', 0)
            tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], index=tip_idx, horizontal=True, key="i_rad")
            u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
            
            with st.container(border=True):
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", key="i_nm")
                q = c2.number_input(f"Qta ({u})", step=1.0, key="i_q") 
                desc = st.text_area("Note", key="i_desc_f", height=80)
                
                val_k = base['k'] * q; val_p = base['p'] * q; val_c = base['c'] * q; val_f = base['f'] * q
                st.session_state['ik']=val_k; st.session_state['ip']=val_p; st.session_state['ic']=val_c; st.session_state['if']=val_f

                st.markdown("###### Macro Totali")
                k=st.number_input("K", key="ik"); p=st.number_input("P", key="ip")
                c=st.number_input("C", key="ic"); f=st.number_input("F", key="if")
                
                if st.button("Aggiungi", type="primary", use_container_width=True, key="bi"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"desc":desc,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.rerun()
        else:
            # === CIBO NORMALE ===
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
                    else: st.session_state['base_food'] = {'k':0,'p':0,'c':0,'f':0}
                
                base_f = st.session_state.get('base_food', {'k':0,'p':0,'c':0,'f':0})
                c1, c2 = st.columns([2,1])
                nom = c1.text_input("Nome Alimento", key="f_nm")
                gr = c2.number_input("Quantità (g)", step=10.0, key="f_gr")
                
                fac = gr / 100
                st.session_state['fk'] = base_f['k']*fac; st.session_state['fp'] = base_f['p']*fac
                st.session_state['fc'] = base_f['c']*fac; st.session_state['ff'] = base_f['f']*fac
                
                st.markdown("###### 📊 Valori Nutrizionali")
                m1,m2,m3,m4 = st.columns(4)
                k=m1.number_input("Kcal", key="fk"); p=m2.number_input("Pro", key="fp")
                c=m3.number_input("Carb", key="fc"); f=m4.number_input("Fat", key="ff")
                st.write("")
                if st.button("🍽️ Aggiungi al Diario", type="primary", use_container_width=True, key="bf"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Pasto aggiunto!"); st.rerun()

    with c_db:
        st.subheader("💾 DB")
        t_cibo, t_int, t_ex = st.tabs(["Cibo", "Int", "Ex"])
        with t_cibo:
            with st.form("dbf"):
                n=st.text_input("Nome", key="dbn"); k=st.number_input("K/100g", key="dbk"); p=st.number_input("P", key="dbp"); c=st.number_input("C", key="dbc"); f=st.number_input("F", key="dbf")
                if st.form_submit_button("Salva"):
                    if n: save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()
        with t_int:
            with st.form("dbi"):
                ni=st.text_input("Nome", key="dbi_n"); di=st.text_area("Desc", key="dbi_d", height=60)
                ti_sel = st.radio("Tipo", ["Polvere", "Capsula", "Mg"], key="dbi_t")
                ki=st.number_input("K", key="dbi_k"); pi=st.number_input("P", key="dbi_p"); ci=st.number_input("C", key="dbi_c"); fi=st.number_input("F", key="dbi_f")
                if st.form_submit_button("Salva"):
                    if ni: save_data("integratori", pd.concat([df_int, pd.DataFrame([{"nome":ni,"tipo":("g" if "Polvere" in ti_sel else "cps"),"descrizione":di,"kcal":ki,"pro":pi,"carb":ci,"fat":fi}])], ignore_index=True)); st.rerun()
        with t_ex:
            bulk_text = st.text_area("Lista Esercizi", height=200, key="bulk_ex_area")
            if st.button("Salva Lista"):
                if bulk_text:
                    df_current_ex = get_data("esercizi")
                    lista = [x.strip() for x in bulk_text.split('\n') if x.strip()]
                    if lista:
                        new_df = pd.DataFrame({'nome': lista, 'categoria': 'Pesi'})
                        save_data("esercizi", pd.concat([df_current_ex, new_df], ignore_index=True)); st.rerun()

# --- TAB 3: WORKOUT ---
with tab3:
    st.subheader("Workout")
    df_ex = get_data("esercizi")
    if df_ex.empty: df_ex = pd.DataFrame(columns=["nome", "categoria"])
    elif "categoria" not in df_ex.columns: df_ex["categoria"] = "Pesi"
    
    ls_pesi = df_ex[df_ex['categoria'] == 'Pesi']['nome'].tolist()
    ls_cali = df_ex[df_ex['categoria'] == 'Calisthenics']['nome'].tolist()
    ls_iso = df_ex[df_ex['categoria'] == 'Isometria']['nome'].tolist()
    ls_cardio = df_ex[df_ex['categoria'] == 'Cardio']['nome'].tolist()

    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    c1, c2 = st.columns([1,2])
    with c1:
        st.caption("Setup Sessione")
        ses = st.text_input("Nome Sessione", "Workout", key="w_ses")
        mod = st.radio("Modo", ["Pesi", "Calisthenics", "Isometria", "Cardio"], horizontal=True, key="w_mod")
        
        if mod == "Pesi":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"] + sorted(ls_pesi), key="w_sl")
            nm = st.text_input("Nome", key="w_nm") if sl == "-- Nuovo --" else sl
            s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
            if st.button("Aggiungi Set", key="wb"): st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
            with st.expander("Salva nel DB"):
                if st.button("Salva Pesi", key="wds"): save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Pesi"}])], ignore_index=True)); st.rerun()

        elif mod == "Calisthenics":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"] + sorted(ls_cali), key="w_cali_sl")
            nm = st.text_input("Nome", key="w_cali_nm") if sl == "-- Nuovo --" else sl
            c_a,c_b,c_c = st.columns(3)
            s = c_a.number_input("Set", 1, key="wcs"); r = c_b.number_input("Rep", 1, key="wcr"); w = c_c.number_input("Kg", 0.0, key="wcw")
            if st.button("Aggiungi Set", key="w_cali_b"): st.session_state['sess_w'].append({"type":"calisthenics","nome":nm,"serie":s,"reps":r,"kg":w})
            with st.expander("Salva nel DB"):
                if st.button("Salva Cali", key="wds_cali"): save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Calisthenics"}])], ignore_index=True)); st.rerun()

        elif mod == "Isometria":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"] + sorted(ls_iso), key="w_iso_sl")
            nm = st.text_input("Nome", key="w_iso_nm") if sl == "-- Nuovo --" else sl
            c_a,c_b,c_c = st.columns(3)
            s = c_a.number_input("Set", 1, key="wis_s"); t = c_b.number_input("Sec", 10, step=5, key="wis_t"); w = c_c.number_input("Kg", 0.0, key="wis_w")
            if st.button("Aggiungi Set", key="w_iso_b"): st.session_state['sess_w'].append({"type":"isometria","nome":nm,"serie":s,"tempo":t,"kg":w})
            with st.expander("Salva nel DB"):
                if st.button("Salva Iso", key="wds_iso"): save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Isometria"}])], ignore_index=True)); st.rerun()

        else:
            sl = st.selectbox("Attività", ["-- Nuovo --"] + sorted(ls_cardio), key="w_cardio_sl")
            nm = st.text_input("Nome", key="ca_nm") if sl == "-- Nuovo --" else sl
            km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
            if st.button("Aggiungi Cardio", key="cb"): st.session_state['sess_w'].append({"type":"cardio","nome":nm,"km":km,"tempo":mi,"kcal":kc})
            with st.expander("Salva nel DB"):
                if st.button("Salva Cardio", key="wds_cardio"): save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":nm, "categoria":"Cardio"}])], ignore_index=True)); st.rerun()

    with c2:
        st.subheader(f"In Corso: {ses}")
        if st.session_state['sess_w']:
            for i,e in enumerate(st.session_state['sess_w']):
                t = e.get('type','pesi')
                if t == "pesi": det = f"{e['serie']}x{e['reps']} @ {e['kg']}kg"
                elif t == "calisthenics": det = f"{e['serie']}x{e['reps']} (+{e['kg']}kg)"
                elif t == "isometria": det = f"{e['serie']}x {e['tempo']}s (+{e['kg']}kg)"
                else: det = f"{e['km']}km in {e['tempo']}m ({e['kcal']} kcal)"
                c_txt, c_del = st.columns([5,1])
                c_txt.markdown(f"**{e['nome']}** : {det}")
                if c_del.button("❌", key=f"del_w_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
            
            st.divider()
            du = st.number_input("Durata (min)", 0, step=5, key="wdur")
            if st.button("TERMINA & SALVA", type="primary", use_container_width=True):
                add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']})
                st.session_state['sess_w'] = []
                st.success("Salvato!"); st.rerun()
        else: st.info("Aggiungi il primo esercizio.")

# --- TAB 4: STORICO (FIXED) ---
with tab4:
    if misure_list: st.table(pd.DataFrame(misure_list))
    else: st.info("Nessuna misurazione.")
    with st.expander("Misure Complete"):
        c1,c2 = st.columns(2)
        p=c1.number_input("Peso", key="ms_p"); a=c2.number_input("Altezza", key="ms_a")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="ms_co"); vi=c4.number_input("Vita", key="ms_vi"); fi=c5.number_input("Fianchi", key="ms_fi")
        if st.button("Salva", key="fs"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi}); st.success("OK")

# --- TAB 5: CALISTHENICS ---
with tab5:
    st.subheader("🤸 Skills")
    with st.expander("➕ Nuova Skill", expanded=True):
        with st.form("f_cali"):
            c1, c2 = st.columns([2, 1])
            n_sk = c1.text_input("Skill")
            u_sk = c2.text_input("Link Foto")
            d_sk = st.text_area("Note")
            if st.form_submit_button("Salva"):
                if n_sk: add_riga_diario("calisthenics", {"nome": n_sk, "desc": d_sk, "url": u_sk}); st.rerun()
    
    st.divider()
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
                ci, ct = st.columns([1, 3])
                with ci:
                    if s.get('url'): 
                        try: st.image(s['url'], use_container_width=True)
                        except: pass
                    else: st.info("No img")
                with ct:
                    c_h, c_d = st.columns([5, 1])
                    c_h.markdown(f"### {s['nome']}")
                    if c_d.button("🗑️", key=f"dc_{s['idx']}"): delete_riga(s['idx']); st.rerun()
                    st.caption(f"📅 {s['dt']}")
                    st.write(s['desc'])
    else: st.info("Nessuna skill.")

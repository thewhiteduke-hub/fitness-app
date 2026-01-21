import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V15.0 - PREMIUM)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* Global Background */
    .stApp { background-color: #F4F6F9; color: #1f1f1f; }
    
    /* Typography */
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; font-weight: 700; color: #111827 !important; }
    p, div, label, span { color: #374151 !important; }
    
    /* Cards (Container standard) */
    div[data-testid="stContainer"] {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }

    /* Input Fields styling */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #d1d5db !important;
        color: #111827 !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #0051FF !important;
        box-shadow: 0 0 0 2px rgba(0, 81, 255, 0.2) !important;
    }

    /* Buttons */
    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    /* Tabs styling */
    button[data-baseweb="tab"] {
        font-size: 16px;
        font-weight: 600;
        background-color: transparent !important;
    }
    
    /* Fix Menu Tendina */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul { background-color: #ffffff !important; }
    li[role="option"] { color: #000000 !important; background-color: #ffffff !important; }
    li[role="option"]:hover { background-color: #f0f2f6 !important; }

    img { border-radius: 12px; }
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
            st.title("🔒 Accesso")
            st.text_input("Password", type="password", on_change=password_entered, key="pwd_login_15")
    return False

def password_entered():
    if st.session_state["pwd_login_15"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["pwd_login_15"]
    else: st.error("Password errata")

if not check_password(): st.stop()

# AI CONFIG
gemini_ok = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.0-flash') # Aggiornato a modello più recente se disp.
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
    
    # Salva con la data selezionata nella navigazione (o oggi se fallback)
    data_target = st.session_state.get('nav_date', datetime.date.today()).strftime("%Y-%m-%d")
    
    nuova = pd.DataFrame([{
        "data": data_target,
        "tipo": tipo,
        "dettaglio_json": json.dumps(dati)
    }])
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
# 📊 HELPER CHART (DONUT)
# ==========================================
def make_donut(input_response, input_text, input_color, target):
    if target == 0: target = 1
    progresso = min(input_response / target, 1.0) * 100
    
    source = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100-progresso, progresso]
    })
    
    plot = alt.Chart(source).mark_arc(innerRadius=45, outerRadius=60, cornerRadius=10).encode(
        theta="% value",
        color= alt.Color("Topic:N",
            scale=alt.Scale(domain=[input_text, ''], range=[input_color, '#e5e7eb']),
            legend=None),
    ).properties(width=130, height=130)
    
    text = plot.mark_text(align='center', color=input_color, font="Segoe UI", fontSize=20, fontWeight=700).encode(
        text=alt.value(f'{int(input_response)}')
    )
    return plot + text

# ==========================================
# 📱 SIDEBAR & NAVIGATION
# ==========================================
user_settings = get_user_settings()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=60)
    st.markdown("### Fit Tracker Pro")
    st.caption("v15.0 - UIX Overhaul")
    
    st.markdown("---")
    
    # --- NAVIGAZIONE INTELLIGENTE ---
    st.markdown("### 📅 Navigazione")
    if "nav_date" not in st.session_state:
        st.session_state.nav_date = datetime.date.today()

    c_prev, c_dt, c_next = st.columns([1, 4, 1])
    with c_prev:
        if st.button("◀", key="d_prev"):
            st.session_state.nav_date -= datetime.timedelta(days=1)
            st.rerun()
    with c_next:
        if st.button("▶", key="d_next"):
            st.session_state.nav_date += datetime.timedelta(days=1)
            st.rerun()
    with c_dt:
        sel_date = st.date_input("Data", value=st.session_state.nav_date, label_visibility="collapsed")
        if sel_date != st.session_state.nav_date:
            st.session_state.nav_date = sel_date
            st.rerun()

    data_filtro = st.session_state.nav_date.strftime("%Y-%m-%d")

    st.markdown("---")
    st.markdown("**🎯 Target**")
    with st.expander("Modifica"):
        with st.form("target_form"):
            tc = st.number_input("Target Kcal", value=int(user_settings['target_cal']))
            tp = st.number_input("Target Pro", value=int(user_settings['target_pro']))
            tca = st.number_input("Target Carb", value=int(user_settings['target_carb']))
            tf = st.number_input("Target Fat", value=int(user_settings['target_fat']))
            if st.form_submit_button("Salva"):
                ns = user_settings.copy(); ns.update({"target_cal":tc,"target_pro":tp,"target_carb":tca,"target_fat":tf})
                add_riga_diario("settings", ns); st.rerun()

    if user_settings['url_foto']:
        st.markdown("---")
        try: st.image(user_settings['url_foto'], use_container_width=True)
        except: pass
        with st.expander("📸 Cambia Foto"):
            nu = st.text_input("Link Foto", key="s_url")
            if st.button("Salva", key="s_btn") and nu:
                ns = user_settings.copy(); ns['url_foto'] = nu
                add_riga_diario("settings", ns); st.rerun()

    st.markdown("---")
    w_fast = st.number_input("Peso Rapido (kg)", 0.0, format="%.1f", key="side_w_f")
    if st.button("Salva Peso", key="side_btn_w") and w_fast > 0:
        add_riga_diario("misure", {"peso": w_fast})
        st.toast("Salvato!"); st.rerun()

    st.markdown("---")
    if "chat" not in st.session_state: st.session_state.chat = []
    q_ai = st.text_input("Coach AI...", key="s_ai")
    if st.button("Invia", key="s_aibtn"):
        st.session_state.chat.append({"role":"user","txt":q_ai})
        ans="Errore AI"
        if gemini_ok:
            try: ans=model.generate_content(f"Sei un PT esperto. Rispondi brevemente: {q_ai}").text
            except: pass
        st.session_state.chat.append({"role":"assistant","txt":ans}); st.rerun()
    if st.session_state.chat: st.info(st.session_state.chat[-1]['txt'])

# ==========================================
# 🏠 MAIN PAGE
# ==========================================
st.title(f"Dashboard Atleta")
st.caption(f"Visualizzazione del: **{data_filtro}**")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Skills"])

# --- DASHBOARD (NEW VISUALS) ---
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

    # Recupero Peso Ultimo
    misure_list = []
    curr_peso = "--"
    if not df.empty:
        df_m = df[df['tipo'] == 'misure']
        for _, r in df_m.iterrows():
            try:
                d = json.loads(r['dettaglio_json'])
                misure_list.append({"Data": r['data'], "Peso": d['peso']})
                if r['data'] == data_filtro: curr_peso = f"{d['peso']} kg"
            except: pass
    if curr_peso == "--" and misure_list: curr_peso = f"{misure_list[-1]['Peso']} kg"

    # --- SECTION: MACRO RINGS ---
    TC = user_settings['target_cal']; TP = user_settings['target_pro']
    TCarb = user_settings['target_carb']; TFat = user_settings['target_fat']

    st.subheader("🔥 Daily Summary")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(f"<div style='text-align:center; font-weight:bold; margin-bottom:5px'>Kcal ({int(TC)})</div>", unsafe_allow_html=True)
        st.altair_chart(make_donut(cal, "Kcal", "#0051FF", TC), use_container_width=True)
    with d2:
        st.markdown(f"<div style='text-align:center; font-weight:bold; margin-bottom:5px'>Pro ({int(TP)}g)</div>", unsafe_allow_html=True)
        st.altair_chart(make_donut(pro, "Pro", "#8B5CF6", TP), use_container_width=True)
    with d3:
        st.markdown(f"<div style='text-align:center; font-weight:bold; margin-bottom:5px'>Carb ({int(TCarb)}g)</div>", unsafe_allow_html=True)
        st.altair_chart(make_donut(carb, "Carb", "#10B981", TCarb), use_container_width=True)
    with d4:
        st.markdown(f"<div style='text-align:center; font-weight:bold; margin-bottom:5px'>Fat ({int(TFat)}g)</div>", unsafe_allow_html=True)
        st.altair_chart(make_donut(fat, "Fat", "#F59E0B", TFat), use_container_width=True)

    st.markdown("---")
    
    # --- SECTION: DETTAGLI & GRAFICO SETTIMANALE ---
    cl1, cl2 = st.columns([1,1])
    
    with cl1:
        st.subheader("🍎 Diario Alimentare")
        found_meals = False
        for cat in ["Colazione", "Pranzo", "Cena", "Spuntino", "Integrazione"]:
            items = meal_groups[cat]
            if items:
                found_meals = True
                sub_cal = sum(x['cal'] for x in items)
                with st.expander(f"**{cat}** ({int(sub_cal)} kcal)", expanded=False):
                    for p in items:
                        c_txt, c_btn = st.columns([5, 1])
                        c_txt.markdown(f"- {p['nome']} ({int(p.get('gr',0))}{p.get('unita','g')})")
                        if c_btn.button("❌", key=f"del_p_{p['idx']}"): 
                            delete_riga(p['idx']); st.rerun()
        if not found_meals: st.info("Nessun pasto registrato.")

        st.subheader("🏋️ Allenamenti")
        if allenamenti:
            for w in allenamenti:
                with st.expander(f"**{w.get('nome_sessione','Workout')}** ({w['durata']} min)", expanded=False):
                    if 'esercizi' in w:
                        for ex in w['esercizi']:
                            t = ex.get('type', 'pesi')
                            if t == "pesi": det = f"{ex['serie']}x{ex['reps']} {ex['kg']}kg"
                            elif t == "isometria": det = f"{ex['serie']}x {ex['tempo']}s"
                            elif t == "calisthenics": det = f"{ex['serie']}x{ex['reps']} (+{ex.get('kg',0)}kg)"
                            else: det = f"{ex['km']}km"
                            st.markdown(f"🔹 **{ex['nome']}**: {det}")
                    if st.button("Elimina Sessione", key=f"del_w_{w['idx']}"):
                        delete_riga(w['idx']); st.rerun()
        else: st.info("Riposo.")

    with cl2:
        st.subheader("📅 Consistenza (7gg)")
        # Calcolo storico settimanale
        today_date = st.session_state.nav_date
        dates = [(today_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        dates.reverse()
        
        weekly_data = []
        if not df.empty:
            df_week = df[df['data'].isin(dates) & (df['tipo'] == 'pasto')]
            for d_str in dates:
                day_rows = df_week[df_week['data'] == d_str]
                day_cal = 0
                if not day_rows.empty:
                    for _, r in day_rows.iterrows():
                        try: day_cal += json.loads(r['dettaglio_json'])['cal']
                        except: pass
                weekly_data.append({"Data": d_str[5:], "Kcal": int(day_cal), "Target": TC})

        if weekly_data:
            chart_week = alt.Chart(pd.DataFrame(weekly_data)).mark_bar(cornerRadius=6).encode(
                x=alt.X('Data', sort=None),
                y='Kcal',
                color=alt.condition(
                    alt.datum.Kcal > alt.datum.Target,
                    alt.value('#EF4444'),  # Rosso
                    alt.value('#0051FF')   # Blu
                ),
                tooltip=['Data', 'Kcal', 'Target']
            ).properties(height=250)
            rule = alt.Chart(pd.DataFrame(weekly_data)).mark_rule(color='#10B981', strokeDash=[5,5]).encode(y='Target')
            st.altair_chart(chart_week + rule, use_container_width=True)
        
        st.subheader("📉 Peso")
        if misure_list:
            chart_w = alt.Chart(pd.DataFrame(misure_list)).mark_line(point=True).encode(
                x='Data:T', y=alt.Y('Peso:Q', scale=alt.Scale(zero=False)), color=alt.value("#0051FF")
            ).properties(height=200)
            st.altair_chart(chart_w, use_container_width=True)

# --- ALIMENTAZIONE ---
with tab2:
    c_in, c_db = st.columns([2,1])
    df_cibi = get_data("cibi"); nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []
    df_int = get_data("integratori"); nomi_int = df_int['nome'].tolist() if not df_int.empty else []

    with c_in:
        with st.container():
            st.subheader("🍽️ Aggiungi Pasto")
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
            
            # --- INTEGRATORI ---
            if cat == "Integrazione":
                sel_i = st.selectbox("Cerca", ["-- Manuale --"] + nomi_int, key="search_int")
                if "last_sel_int" not in st.session_state: st.session_state.last_sel_int = None
                
                if sel_i != st.session_state.last_sel_int:
                    st.session_state.last_sel_int = sel_i
                    if sel_i != "-- Manuale --":
                        try:
                            row = df_int[df_int['nome'] == sel_i].iloc[0]
                            st.session_state['i_nm'] = str(row['nome'])
                            st.session_state['base_int'] = {'k':row['kcal'],'p':row['pro'],'c':row['carb'],'f':row['fat']}
                        except: pass
                    else: st.session_state['base_int'] = {'k':0,'p':0,'c':0,'f':0}
                
                base = st.session_state.get('base_int', {'k':0,'p':0,'c':0,'f':0})
                tip = st.radio("Tipo", ["Polvere (g)","Capsule","Mg"], horizontal=True, key="i_rad")
                u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", key="i_nm"); q = c2.number_input(f"Qta ({u})", 1.0, key="i_q")
                
                # Auto calc
                st.session_state['ik'] = base['k'] * q; st.session_state['ip'] = base['p'] * q
                st.session_state['ic'] = base['c'] * q; st.session_state['if'] = base['f'] * q

                with st.expander("Macro"):
                    k=st.number_input("K", key="ik"); p=st.number_input("P", key="ip")
                    c=st.number_input("C", key="ic"); f=st.number_input("F", key="if")
                
                if st.button("Aggiungi Integratore", type="primary", use_container_width=True):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("OK"); st.rerun()

            # --- CIBO ---
            else:
                sel = st.selectbox("Cerca", ["-- Manuale --"]+nomi_cibi, key="f_sel")
                if "last_sel_food" not in st.session_state: st.session_state.last_sel_food = None
                
                if sel != st.session_state.last_sel_food:
                    st.session_state.last_sel_food = sel
                    if sel != "-- Manuale --":
                        try:
                            row = df_cibi[df_cibi['nome'] == sel].iloc[0]
                            st.session_state['f_nm'] = str(row['nome']); st.session_state['f_gr'] = 100.0
                            st.session_state['base_food'] = {'k':row['kcal'],'p':row['pro'],'c':row['carb'],'f':row['fat']}
                        except: pass
                    else: st.session_state['base_food'] = {'k':0,'p':0,'c':0,'f':0}
                
                base_f = st.session_state.get('base_food', {'k':0,'p':0,'c':0,'f':0})
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", key="f_nm"); gr = c2.number_input("Grammi", step=10.0, key="f_gr")
                
                fac = gr / 100
                st.session_state['fk'] = base_f['k']*fac; st.session_state['fp'] = base_f['p']*fac
                st.session_state['fc'] = base_f['c']*fac; st.session_state['ff'] = base_f['f']*fac
                
                m1,m2,m3,m4=st.columns(4)
                k=m1.number_input("K",key="fk"); p=m2.number_input("P",key="fp"); c=m3.number_input("C",key="fc"); f=m4.number_input("F",key="ff")
                
                if st.button("Aggiungi Cibo", type="primary", use_container_width=True):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("OK"); st.rerun()

    with c_db:
        st.subheader("💾 Database")
        t1, t2, t3 = st.tabs(["Cibo", "Int", "Ex"])
        with t1:
            with st.form("dbf"):
                n=st.text_input("Nome"); k=st.number_input("Kcal 100g"); p=st.number_input("Pro"); c=st.number_input("Carb"); f=st.number_input("Fat")
                if st.form_submit_button("Salva"):
                    if n: save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()
        with t3:
            bulk = st.text_area("Lista Esercizi (uno per riga)")
            if st.button("Carica Esercizi"):
                df_ex = get_data("esercizi")
                l = [x.strip() for x in bulk.split('\n') if x.strip()]
                if l:
                    save_data("esercizi", pd.concat([df_ex, pd.DataFrame({'nome': l, 'categoria': 'Pesi'})], ignore_index=True))
                    st.success(f"Caricati {len(l)}"); st.rerun()

# --- WORKOUT ---
with tab3:
    st.subheader("🏋️ Session Builder")
    df_ex = get_data("esercizi")
    if df_ex.empty: df_ex = pd.DataFrame(columns=["nome", "categoria"])
    if "categoria" not in df_ex.columns: df_ex["categoria"] = "Pesi"
    
    ls_pesi = df_ex[df_ex['categoria']=='Pesi']['nome'].tolist()
    ls_cali = df_ex[df_ex['categoria']=='Calisthenics']['nome'].tolist()
    
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    c1, c2 = st.columns([1, 2])
    with c1:
        ses = st.text_input("Nome Sessione", "Workout", key="w_ses")
        mod = st.radio("Tipo", ["Pesi", "Cali", "Iso", "Cardio"], horizontal=True)
        
        if mod == "Pesi":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"]+sorted(ls_pesi), key="w_sl")
            nm = st.text_input("Nome", key="w_nm") if sl == "-- Nuovo --" else sl
            s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
            if st.button("Add Set"): st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})

        elif mod == "Cali":
            sl = st.selectbox("Esercizio", ["-- Nuovo --"]+sorted(ls_cali), key="w_c_sl")
            nm = st.text_input("Nome", key="w_c_nm") if sl == "-- Nuovo --" else sl
            s=st.number_input("Set",1,key="wcs"); r=st.number_input("Rep",1,key="wcr"); w=st.number_input("Zavorra",0.0,key="wcw")
            if st.button("Add Cali"): st.session_state['sess_w'].append({"type":"calisthenics","nome":nm,"serie":s,"reps":r,"kg":w})
            
    with c2:
        st.markdown(f"**In Corso: {ses}**")
        for i,e in enumerate(st.session_state['sess_w']):
            det = f"{e['serie']}x{e['reps']} {e.get('kg',0)}kg"
            c_txt, c_del = st.columns([6,1])
            c_txt.text(f"{e['nome']}: {det}")
            if c_del.button("x", key=f"d_s_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
        
        st.divider()
        du = st.number_input("Durata (min)", 0, step=5)
        if st.button("✅ TERMINA E SALVA", type="primary", use_container_width=True):
            if st.session_state['sess_w']:
                add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']})
                st.session_state['sess_w'] = []; st.success("Saved!"); st.rerun()

# --- STORICO ---
with tab4:
    st.subheader("📏 Misure Corporee")
    if misure_list: st.dataframe(pd.DataFrame(misure_list), use_container_width=True)
    with st.expander("Nuova Misurazione"):
        c1,c2=st.columns(2)
        p=c1.number_input("Peso", key="m_p"); a=c2.number_input("Altezza", key="m_a")
        if st.button("Salva Misure"):
            add_riga_diario("misure", {"peso":p,"alt":a}); st.success("OK"); st.rerun()

# --- SKILLS ---
with tab5:
    st.subheader("🤸 Skill Tracker")
    with st.expander("Nuova Skill"):
        n=st.text_input("Nome Skill"); d=st.text_area("Note"); u=st.text_input("Foto URL")
        if st.button("Salva Skill") and n:
            add_riga_diario("calisthenics", {"nome":n,"desc":d,"url":u}); st.rerun()
    
    if not df.empty:
        skills = [json.loads(r['dettaglio_json']) for i,r in df.iterrows() if r['tipo'] == 'calisthenics']
        for s in reversed(skills):
            with st.container():
                c1,c2=st.columns([1,3])
                if s.get('url'): c1.image(s['url'])
                c2.markdown(f"**{s['nome']}**"); c2.caption(s.get('desc',''))

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V10.0 - CSS NUCLEARE & LOGICA FIX)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

st.markdown("""
<style>
    /* 1. Reset Colori Base */
    .stApp {
        background-color: #F8F9FB;
        color: #1f1f1f;
    }
    
    /* 2. Testi */
    h1, h2, h3, h4, h5, h6, p, div, span, label {
        color: #1f1f1f !important;
    }
    
    /* 3. Card */
    div[data-testid="stContainer"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    /* 4. Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }

    /* 5. FIX MENU A TENDINA (Override Totale) */
    /* Box principale */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
    }
    /* Testo dentro il box */
    div[data-baseweb="select"] span {
        color: #000000 !important;
    }
    /* Menu a discesa */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul {
        background-color: #ffffff !important;
    }
    /* Le opzioni singole */
    li[role="option"] {
        color: #000000 !important; 
        background-color: #ffffff !important;
    }
    div[role="option"] {
        color: #000000 !important;
    }
    /* Hover */
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: #e6f0ff !important;
        color: #000000 !important;
    }

    /* 6. Input Fields */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
    }

    /* 7. Metriche */
    div[data-testid="stMetricValue"] {
        color: #0051FF !important;
    }
    
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
            st.text_input("Password", type="password", on_change=password_entered, key="pwd_login_10")
    return False

def password_entered():
    if st.session_state["pwd_login_10"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["pwd_login_10"]
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
# 🔗 DATABASE & FUNCTIONS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet):
    try: return conn.read(worksheet=sheet, ttl=0)
    except: return pd.DataFrame()

def save_data(sheet, df):
    conn.update(worksheet=sheet, data=df)
    st.cache_data.clear()

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
    st.caption("v10.0 - Final Fix")
    
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

    st.markdown("---")
    if user_settings['url_foto']:
        try: st.image(user_settings['url_foto'], use_container_width=True)
        except: st.error("Link rotto")
    
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
# 🏠 MAIN
# ==========================================
st.title(f"Bentornato, Atleta.")
st.caption(f"📅 Data: {get_oggi()}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Calisthenics"])

# --- DASHBOARD ---
with tab1:
    df = get_data("diario")
    oggi = get_oggi()
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    cal=pro=carb=fat=0
    pasti=[]; allenamenti=[]
    if not df_oggi.empty:
        for i,r in df_oggi.iterrows():
            try:
                d=json.loads(r['dettaglio_json']); d['idx']=i
                if r['tipo']=='pasto':
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
                    pasti.append(d)
                elif r['tipo']=='allenamento':
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
                    curr_peso = f"{d['peso']} kg"
                except: pass

    TC=user_settings['target_cal']; TP=user_settings['target_pro']
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: st.metric("Kcal", int(cal), f"Rim: {int(TC-cal)}"); st.progress(min(cal/TC, 1.0) if TC>0 else 0)
    with k2: st.metric("Pro", f"{int(pro)}g", f"Target: {TP}g"); st.progress(min(pro/TP, 1.0) if TP>0 else 0)
    with k3: st.metric("Carb", f"{int(carb)}g")
    with k4: st.metric("Fat", f"{int(fat)}g")
    with k5: st.metric("Peso", curr_peso)

    cg1, cg2 = st.columns([2, 1])
    with cg1:
        st.subheader("📉 Andamento Peso")
        if misure_list:
            chart = alt.Chart(pd.DataFrame(misure_list)).mark_area(
                line={'color':'#0051FF'},
                color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#0051FF', offset=0), alt.GradientStop(color='white', offset=1)], x1=1, x2=1, y1=1, y2=0)
            ).encode(x='Data:T', y=alt.Y('Peso:Q', scale=alt.Scale(zero=False))).properties(height=250)
            st.altair_chart(chart, use_container_width=True)
        else: st.info("Nessun dato peso.")

    with cg2:
        st.subheader("📊 Ripartizione Macro")
        if cal>0:
            s = pd.DataFrame({"M":["P","C","F"], "V":[pro*4,carb*4,fat*9]})
            c = alt.Chart(s).encode(theta=alt.Theta("V",stack=True), color=alt.Color("M", scale=alt.Scale(range=['#0051FF','#FFC107','#FF4B4B'])))
            st.altair_chart(c.mark_arc(innerRadius=60), use_container_width=True)
        else: st.caption("Nessun dato.")

    cl1, cl2 = st.columns(2)
    with cl1:
        st.subheader("🍎 Pasti")
        if pasti:
            for p in pasti:
                with st.container():
                    c_txt, c_btn = st.columns([5,1])
                    qty = f"{int(p.get('gr',0))} {p.get('unita','g')}"
                    icon = "💊" if p.get('pasto')=="Integrazione" else "🍽️"
                    c_txt.markdown(f"**{icon} {p['nome']}** ({qty})")
                    c_txt.caption(f"{int(p['cal'])} kcal")
                    if c_btn.button("🗑️", key=f"d_p_{p['idx']}"): delete_riga(p['idx']); st.rerun()
        else: st.info("Vuoto.")

    with cl2:
        st.subheader("🏋️ Workout")
        if allenamenti:
            for w in allenamenti:
                with st.container():
                    c_txt, c_btn = st.columns([5,1])
                    c_txt.markdown(f"**{w.get('nome_sessione','Workout')}** ({w['durata']} min)")
                    if c_btn.button("🗑️", key=f"d_w_{w['idx']}"): delete_riga(w['idx']); st.rerun()
        else: st.info("Riposo.")

# --- ALIMENTAZIONE (AUTOFILL & PROPORTIONAL FIX) ---
with tab2:
    c_in, c_db = st.columns([2,1])
    
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []
    
    df_int = get_data("integratori")
    nomi_int = df_int['nome'].tolist() if not df_int.empty else []

    with c_in:
        with st.container():
            st.subheader("Inserimento")
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
            
            # ==========================
            # === INTEGRATORI LOGIC ===
            # ==========================
            if cat == "Integrazione":
                sel_i = st.selectbox("Cerca Integratore", ["-- Manuale --"] + nomi_int, key="search_int")
                
                # TRIGGER: CAMBIO SELEZIONE
                if "last_sel_int" not in st.session_state: st.session_state.last_sel_int = None
                
                if sel_i != st.session_state.last_sel_int:
                    st.session_state.last_sel_int = sel_i
                    if sel_i != "-- Manuale --" and not df_int.empty:
                        try:
                            row = df_int[df_int['nome'] == sel_i].iloc[0]
                            st.session_state['i_nm'] = str(row['nome']) 
                            # FIX DESCRIZIONE NULLA
                            d_val = row.get('descrizione', '')
                            st.session_state['i_desc_f'] = str(d_val) if pd.notna(d_val) else ""
                            st.session_state['i_q'] = 1.0 
                            
                            # SALVO VALORI BASE (UNITARI)
                            st.session_state['base_int'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                            
                            map_tipo = {"g": 0, "cps": 1, "mg": 2}
                            st.session_state['temp_tipo_idx'] = map_tipo.get(row.get('tipo', 'g'), 0)
                        except: pass
                    else:
                        st.session_state['base_int'] = {'k':0,'p':0,'c':0,'f':0}
                
                # Recupero valori base
                base = st.session_state.get('base_int', {'k':0,'p':0,'c':0,'f':0})
                tip_idx = st.session_state.get('temp_tipo_idx', 0)

                # Widgets
                tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], index=tip_idx, horizontal=True, key="i_rad")
                u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", key="i_nm")
                q = c2.number_input(f"Qta ({u})", step=1.0, key="i_q") 
                desc = st.text_input("A cosa serve / Note", key="i_desc_f")
                
                # CALCOLO PROPORZIONALE LIVE E UPDATE STATO
                val_k = base['k'] * q
                val_p = base['p'] * q
                val_c = base['c'] * q
                val_f = base['f'] * q
                
                # IMPORTANTISSIMO: FORZO LO STATO DELLE CASELLE MACRO
                st.session_state['ik'] = float(val_k)
                st.session_state['ip'] = float(val_p)
                st.session_state['ic'] = float(val_c)
                st.session_state['if'] = float(val_f)

                with st.expander("Macro Totali"):
                    k=st.number_input("K", key="ik"); p=st.number_input("P", key="ip")
                    c=st.number_input("C", key="ic"); f=st.number_input("F", key="if")
                
                if st.button("Aggiungi", type="primary", use_container_width=True, key="bi"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"desc":desc,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("OK"); st.rerun()
            
            # ==========================
            # === CIBO NORMALE LOGIC ===
            # ==========================
            else:
                sel = st.selectbox("Cerca Cibo", ["-- Manuale --"]+nomi_cibi, key="f_sel")
                
                # TRIGGER: CAMBIO SELEZIONE
                if "last_sel_food" not in st.session_state: st.session_state.last_sel_food = None
                
                if sel != st.session_state.last_sel_food:
                    st.session_state.last_sel_food = sel
                    if sel != "-- Manuale --" and not df_cibi.empty:
                        try:
                            row = df_cibi[df_cibi['nome'] == sel].iloc[0]
                            st.session_state['f_nm'] = str(row['nome']) 
                            st.session_state['f_gr'] = 100.0 # Default 100g
                            
                            # SALVO VALORI BASE (PER 100g)
                            st.session_state['base_food'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                        except: pass
                    else:
                        st.session_state['base_food'] = {'k':0,'p':0,'c':0,'f':0}
                
                # Recupero valori base
                base_f = st.session_state.get('base_food', {'k':0,'p':0,'c':0,'f':0})

                # Widgets
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", key="f_nm")
                gr = c2.number_input("Grammi", step=10.0, key="f_gr")
                
                # CALCOLO PROPORZIONALE LIVE E UPDATE STATO
                fac = gr / 100
                val_k = base_f['k'] * fac
                val_p = base_f['p'] * fac
                val_c = base_f['c'] * fac
                val_f = base_f['f'] * fac
                
                # FORZO LO STATO MACRO
                st.session_state['fk'] = float(val_k)
                st.session_state['fp'] = float(val_p)
                st.session_state['fc'] = float(val_c)
                st.session_state['ff'] = float(val_f)
                
                m1,m2,m3,m4=st.columns(4)
                k=m1.number_input("K",key="fk"); p=m2.number_input("P",key="fp"); c=m3.number_input("C",key="fc"); f=m4.number_input("F",key="ff")
                
                if st.button("Mangia", type="primary", use_container_width=True, key="bf"):
                    if nom: add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f}); st.success("OK"); st.rerun()

    # --- DB MANAGER ---
    with c_db:
        st.subheader("💾 Gestione DB")
        t_cibo, t_int = st.tabs(["Cibo", "Integratori"])
        
        with t_cibo:
            with st.container():
                st.caption("Valori per 100g")
                with st.form("dbf"):
                    n=st.text_input("Nome", key="dbn"); k=st.number_input("K 100g", key="dbk"); p=st.number_input("P", key="dbp"); c=st.number_input("C", key="dbc"); f=st.number_input("F", key="dbf")
                    if st.form_submit_button("Salva Cibo"):
                        if n: save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()
        
        with t_int:
            with st.container():
                st.caption("Valori per 1 dose/grammo")
                with st.form("dbi"):
                    ni=st.text_input("Nome", key="dbi_n")
                    di=st.text_input("Descrizione", key="dbi_d")
                    ti_sel = st.radio("Tipo", ["Polvere (g)", "Capsula (cps)", "Mg"], key="dbi_t")
                    ti_val = "g" if "Polvere" in ti_sel else ("cps" if "Capsula" in ti_sel else "mg")
                    c1,c2=st.columns(2)
                    ki=c1.number_input("K", key="dbi_k"); pi=c2.number_input("P", key="dbi_p")
                    ci=c1.number_input("C", key="dbi_c"); fi=c2.number_input("F", key="dbi_f")
                    
                    if st.form_submit_button("Salva Integratore"):
                        if ni:
                            save_data("integratori", pd.concat([df_int, pd.DataFrame([{
                                "nome":ni, "tipo":ti_val, "descrizione":di,
                                "kcal":ki, "pro":pi, "carb":ci, "fat":fi
                            }])], ignore_index=True))
                            st.rerun()

# --- WORKOUT ---
with tab3:
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    c1, c2 = st.columns([1,2])
    df_ex = get_data("esercizi")
    ls_ex = df_ex['nome'].tolist() if not df_ex.empty else []

    with c1:
        with st.container():
            st.subheader("Setup")
            ses = st.text_input("Sessione", "Workout", key="w_ses")
            mod = st.radio("Modo", ["Pesi","Cardio"], horizontal=True, key="w_mod")
            if mod=="Pesi":
                sl = st.selectbox("Ex", ["-- New --"]+ls_ex, key="w_sl")
                nm = sl if sl!="-- New --" else st.text_input("Nome", key="w_nm")
                s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
                if st.button("Add", key="wb"): st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
                with st.expander("Salva Ex"):
                    dn = st.text_input("Nome DB", key="wdn")
                    if st.button("Salva", key="wds"): save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":dn}])], ignore_index=True)); st.rerun()
            else:
                act = st.text_input("Attività", "Corsa", key="ca"); km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
                if st.button("Add", key="cb"): st.session_state['sess_w'].append({"type":"cardio","nome":act,"km":km,"tempo":mi,"kcal":kc})

    with c2:
        with st.container():
            st.subheader(f"In Corso: {ses}")
            for i,e in enumerate(st.session_state['sess_w']):
                det = f"{e['serie']}x{e['reps']} {e['kg']}kg" if e['type']=="pesi" else f"{e['km']}km {e['tempo']}min"
                c_a, c_b = st.columns([5,1])
                c_a.write(f"**{e['nome']}** - {det}")
                if c_b.button("❌", key=f"wd_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
            st.divider()
            du = st.number_input("Durata Tot", 0, step=5, key="wdur")
            if st.button("TERMINA", type="primary", use_container_width=True, key="wend"):
                add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']})
                st.session_state['sess_w']=[]; st.success("Salvato!"); st.rerun()

# --- STORICO ---
with tab4:
    if misure_list: st.table(pd.DataFrame(misure_list))
    else: st.info("No data")
    with st.expander("Misure Complete"):
        c1,c2 = st.columns(2)
        p=c1.number_input("Peso", key="ms_p"); a=c2.number_input("Altezza", key="ms_a")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="ms_co"); vi=c4.number_input("Vita", key="ms_vi"); fi=c5.number_input("Fianchi", key="ms_fi")
        if st.button("Salva", key="fs"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi}); st.success("OK")

# --- CALISTHENICS ---
with tab5:
    st.subheader("🤸 Skills")
    with st.container():
        with st.expander("➕ Nuova Skill", expanded=True):
            with st.form("f_cali"):
                c1, c2 = st.columns([2, 1])
                n_sk = c1.text_input("Skill (es. Front Lever)")
                u_sk = c2.text_input("Link Foto")
                d_sk = st.text_area("Note / Progressione")
                if st.form_submit_button("Salva"):
                    if n_sk:
                        add_riga_diario("calisthenics", {"nome": n_sk, "desc": d_sk, "url": u_sk})
                        st.success("OK"); st.rerun()
    
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
            with st.container():
                ci, ct = st.columns([1, 3])
                with ci:
                    if s.get('url'): 
                        try: st.image(s['url'], use_container_width=True)
                        except: st.caption("No img")
                    else: st.info("No img")
                with ct:
                    c_h, c_d = st.columns([5, 1])
                    c_h.markdown(f"### {s['nome']}")
                    if c_d.button("🗑️", key=f"dc_{s['idx']}"): delete_riga(s['idx']); st.rerun()
                    st.caption(f"📅 {s['dt']}")
                    st.write(s['desc'])
    else: st.info("Nessuna skill.")

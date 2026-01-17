import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (CONTRAST FIX DEFINITIVO)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

st.markdown("""
<style>
    /* 1. Sfondo e Testo Base */
    .stApp {
        background-color: #F8F9FB;
        color: #1f1f1f;
    }
    p, div, label, span, li {
        color: #1f1f1f !important;
    }
    
    /* 2. Titoli in Blu Elettrico */
    h1, h2, h3, h4, h5, h6 {
        color: #0051FF !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* 3. Card Bianche con Ombra */
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
    
    /* 5. FIX CRITICO: MENU A TENDINA (Selectbox) */
    /* Questo blocco forza lo sfondo bianco e il testo nero nei menu a tendina */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"] {
        background-color: #ffffff !important;
        border: 1px solid #ccc;
    }
    /* Opzioni dentro il menu */
    div[role="option"] {
        background-color: #ffffff !important;
    }
    div[role="option"] > div {
        color: #000000 !important;
    }
    /* Effetto Hover nel menu */
    div[role="option"]:hover {
        background-color: #f0f2f6 !important;
    }
    
    /* 6. Input Fields (Testo e Numeri) */
    .stTextInput input, .stNumberInput input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc;
    }
    
    /* 7. Metriche */
    div[data-testid="stMetricValue"] {
        color: #0051FF !important;
        font-size: 26px !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #666 !important;
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
            st.text_input("Password", type="password", on_change=password_entered, key="pwd_login_52")
    return False

def password_entered():
    if st.session_state["pwd_login_52"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["pwd_login_52"]
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
# 🔗 DATABASE
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
    st.markdown("### Fit Tracker v5.2")
    
    st.markdown("---")
    st.markdown("**🎯 I tuoi Obiettivi**")
    with st.expander("Modifica Target"):
        with st.form("target_form_side"):
            tc = st.number_input("Target Kcal", value=int(user_settings['target_cal']))
            tp = st.number_input("Target Pro", value=int(user_settings['target_pro']))
            tca = st.number_input("Target Carb", value=int(user_settings['target_carb']))
            tf = st.number_input("Target Fat", value=int(user_settings['target_fat']))
            
            if st.form_submit_button("Aggiorna Obiettivi"):
                new_s = user_settings.copy()
                new_s.update({"target_cal":tc, "target_pro":tp, "target_carb":tca, "target_fat":tf})
                add_riga_diario("settings", new_s)
                st.success("Salvati!")
                st.rerun()

    st.markdown("---")
    st.markdown("**🏆 Vision**")
    if user_settings['url_foto']:
        try: st.image(user_settings['url_foto'], use_container_width=True)
        except: st.error("Link errato")
    else: st.info("Nessuna foto")
    
    with st.expander("📸 Cambia Foto"):
        nu = st.text_input("Link Foto (.jpg)", key="side_foto_url")
        if st.button("Salva Foto", key="side_foto_btn"):
            if nu:
                new_s = user_settings.copy()
                new_s['url_foto'] = nu
                add_riga_diario("settings", new_s)
                st.rerun()

    st.markdown("---")
    st.markdown("**⚖️ Peso Rapido**")
    w_fast = st.number_input("Peso (kg)", 0.0, format="%.1f", key="side_fast_w")
    if st.button("Salva Peso", key="side_btn_w"):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast})
            st.toast("Salvato!"); st.rerun()

    st.markdown("---")
    st.markdown("**🤖 Coach AI**")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    qs = st.text_input("Domanda...", key="side_ai_q")
    if st.button("Chiedi", key="side_ai_btn"):
        st.session_state.chat.append({"role":"user","txt":qs})
        ans="Errore AI"
        if gemini_ok:
            try: ans=model.generate_content(f"Sei un PT esperto. Rispondi: {qs}").text
            except: pass
        st.session_state.chat.append({"role":"assistant","txt":ans})
        st.rerun()
        
    if st.session_state.chat:
        st.info(st.session_state.chat[-1]['txt'])

# ==========================================
# 🏠 MAIN DASHBOARD
# ==========================================
st.title(f"Bentornato, Atleta.")
st.caption(f"📅 Diario di oggi: {get_oggi()}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico"])

# --- TAB 1: DASHBOARD COMPLETA ---
with tab1:
    df = get_data("diario")
    oggi = get_oggi()
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    # CALCOLI OGGI
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

    # CALCOLI PESO
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

    # KPI ROW
    TC = user_settings['target_cal']
    TP = user_settings['target_pro']
    
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1:
        with st.container():
            st.metric("Kcal", int(cal), f"Rim: {int(TC-cal)}")
            st.progress(min(cal/TC, 1.0) if TC>0 else 0)
    with k2:
        with st.container():
            st.metric("Pro", f"{int(pro)}g", f"Target: {TP}g")
            st.progress(min(pro/TP, 1.0) if TP>0 else 0)
    with k3:
        with st.container(): st.metric("Carb", f"{int(carb)}g")
    with k4:
        with st.container(): st.metric("Fat", f"{int(fat)}g")
    with k5:
        with st.container(): st.metric("Peso", curr_peso)

    # GRAFICI
    cg1, cg2 = st.columns([2, 1])
    
    with cg1:
        with st.container():
            st.subheader("📉 Andamento Peso")
            if misure_list:
                chart = alt.Chart(pd.DataFrame(misure_list)).mark_area(
                    line={'color':'#0051FF'},
                    color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#0051FF', offset=0), alt.GradientStop(color='white', offset=1)], x1=1, x2=1, y1=1, y2=0)
                ).encode(x='Data:T', y=alt.Y('Peso:Q', scale=alt.Scale(zero=False))).properties(height=250)
                st.altair_chart(chart, use_container_width=True)
            else: st.info("Nessun dato peso.")

    with cg2:
        with st.container():
            st.subheader("📊 Ripartizione Macro")
            if cal > 0:
                s = pd.DataFrame({"M":["P","C","F"], "V":[pro*4,carb*4,fat*9]})
                c = alt.Chart(s).encode(theta=alt.Theta("V",stack=True), color=alt.Color("M", scale=alt.Scale(range=['#0051FF','#FFC107','#FF4B4B'])))
                st.altair_chart(c.mark_arc(innerRadius=60), use_container_width=True)
            else: st.caption("Nessun dato.")

    # LISTE DIARIO
    cl1, cl2 = st.columns(2)
    with cl1:
        st.subheader("🍎 Pasti Oggi")
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
        st.subheader("🏋️ Workout Oggi")
        if allenamenti:
            for w in allenamenti:
                with st.container():
                    c_txt, c_btn = st.columns([5,1])
                    c_txt.markdown(f"**{w.get('nome_sessione','Workout')}** ({w['durata']} min)")
                    if c_btn.button("🗑️", key=f"d_w_{w['idx']}"): delete_riga(w['idx']); st.rerun()
        else: st.info("Riposo.")

# --- TAB 2: ALIMENTAZIONE ---
with tab2:
    c_in, c_db = st.columns([2,1])
    df_cibi = get_data("cibi")
    nomi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with c_in:
        with st.container():
            st.subheader("Inserimento")
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="cat_pasto_sel")
            
            if cat == "Integrazione":
                tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], horizontal=True, key="int_tip_rad")
                u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                c1,c2=st.columns([2,1])
                nom = c1.text_input("Nome Integratore", key="int_nm")
                q = c2.number_input(f"Qta ({u})", 0.0, step=1.0, key="int_qt")
                
                with st.expander("Macro (Opzionale)"):
                    k=st.number_input("K",0.0,key="ik"); p=st.number_input("P",0.0,key="ip"); c=st.number_input("C",0.0,key="ic"); f=st.number_input("F",0.0,key="if")
                
                if st.button("Aggiungi", type="primary", use_container_width=True, key="btn_add_int"):
                    if nom:
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()
            else:
                sel = st.selectbox("Cerca", ["-- Manuale --"]+nomi, key="fd_srch")
                vn,vk,vp,vc,vf = "",0,0,0,0
                if sel!="-- Manuale --" and not df_cibi.empty:
                    r = df_cibi[df_cibi['nome']==sel].iloc[0]
                    vn=r['nome']; vk=r['kcal']; vp=r['pro']; vc=r['carb']; vf=r['fat']
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", vn, key="fd_nm")
                gr = c2.number_input("Grammi", 100.0, step=10.0, key="fd_gr")
                
                fac = gr/100
                m1,m2,m3,m4=st.columns(4)
                k=m1.number_input("K",float(vk*fac),key="fk_in"); p=m2.number_input("P",float(vp*fac),key="fp_in"); c=m3.number_input("C",float(vc*fac),key="fc_in"); f=m4.number_input("F",float(vf*fac),key="ff_in")
                
                if st.button("Mangia", type="primary", use_container_width=True, key="btn_eat"):
                    if nom:
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()

    with c_db:
        with st.container():
            st.subheader("Database")
            with st.form("db_form"):
                n=st.text_input("Nome", key="db_n"); k=st.number_input("Kcal 100g", key="db_k"); p=st.number_input("Pro", key="db_p"); c=st.number_input("Carb", key="db_c"); f=st.number_input("Fat", key="db_f")
                if st.form_submit_button("Salva"):
                    if n:
                        save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True))
                        st.rerun()

# --- TAB 3: WORKOUT ---
with tab3:
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    c1, c2 = st.columns([1,2])
    df_ex = get_data("esercizi")
    ls_ex = df_ex['nome'].tolist() if not df_ex.empty else []

    with c1:
        with st.container():
            st.subheader("Setup")
            ses = st.text_input("Sessione", "Workout", key="w_ses_nm")
            mod = st.radio("Modo", ["Pesi","Cardio"], horizontal=True, key="w_mode_rd")
            
            if mod=="Pesi":
                sl = st.selectbox("Ex", ["-- New --"]+ls_ex, key="w_ex_sl")
                nm = sl if sl!="-- New --" else st.text_input("Nome", key="w_ex_nm")
                s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
                if st.button("Aggiungi", key="w_add_bt"): 
                    st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
                
                with st.expander("Salva nuovo Ex"):
                    dn = st.text_input("Nome DB", key="w_db_nm")
                    if st.button("Salva", key="w_db_sv"): 
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":dn}])], ignore_index=True)); st.rerun()
            else:
                act = st.text_input("Attività", "Corsa", key="c_act_nm")
                km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
                if st.button("Aggiungi", key="c_add_bt"): 
                    st.session_state['sess_w'].append({"type":"cardio","nome":act,"km":km,"tempo":mi,"kcal":kc})

    with c2:
        with st.container():
            st.subheader(f"In Corso: {ses}")
            for i,e in enumerate(st.session_state['sess_w']):
                det = f"{e['serie']}x{e['reps']} {e['kg']}kg" if e['type']=="pesi" else f"{e['km']}km {e['tempo']}min"
                c_a, c_b = st.columns([5,1])
                c_a.write(f"**{e['nome']}** - {det}")
                if c_b.button("❌", key=f"wd_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
            
            st.divider()
            du = st.number_input("Durata Tot", 0, step=5, key="w_dur_t")
            if st.button("TERMINA & SALVA", type="primary", use_container_width=True, key="w_end_bt"):
                add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']})
                st.session_state['sess_w']=[]; st.success("Salvato!"); st.rerun()

# --- TAB 4: STORICO MISURE ---
with tab4:
    st.subheader("📉 Storico Peso")
    df = get_data("diario")
    ml = []
    if not df.empty:
        for _,r in df.iterrows():
            if r['tipo']=='misure':
                try: ml.append({"Data":r['data'],"Peso":json.loads(r['dettaglio_json'])['peso']})
                except:pass
    if ml: 
        st.line_chart(pd.DataFrame(ml).set_index("Data"), color="#0051FF")
    else: st.info("Nessun dato.")
    
    with st.expander("Misure Complete"):
        c1,c2 = st.columns(2)
        p=c1.number_input("Peso", key="ms_p"); a=c2.number_input("Altezza", key="ms_a")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="ms_co"); vi=c4.number_input("Vita", key="ms_vi"); fi=c5.number_input("Fianchi", key="ms_fi")
        if st.button("Salva Tutto", key="ms_sv"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi})
            st.success("OK")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (FIX COLORI & CHIAVI)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

# CSS Avanzato: Fix specifico per Dropdown e Input
st.markdown("""
<style>
    /* Forza l'intera app in Light Mode */
    .stApp {
        background-color: #F8F9FB;
        color: #1f1f1f;
    }
    
    /* Testi generici */
    p, div, label, span, li {
        color: #1f1f1f !important;
    }
    
    /* Titoli in Blu */
    h1, h2, h3, h4, h5, h6 {
        color: #0051FF !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Card Bianche con ombra */
    div[data-testid="stContainer"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    
    /* FIX MENU A TENDINA (Selectbox) - Forza sfondo bianco e testo nero */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"] {
        background-color: #ffffff !important;
    }
    div[role="option"] {
        color: #000000 !important;
        background-color: #ffffff !important;
    }
    div[role="option"]:hover {
        background-color: #f0f2f6 !important;
    }
    
    /* Input Fields (Numeri e Testo) */
    .stTextInput input, .stNumberInput input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc;
    }
    
    /* Metriche */
    div[data-testid="stMetricValue"] {
        color: #0051FF !important;
        font-size: 26px !important;
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
            st.text_input("Password", type="password", on_change=password_entered, key="main_login_pwd")
    return False

def password_entered():
    if st.session_state["main_login_pwd"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["main_login_pwd"]
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

def get_foto_obiettivo():
    df = get_data("diario")
    if not df.empty:
        settings = df[df['tipo'] == 'settings']
        if not settings.empty:
            try:
                last = settings.iloc[-1]
                d = json.loads(last['dettaglio_json'])
                return d.get('url_foto', '')
            except: pass
    return ''

# ==========================================
# 📱 SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=60)
    st.markdown("### Fit Tracker Pro")
    
    st.markdown("---")
    st.markdown("**🏆 Obiettivo**")
    url_foto = get_foto_obiettivo()
    if url_foto:
        try: st.image(url_foto, use_container_width=True)
        except: st.error("Link rotto")
    else: st.info("Nessuna foto")
    
    with st.expander("📸 Cambia Foto"):
        new_url = st.text_input("Link Foto (.jpg)", key="side_foto_url")
        if st.button("Salva", type="primary", key="side_foto_btn"):
            if new_url:
                add_riga_diario("settings", {"url_foto": new_url})
                st.success("OK!"); st.rerun()

    st.markdown("---")
    st.markdown("**⚖️ Peso Rapido**")
    w_fast = st.number_input("Peso (kg)", 0.0, format="%.1f", key="side_w_fast")
    if st.button("Salva Peso", key="side_w_btn"):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast})
            st.toast("Salvato!"); st.rerun()
            
    st.markdown("---")
    st.markdown("**🤖 Coach AI**")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    if st.session_state.chat:
        last = st.session_state.chat[-1]
        if last['role']=='assistant': st.info(last['txt'])
    
    qs = st.text_input("Domanda veloce...", key="side_ai_q")
    if st.button("Chiedi", key="side_ai_btn"):
        st.session_state.chat.append({"role":"user","txt":qs})
        ans = "Errore AI"
        if gemini_ok:
            try: ans = model.generate_content(f"Sei un PT esperto. Rispondi brevemente a: {qs}").text
            except Exception as e: ans = str(e)
        st.session_state.chat.append({"role":"assistant","txt":ans})
        st.rerun()

# ==========================================
# 🏠 MAIN APP
# ==========================================
st.title(f"Bentornato, Atleta.")
st.caption(f"📅 Diario: {get_oggi()}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df = get_data("diario")
    oggi = get_oggi()
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    cal=pro=carb=fat=0
    pasti=[]
    if not df_oggi.empty:
        for i,r in df_oggi.iterrows():
            if r['tipo']=='pasto':
                try:
                    d=json.loads(r['dettaglio_json'])
                    d['idx']=i
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
                    pasti.append(d)
                except:pass

    k1,k2,k3,k4 = st.columns(4)
    with k1:
        with st.container():
            st.metric("Kcal", int(cal), delta="Target: 2500")
            st.progress(min(cal/2500,1.0))
    with k2:
        with st.container():
            st.metric("Pro", f"{int(pro)}g", delta="Target: 180g")
            st.progress(min(pro/180,1.0))
    with k3:
        with st.container(): st.metric("Carb", f"{int(carb)}g")
    with k4:
        with st.container(): st.metric("Fat", f"{int(fat)}g")

    c_gr, c_list = st.columns([1,2])
    with c_gr:
        with st.container():
            st.markdown("**Macro**")
            if cal>0:
                s = pd.DataFrame({"M":["P","C","F"], "V":[pro*4,carb*4,fat*9]})
                c = alt.Chart(s).encode(theta=alt.Theta("V",stack=True), color=alt.Color("M", scale=alt.Scale(range=['#0051FF','#FFC107','#FF4B4B'])))
                st.altair_chart(c.mark_arc(innerRadius=40), use_container_width=True)
            else: st.caption("No data")
    
    with c_list:
        with st.container():
            st.markdown("**Diario Oggi**")
            if pasti:
                for p in pasti:
                    ic = "💊" if p.get('pasto')=="Integrazione" else "🍽️"
                    c1,c2,c3 = st.columns([4,2,1])
                    c1.markdown(f"{ic} **{p['nome']}**")
                    c2.caption(f"{int(p['cal'])} kcal")
                    if c3.button("🗑️", key=f"del_dash_{p['idx']}"): delete_riga(p['idx']); st.rerun()
            else: st.caption("Vuoto.")

# --- TAB 2: ALIMENTAZIONE ---
with tab2:
    c_in, c_db = st.columns([2,1])
    df_cibi = get_data("cibi")
    nomi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with c_in:
        st.subheader("Aggiungi")
        with st.container():
            cat = st.selectbox("Tipo", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="cat_alim_sel")
            
            if cat == "Integrazione":
                tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], horizontal=True, key="int_form_rad")
                u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                c1,c2=st.columns([2,1])
                nom = c1.text_input("Nome", key="int_name")
                q = c2.number_input(f"Qta ({u})", 0.0, step=1.0, key="int_qty")
                
                with st.expander("Macro"):
                    k=st.number_input("K",0.0,key="ik"); p=st.number_input("P",0.0,key="ip"); c=st.number_input("C",0.0,key="ic"); f=st.number_input("F",0.0,key="if")
                
                if st.button("Aggiungi", type="primary", use_container_width=True, key="btn_add_int"):
                    if nom:
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()
            else:
                sel = st.selectbox("Cerca", ["-- Manuale --"]+nomi, key="food_search_sel")
                vn,vk,vp,vc,vf = "",0,0,0,0
                if sel!="-- Manuale --" and not df_cibi.empty:
                    r = df_cibi[df_cibi['nome']==sel].iloc[0]
                    vn=r['nome']; vk=r['kcal']; vp=r['pro']; vc=r['carb']; vf=r['fat']
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", vn, key="food_name_in")
                gr = c2.number_input("Grammi", 100.0, step=10.0, key="food_gr_in")
                
                fac = gr/100
                m1,m2,m3,m4=st.columns(4)
                # CHIAVI AGGIORNATE PER EVITARE CONFLITTI
                k=m1.number_input("K",float(vk*fac),key="fk_in"); p=m2.number_input("P",float(vp*fac),key="fp_in"); c=m3.number_input("C",float(vc*fac),key="fc_in"); f=m4.number_input("F",float(vf*fac),key="ff_in")
                
                if st.button("Mangia", type="primary", use_container_width=True, key="btn_eat"):
                    if nom:
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()

    with c_db:
        st.subheader("Database")
        with st.container():
            with st.form("db_f"):
                n=st.text_input("Nome", key="dbn"); k=st.number_input("Kcal 100g", key="dbk"); p=st.number_input("Pro", key="dbp"); c=st.number_input("Carb", key="dbc"); f=st.number_input("Fat", key="dbf")
                if st.form_submit_button("Salva"):
                    if n:
                        save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True))
                        st.rerun()

# --- WORKOUT ---
with tab3:
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    c1, c2 = st.columns([1,2])
    df_ex = get_data("esercizi")
    ls_ex = df_ex['nome'].tolist() if not df_ex.empty else []

    with c1:
        with st.container():
            st.markdown("**Setup**")
            ses = st.text_input("Sessione", "Workout", key="w_ses_title")
            mod = st.radio("Modo", ["Pesi","Cardio"], horizontal=True, key="w_mode_r")
            
            if mod=="Pesi":
                sl = st.selectbox("Ex", ["-- New --"]+ls_ex, key="w_sel_ex")
                nm = sl if sl!="-- New --" else st.text_input("Nome", key="w_nm_new")
                s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
                if st.button("Aggiungi", key="w_add_btn"): 
                    st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
                
                with st.expander("Salva nuovo Ex"):
                    dn = st.text_input("Nome DB", key="w_db_name")
                    if st.button("Salva", key="w_db_save"): 
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":dn}])], ignore_index=True)); st.rerun()
            else:
                act = st.text_input("Attività", "Corsa", key="c_act_name")
                km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
                if st.button("Aggiungi", key="c_add_btn"): 
                    st.session_state['sess_w'].append({"type":"cardio","nome":act,"km":km,"tempo":mi,"kcal":kc})

    with c2:
        with st.container():
            st.markdown(f"**In Corso: {ses}**")
            for i,e in enumerate(st.session_state['sess_w']):
                det = f"{e['serie']}x{e['reps']} {e['kg']}kg" if e['type']=="pesi" else f"{e['km']}km {e['tempo']}min"
                c_a, c_b = st.columns([5,1])
                c_a.write(f"**{e['nome']}** - {det}")
                if c_b.button("❌", key=f"wd_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
            
            st.divider()
            du = st.number_input("Durata Tot", 0, step=5, key="wdur_tot")
            if st.button("TERMINA & SALVA", type="primary", use_container_width=True, key="wend_btn"):
                add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']})
                st.session_state['sess_w']=[]; st.success("Salvato!"); st.rerun()

# --- STORICO ---
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
    else: st.info("No data")
    
    with st.expander("Inserimento Misure Completo"):
        c1,c2 = st.columns(2)
        # CHIAVI AGGIORNATE QUI (MIS_*) PER NON ANDARE IN CONFLITTO CON TAB 2
        p=c1.number_input("Peso", key="mis_p"); a=c2.number_input("Altezza", key="mis_a")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="mis_co"); vi=c4.number_input("Vita", key="mis_vi"); fi=c5.number_input("Fianchi", key="mis_fi")
        if st.button("Salva tutto", key="mis_save_btn"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi})
            st.success("Salvato!")

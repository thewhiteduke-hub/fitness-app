import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 DESIGN SYSTEM (CARD & SHADOWS)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

# CSS per le Card (Il tema Colori è gestito da config.toml)
st.markdown("""
<style>
    .block-container {padding-top: 2rem;}
    
    /* Stile Card Professionali */
    div[data-testid="stContainer"] {
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e6e6e6; /* Bordo grigio chiarissimo */
        background-color: white;   /* Sfondo card bianco */
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); /* Ombra leggera */
    }
    
    /* Sidebar pulita */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #e6e6e6;
    }
    
    /* Metriche grandi e blu */
    div[data-testid="stMetricValue"] {
        font-size: 26px;
        font-weight: 700;
        color: #0051FF;
    }
    
    /* Titoli */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
    }
    
    /* Immagini stondate */
    img { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    if "APP_PASSWORD" not in st.secrets: return True

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("")
        with st.container(border=True):
            st.markdown("### 🔒 Login Atleta")
            st.text_input("Password", type="password", on_change=password_entered, key="login_pwd")
    return False

def password_entered():
    if st.session_state["login_pwd"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["login_pwd"]
    else: st.error("Errore.")

if not check_password(): st.stop()

# AI SETUP
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
# 📱 SIDEBAR: PROFILO
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=60)
    st.markdown("### Fit Tracker Pro")
    
    st.divider()
    
    # FOTO OBIETTIVO
    st.caption("IL TUO OBIETTIVO")
    url_foto = get_foto_obiettivo()
    if url_foto:
        try: st.image(url_foto, use_container_width=True)
        except: st.error("Link errato")
    else: st.info("Nessuna foto")
    
    with st.expander("📸 Cambia Foto"):
        new_url = st.text_input("Link (.jpg)", key="side_url")
        if st.button("Salva Foto", key="btn_side_foto"):
            if new_url:
                add_riga_diario("settings", {"url_foto": new_url})
                st.success("OK"); st.rerun()

    st.divider()
    
    # PESO VELOCE
    st.caption("PESATA RAPIDA")
    col_p1, col_p2 = st.columns([2,1])
    w_fast = col_p1.number_input("Kg", 0.0, format="%.1f", key="side_w", label_visibility="collapsed")
    if col_p2.button("Salva", key="btn_side_w"):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast})
            st.toast("Peso salvato!"); st.rerun()
            
    st.divider()
    
    # AI COACH
    st.caption("AI COACH")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    if st.session_state.chat:
        last = st.session_state.chat[-1]
        if last['role']=='assistant': st.info(last['txt'])
    
    q_ai = st.text_input("Domanda...", key="ai_in")
    if st.button("Chiedi", key="ai_btn"):
        st.session_state.chat.append({"role":"user","txt":q_ai})
        ans = "Errore AI"
        if gemini_ok:
            try: ans = model.generate_content(f"Sei un PT d'elite. Rispondi brevemente: {q_ai}").text
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
                except: pass

    # KPI
    k1,k2,k3,k4 = st.columns(4)
    with k1:
        with st.container():
            st.metric("Kcal", int(cal), delta="Target: 2500")
            st.progress(min(cal/2500, 1.0))
    with k2:
        with st.container():
            st.metric("Pro", f"{int(pro)}g", delta="Target: 180g")
            st.progress(min(pro/180, 1.0))
    with k3:
        with st.container(): st.metric("Carb", f"{int(carb)}g")
    with k4:
        with st.container(): st.metric("Fat", f"{int(fat)}g")

    # Chart & List
    c_graf, c_list = st.columns([1,2])
    
    with c_graf:
        with st.container():
            st.markdown("**Bilanciamento**")
            if cal>0:
                s = pd.DataFrame({"M":["P","C","F"], "V":[pro*4,carb*4,fat*9]})
                c = alt.Chart(s).encode(theta=alt.Theta("V",stack=True), color=alt.Color("M", scale=alt.Scale(range=['#0051FF','#FFC107','#FF4B4B'])))
                st.altair_chart(c.mark_arc(innerRadius=45), use_container_width=True)
            else: st.caption("Nessun dato.")

    with c_list:
        with st.container():
            st.markdown("**Diario Oggi**")
            if pasti:
                for p in pasti:
                    ic = "💊" if p.get('pasto')=="Integrazione" else "🍽️"
                    # Usiamo colonne per allineare bene testo e bottone
                    c_txt, c_btn = st.columns([5,1])
                    c_txt.markdown(f"{ic} **{p['nome']}** \n<span style='color:gray; font-size:0.8em'>{int(p['cal'])} kcal</span>", unsafe_allow_html=True)
                    if c_btn.button("🗑️", key=f"del_{p['idx']}"):
                        delete_riga(p['idx']); st.rerun()
            else: st.caption("Vuoto.")

# --- TAB 2: CIBO ---
with tab2:
    ci, cdb = st.columns([2,1])
    df_cibi = get_data("cibi")
    nomi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with ci:
        st.subheader("Aggiungi")
        with st.container():
            # I menu a tendina ora saranno leggibili grazie al config.toml
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="cat_sel")
            
            if cat == "Integrazione":
                tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], horizontal=True, key="int_rad")
                u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                col_n, col_q = st.columns([2,1])
                nom = col_n.text_input("Nome", key="i_nom")
                q = col_q.number_input(f"Qta ({u})", 0.0, step=1.0, key="i_q")
                
                with st.expander("Valori Nutrizionali"):
                    k=st.number_input("K",0.0,key="ik"); p=st.number_input("P",0.0,key="ip"); c=st.number_input("C",0.0,key="ic"); f=st.number_input("F",0.0,key="if")
                
                if st.button("Aggiungi", type="primary", use_container_width=True, key="btn_i"):
                    if nom:
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()
            else:
                sel = st.selectbox("Cerca", ["-- Manuale --"]+nomi, key="f_sel")
                vn,vk,vp,vc,vf = "",0,0,0,0
                if sel!="-- Manuale --" and not df_cibi.empty:
                    r = df_cibi[df_cibi['nome']==sel].iloc[0]
                    vn=r['nome']; vk=r['kcal']; vp=r['pro']; vc=r['carb']; vf=r['fat']
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", vn, key="f_nom")
                gr = c2.number_input("Grammi", 100.0, step=10.0, key="f_gr")
                
                fac = gr/100
                m1,m2,m3,m4=st.columns(4)
                k=m1.number_input("K",float(vk*fac),key="fk"); p=m2.number_input("P",float(vp*fac),key="fp"); c=m3.number_input("C",float(vc*fac),key="fc"); f=m4.number_input("F",float(vf*fac),key="ff")
                
                if st.button("Mangia", type="primary", use_container_width=True, key="btn_f"):
                    if nom:
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()

    with cdb:
        st.subheader("Database")
        with st.container():
            st.info("Salva cibi (100g)")
            with st.form("dbf"):
                n=st.text_input("Nome", key="dbn"); k=st.number_input("Kcal", key="dbk"); p=st.number_input("Pro", key="dbp"); c=st.number_input("Carb", key="dbc"); f=st.number_input("Fat", key="dbf")
                if st.form_submit_button("Salva nel DB"):
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
            ses = st.text_input("Sessione", "Workout", key="w_ses")
            mod = st.radio("Modo", ["Pesi","Cardio"], horizontal=True, key="w_mod")
            
            if mod=="Pesi":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"]+ls_ex, key="w_sel")
                nm = sl if sl!="-- Nuovo --" else st.text_input("Nome", key="w_nom")
                s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
                if st.button("Aggiungi", key="w_btn"): 
                    st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
                
                with st.expander("Salva nuovo Ex"):
                    dn = st.text_input("Nome DB", key="wdn")
                    if st.button("Salva", key="wds"): 
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":dn}])], ignore_index=True)); st.rerun()
            else:
                act = st.text_input("Attività", "Corsa", key="c_act")
                km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
                if st.button("Aggiungi", key="c_btn"): 
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
            du = st.number_input("Durata Tot (min)", 0, step=5, key="wdur")
            if st.button("TERMINA & SALVA", type="primary", use_container_width=True, key="wend"):
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
        p=c1.number_input("Peso", key="fp"); a=c2.number_input("Altezza", key="fa")
        c3,c4,c5 = st.columns(3)
        co=c3.number_input("Collo", key="fco"); vi=c4.number_input("Vita", key="fv"); fi=c5.number_input("Fianchi", key="ffi")
        if st.button("Salva tutto", key="fs"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi})
            st.success("Salvato!")

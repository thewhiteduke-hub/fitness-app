import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V12.0 - SPEED OPTIMIZED)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FB; color: #1f1f1f; }
    h1, h2, h3, h4, h5, h6, p, div, span, label { color: #1f1f1f !important; }
    div[data-testid="stContainer"] { background-color: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #e0e0e0; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    
    /* FIX MENU & INPUT */
    div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #ccc !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul { background-color: #ffffff !important; }
    li[role="option"], div[role="option"] { color: #000000 !important; background-color: #ffffff !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background-color: #f0f2f6 !important; color: #000000 !important; }
    div[data-testid="stMetricValue"] { color: #0051FF !important; }
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
        st.write(""); st.title("🔒 Accesso")
        st.text_input("Password", type="password", on_change=password_entered, key="pwd_login_12")
    return False

def password_entered():
    if st.session_state["pwd_login_12"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["pwd_login_12"]
    else: st.error("Password errata")

if not check_password(): st.stop()

# AI
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash')
except: pass

# ==========================================
# 🚀 DATABASE ENGINE (CACHE OPTIMIZED)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# Cache dei dati: scarica solo ogni 10 minuti (ttl=600) se non forzato
@st.cache_data(ttl=600)
def load_data_cached(sheet_name):
    try:
        return conn.read(worksheet=sheet_name)
    except:
        return pd.DataFrame()

def get_data(sheet):
    # Se abbiamo appena salvato, usa i dati freschi, altrimenti usa la cache
    if f"last_update_{sheet}" not in st.session_state:
        return load_data_cached(sheet)
    return conn.read(worksheet=sheet, ttl=0) # Forza lettura fresca solo se necessario

def save_data(sheet, df):
    df = df.fillna("") # Anti-Crash
    conn.update(worksheet=sheet, data=df)
    st.cache_data.clear() # Pulisce la cache per forzare il ricaricamento al prossimo giro
    st.session_state[f"last_update_{sheet}"] = datetime.datetime.now() # Segna l'aggiornamento

def add_riga_diario(tipo, dati):
    df = get_data("diario") # Legge cache o fresco
    if df.empty: df = pd.DataFrame(columns=["data", "tipo", "dettaglio_json"])
    
    nuova = pd.DataFrame([{
        "data": datetime.datetime.now().strftime("%Y-%m-%d"),
        "tipo": tipo,
        "dettaglio_json": json.dumps(dati)
    }])
    
    # Concatenazione ottimizzata
    df_totale = pd.concat([df, nuova], ignore_index=True)
    save_data("diario", df_totale)

def delete_riga(idx):
    df = get_data("diario")
    df = df.drop(idx)
    save_data("diario", df)

def get_oggi(): return datetime.datetime.now().strftime("%Y-%m-%d")

# Gestione Settings con cache
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
    st.caption("v12.0 - Turbo Mode ⚡")
    
    with st.expander("Modifica Target"):
        with st.form("target_form"):
            tc = st.number_input("Target Kcal", value=int(user_settings['target_cal']))
            tp = st.number_input("Target Pro", value=int(user_settings['target_pro']))
            tca = st.number_input("Target Carb", value=int(user_settings['target_carb']))
            tf = st.number_input("Target Fat", value=int(user_settings['target_fat']))
            if st.form_submit_button("Salva"):
                ns = user_settings.copy(); ns.update({"target_cal":tc,"target_pro":tp,"target_carb":tca,"target_fat":tf})
                add_riga_diario("settings", ns); st.rerun()

    if st.button("🔄 Aggiorna Dati"): # Tasto manuale se serve refresh
        st.cache_data.clear()
        st.rerun()

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

    # KPI Veloci
    TC=user_settings['target_cal']
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Kcal", int(cal), f"Rim: {int(TC-cal)}")
    k2.metric("Pro", f"{int(pro)}g")
    k3.metric("Carb", f"{int(carb)}g")
    k4.metric("Fat", f"{int(fat)}g")
    k1.progress(min(cal/TC, 1.0) if TC>0 else 0)

    # Grafico Veloce
    cg1, cg2 = st.columns([2, 1])
    with cg2:
        if cal>0:
            s = pd.DataFrame({"M":["P","C","F"], "V":[pro*4,carb*4,fat*9]})
            c = alt.Chart(s).encode(theta=alt.Theta("V",stack=True), color=alt.Color("M", scale=alt.Scale(range=['#0051FF','#FFC107','#FF4B4B'])))
            st.altair_chart(c.mark_arc(innerRadius=60), use_container_width=True)
    
    # Liste con delete rapido
    st.subheader("🍎 Pasti Oggi")
    if pasti:
        for p in pasti:
            c1, c2 = st.columns([5,1])
            c1.markdown(f"**{p['nome']}** - {int(p['cal'])} kcal")
            if c2.button("🗑️", key=f"del_p_{p['idx']}"): delete_riga(p['idx']); st.rerun()

# --- ALIMENTAZIONE ---
with tab2:
    c_in, c_db = st.columns([2,1])
    
    # Caricamento DB Ottimizzato
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []
    
    df_int = get_data("integratori")
    nomi_int = df_int['nome'].tolist() if not df_int.empty else []

    with c_in:
        st.subheader("Inserimento")
        cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
        
        # LOGICA INTEGRATORI
        if cat == "Integrazione":
            sel_i = st.selectbox("Cerca Integratore", ["-- Manuale --"] + nomi_int, key="search_int")
            
            # TRIGGER DI AGGIORNAMENTO DATI
            if "last_sel_int" not in st.session_state: st.session_state.last_sel_int = None
            if sel_i != st.session_state.last_sel_int:
                st.session_state.last_sel_int = sel_i
                if sel_i != "-- Manuale --" and not df_int.empty:
                    try:
                        row = df_int[df_int['nome'] == sel_i].iloc[0]
                        st.session_state['i_nm'] = str(row['nome'])
                        st.session_state['i_desc_f'] = str(row.get('descrizione', ''))
                        st.session_state['i_q'] = 1.0
                        st.session_state['base_int'] = {'k': row['kcal'], 'p': row['pro'], 'c': row['carb'], 'f': row['fat']}
                        map_tipo = {"g": 0, "cps": 1, "mg": 2}
                        st.session_state['temp_tipo_idx'] = map_tipo.get(row.get('tipo', 'g'), 0)
                    except: pass
                else:
                    st.session_state['base_int'] = {'k':0,'p':0,'c':0,'f':0}
            
            base = st.session_state.get('base_int', {'k':0,'p':0,'c':0,'f':0})
            tip_idx = st.session_state.get('temp_tipo_idx', 0)

            tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], index=tip_idx, horizontal=True, key="i_rad")
            u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
            
            c1,c2 = st.columns([2,1])
            nom = c1.text_input("Nome", key="i_nm")
            q = c2.number_input(f"Qta ({u})", step=1.0, key="i_q")
            desc = st.text_area("Note", key="i_desc_f", height=100)
            
            # Calcolo Live
            val_k = base['k'] * q; val_p = base['p'] * q; val_c = base['c'] * q; val_f = base['f'] * q
            
            with st.expander("Macro"):
                k=st.number_input("K", float(val_k)); p=st.number_input("P", float(val_p))
                c=st.number_input("C", float(val_c)); f=st.number_input("F", float(val_f))
            
            if st.button("Aggiungi", type="primary", use_container_width=True):
                if nom: add_riga_diario("pasto",{"pasto":cat,"nome":nom,"desc":desc,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f}); st.success("Fatto"); st.rerun()

        # LOGICA CIBO
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
                else:
                    st.session_state['base_food'] = {'k':0,'p':0,'c':0,'f':0}
            
            base_f = st.session_state.get('base_food', {'k':0,'p':0,'c':0,'f':0})

            c1,c2 = st.columns([2,1])
            nom = c1.text_input("Nome", key="f_nm")
            gr = c2.number_input("Grammi", step=10.0, key="f_gr")
            
            fac = gr / 100
            val_k = base_f['k'] * fac; val_p = base_f['p'] * fac
            val_c = base_f['c'] * fac; val_f = base_f['f'] * fac
            
            m1,m2,m3,m4=st.columns(4)
            k=m1.number_input("K", float(val_k)); p=m2.number_input("P", float(val_p))
            c=m3.number_input("C", float(val_c)); f=m4.number_input("F", float(val_f))
            
            if st.button("Mangia", type="primary", use_container_width=True):
                if nom: add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f}); st.success("Fatto"); st.rerun()

    with c_db:
        st.subheader("DB Rapido")
        t_cibo, t_int = st.tabs(["Cibo", "Integratori"])
        with t_cibo:
            with st.form("dbf"):
                n=st.text_input("Nome"); k=st.number_input("Kcal 100g"); p=st.number_input("P"); c=st.number_input("C"); f=st.number_input("F")
                if st.form_submit_button("Salva"):
                    save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()
        with t_int:
            with st.form("dbi"):
                n=st.text_input("Nome"); d=st.text_input("Desc"); k=st.number_input("Kcal 1"); p=st.number_input("P"); c=st.number_input("C"); f=st.number_input("F")
                if st.form_submit_button("Salva"):
                    save_data("integratori", pd.concat([df_int, pd.DataFrame([{"nome":n,"descrizione":d,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()

# --- ALTRE TAB ---
with tab3:
    st.subheader("Workout")
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    c1, c2 = st.columns([1,2])
    with c1:
        ses = st.text_input("Nome Sessione", "Workout")
        ex_nm = st.text_input("Esercizio")
        s=st.number_input("Set",1); r=st.number_input("Rep",1); w=st.number_input("Kg",0.0)
        if st.button("Aggiungi Set"): st.session_state['sess_w'].append({"nome":ex_nm,"serie":s,"reps":r,"kg":w})
    
    with c2:
        for i,e in enumerate(st.session_state['sess_w']):
            st.write(f"{e['nome']}: {e['serie']}x{e['reps']} - {e['kg']}kg")
        if st.button("Salva Workout", type="primary"):
            add_riga_diario("allenamento",{"nome_sessione":ses,"durata":60,"esercizi":st.session_state['sess_w']})
            st.session_state['sess_w']=[]; st.success("Salvato"); st.rerun()

with tab4:
    st.info("Storico Misure in arrivo...")

with tab5:
    st.subheader("Calisthenics")
    n = st.text_input("Skill"); d = st.text_area("Descrizione"); u = st.text_input("Link Foto")
    if st.button("Salva Skill"):
        add_riga_diario("calisthenics", {"nome": n, "desc": d, "url": u}); st.success("OK"); st.rerun()
    
    df = get_data("diario")
    for i,r in df.iterrows():
        if r['tipo'] == 'calisthenics':
            try:
                data = json.loads(r['dettaglio_json'])
                st.markdown(f"**{data['nome']}**"); st.write(data['desc'])
                if st.button("Elimina", key=f"del_c_{i}"): delete_riga(i); st.rerun()
            except: pass

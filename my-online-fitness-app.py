import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (THE "PRO" LOOK)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

# CSS Avanzato per trasformare Streamlit in una Web App moderna
st.markdown("""
<style>
    /* Sfondo generale leggermente grigio per far risaltare le card */
    .stApp {
        background-color: #F8F9FB;
    }
    
    /* Stile per i container (Card Effect) */
    div[data-testid="stContainer"] {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #f0f2f6;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f0f2f6;
    }
    
    /* Metriche */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #0051FF;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #6c757d;
    }
    
    /* Titoli */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #1a1a1a;
        font-weight: 700;
    }
    
    /* Bottoni Primari */
    button[kind="primary"] {
        background-color: #0051FF;
        border-radius: 8px;
        border: none;
        transition: all 0.2s;
    }
    button[kind="primary"]:hover {
        background-color: #003db3;
        box-shadow: 0 4px 8px rgba(0,81,255,0.2);
    }
    
    /* Immagini Arrotondate */
    img {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN & SETUP
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    if "APP_PASSWORD" not in st.secrets: return True

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.title("🔒 Accesso")
            st.text_input("Inserisci Password", type="password", on_change=password_entered, key="password_input")
    return False

def password_entered():
    if st.session_state["password_input"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["password_input"]
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
# 🔗 DATABASE & FUNZIONI
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
# 📱 SIDEBAR: PROFILO & IMPOSTAZIONI
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=50)
    st.markdown("### Fit Tracker Pro")
    
    # 1. FOTO OBIETTIVO (Sempre visibile)
    st.markdown("---")
    st.markdown("**🏆 Il tuo Obiettivo**")
    url_foto = get_foto_obiettivo()
    if url_foto:
        try: st.image(url_foto, use_container_width=True)
        except: st.error("Link non valido")
    else:
        st.info("Nessuna foto impostata")
    
    # TASTO PER CAMBIARE FOTO (Expander)
    with st.expander("📸 Cambia Foto"):
        new_url = st.text_input("Incolla Link (.jpg/.png)", key="side_url_foto")
        if st.button("Salva Foto", key="side_btn_foto"):
            if new_url:
                add_riga_diario("settings", {"url_foto": new_url})
                st.success("Aggiornata!")
                st.rerun()

    # 2. AGGIORNAMENTO PESO RAPIDO
    st.markdown("---")
    st.markdown("**⚖️ Peso Veloce**")
    w_fast = st.number_input("Peso (kg)", 0.0, format="%.1f", key="side_weight")
    if st.button("Aggiorna Peso", key="side_btn_weight"):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast})
            st.toast("Peso salvato!")
            st.rerun()
    
    # 3. AI COACH
    st.markdown("---")
    st.markdown("**🤖 AI Coach**")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    # Mostriamo solo l'ultima risposta per non intasare la sidebar
    if st.session_state.chat:
        last_msg = st.session_state.chat[-1]
        if last_msg['role'] == 'assistant':
            st.info(last_msg['txt'])
    
    q_side = st.text_input("Chiedi al coach...", key="side_chat_in")
    if st.button("Invia", key="side_chat_btn"):
        if q_side:
            st.session_state.chat.append({"role":"user", "txt":q_side})
            ans = "Errore connessione AI"
            if gemini_ok:
                try: ans = model.generate_content(f"Sei un Personal Trainer d'élite. Rispondi brevemente a: {q_side}").text
                except Exception as e: ans = str(e)
            st.session_state.chat.append({"role":"assistant", "txt":ans})
            st.rerun()

# ==========================================
# 🏠 MAIN APP
# ==========================================
st.title(f"Bentornato, Atleta.")
st.caption(f"📅 Diario di oggi: {get_oggi()}")

# Tabs principali
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico Misure"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df = get_data("diario")
    oggi = get_oggi()
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    # CALCOLI
    cal = pro = carb = fat = 0
    pasti_oggi = []
    
    if not df_oggi.empty:
        for idx, r in df_oggi.iterrows():
            if r['tipo'] == 'pasto':
                try:
                    d = json.loads(r['dettaglio_json'])
                    d['idx'] = idx
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
                    pasti_oggi.append(d)
                except: pass

    # KPI ROW
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        with st.container():
            st.metric("Calorie", int(cal), delta="Target: 2500")
            st.progress(min(cal/2500, 1.0))
    with k2:
        with st.container():
            st.metric("Proteine", f"{int(pro)}g", delta="Target: 180g")
            st.progress(min(pro/180, 1.0))
    with k3:
        with st.container():
            st.metric("Carboidrati", f"{int(carb)}g")
    with k4:
        with st.container():
            st.metric("Grassi", f"{int(fat)}g")

    st.markdown("### 📈 Analisi")
    c_chart, c_list = st.columns([1, 2])
    
    with c_chart:
        with st.container():
            st.markdown("**Bilanciamento Macro**")
            if cal > 0:
                source = pd.DataFrame({"Macro": ["Pro", "Carb", "Fat"], "Val": [pro*4, carb*4, fat*9]})
                base = alt.Chart(source).encode(theta=alt.Theta("Val", stack=True))
                pie = base.mark_arc(innerRadius=50).encode(color=alt.Color("Macro", scale=alt.Scale(range=['#0051FF', '#FFC107', '#FF4B4B'])))
                st.altair_chart(pie, use_container_width=True)
            else:
                st.info("Nessun dato nutrizionale.")
    
    with c_list:
        with st.container():
            st.markdown("**📋 Attività Recenti**")
            if pasti_oggi:
                for p in pasti_oggi:
                    ico = "💊" if p.get('pasto')=="Integrazione" else "🍽️"
                    c1, c2, c3 = st.columns([4, 2, 1])
                    c1.markdown(f"{ico} **{p['nome']}**")
                    c2.caption(f"{int(p['cal'])} kcal")
                    if c3.button("🗑️", key=f"del_dash_{p['idx']}"):
                        delete_riga(p['idx']); st.rerun()
            else:
                st.caption("Il diario è vuoto oggi.")

# --- TAB 2: ALIMENTAZIONE ---
with tab2:
    ci, cdb = st.columns([2, 1])
    df_cibi = get_data("cibi")
    nomi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with ci:
        st.markdown("### 🍽️ Aggiungi Pasto")
        with st.container():
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="cat_sel")
            
            if cat == "Integrazione":
                col_type, col_dose = st.columns([2,1])
                tip = col_type.radio("Tipo", ["Polvere (g)", "Capsule (pz)", "Mg"], horizontal=True, key="int_rad")
                unita = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                c_name, c_qty = st.columns([2,1])
                nome = c_name.text_input("Nome Integratore", key="int_name")
                q = c_qty.number_input(f"Quantità ({unita})", 0.0, step=1.0, key="int_q")
                
                with st.expander("Valori Nutrizionali (Opzionale)"):
                    k=st.number_input("K",0.0, key="ik"); p=st.number_input("P",0.0, key="ip"); c=st.number_input("C",0.0, key="ic"); f=st.number_input("F",0.0, key="if")
                
                if st.button("Aggiungi Integratore", kind="primary", use_container_width=True, key="btn_int"):
                    if nome:
                        add_riga_diario("pasto", {"pasto":cat,"nome":nome,"gr":q,"unita":unita,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Salvato!"); st.rerun()
            else:
                sel = st.selectbox("Cerca nel Database", ["-- Manuale --"] + nomi, key="food_sel")
                vn,vk,vp,vc,vf = "",0,0,0,0
                if sel != "-- Manuale --" and not df_cibi.empty:
                    r = df_cibi[df_cibi['nome']==sel].iloc[0]
                    vn=r['nome']; vk=r['kcal']; vp=r['pro']; vc=r['carb']; vf=r['fat']
                
                c_name, c_gr = st.columns([2,1])
                nome = c_name.text_input("Nome Alimento", vn, key="food_name")
                gr = c_gr.number_input("Grammi", 100.0, step=10.0, key="food_gr")
                
                # Ricalcolo
                fac = gr/100
                m1,m2,m3,m4 = st.columns(4)
                k = m1.number_input("Kcal", value=float(vk*fac), key="fk")
                p = m2.number_input("Pro", value=float(vp*fac), key="fp")
                c = m3.number_input("Carb", value=float(vc*fac), key="fc")
                f = m4.number_input("Fat", value=float(vf*fac), key="ff")
                
                if st.button("Aggiungi Pasto", kind="primary", use_container_width=True, key="btn_food"):
                    if nome:
                        add_riga_diario("pasto", {"pasto":cat,"nome":nome,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Salvato!"); st.rerun()

    with cdb:
        st.markdown("### 💾 Database")
        with st.container():
            st.info("Salva i tuoi cibi preferiti (valori x 100g)")
            with st.form("db_form"):
                nn=st.text_input("Nome", key="db_n"); kk=st.number_input("Kcal", key="db_k"); pp=st.number_input("Pro", key="db_p"); cc=st.number_input("Carb", key="db_c"); ff=st.number_input("Fat", key="db_f")
                if st.form_submit_button("Salva nel DB"):
                    if nn:
                        save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":nn,"kcal":kk,"pro":pp,"carb":cc,"fat":ff}])], ignore_index=True))
                        st.rerun()

# --- TAB 3: WORKOUT ---
with tab3:
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    col_w1, col_w2 = st.columns([1, 2])
    df_ex = get_data("esercizi")
    ls_ex = df_ex['nome'].tolist() if not df_ex.empty else []
    
    with col_w1:
        st.markdown("### ⚙️ Setup")
        with st.container():
            sess = st.text_input("Titolo Sessione", "Workout", key="sess_tit")
            mod = st.radio("Modalità", ["Pesi", "Cardio"], horizontal=True, key="w_mod")
            st.divider()
            
            if mod == "Pesi":
                sel = st.selectbox("Scegli Esercizio", ["-- Nuovo --"] + ls_ex, key="ex_s")
                nom = sel if sel != "-- Nuovo --" else st.text_input("Nome Ex", key="ex_n")
                s=st.number_input("Serie",1, key="ws"); r=st.number_input("Reps",1, key="wr"); w=st.number_input("Kg",0.0, key="wk")
                if st.button("Aggiungi Set", key="w_add"):
                    st.session_state['sess_w'].append({"type":"pesi","nome":nom,"serie":s,"reps":r,"kg":w})
                
                with st.expander("Salva Esercizio in DB"):
                    ndb = st.text_input("Nome DB", key="w_db_n")
                    if st.button("Salva", key="w_db_s"):
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":ndb}])], ignore_index=True)); st.rerun()
            else:
                act = st.text_input("Attività", "Corsa", key="c_act")
                km = st.number_input("Km", 0.0, key="c_km"); mi = st.number_input("Min", 0, key="c_min"); kc = st.number_input("Kcal", 0, key="c_kc")
                if st.button("Aggiungi Cardio", key="c_add"):
                    st.session_state['sess_w'].append({"type":"cardio","nome":act,"km":km,"tempo":mi,"kcal":kc})

    with col_w2:
        st.markdown(f"### 📝 In Corso: {sess}")
        if st.session_state['sess_w']:
            for i,e in enumerate(st.session_state['sess_w']):
                with st.container():
                    c1, c2 = st.columns([5,1])
                    det = f"{e['serie']}x{e['reps']} @ {e['kg']}kg" if e['type']=="pesi" else f"{e['km']}km in {e['tempo']}min"
                    c1.markdown(f"**{e['nome']}** — {det}")
                    if c2.button("❌", key=f"wdel_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
            
            st.divider()
            dur = st.number_input("Durata Totale (min)", 0, step=5, key="w_dur_tot")
            if st.button("Termina e Salva Sessione", kind="primary", use_container_width=True, key="w_save_all"):
                add_riga_diario("allenamento", {"nome_sessione":sess,"durata":dur,"esercizi":st.session_state['sess_w']})
                st.session_state['sess_w'] = []; st.balloons(); st.success("Grande allenamento!"); st.rerun()
        else:
            st.info("Inizia ad aggiungere esercizi dal pannello a sinistra.")

# --- TAB 4: MISURE ---
with tab4:
    st.markdown("### 📉 Storico Peso")
    df = get_data("diario")
    misure_list = []
    if not df.empty:
        for _, r in df.iterrows():
            if r['tipo'] == 'misure':
                try:
                    d = json.loads(r['dettaglio_json'])
                    misure_list.append({"Data": r['data'], "Peso": d['peso']})
                except: pass
    
    if misure_list:
        chart_data = pd.DataFrame(misure_list).set_index("Data")
        st.line_chart(chart_data, color="#0051FF")
    else:
        st.info("Nessun dato storico disponibile.")
    
    with st.expander("Inserimento Misure Completo"):
        c1, c2 = st.columns(2)
        p=c1.number_input("Peso (kg)", key="full_p"); a=c2.number_input("Altezza (cm)", key="full_a")
        c3, c4, c5 = st.columns(3)
        co=c3.number_input("Collo", key="full_co"); vi=c4.number_input("Vita", key="full_vi"); fi=c5.number_input("Fianchi", key="full_fi")
        if st.button("Salva Report Completo", key="full_save"):
            add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi})
            st.success("Salvato!")

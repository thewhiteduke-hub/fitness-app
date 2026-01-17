import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import google.generativeai as genai

# ==========================================
# 🎨 STILE & CSS (IL TOCCO "PRO")
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

# Iniettiamo CSS per pulire l'interfaccia
st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem;}
    div[data-testid="stMetricValue"] {font-size: 1.8rem;}
    /* Stile per i box delle metriche */
    div[data-testid="metric-container"] {
        background-color: #f9f9f9;
        border: 1px solid #e6e6e6;
        padding: 10px;
        border-radius: 10px;
        color: black;
    }
    /* Bottone elimina rosso tenue */
    button[kind="secondary"] {
        border-color: #ffcccc;
        color: #ff4b4b;
    }
    button[kind="secondary"]:hover {
        background-color: #ff4b4b;
        color: white;
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

    # Layout login centrato
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 Fit Tracker Pro")
        st.text_input("Password", type="password", on_change=password_entered, key="password_input")
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
# 🔗 GESTIONE DATABASE
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
# 🤖 SIDEBAR: AI COACH (Sempre Visibile)
# ==========================================
with st.sidebar:
    st.title("🤖 Coach AI")
    st.caption("Il tuo PT sempre con te")
    
    # Chat container
    messages_container = st.container(height=400)
    if "chat" not in st.session_state: st.session_state.chat = []
    
    with messages_container:
        for m in st.session_state.chat:
            with st.chat_message(m["role"]): st.markdown(m["txt"])
            
    if p := st.chat_input("Chiedi consiglio..."):
        st.session_state.chat.append({"role":"user", "txt":p})
        with messages_container:
            with st.chat_message("user"): st.markdown(p)
            
            resp = "Errore AI"
            if gemini_ok:
                try: 
                    with st.spinner("Ragiono..."):
                        resp = model.generate_content(f"Sei un Personal Trainer esperto e motivante. Rispondi brevemente a: {p}").text
                except Exception as e: resp = str(e)
            
            st.session_state.chat.append({"role":"assistant", "txt":resp})
            with st.chat_message("assistant"): st.markdown(resp)

    st.divider()
    st.caption("Fit Tracker v2.0 Pro")

# ==========================================
# MAIN INTERFACE
# ==========================================
st.title("💪 Fit Tracker Pro")

# Tabs principali (Coach spostato in sidebar)
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Misure"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df = get_data("diario")
    oggi = get_oggi()
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    # Calcolo dati
    cal = pro = carb = fat = 0
    if not df_oggi.empty:
        for _, r in df_oggi.iterrows():
            if r['tipo'] == 'pasto':
                try:
                    d = json.loads(r['dettaglio_json'])
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
                except: pass

    ultimo_peso = "--"
    if not df.empty:
        df_misure = df[df['tipo'] == 'misure']
        if not df_misure.empty:
            try:
                last_row = df_misure.iloc[-1]
                d_mis = json.loads(last_row['dettaglio_json'])
                ultimo_peso = f"{d_mis['peso']} kg"
            except: pass

    # --- SEZIONE KPI CON PROGRESS BAR ---
    st.subheader(f"Riepilogo del {oggi}")
    
    # Obiettivi (Esempio modificabile)
    TARGET_CAL = 2500
    TARGET_PRO = 180
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🔥 Kcal", int(cal), f"{int(cal - TARGET_CAL)}")
    k2.metric("🥩 Pro", f"{int(pro)}g", f"{int(pro - TARGET_PRO)}")
    k3.metric("🍚 Carb", f"{int(carb)}g")
    k4.metric("🥑 Fat", f"{int(fat)}g")
    k5.metric("⚖️ Peso", ultimo_peso)
    
    # Barre di Progresso (Visual Impact)
    st.caption("Progresso Calorie & Proteine")
    pg1, pg2 = st.columns(2)
    with pg1:
        prog_cal = min(cal / TARGET_CAL, 1.0)
        st.progress(prog_cal)
    with pg2:
        prog_pro = min(pro / TARGET_PRO, 1.0)
        st.progress(prog_pro)

    st.markdown("---")

    # --- LAYOUT A CARD ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Selettore Rapido "Cosa vuoi vedere?"
        view_mode = st.radio("Dettagli", ["Tutto", "Solo Cibo", "Solo Workout"], horizontal=True, label_visibility="collapsed")
        
        if not df_oggi.empty:
            st.write("") # Spacer
            for idx, r in df_oggi.iterrows():
                try:
                    d = json.loads(r['dettaglio_json'])
                    mostra = False
                    
                    if r['tipo'] == 'pasto' and view_mode in ["Tutto", "Solo Cibo"]:
                        mostra = True
                        ico = "💊" if d.get('pasto') == "Integrazione" else "🍽️"
                        u_mis = d.get('unita', 'g')
                        qty = d.get('gr', 0)
                        qty_s = f"{int(qty) if qty==int(qty) else qty} {u_mis}"
                        titolo = f"{ico} {d['pasto']} - **{d['nome']}**"
                        desc = f"{qty_s} | {int(d['cal'])} kcal (P:{d['pro']} C:{d['carb']} F:{d['fat']})"
                        
                    elif r['tipo'] == 'allenamento' and view_mode in ["Tutto", "Solo Workout"]:
                        mostra = True
                        titolo = f"🏋️ Workout - **{d.get('nome_sessione','Sessione')}**"
                        desc = f"Durata: {d['durata']} min"

                    if mostra:
                        # CARD DESIGN
                        with st.container(border=True):
                            c_txt, c_btn = st.columns([5, 1])
                            with c_txt:
                                st.markdown(titolo)
                                st.caption(desc)
                            with c_btn:
                                if st.button("🗑️", key=f"dash_{idx}"):
                                    delete_riga(idx); st.rerun()
                except: pass
        else:
            st.info("Nessuna attività registrata oggi.")
            
        # Grafico Peso (Integrato qui per pulizia)
        st.subheader("📉 Trend Peso")
        if not df.empty:
            misure_list = []
            for _, r in df.iterrows():
                if r['tipo'] == 'misure':
                    try:
                        d = json.loads(r['dettaglio_json'])
                        misure_list.append({"Data": r['data'], "Peso": d['peso']})
                    except: pass
            if misure_list:
                chart_data = pd.DataFrame(misure_list).set_index("Data")
                st.area_chart(chart_data, color="#0051FF") # Area chart è più carino

    with col_right:
        # FOTO OBIETTIVO (STICKY LOOK)
        with st.container(border=True):
            st.subheader("🏆 Vision")
            saved_url = get_foto_obiettivo()
            if saved_url:
                try: st.image(saved_url, use_container_width=True)
                except: st.error("Link immagine rotto.")
            else:
                st.info("Imposta una foto obiettivo in 'Misure'")

# --- TAB 2: CIBO ---
with tab2:
    col_input, col_db = st.columns([1.5, 1])
    
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with col_input:
        st.subheader("🍽️ Aggiungi")
        
        # Container per dare ordine al form
        with st.container(border=True):
            categorie_pasto = ["Colazione", "Pranzo", "Cena", "Spuntino", "Integrazione"]
            # Usiamo i "pills" o radio orizzontali per stile
            pasto = st.selectbox("Categoria", categorie_pasto)
            
            # --- LOGICA INTEGRAZIONE ---
            if pasto == "Integrazione":
                tipo_int = st.radio("Tipo", ["Polvere (g)", "Capsule (pz)", "Mg"], horizontal=True)
                if "Polvere" in tipo_int: unita = "g"
                elif "Capsule" in tipo_int: unita = "cps"
                else: unita = "mg"
                
                c1, c2 = st.columns([2,1])
                nome = c1.text_input("Nome", placeholder="es. Creatina")
                gr = c2.number_input(f"Qta ({unita})", min_value=0.0, step=1.0)
                
                with st.expander("Valori Nutrizionali (Opzionale)"):
                    k = st.number_input("Kcal", 0.0)
                    p = st.number_input("Pro", 0.0)
                    c = st.number_input("Carb", 0.0)
                    f = st.number_input("Fat", 0.0)
                
                if st.button("Aggiungi Integratore", type="primary", use_container_width=True):
                    if nome:
                        add_riga_diario("pasto", {"pasto":pasto, "nome":nome, "cal":k, "pro":p, "carb":c, "fat":f, "gr":gr, "unita": unita})
                        st.success("Salvato!"); st.rerun()

            # --- LOGICA CIBO ---
            else:
                sel_cibo = st.selectbox("Cerca", ["-- Manuale --"] + nomi_cibi)
                gr = st.number_input("Grammi", value=100.0, step=10.0)
                
                # Auto-fill values
                v_n, v_k, v_p, v_c, v_f = "", 0.0, 0.0, 0.0, 0.0
                if sel_cibo != "-- Manuale --" and not df_cibi.empty:
                    r = df_cibi[df_cibi['nome'] == sel_cibo].iloc[0]
                    factor = gr/100
                    v_n=r['nome']; v_k=r['kcal']*factor; v_p=r['pro']*factor; v_c=r['carb']*factor; v_f=r['fat']*factor

                nome = st.text_input("Nome Alimento", v_n)
                
                # Macro in 4 colonne strette
                m1, m2, m3, m4 = st.columns(4)
                k = m1.number_input("Kcal", value=float(v_k))
                p = m2.number_input("Pro", value=float(v_p))
                c = m3.number_input("Carb", value=float(v_c))
                f = m4.number_input("Fat", value=float(v_f))
                
                if st.button("Aggiungi Pasto", type="primary", use_container_width=True):
                    if nome:
                        add_riga_diario("pasto", {"pasto":pasto, "nome":nome, "cal":k, "pro":p, "carb":c, "fat":f, "gr":gr, "unita": "g"})
                        st.success("Salvato!"); st.rerun()

    with col_db:
        st.subheader("💾 Database Personale")
        with st.container(border=True):
            st.info("Salva qui i cibi (per 100g) per trovarli dopo.")
            with st.form("db_add"):
                nn = st.text_input("Nome")
                c1,c2 = st.columns(2)
                kk = c1.number_input("Kcal")
                pp = c2.number_input("Pro")
                cc = c1.number_input("Carb")
                ff = c2.number_input("Fat")
                if st.form_submit_button("Salva nel DB"):
                    if nn:
                        new = pd.DataFrame([{"nome":nn, "kcal":kk, "pro":pp, "carb":cc, "fat":ff}])
                        save_data("cibi", pd.concat([df_cibi, new], ignore_index=True))
                        st.success("OK!"); st.rerun()

# --- TAB 3: WORKOUT ---
with tab3:
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    col_w_in, col_w_list = st.columns([1, 2])
    
    df_ex = get_data("esercizi")
    lista_ex = df_ex['nome'].tolist() if not df_ex.empty else []
    
    with col_w_in:
        with st.container(border=True):
            st.subheader("Settings")
            nome_sess = st.text_input("Titolo Sessione", value="Workout")
            mode = st.radio("Tipo", ["Pesi", "Cardio"], horizontal=True)
            
            st.divider()
            
            if mode == "Pesi":
                sel = st.selectbox("Esercizio", ["-- Nuovo --"] + lista_ex)
                nom_ex = sel if sel != "-- Nuovo --" else st.text_input("Nome Ex")
                
                r1, r2, r3 = st.columns(3)
                s = r1.number_input("Serie", 1)
                r = r2.number_input("Reps", 1)
                w = r3.number_input("Kg", 0.0)
                
                if st.button("➕ Aggiungi"):
                    if nom_ex: st.session_state['sess_w'].append({"type":"pesi", "nome":nom_ex, "serie":s, "reps":r, "kg":w})
            else:
                nom_c = st.text_input("Attività", "Corsa")
                c1, c2 = st.columns(2)
                km = c1.number_input("Km", 0.0)
                mins = c2.number_input("Min", 0)
                kc = st.number_input("Kcal Burned", 0)
                
                if st.button("➕ Aggiungi"):
                     st.session_state['sess_w'].append({"type":"cardio", "nome":nom_c, "km":km, "tempo":mins, "kcal":kc})

            # Salva nuovo esercizio in DB
            with st.expander("Salva nuovo esercizio in DB"):
                new_db_n = st.text_input("Nome")
                if st.button("Salva Ex"):
                    if new_db_n:
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":new_db_n}])], ignore_index=True))
                        st.rerun()

    with col_w_list:
        st.subheader(f"Scheda: {nome_sess}")
        
        if st.session_state['sess_w']:
            for i, item in enumerate(st.session_state['sess_w']):
                with st.container(border=True):
                    c_info, c_del = st.columns([5,1])
                    if item['type'] == "pesi":
                        c_info.markdown(f"**{item['nome']}** — {item['serie']}x{item['reps']} @ {item['kg']}kg")
                    else:
                        c_info.markdown(f"**{item['nome']}** — {item['km']}km in {item['tempo']}min")
                    
                    if c_del.button("❌", key=f"w_del_{i}"):
                        st.session_state['sess_w'].pop(i); st.rerun()
            
            st.divider()
            durata = st.number_input("Durata Totale (min)", 0, step=5)
            if st.button("💾 TERMINA & SALVA SESSIONE", type="primary", use_container_width=True):
                add_riga_diario("allenamento", {"nome_sessione": nome_sess, "durata": durata, "esercizi": st.session_state['sess_w']})
                st.session_state['sess_w'] = []
                st.balloons()
                st.success("Grande allenamento!"); st.rerun()
        else:
            st.info("Aggiungi esercizi dal pannello a sinistra.")

# --- TAB 4: MISURE ---
with tab4:
    col_m1, col_m2 = st.columns([1, 1])
    
    with col_m1:
        st.subheader("Aggiorna Misure")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            peso = c1.number_input("Peso (kg)", 0.0, format="%.1f")
            alt = c2.number_input("Altezza (cm)", 0)
            
            c3, c4, c5 = st.columns(3)
            collo = c3.number_input("Collo", 0.0)
            vita = c4.number_input("Vita", 0.0)
            fianchi = c5.number_input("Fianchi", 0.0)
            
            if st.button("Salva Misure", type="primary", use_container_width=True):
                add_riga_diario("misure", {"peso":peso, "alt":alt, "collo":collo, "vita":vita, "fianchi":fianchi})
                st.success("Aggiornato!"); st.rerun()
                
    with col_m2:
        st.subheader("Imposta Foto Obiettivo")
        with st.container(border=True):
            tabs_f = st.tabs(["Link", "Upload"])
            with tabs_f[0]:
                url = st.text_input("URL Immagine (.jpg/.png)")
                if st.button("Salva Link"):
                    if url: add_riga_diario("settings", {"url_foto": url}); st.rerun()
            with tabs_f[1]:
                up = st.file_uploader("Carica", type=['jpg','png'])
                if up: st.image(up)

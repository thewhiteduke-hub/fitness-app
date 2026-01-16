import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import google.generativeai as genai

# ==========================================
# 🔒 LOGIN
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    if "APP_PASSWORD" not in st.secrets: return True

    st.text_input("🔒 Password", type="password", on_change=password_entered, key="password_input")
    return False

def password_entered():
    if st.session_state["password_input"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["password_input"]
    else: st.error("Password errata")

# ==========================================
# CONFIGURAZIONE
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")
if not check_password(): st.stop()

# AI CONFIG
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    gemini_ok = True
except: gemini_ok = False

# ==========================================
# 🔗 DATABASE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet):
    try: return conn.read(worksheet=sheet, ttl=0)
    except: return pd.DataFrame()

def save_data(sheet, df):
    conn.update(worksheet=sheet, data=df)

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

# ==========================================
# UI & TAB
# ==========================================
st.title("💪 Fit Tracker AI")
st.caption(f"📅 Data: {get_oggi()}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Cibo", "🏋️ Workout", "📏 Misure", "🤖 AI"])

# --- DASHBOARD ---
with tab1:
    st.header("Il tuo andamento")
    df = get_data("diario")
    oggi = get_oggi()
    
    # 1. Calcolo Calorie Oggi
    cal = pro = carb = fat = 0
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    if not df_oggi.empty:
        for _, r in df_oggi.iterrows():
            try:
                d = json.loads(r['dettaglio_json'])
                if r['tipo'] == 'pasto':
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
            except: pass

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Kcal", int(cal), delta_color="normal")
    col2.metric("Pro", f"{int(pro)}g")
    col3.metric("Carb", f"{int(carb)}g")
    col4.metric("Fat", f"{int(fat)}g")

    st.divider()

    # 2. Grafico Peso
    st.subheader("📉 Andamento Peso")
    if not df.empty:
        misure_list = []
        for _, r in df.iterrows():
            if r['tipo'] == 'misure':
                try:
                    d = json.loads(r['dettaglio_json'])
                    misure_list.append({"data": r['data'], "peso": d['peso']})
                except: pass
        
        if misure_list:
            chart_data = pd.DataFrame(misure_list).set_index("data")
            st.line_chart(chart_data)
        else:
            st.info("Nessuna misura registrata ancora.")

    st.divider()

    # 3. Diario Odierno (con tasto elimina)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🍎 Pasti Oggi")
        if not df_oggi.empty:
            for idx, r in df_oggi.iterrows():
                if r['tipo'] == 'pasto':
                    d = json.loads(r['dettaglio_json'])
                    cc1, cc2 = st.columns([4,1])
                    cc1.text(f"🍽️ {d['nome']} ({int(d['cal'])} kcal)")
                    if cc2.button("🗑️", key=f"d_p_{idx}"): delete_riga(idx); st.rerun()

    with c2:
        st.subheader("🏋️ Workout Oggi")
        if not df_oggi.empty:
            for idx, r in df_oggi.iterrows():
                if r['tipo'] == 'allenamento':
                    d = json.loads(r['dettaglio_json'])
                    cc1, cc2 = st.columns([4,1])
                    with cc1:
                        st.info(f"⏱️ {d.get('durata',0)} min")
                        for ex in d['esercizi']: st.caption(f"• {ex['nome']}: {ex['serie']}x{ex['reps']} {ex['kg']}kg")
                    if cc2.button("🗑️", key=f"d_w_{idx}"): delete_riga(idx); st.rerun()

# --- CIBO ---
with tab2:
    st.header("Diario Alimentare")
    c_in, c_db = st.columns([1,1])
    
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with c_in:
        st.subheader("Mangia")
        pasto = st.selectbox("Momento", ["Colazione", "Pranzo", "Cena", "Spuntino"])
        sel_cibo = st.selectbox("Cerca Cibo", ["-- Manuale --"] + nomi_cibi)
        gr = st.number_input("Grammi", 100.0, step=10.0)

        # Autocompilazione
        v_n, v_k, v_p, v_c, v_f = "", 0.0, 0.0, 0.0, 0.0
        if sel_cibo != "-- Manuale --" and not df_cibi.empty:
            row = df_cibi[df_cibi['nome'] == sel_cibo].iloc[0]
            f = gr/100
            v_n=row['nome']; v_k=row['kcal']*f; v_p=row['pro']*f; v_c=row['carb']*f; v_f=row['fat']*f

        with st.form("f_pasto"):
            st.caption(f"Valori per {gr}g")
            nome = st.text_input("Nome", v_n)
            k = st.number_input("Kcal", value=float(v_k))
            p = st.number_input("Pro", value=float(v_p))
            c = st.number_input("Carb", value=float(v_c))
            fat = st.number_input("Fat", value=float(v_f))
            if st.form_submit_button("Aggiungi"):
                add_riga_diario("pasto", {"pasto":pasto, "nome":nome, "cal":k, "pro":p, "carb":c, "fat":fat, "gr":gr})
                st.success("Fatto!"); st.rerun()

    with c_db:
        st.subheader("Nuovo Cibo nel DB (100g)")
        with st.form("f_new_cibo"):
            nn = st.text_input("Nome")
            kk = st.number_input("Kcal"); pp = st.number_input("Pro"); cc = st.number_input("Carb"); ff = st.number_input("Fat")
            if st.form_submit_button("Salva Cibo"):
                if nn: 
                    new = pd.DataFrame([{"nome":nn, "kcal":kk, "pro":pp, "carb":cc, "fat":ff}])
                    save_data("cibi", pd.concat([df_cibi, new], ignore_index=True))
                    st.success("Salvato!"); st.rerun()

# --- WORKOUT ---
with tab3:
    st.header("🏋️ Registro Allenamenti")
    
    # Inizializza la lista temporanea della sessione
    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    # 1. SETUP SESSIONE (Nome della scheda/sessione)
    col_setup, col_list = st.columns([1, 2])
    with col_setup:
        st.subheader("Impostazioni")
        # Qui puoi scrivere "Scheda A", "Scheda B", "Cardio", ecc.
        nome_sessione = st.text_input("Nome Sessione", value="Workout", placeholder="es. Scheda A, Cardio...")
        
        st.markdown("---")
        st.write("#### Aggiungi Esercizio")
        
        # Scelta Tipo: Pesi o Cardio
        tipo_ex = st.radio("Tipo Attività", ["🏋️ Pesi", "🏃 Cardio"], horizontal=True)
        
        # Carica lista esercizi dal DB (solo per Pesi ha senso cercare i nomi)
        df_ex = get_data("esercizi")
        lista_ex = df_ex['nome'].tolist() if not df_ex.empty else []

        if tipo_ex == "🏋️ Pesi":
            # Input per PESI
            ex_sel = st.selectbox("Esercizio", ["-- Nuovo/Manuale --"] + lista_ex)
            nome_ex = ex_sel if ex_sel != "-- Nuovo/Manuale --" else st.text_input("Nome (es. Panca)")
            
            c1, c2, c3 = st.columns(3)
            serie = c1.number_input("Serie", 1, step=1)
            reps = c2.number_input("Reps", 1, step=1)
            kg = c3.number_input("Kg", 0.0, step=0.5)
            
            if st.button("➕ Aggiungi Pesi", type="primary"):
                if nome_ex:
                    st.session_state['sess_w'].append({
                        "type": "pesi", "nome": nome_ex, 
                        "serie": serie, "reps": reps, "kg": kg
                    })
                else: st.error("Inserisci il nome!")
                
        else:
            # Input per CARDIO
            nome_cardio = st.text_input("Attività (es. Corsa, Bici)", "Corsa")
            c1, c2, c3 = st.columns(3)
            km = c1.number_input("Km", 0.0, step=0.1)
            tempo = c2.number_input("Minuti", 0, step=1)
            kcal_burn = c3.number_input("Kcal", 0, step=10)
            
            if st.button("➕ Aggiungi Cardio", type="primary"):
                if nome_cardio:
                    st.session_state['sess_w'].append({
                        "type": "cardio", "nome": nome_cardio, 
                        "km": km, "tempo": tempo, "kcal": kcal_burn
                    })
        
        # Sezione per Salvare nuovi esercizi nel DB (solo nomi)
        st.markdown("---")
        with st.expander("📝 Crea nuovo Esercizio (DB)"):
            with st.form("new_ex_db"):
                new_n = st.text_input("Nome Esercizio")
                if st.form_submit_button("Salva in DB"):
                    if new_n:
                        save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":new_n}])], ignore_index=True))
                        st.success("Creato!"); st.rerun()

    # 2. LISTA SESSIONE CORRENTE
    with col_list:
        st.subheader(f"Riepilogo: {nome_sessione}")
        
        if st.session_state['sess_w']:
            # Tabella riepilogativa carina
            for i, item in enumerate(st.session_state['sess_w']):
                with st.container(border=True):
                    cols = st.columns([1, 4, 1])
                    
                    # Icona
                    cols[0].title("🏋️" if item['type']=="pesi" else "🏃")
                    
                    # Dettagli
                    with cols[1]:
                        st.write(f"**{item['nome']}**")
                        if item['type'] == "pesi":
                            st.caption(f"{item['serie']} serie x {item['reps']} reps @ {item['kg']} kg")
                        else:
                            st.caption(f"{item['km']} km in {item['tempo']} min ({item['kcal']} kcal)")
                    
                    # Tasto Rimuovi
                    if cols[2].button("🗑️", key=f"del_sess_{i}"):
                        st.session_state['sess_w'].pop(i)
                        st.rerun()

            st.divider()
            # Salvataggio Finale
            durata_tot = st.number_input("Durata Totale Sessione (min)", 0, step=5)
            
            if st.button("💾 SALVA SESSIONE NEL DIARIO", type="primary", use_container_width=True):
                # Salviamo tutto nel diario
                dati_sessione = {
                    "nome_sessione": nome_sessione, # "Scheda A", "Cardio", ecc.
                    "durata": durata_tot,
                    "esercizi": st.session_state['sess_w']
                }
                add_riga_diario("allenamento", dati_sessione)
                
                # Reset
                st.session_state['sess_w'] = []
                st.balloons()
                st.success(f"Sessione '{nome_sessione}' salvata!")
                st.rerun()
        else:
            st.info("La sessione è vuota. Aggiungi esercizi o cardio dalla colonna a sinistra.")

# --- MISURE ---
with tab4:
    st.header("📏 Misure Corporee")
    with st.form("misure_form"):
        col1, col2 = st.columns(2)
        peso = col1.number_input("Peso Corporeo (kg)", 0.0, step=0.1, format="%.1f")
        alt = col2.number_input("Altezza (cm)", 0, step=1)
        
        c1, c2, c3 = st.columns(3)
        collo = c1.number_input("Collo (cm)", 0.0, step=0.5)
        vita = c2.number_input("Vita (cm)", 0.0, step=0.5)
        fianchi = c3.number_input("Fianchi (cm)", 0.0, step=0.5)
        
        if st.form_submit_button("Salva Misure"):
            add_riga_diario("misure", {"peso":peso, "alt":alt, "collo":collo, "vita":vita, "fianchi":fianchi})
            st.success("Misure aggiornate!"); st.rerun()

# --- AI ---
with tab5:
    st.header("🤖 Coach")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["txt"])
        
    if p := st.chat_input("Chiedi..."):
        st.session_state.chat.append({"role":"user", "txt":p})
        with st.chat_message("user"): st.markdown(p)
        
        resp = "Errore AI"
        if gemini_ok:
            try: resp = model.generate_content(f"Sei un PT. Rispondi a: {p}").text
            except Exception as e: resp = str(e)
            
        st.session_state.chat.append({"role":"assistant", "txt":resp})
        with st.chat_message("assistant"): st.markdown(resp)

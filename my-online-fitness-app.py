import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 UI/UX DESIGN SYSTEM (V14.0 - DATE PICKER)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* 1. Sfondo App */
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

    /* 5. FIX MENU A TENDINA E INPUT */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul {
        background-color: #ffffff !important;
    }
    li[role="option"], div[role="option"] {
        color: #000000 !important; 
        background-color: #ffffff !important;
    }
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: #f0f2f6 !important;
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
# 🚀 DATABASE ENGINE (CACHING SYSTEM)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# Funzione interna che usa la cache per non scaricare sempre i dati
@st.cache_data(ttl=600)  # Mantiene i dati in memoria per 10 minuti
def fetch_data_cached(sheet_name):
    try:
        return conn.read(worksheet=sheet_name)
    except:
        return pd.DataFrame()

def get_data(sheet):
    # Chiama la funzione cachata
    return fetch_data_cached(sheet)

def save_data(sheet, df):
    # 1. Pulisce i dati (Anti-Crash)
    df = df.fillna("") 
    # 2. Scrive su Google Sheets
    conn.update(worksheet=sheet, data=df)
    # 3. SVUOTA LA CACHE: Così al prossimo "get_data" scaricherà i dati aggiornati
    fetch_data_cached.clear()
    st.cache_data.clear()

def add_riga_diario(tipo, dati):
    df = get_data("diario")
    if df.empty: df = pd.DataFrame(columns=["data", "tipo", "dettaglio_json"])
    
    # IMPORTANTE: Salva sempre con la data di OGGI, indipendentemente dalla visualizzazione
    data_oggi = datetime.datetime.now().strftime("%Y-%m-%d")
    
    nuova = pd.DataFrame([{
        "data": data_oggi,
        "tipo": tipo,
        "dettaglio_json": json.dumps(dati)
    }])
    df_totale = pd.concat([df, nuova], ignore_index=True)
    save_data("diario", df_totale)

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
    st.caption("v14.0 - Date Picker")
    
    st.markdown("---")
    # --- NUOVO SELETTORE DATA ---
    st.markdown("**📅 Seleziona Data**")
    selected_date = st.date_input("Visualizza diario del:", datetime.date.today())
    # Converti in stringa per il filtro dataframe
    data_filtro = selected_date.strftime("%Y-%m-%d")
    
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
# Mostra la data che stiamo visualizzando
st.caption(f"📅 Riepilogo del: {data_filtro}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Alimentazione", "🏋️ Workout", "📏 Storico", "🤸 Calisthenics"])

# --- DASHBOARD ---
with tab1:
    df = get_data("diario")
    
    # FILTRO DATI IN BASE ALLA DATA SELEZIONATA NELLA SIDEBAR
    df_oggi = df[df['data'] == data_filtro] if not df.empty else pd.DataFrame()
    
    cal = pro = carb = fat = 0
    # Struttura per raggruppare i pasti per categoria
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
                    # Calcolo Totali
                    cal += d['cal']; pro += d['pro']; carb += d['carb']; fat += d['fat']
                    # Raggruppamento
                    cat = d.get('pasto', 'Spuntino')
                    if cat in meal_groups:
                        meal_groups[cat].append(d)
                    else:
                        # Fallback se la categoria non matcha
                        meal_groups["Spuntino"].append(d)
                elif r['tipo'] == 'allenamento':
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
                    # Se la misura è della data selezionata, la mostriamo come "Peso del giorno"
                    if r['data'] == data_filtro:
                        curr_peso = f"{d['peso']} kg"
                except: pass
    
    # Se non c'è peso registrato OGGI, mostra l'ultimo disponibile in assoluto
    if curr_peso == "--" and misure_list:
        curr_peso = f"{misure_list[-1]['Peso']} kg"

    # KPI
    TC = user_settings['target_cal']; TP = user_settings['target_pro']
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Kcal", int(cal), f"Rim: {int(TC-cal)}"); st.progress(min(cal/TC, 1.0) if TC > 0 else 0)
    with k2: st.metric("Pro", f"{int(pro)}g", f"Target: {TP}g"); st.progress(min(pro/TP, 1.0) if TP > 0 else 0)
    with k3: st.metric("Carb", f"{int(carb)}g")
    with k4: st.metric("Fat", f"{int(fat)}g")
    with k5: st.metric("Peso", curr_peso)

    # GRAFICI
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
        if cal > 0:
            s = pd.DataFrame({"M":["P","C","F"], "V":[pro*4,carb*4,fat*9]})
            c = alt.Chart(s).encode(theta=alt.Theta("V",stack=True), color=alt.Color("M", scale=alt.Scale(range=['#0051FF','#FFC107','#FF4B4B'])))
            st.altair_chart(c.mark_arc(innerRadius=60), use_container_width=True)
        else: st.caption("Nessun dato.")

    # LISTE DETTAGLIATE CON MENU A TENDINA
    cl1, cl2 = st.columns(2)
    
    # --- COLONNA PASTI SUDDIVISI ---
    with cl1:
        st.subheader("🍎 Diario Alimentare")
        found_meals = False
        # Ordine di visualizzazione personalizzato
        order = ["Colazione", "Pranzo", "Cena", "Spuntino", "Integrazione"]
        
        for cat in order:
            items = meal_groups[cat]
            if items:
                found_meals = True
                # Calcolo calorie parziali per il titolo dell'expander
                sub_cal = sum(x['cal'] for x in items)
                
                # Menu a tendina per categoria
                with st.expander(f"**{cat}** ({int(sub_cal)} kcal)", expanded=True):
                    for p in items:
                        c_txt, c_btn = st.columns([5, 1])
                        qty = f"{int(p.get('gr',0))} {p.get('unita','g')}"
                        c_txt.markdown(f"- {p['nome']} ({qty})")
                        # Tasto delete piccolo
                        if c_btn.button("❌", key=f"del_p_{p['idx']}"): 
                            delete_riga(p['idx'])
                            st.rerun()
        
        if not found_meals:
            st.info(f"Nessun pasto il {data_filtro}.")

    # --- COLONNA WORKOUT CON ESERCIZI ---
    with cl2:
        st.subheader("🏋️ Scheda Allenamento")
        if allenamenti:
            for w in allenamenti:
                # Menu a tendina per la sessione
                with st.expander(f"**{w.get('nome_sessione','Workout')}** ({w['durata']} min)", expanded=True):
                    
                    # Lista esercizi dentro l'expander
                    if 'esercizi' in w and w['esercizi']:
                        for ex in w['esercizi']:
                            t = ex.get('type', 'pesi')
                            
                            # Formattazione corretta per ogni tipo
                            if t == "pesi": 
                                det = f"{ex['serie']}x{ex['reps']} {ex['kg']}kg"
                            elif t == "isometria":
                                zav = f"+{ex['kg']}kg" if ex.get('kg', 0) > 0 else "bw"
                                det = f"{ex['serie']}x {ex['tempo']}s ({zav})"
                            elif t == "calisthenics":
                                zav = f"+{ex['kg']}kg" if ex.get('kg', 0) > 0 else "bw"
                                det = f"{ex['serie']}x{ex['reps']} ({zav})"
                            else: 
                                det = f"{ex['km']}km {ex['tempo']}m"
                            
                            st.markdown(f"🔹 **{ex['nome']}**: {det}")
                    else:
                        st.caption("Nessun esercizio salvato.")
                    
                    st.markdown("---")
                    # Tasto per eliminare l'intera sessione
                    if st.button("Elimina Sessione", key=f"del_w_{w['idx']}"):
                        delete_riga(w['idx'])
                        st.rerun()
        else:
            st.info(f"Nessun allenamento il {data_filtro}.")

# --- ALIMENTAZIONE (AUTOFILL + FIX) ---
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
            
            # === INTEGRATORI LOGIC ===
            if cat == "Integrazione":
                sel_i = st.selectbox("Cerca Integratore", ["-- Manuale --"] + nomi_int, key="search_int")
                
                # TRIGGER UPDATE
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
                
                # TEXT AREA PER DESCRIZIONE
                desc = st.text_area("A cosa serve / Note", key="i_desc_f", height=130)
                
                # CALCOLO LIVE
                val_k = base['k'] * q
                val_p = base['p'] * q
                val_c = base['c'] * q
                val_f = base['f'] * q
                
                # FORZO STATO
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
            
            # === CIBO NORMALE LOGIC ===
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
                val_k = base_f['k'] * fac
                val_p = base_f['p'] * fac
                val_c = base_f['c'] * fac
                val_f = base_f['f'] * fac
                
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
        t_cibo, t_int, t_ex = st.tabs(["Cibo", "Integratori", "Esercizi"])
        
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
                    # Text area anche nel DB per consistenza
                    di=st.text_area("Descrizione", key="dbi_d", height=100)
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
        
        # 3. NUOVA SCHEDA: Caricamento Esercizi in Massa
        with t_ex:
            st.caption("Incolla qui la lista (uno per riga)")
            bulk_text = st.text_area("Lista Esercizi", height=200, key="bulk_ex_area")
            
            if st.button("Salva Lista Esercizi"):
                if bulk_text:
                    # Carica gli esercizi attuali per sicurezza
                    df_current_ex = get_data("esercizi")
                    
                    # Pulisce la lista (rimuove righe vuote)
                    lista = [x.strip() for x in bulk_text.split('\n') if x.strip()]
                    
                    if lista:
                        # Crea il dataframe e salva (Default Pesi se non specificato)
                        new_df = pd.DataFrame({'nome': lista, 'categoria': 'Pesi'})
                        save_data("esercizi", pd.concat([df_current_ex, new_df], ignore_index=True))
                        st.success(f"Caricati {len(lista)} esercizi!"); st.rerun()

# --- WORKOUT ---
with tab3:
    st.subheader("Workout")
    
    # 1. Caricamento e Preparazione DB Esercizi
    df_ex = get_data("esercizi")
    
    # Se il DB è vuoto o manca la colonna 'categoria', crea una struttura base
    if df_ex.empty:
        df_ex = pd.DataFrame(columns=["nome", "categoria"])
    elif "categoria" not in df_ex.columns:
        df_ex["categoria"] = "Pesi" # Default fallback per vecchi dati
    
    # Liste filtrate per categoria
    ls_pesi = df_ex[df_ex['categoria'] == 'Pesi']['nome'].tolist()
    ls_cali = df_ex[df_ex['categoria'] == 'Calisthenics']['nome'].tolist()
    ls_iso = df_ex[df_ex['categoria'] == 'Isometria']['nome'].tolist()
    ls_cardio = df_ex[df_ex['categoria'] == 'Cardio']['nome'].tolist()

    if 'sess_w' not in st.session_state: st.session_state['sess_w'] = []
    
    c1, c2 = st.columns([1,2])

    with c1:
        with st.container():
            st.caption("Setup Sessione")
            ses = st.text_input("Nome Sessione", "Workout", key="w_ses")
            mod = st.radio("Modo", ["Pesi", "Calisthenics", "Isometria", "Cardio"], horizontal=True, key="w_mod")
            
            # === PESI ===
            if mod == "Pesi":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + sorted(ls_pesi), key="w_sl")
                nm = st.text_input("Nome", key="w_nm") if sl == "-- Nuovo --" else sl
                
                s=st.number_input("Set",1,key="ws"); r=st.number_input("Rep",1,key="wr"); w=st.number_input("Kg",0.0,key="ww")
                
                if st.button("Aggiungi Set", key="wb"): 
                    st.session_state['sess_w'].append({"type":"pesi","nome":nm,"serie":s,"reps":r,"kg":w})
                
                # Salva con categoria "Pesi"
                with st.expander("Salva nel DB"):
                    if st.button("Salva come Pesi", key="wds"): 
                        new_row = pd.DataFrame([{"nome":nm, "categoria":"Pesi"}])
                        save_data("esercizi", pd.concat([df_ex, new_row], ignore_index=True)); st.rerun()

            # === CALISTHENICS ===
            elif mod == "Calisthenics":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + sorted(ls_cali), key="w_cali_sl")
                nm = st.text_input("Nome", key="w_cali_nm") if sl == "-- Nuovo --" else sl
                
                c_a,c_b,c_c = st.columns(3)
                s = c_a.number_input("Set", 1, key="wcs"); r = c_b.number_input("Rep", 1, key="wcr"); w = c_c.number_input("Kg", 0.0, key="wcw")
                
                if st.button("Aggiungi Set", key="w_cali_b"):
                    st.session_state['sess_w'].append({"type":"calisthenics","nome":nm,"serie":s,"reps":r,"kg":w})
                
                with st.expander("Salva nel DB"):
                    if st.button("Salva come Cali", key="wds_cali"): 
                        new_row = pd.DataFrame([{"nome":nm, "categoria":"Calisthenics"}])
                        save_data("esercizi", pd.concat([df_ex, new_row], ignore_index=True)); st.rerun()

            # === ISOMETRIA ===
            elif mod == "Isometria":
                sl = st.selectbox("Esercizio", ["-- Nuovo --"] + sorted(ls_iso), key="w_iso_sl")
                nm = st.text_input("Nome", key="w_iso_nm") if sl == "-- Nuovo --" else sl
                
                c_a,c_b,c_c = st.columns(3)
                s = c_a.number_input("Set", 1, key="wis_s"); t = c_b.number_input("Sec", 10, step=5, key="wis_t"); w = c_c.number_input("Kg", 0.0, key="wis_w")
                
                if st.button("Aggiungi Set", key="w_iso_b"):
                    st.session_state['sess_w'].append({"type":"isometria","nome":nm,"serie":s,"tempo":t,"kg":w})
                
                with st.expander("Salva nel DB"):
                    if st.button("Salva come Iso", key="wds_iso"): 
                        new_row = pd.DataFrame([{"nome":nm, "categoria":"Isometria"}])
                        save_data("esercizi", pd.concat([df_ex, new_row], ignore_index=True)); st.rerun()

            # === CARDIO ===
            else:
                sl = st.selectbox("Attività", ["-- Nuovo --"] + sorted(ls_cardio), key="w_cardio_sl")
                nm = st.text_input("Nome", key="ca_nm") if sl == "-- Nuovo --" else sl
                
                km=st.number_input("Km",0.0,key="ck"); mi=st.number_input("Min",0,key="cm"); kc=st.number_input("Kcal",0,key="cc")
                
                if st.button("Aggiungi Cardio", key="cb"): 
                    st.session_state['sess_w'].append({"type":"cardio","nome":nm,"km":km,"tempo":mi,"kcal":kc})
                
                with st.expander("Salva nel DB"):
                    if st.button("Salva come Cardio", key="wds_cardio"): 
                        new_row = pd.DataFrame([{"nome":nm, "categoria":"Cardio"}])
                        save_data("esercizi", pd.concat([df_ex, new_row], ignore_index=True)); st.rerun()

    with c2:
        with st.container():
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
                    if c_del.button("❌", key=f"del_w_{i}"):
                        st.session_state['sess_w'].pop(i)
                        st.rerun()
                
                st.divider()
                du = st.number_input("Durata (min)", 0, step=5, key="wdur")
                if st.button("TERMINA & SALVA", type="primary", use_container_width=True):
                    add_riga_diario("allenamento",{"nome_sessione":ses,"durata":du,"esercizi":st.session_state['sess_w']})
                    st.session_state['sess_w'] = []
                    st.success("Allenamento Salvato!")
                    st.rerun()
            else:
                st.info("Aggiungi il primo esercizio dalla colonna a sinistra.")

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

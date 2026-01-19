import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt
import google.generativeai as genai

# ==========================================
# 🎨 SETUP PRO (Il design è gestito da config.toml)
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

# CSS SOLO per Layout, Ombre e Bordi (I colori sono nel config.toml)
st.markdown("""
<style>
    /* Card Design */
    div[data-testid="stContainer"] {
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        background-color: white;
    }
    
    /* Sidebar Border */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #e0e0e0;
    }
    
    /* Titoli */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
    }
    
    /* Metriche Grandi */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
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
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    if "APP_PASSWORD" not in st.secrets: return True
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("")
        with st.container(border=True):
            st.title("🔒 Accesso")
            st.text_input("Password", type="password", on_change=password_entered, key="pwd_login_v6")
    return False

def password_entered():
    if st.session_state["pwd_login_v6"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["pwd_login_v6"]
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
    st.markdown("### Fit Tracker Pro")
    st.caption("v6.0 - Ultimate")
    
    st.markdown("---")
    st.markdown("**🎯 Target**")
    with st.expander("Modifica"):
        with st.form("t_form"):
            tc=st.number_input("Kcal", int(user_settings['target_cal']))
            tp=st.number_input("Pro", int(user_settings['target_pro']))
            tca=st.number_input("Carb", int(user_settings['target_carb']))
            tf=st.number_input("Fat", int(user_settings['target_fat']))
            if st.form_submit_button("Salva"):
                ns = user_settings.copy(); ns.update({"target_cal":tc,"target_pro":tp,"target_carb":tca,"target_fat":tf})
                add_riga_diario("settings", ns); st.rerun()

    st.markdown("---")
    st.markdown("**🏆 Vision**")
    if user_settings['url_foto']:
        try: st.image(user_settings['url_foto'], use_container_width=True)
        except: st.error("Link rotto")
    else: st.info("No foto")
    
    with st.expander("📸 Cambia"):
        nu = st.text_input("Link Foto", key="s_url")
        if st.button("Salva", key="s_btn"):
            if nu:
                ns = user_settings.copy(); ns['url_foto'] = nu
                add_riga_diario("settings", ns); st.rerun()

    st.markdown("---")
    st.markdown("**⚖️ Peso Rapido**")
    w_fast = st.number_input("Peso (kg)", 0.0, format="%.1f", key="side_w_f")
    if st.button("Salva Peso", key="side_btn_w"):
        if w_fast > 0:
            add_riga_diario("misure", {"peso": w_fast})
            st.toast("Salvato!"); st.rerun()

    st.markdown("---")
    st.markdown("**🤖 Coach**")
    if "chat" not in st.session_state: st.session_state.chat = []
    q_ai = st.text_input("Chiedi...", key="s_ai")
    if st.button("Invia", key="s_aibtn"):
        st.session_state.chat.append({"role":"user","txt":q_ai})
        ans="Errore AI"; 
        if gemini_ok:
            try: ans=model.generate_content(f"Sei un PT. Rispondi: {q_ai}").text
            except: pass
        st.session_state.chat.append({"role":"assistant","txt":ans}); st.rerun()
    if st.session_state.chat: st.info(st.session_state.chat[-1]['txt'])

# ==========================================
# 🏠 MAIN
# ==========================================
st.title(f"Bentornato, Atleta.")
st.caption(f"📅 Data: {get_oggi()}")

# Modifica questa riga nel tuo codice:
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

    # KPI
    TC=user_settings['target_cal']; TP=user_settings['target_pro']
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1:
        with st.container():
            st.metric("Kcal", int(cal), f"Rim: {int(TC-cal)}")
            st.progress(min(cal/TC, 1.0) if TC>0 else 0)
    with k2:
        with st.container(): st.metric("Pro", f"{int(pro)}g", f"Target: {TP}g")
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
            st.subheader("📊 Ripartizione Macro") # Titolo corretto
            if cal>0:
                s = pd.DataFrame({"M":["P","C","F"], "V":[pro*4,carb*4,fat*9]})
                c = alt.Chart(s).encode(theta=alt.Theta("V",stack=True), color=alt.Color("M", scale=alt.Scale(range=['#0051FF','#FFC107','#FF4B4B'])))
                st.altair_chart(c.mark_arc(innerRadius=60), use_container_width=True)
            else: st.caption("Nessun dato.")

    # LISTE
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

# --- ALIMENTAZIONE ---
# --- TAB 2: ALIMENTAZIONE (AUTOFIL + DESCRIZIONE) ---
with tab2:
    c_in, c_db = st.columns([2,1])
    
    # Carichiamo i DB
    df_cibi = get_data("cibi")
    nomi_cibi = df_cibi['nome'].tolist() if not df_cibi.empty else []
    
    df_int = get_data("integratori")
    nomi_int = df_int['nome'].tolist() if not df_int.empty else []

    # --- COLONNA SINISTRA: INSERIMENTO NEL DIARIO ---
    with c_in:
        with st.container():
            st.subheader("Inserimento")
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="c_sel")
            
            # === INTEGRATORI ===
            if cat == "Integrazione":
                sel_i = st.selectbox("Cerca Integratore", ["-- Manuale --"] + nomi_int, key="search_int")
                
                # Variabili default (se Manuale)
                v_ni = ""; v_ti = 0; v_desc = ""; v_qta = 0.0
                unit_k=0.0; unit_p=0.0; unit_c=0.0; unit_f=0.0
                
                # LOGICA DI AUTOCOMPILAZIONE
                if sel_i != "-- Manuale --" and not df_int.empty:
                    # Trova la riga corrispondente
                    row = df_int[df_int['nome'] == sel_i].iloc[0]
                    
                    v_ni = row['nome']
                    v_desc = row.get('descrizione', '') # Recupera descrizione se c'è
                    v_qta = 1.0 # <--- Qta predefinita a 1 se selezionato da DB
                    
                    map_tipo = {"g": 0, "cps": 1, "mg": 2}
                    # Gestione robusta se il tipo non fosse salvato correttamente
                    v_ti = map_tipo.get(row.get('tipo', 'g'), 0)
                    
                    unit_k, unit_p, unit_c, unit_f = row['kcal'], row['pro'], row['carb'], row['fat']

                # Form
                tip = st.radio("Formato", ["Polvere (g)","Capsule (pz)","Mg"], index=v_ti, horizontal=True, key="i_rad")
                u = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", v_ni, key="i_nm")
                # Qui usiamo v_qta che sarà 1.0 se preso da DB, o 0.0 se manuale
                q = c2.number_input(f"Qta ({u})", value=float(v_qta), step=1.0, key="i_q")
                
                # Campo Descrizione Autocompilato
                desc = st.text_input("A cosa serve / Note", v_desc, key="i_desc_field", placeholder="es. Energia pre-workout")
                
                # Calcolo Macro in tempo reale
                val_k = unit_k * q if sel_i != "-- Manuale --" else 0.0
                val_p = unit_p * q if sel_i != "-- Manuale --" else 0.0
                val_c = unit_c * q if sel_i != "-- Manuale --" else 0.0
                val_f = unit_f * q if sel_i != "-- Manuale --" else 0.0

                with st.expander("Macro Totali (Calcolati)"):
                    k=st.number_input("K", float(val_k), key="ik"); p=st.number_input("P", float(val_p), key="ip")
                    c=st.number_input("C", float(val_c), key="ic"); f=st.number_input("F", float(val_f), key="if")
                
                if st.button("Aggiungi", type="primary", use_container_width=True, key="bi"):
                    if nom: 
                        add_riga_diario("pasto",{"pasto":cat,"nome":nom,"desc":desc,"gr":q,"unita":u,"cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("OK"); st.rerun()
            
            # === CIBO NORMALE ===
            else:
                sel = st.selectbox("Cerca", ["-- Manuale --"]+nomi_cibi, key="f_sel")
                vn,vk,vp,vc,vf = "",0,0,0,0
                if sel!="-- Manuale --" and not df_cibi.empty:
                    r = df_cibi[df_cibi['nome']==sel].iloc[0]
                    vn=r['nome']; vk=r['kcal']; vp=r['pro']; vc=r['carb']; vf=r['fat']
                
                c1,c2 = st.columns([2,1])
                nom = c1.text_input("Nome", vn, key="f_nm")
                gr = c2.number_input("Grammi", 100.0, step=10.0, key="f_gr")
                fac = gr/100
                m1,m2,m3,m4=st.columns(4)
                k=m1.number_input("K",float(vk*fac),key="fk"); p=m2.number_input("P",float(vp*fac),key="fp"); c=m3.number_input("C",float(vc*fac),key="fc"); f=m4.number_input("F",float(vf*fac),key="ff")
                
                if st.button("Mangia", type="primary", use_container_width=True, key="bf"):
                    if nom: add_riga_diario("pasto",{"pasto":cat,"nome":nom,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f}); st.success("OK"); st.rerun()

    # --- COLONNA DESTRA: GESTIONE DB ---
    with c_db:
        st.subheader("💾 Gestione DB")
        t_cibo, t_int = st.tabs(["Cibo (100g)", "Integratori"])
        
        with t_cibo:
            with st.container():
                with st.form("dbf"):
                    n=st.text_input("Nome", key="dbn"); k=st.number_input("K 100g", key="dbk"); p=st.number_input("P", key="dbp"); c=st.number_input("C", key="dbc"); f=st.number_input("F", key="dbf")
                    if st.form_submit_button("Salva Cibo"):
                        if n: save_data("cibi", pd.concat([df_cibi, pd.DataFrame([{"nome":n,"kcal":k,"pro":p,"carb":c,"fat":f}])], ignore_index=True)); st.rerun()
        
        with t_int:
            with st.container():
                st.info("Salva valori per 1 dose/grammo")
                with st.form("dbi"):
                    ni=st.text_input("Nome", key="dbi_n")
                    # Campo Descrizione da salvare nel DB
                    di=st.text_input("Descrizione (es. Post-Workout)", key="dbi_d")
                    
                    ti_sel = st.radio("Tipo", ["Polvere (g)", "Capsule (cps)", "Mg"], key="dbi_t")
                    ti_val = "g" if "Polvere" in ti_sel else ("cps" if "Capsula" in ti_sel else "mg")
                    c1,c2=st.columns(2)
                    ki=c1.number_input("Kcal x 1", key="dbi_k"); pi=c2.number_input("Pro x 1", key="dbi_p")
                    ci=c1.number_input("Carb x 1", key="dbi_c"); fi=c2.number_input("Fat x 1", key="dbi_f")
                    
                    if st.form_submit_button("Salva Integratore"):
                        if ni:
                            # Salviamo anche la colonna 'descrizione'
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

# --- TAB 5: CALISTHENICS ---
with tab5:
    st.subheader("🤸 Skills & Esercizi")
    
    # MODULO DI INSERIMENTO
    with st.container():
        with st.expander("➕ Aggiungi Nuova Skill / Foto", expanded=True):
            with st.form("form_calisthenics"):
                c1, c2 = st.columns([2, 1])
                nome_skill = c1.text_input("Nome Esercizio (es. Front Lever, Planche)")
                url_img = c2.text_input("Link Foto (.jpg/.png)")
                descrizione = st.text_area("Descrizione, Note o Progressione")
                
                if st.form_submit_button("Salva nel Diario"):
                    if nome_skill:
                        add_riga_diario("calisthenics", {
                            "nome": nome_skill,
                            "desc": descrizione,
                            "url": url_img
                        })
                        st.success("Skill salvata!")
                        st.rerun()
                    else:
                        st.error("Inserisci almeno il nome.")

    st.divider()
    
    # GALLERIA VISUALE
    df = get_data("diario")
    skills_list = []
    
    # Recuperiamo solo i dati di tipo 'calisthenics'
    if not df.empty:
        for idx, row in df.iterrows():
            if row['tipo'] == 'calisthenics':
                try:
                    d = json.loads(row['dettaglio_json'])
                    d['idx'] = idx
                    d['data_ins'] = row['data']
                    skills_list.append(d)
                except: pass
    
    if skills_list:
        # Mostriamo dall'ultimo inserito al primo
        for skill in reversed(skills_list):
            with st.container():
                col_img, col_txt = st.columns([1, 3])
                
                with col_img:
                    if skill.get('url'):
                        try: st.image(skill['url'], use_container_width=True)
                        except: st.caption("🚫 Link immagine rotto")
                    else:
                        st.info("No Foto")
                
                with col_txt:
                    c_head, c_del = st.columns([5, 1])
                    c_head.markdown(f"### {skill['nome']}")
                    if c_del.button("🗑️", key=f"del_cali_{skill['idx']}"):
                        delete_riga(skill['idx'])
                        st.rerun()
                    
                    st.caption(f"📅 Inserito il: {skill['data_ins']}")
                    st.write(skill['desc'])
    else:
        st.info("Nessuna skill registrata. Aggiungi il tuo primo esercizio sopra!")

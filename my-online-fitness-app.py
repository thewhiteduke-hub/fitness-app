import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import datetime
import altair as alt # Libreria avanzata per grafici
import google.generativeai as genai

# ==========================================
# 🎨 CONFIGURAZIONE & CSS
# ==========================================
st.set_page_config(page_title="Fit Tracker Pro", page_icon="💪", layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 2rem;}
    div[data-testid="stContainer"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    h3 {color: #0051FF;}
    /* Metriche più grandi */
    div[data-testid="stMetricValue"] {font-size: 24px;}
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
        st.title("🔒 Fit Tracker Access")
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
# 🔝 HEADER
# ==========================================
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("💪 Fit Tracker Pro")
    st.caption(f"Progressi e Nutrizione | Data: {get_oggi()}")

with col_h2:
    url_foto = get_foto_obiettivo()
    if url_foto:
        try: st.image(url_foto, use_container_width=True)
        except: st.warning("Link foto rotto")
    else: st.info("Nessuna foto obiettivo")

# ==========================================
# 🖥️ APP LOGIC
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🍎 Cibo", "🏋️ Workout", "📏 Misure", "🤖 AI"])

# --- TAB 1: DASHBOARD AVANZATA ---
with tab1:
    df = get_data("diario")
    oggi = get_oggi()
    df_oggi = df[df['data'] == oggi] if not df.empty else pd.DataFrame()
    
    # 1. ANALISI DATI GIORNALIERI
    cal = pro = carb = fat = 0
    pasti_oggi = []
    
    if not df_oggi.empty:
        for idx, r in df_oggi.iterrows():
            if r['tipo'] == 'pasto':
                try:
                    d = json.loads(r['dettaglio_json'])
                    d['idx'] = idx # Salviamo indice per cancellare
                    cal+=d['cal']; pro+=d['pro']; carb+=d['carb']; fat+=d['fat']
                    pasti_oggi.append(d)
                except: pass

    # 2. ANALISI STORICA (PESO & WORKOUT)
    misure_history = []
    workout_history = []
    
    if not df.empty:
        for _, r in df.iterrows():
            try:
                d = json.loads(r['dettaglio_json'])
                if r['tipo'] == 'misure':
                    misure_history.append({"Data": r['data'], "Peso": d['peso'], "Alt": d.get('alt',0)})
                elif r['tipo'] == 'allenamento':
                    workout_history.append({"Data": r['data'], "Durata": d['durata']})
            except: pass
    
    # Crea Dataframes storici
    df_peso = pd.DataFrame(misure_history)
    if not df_peso.empty: df_peso['Data'] = pd.to_datetime(df_peso['Data'])
    
    df_work = pd.DataFrame(workout_history)
    if not df_work.empty: df_work['Data'] = pd.to_datetime(df_work['Data'])

    # -----------------------------------------------------------
    # SEZIONE 1: PROGRESSO CORPOREO (PESO & CHART)
    # -----------------------------------------------------------
    st.subheader("⚖️ Analisi Corporea")
    with st.container(border=True):
        col_p1, col_p2 = st.columns([1, 2])
        
        with col_p1:
            if not df_peso.empty:
                curr_peso = df_peso.iloc[-1]['Peso']
                curr_alt = df_peso.iloc[-1]['Alt']
                
                # Calcolo Delta (rispetto alla penultima misurazione)
                delta_str = "0 kg"
                delta_val = 0
                if len(df_peso) > 1:
                    prev_peso = df_peso.iloc[-2]['Peso']
                    delta_val = curr_peso - prev_peso
                    delta_str = f"{delta_val:+.1f} kg"
                
                # Calcolo BMI
                bmi_label = "--"
                if curr_alt > 0:
                    bmi = curr_peso / ((curr_alt/100)**2)
                    bmi_label = f"{bmi:.1f}"

                st.metric("Peso Attuale", f"{curr_peso} kg", delta_str, delta_color="inverse")
                st.metric("BMI", bmi_label)
                
                # Totale perso dall'inizio
                start_peso = df_peso.iloc[0]['Peso']
                total_loss = curr_peso - start_peso
                st.caption(f"Variazione Totale: {total_loss:+.1f} kg dall'inizio")
            else:
                st.info("Registra il peso in 'Misure' per vedere i dati.")

        with col_p2:
            if not df_peso.empty:
                # Grafico Area Peso
                chart_peso = alt.Chart(df_peso).mark_area(
                    line={'color':'#0051FF'},
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#0051FF', offset=0),
                               alt.GradientStop(color='rgba(255,255,255,0)', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(
                    x=alt.X('Data:T', title=None),
                    y=alt.Y('Peso:Q', scale=alt.Scale(zero=False), title='Kg'),
                    tooltip=['Data', 'Peso']
                ).properties(height=200)
                st.altair_chart(chart_peso, use_container_width=True)

    # -----------------------------------------------------------
    # SEZIONE 2: PROGRESSO WORKOUT (FREQUENZA & COSTANZA)
    # -----------------------------------------------------------
    st.subheader("🔥 Performance Allenamento")
    with st.container(border=True):
        col_w1, col_w2 = st.columns([1, 2])
        
        with col_w1:
            if not df_work.empty:
                # Calcoli ultima settimana
                oggi_dt = pd.to_datetime(datetime.datetime.now().date())
                sette_giorni_fa = oggi_dt - pd.Timedelta(days=7)
                
                mask = (df_work['Data'] >= sette_giorni_fa) & (df_work['Data'] <= oggi_dt)
                work_week = df_work.loc[mask]
                
                count_week = len(work_week)
                min_week = work_week['Durata'].sum()
                
                st.metric("Allenamenti (7gg)", f"{count_week}", help="Numero di sessioni negli ultimi 7 giorni")
                st.metric("Minuti Totali (7gg)", f"{min_week} min")
            else:
                st.write("Nessun dato allenamento.")

        with col_w2:
            if not df_work.empty:
                # Grafico a barre allenamenti (Ultimi 14 giorni)
                quattordici_giorni = oggi_dt - pd.Timedelta(days=14)
                df_chart_w = df_work[df_work['Data'] >= quattordici_giorni]
                
                bar_chart = alt.Chart(df_chart_w).mark_bar(color="#0051FF", cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                    x=alt.X('Data:T', title=None),
                    y=alt.Y('Durata:Q', title='Minuti'),
                    tooltip=['Data', 'Durata']
                ).properties(height=200)
                st.altair_chart(bar_chart, use_container_width=True)

    # -----------------------------------------------------------
    # SEZIONE 3: NUTRIZIONE DI OGGI
    # -----------------------------------------------------------
    st.subheader(f"🍎 Nutrizione di Oggi ({oggi})")
    
    col_n1, col_n2 = st.columns([1, 2])
    
    with col_n1:
        with st.container(border=True):
            # Donut Chart Macro
            if cal > 0:
                source = pd.DataFrame({
                    "Macro": ["Proteine", "Carboidrati", "Grassi"],
                    "Valore": [pro*4, carb*4, fat*9]
                })
                base = alt.Chart(source).encode(theta=alt.Theta("Valore", stack=True))
                pie = base.mark_arc(outerRadius=70, innerRadius=45).encode(
                    color=alt.Color("Macro", scale=alt.Scale(range=['#FF4B4B', '#FFAA00', '#0051FF'])),
                    tooltip=["Macro", "Valore"]
                )
                st.altair_chart(pie, use_container_width=True)
                
                st.metric("Kcal Assunte", int(cal))
            else:
                st.info("Registra i pasti.")

    with col_n2:
        with st.container(border=True):
            st.write("**Diario Pasti**")
            if pasti_oggi:
                for p in pasti_oggi:
                    cols = st.columns([0.5, 3, 1.5, 0.5])
                    ico = "💊" if p.get('pasto')=="Integrazione" else "🍽️"
                    
                    qty_label = f"{int(p.get('gr',0))} {p.get('unita','g')}"
                    
                    cols[0].write(ico)
                    cols[1].markdown(f"**{p['nome']}**")
                    cols[2].caption(f"{qty_label} | {int(p['cal'])} kcal")
                    if cols[3].button("🗑️", key=f"d_del_{p['idx']}"):
                        delete_riga(p['idx']); st.rerun()
            else:
                st.caption("Ancora nulla.")

# --- TAB 2: CIBO ---
with tab2:
    ci, cdb = st.columns([1.5, 1])
    df_cibi = get_data("cibi")
    nomi = df_cibi['nome'].tolist() if not df_cibi.empty else []

    with ci:
        with st.container(border=True):
            st.subheader("Nuovo Inserimento")
            cat = st.selectbox("Categoria", ["Colazione","Pranzo","Cena","Spuntino","Integrazione"], key="cat_select")
            
            if cat == "Integrazione":
                tip = st.radio("Tipo", ["Polvere (g)", "Capsule (pz)", "Mg"], horizontal=True, key="int_type_radio")
                unita = "g" if "Polvere" in tip else ("cps" if "Capsule" in tip else "mg")
                
                c1,c2 = st.columns([2,1])
                # KEY AGGIUNTA QUI PER EVITARE DUPLICATI
                nome = c1.text_input("Nome Integratore", key="nome_int_input")
                q = c2.number_input(f"Dose ({unita})", 0.0, step=1.0, key="dose_int_input")
                
                with st.expander("Macro (Opzionale)"):
                    # KEYS AGGIUNTE
                    k=st.number_input("K",0.0, key="k_int"); pr=st.number_input("P",0.0, key="p_int"); c=st.number_input("C",0.0, key="c_int"); f=st.number_input("F",0.0, key="f_int")
                
                if st.button("Aggiungi Integratore", type="primary", use_container_width=True, key="btn_add_int"):
                    if nome:
                        add_riga_diario("pasto", {"pasto":cat,"nome":nome,"gr":q,"unita":unita,"cal":k,"pro":pr,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()
            else:
                sel = st.selectbox("Cerca", ["-- Manuale --"] + nomi, key="food_search_box")
                gr = st.number_input("Grammi", 100.0, step=10.0, key="food_grams_input")
                
                vn,vk,vp,vc,vf = "",0,0,0,0
                if sel != "-- Manuale --" and not df_cibi.empty:
                    r = df_cibi[df_cibi['nome']==sel].iloc[0]
                    fac = gr/100
                    vn=r['nome']; vk=r['kcal']*fac; vp=r['pro']*fac; vc=r['carb']*fac; vf=r['fat']*fac
                
                # KEY AGGIUNTA
                nome = st.text_input("Nome", vn, key="nome_pasto_input")
                cc1,cc2,cc3,cc4 = st.columns(4)
                # KEYS AGGIUNTE
                k=cc1.number_input("Kcal", float(vk), key="k_food"); p=cc2.number_input("Pro", float(vp), key="p_food"); c=cc3.number_input("Carb", float(vc), key="c_food"); f=cc4.number_input("Fat", float(vf), key="f_food")
                
                if st.button("Aggiungi Pasto", type="primary", use_container_width=True, key="btn_add_food"):
                    if nome:
                        add_riga_diario("pasto", {"pasto":cat,"nome":nome,"gr":gr,"unita":"g","cal":k,"pro":p,"carb":c,"fat":f})
                        st.success("Fatto!"); st.rerun()

    with cdb:
        st.subheader("💾 DB Cibi")
        with st.form("new_db"):
            # KEY IMPLICITA NEL FORM O KEY ESPLICITA SE NECESSARIO
            n=st.text_input("Nome", key="db_food_name"); k=st.number_input("Kcal (100g)", key="db_k"); p=st.number_input("Pro", key="db_p"); c=st.number_input("Carb", key="db_c"); f=st.number_input("Fat", key="db_f")
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
        with st.container(border=True):
            sess = st.text_input("Nome Sessione", "Workout", key="sess_name_input")
            mod = st.radio("Modo", ["Pesi", "Cardio"], horizontal=True, key="work_mode_radio")
            
            if mod == "Pesi":
                sel = st.selectbox("Ex", ["-- Nuovo --"] + ls_ex, key="ex_select")
                # KEY AGGIUNTA
                nom = sel if sel != "-- Nuovo --" else st.text_input("Nome Ex", key="new_ex_name_input")
                # KEYS AGGIUNTE
                s=st.number_input("Set",1, key="set_in"); r=st.number_input("Reps",1, key="reps_in"); w=st.number_input("Kg",0.0, key="kg_in")
                if st.button("➕", key="btn_add_weight"): st.session_state['sess_w'].append({"type":"pesi","nome":nom,"serie":s,"reps":r,"kg":w})
                
                with st.expander("Salva Ex in DB"):
                    # KEY AGGIUNTA (Questa era quella che causava l'errore probabilmente)
                    ndb = st.text_input("Nome Esercizio DB", key="db_new_ex_name"); 
                    if st.button("Salva DB", key="btn_save_ex_db"): save_data("esercizi", pd.concat([df_ex, pd.DataFrame([{"nome":ndb}])], ignore_index=True)); st.rerun()
            else:
                # KEYS AGGIUNTE
                act = st.text_input("Attività","Corsa", key="cardio_act"); km=st.number_input("Km", key="cardio_km"); mi=st.number_input("Min", key="cardio_min"); kc=st.number_input("Kcal", key="cardio_kcal")
                if st.button("➕", key="btn_add_cardio"): st.session_state['sess_w'].append({"type":"cardio","nome":act,"km":km,"tempo":mi,"kcal":kc})
    
    with c2:
        st.subheader("In Corso")
        for i,e in enumerate(st.session_state['sess_w']):
            with st.container(border=True):
                cl1, cl2 = st.columns([5,1])
                txt = f"**{e['nome']}** " + (f"{e['serie']}x{e['reps']} ({e['kg']}kg)" if e['type']=="pesi" else f"{e['km']}km {e['tempo']}min")
                cl1.write(txt)
                if cl2.button("❌", key=f"wd_{i}"): st.session_state['sess_w'].pop(i); st.rerun()
        
        dur = st.number_input("Minuti Totali", 0, step=5, key="total_duration_input")
        if st.button("💾 TERMINA", type="primary", use_container_width=True, key="btn_finish_workout"):
            add_riga_diario("allenamento", {"nome_sessione":sess,"durata":dur,"esercizi":st.session_state['sess_w']})
            st.session_state['sess_w'] = []; st.success("Salvato!"); st.rerun()

# --- TAB 4: MISURE ---
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("Aggiorna Misure")
            # KEYS AGGIUNTE
            p=st.number_input("Peso (kg)",0.0,format="%.1f", key="weight_input"); a=st.number_input("Altezza (cm)",0, key="height_input")
            c,v,f = st.columns(3)
            # KEYS AGGIUNTE
            co=c.number_input("Collo", key="neck_in"); vi=v.number_input("Vita", key="waist_in"); fi=f.number_input("Fianchi", key="hips_in")
            if st.button("Salva Misure", type="primary", key="btn_save_measures"):
                add_riga_diario("misure", {"peso":p,"alt":a,"collo":co,"vita":vi,"fianchi":fi})
                st.success("Fatto!"); st.rerun()
    with c2:
        with st.container(border=True):
            st.subheader("Foto Obiettivo")
            u = st.text_input("Link Foto (.jpg/.png)", key="photo_url_input")
            if st.button("Salva Foto", key="btn_save_photo"): add_riga_diario("settings", {"url_foto":u}); st.rerun()

# --- TAB 5: AI ---
with tab5:
    st.header("Coach")
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["txt"])
    if q := st.chat_input("..."):
        st.session_state.chat.append({"role":"user","txt":q})
        with st.chat_message("user"): st.markdown(q)
        ans = "No API"
        if gemini_ok:
            try: ans = model.generate_content(f"Sei un PT. Rispondi a: {q}").text
            except Exception as e: ans = str(e)
        st.session_state.chat.append({"role":"assistant","txt":ans})
        with st.chat_message("assistant"): st.markdown(ans)

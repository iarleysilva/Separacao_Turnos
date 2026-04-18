import streamlit as st
import pandas as pd
import plotly.express as px

# --- SISTEMA DE SENHA ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 Acesso Restrito")
        st.text_input("Insira a senha de acesso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Senha incorreta. Tente novamente", type="password", on_change=password_entered, key="password")
        return False
    return True

def password_entered():
    if st.session_state["password"] == "Produtividade_TURNOS":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if not check_password():
    st.stop()

st.set_page_config(page_title="Gestão Operacional 2026", layout="wide")

# FUNÇÃO DE CARGA UNITÁRIA
def carregar_dados_aba(url, nome_aba):
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome_aba}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def carregar_todo_o_sistema():
    links = {
        "TURNO 1": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=0&single=true&output=csv",
        "TURNO 2": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=1250180014&single=true&output=csv",
        "TURNO 3": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=1415290687&single=true&output=csv",
        "LASTRAS": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=1675809741&single=true&output=csv"
    }
    
    dfs_lista = []
    for t in ["TURNO 1", "TURNO 2", "TURNO 3"]:
        df_t = carregar_dados_aba(links[t], t)
        if not df_t.empty:
            c_data = next((c for c in df_t.columns if "DATA" in c), df_t.columns[0])
            df_t['DATA_LIMPA'] = pd.to_datetime(df_t[c_data], dayfirst=True, errors='coerce')
            df_t['NOME_TURNO_REF'] = t
            
            c_per = next((c for c in df_t.columns if "PERCURSO" in c), None)
            if c_per:
                df_t['PERCURSO_TXT'] = df_t[c_per].astype(str).str.split('.').str[0].str.strip()
            
            df_t['TURNO_NUM'] = t.split(" ")[-1].strip()
            
            c_mi = next((c for c in df_t.columns if "MI" in c and "TOTAL" in c), None)
            c_me = next((c for c in df_t.columns if "ME" in c and "TOTAL" in c), None)
            df_t['MI_VAL'] = pd.to_numeric(df_t[c_mi], errors='coerce').fillna(0) if c_mi else 0
            df_t['ME_VAL'] = pd.to_numeric(df_t[c_me], errors='coerce').fillna(0) if c_me else 0
            
            c_gat = next((c for c in df_t.columns if "LASTRA" in c and "ACESSOS" in c), None)
            df_t['GATILHO'] = pd.to_numeric(df_t[c_gat], errors='coerce').fillna(0) if c_gat else 0
            
            dfs_lista.append(df_t.dropna(subset=['DATA_LIMPA']))
    
    df_full = pd.concat(dfs_lista, ignore_index=True) if dfs_lista else pd.DataFrame()
    
    df_l = pd.DataFrame()
    try:
        df_l = pd.read_csv(links["LASTRAS"], skiprows=range(1, 22413))
        df_l.columns = [str(c).strip().upper() for c in df_l.columns]
        
        c_per_l = 'PERCURSO / ITEM' if 'PERCURSO / ITEM' in df_l.columns else df_l.columns[3]
        df_l['PERCURSO_CHAVE'] = df_l[c_per_l].astype(str).str.split('.').str[0].str.strip()
        
        if 'TURNO' in df_l.columns:
            df_l['TURNO_CHAVE'] = df_l['TURNO'].astype(str).str.split('.').str[0].str.strip()
        
        df_l = df_l.drop_duplicates(subset=['PERCURSO_CHAVE', 'PC', 'TURNO_CHAVE'], keep='last')
        
        for f in ['120X270', '160 X 160', 'PC']:
            if f in df_l.columns:
                df_l[f] = pd.to_numeric(df_l[f], errors='coerce').fillna(0)
                
    except Exception as e:
        st.error(f"Erro na aba LASTRAS: {e}")
        
    return df_full, df_l

df_geral, df_tec = carregar_todo_o_sistema()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    if not df_geral.empty:
        df_geral['MES_ANO'] = df_geral['DATA_LIMPA'].dt.strftime('%m/%Y')
        mes_sel = st.selectbox("Mês de Análise", sorted(df_geral['MES_ANO'].unique(), reverse=True))
        turnos_ok = sorted(df_geral['NOME_TURNO_REF'].unique())
        turnos_sel = st.multiselect("Filtro de Turnos", turnos_ok, default=turnos_ok)
        df_f = df_geral[(df_geral['MES_ANO'] == mes_sel) & (df_geral['NOME_TURNO_REF'].isin(turnos_sel))]
    else:
        st.stop()

tab1, tab2 = st.tabs(["🚀 Produção Geral", "📦 Detalhamento Lastras"])

with tab1:
    st.subheader(f"Resumo Operacional - {mes_sel}")
    mi, me = df_f['MI_VAL'].sum(), df_f['ME_VAL'].sum()
    dias_totais = df_f['DATA_LIMPA'].dt.date.nunique()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total MI", f"{int(mi):,}".replace(',', '.'))
    c2.metric("Total ME", f"{int(me):,}".replace(',', '.'))
    c3.metric("Geral (MI+ME)", f"{int(mi+me):,}".replace(',', '.'))
    if dias_totais > 0:
        c4, c5, c6 = st.columns(3)
        c4.metric("Dias com Registro", dias_totais)
        c5.metric("Média MI/Dia", f"{(mi/dias_totais):.1f}".replace('.', ','))
        c6.metric("Média ME/Dia", f"{(me/dias_totais):.1f}".replace('.', ','))
    st.divider()
    evol = df_f.groupby(df_f['DATA_LIMPA'].dt.date)[['MI_VAL', 'ME_VAL']].sum().reset_index()
    fig = px.line(evol, x='DATA_LIMPA', y=['MI_VAL', 'ME_VAL'], markers=True, text='value', title="Acessos Totais por Dia")
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    df_gat = df_f[df_f['GATILHO'] > 0].copy()
    if df_gat.empty:
        st.info("Nenhuma operação de Lastra detectada.")
    else:
        # CRUZAMENTO COM LÓGICA DE RESGATE
        df_res = pd.merge(df_gat, df_tec, left_on=['PERCURSO_TXT', 'TURNO_NUM'], right_on=['PERCURSO_CHAVE', 'TURNO_CHAVE'], how='inner')
        if df_res.empty:
            df_res = pd.merge(df_gat, df_tec.drop_duplicates('PERCURSO_CHAVE', keep='last'), left_on='PERCURSO_TXT', right_on='PERCURSO_CHAVE', how='inner')
        
        if not df_res.empty:
            # --- NOVA MÉTRICA DE DIAS TRABALHADOS EM LASTRAS ---
            d_l = df_res['DATA_LIMPA'].dt.date.nunique()
            
            st.markdown(f"### 📦 Performance Técnica: Lastras ({mes_sel})")
            
            # Card de destaque para os dias trabalhados
            st.info(f"📅 **Atenção:** Foram identificados {d_l} dias com operação efetiva de Lastras neste período.")

            df_caix = df_res[df_res['TIPO DE OPERAÇÃO'].fillna('').str.upper().str.contains('CAIXOTE')]
            df_unit = df_res[df_res['TIPO DE OPERAÇÃO'].fillna('').str.upper().str.contains('UNITIZAR')]
            
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Unitizar 120x270", f"{int(df_unit['120X270'].sum()):,}".replace(',', '.'))
            k2.metric("Unitizar 160x160", f"{int(df_unit['160 X 160'].sum()):,}".replace(',', '.'))
            k3.metric("Caixote 120x270", f"{int(df_caix['120X270'].sum()):,}".replace(',', '.'))
            k4.metric("Caixote 160x160", f"{int(df_caix['160 X 160'].sum()):,}".replace(',', '.'))
            k5.metric("Total Acessos", f"{int(df_res['GATILHO'].sum()):,}".replace(',', '.'))

            st.write("**Médias Reais (Peças / Dias de Operação Lastra)**")
            m1, m2, m3, m4, m5 = st.columns(5)
            if d_l > 0:
                m1.metric("Média Unit. 120x270", f"{(df_unit['120X270'].sum()/d_l):.1f}".replace('.', ','))
                m2.metric("Média Unit. 160x160", f"{(df_unit['160 X 160'].sum()/d_l):.1f}".replace('.', ','))
                m3.metric("Média Caix. 120x270", f"{(df_caix['120X270'].sum()/d_l):.1f}".replace('.', ','))
                m4.metric("Média Caix. 160x160", f"{(df_caix['160 X 160'].sum()/d_l):.1f}".replace('.', ','))
                m5.metric("Dias Trabalhados", d_l) # Métrica adicional visual

            st.divider()
            df_ev_l = df_res.groupby([df_res['DATA_LIMPA'].dt.date, 'TIPO DE OPERAÇÃO'])[['120X270', '160 X 160']].sum().reset_index().melt(id_vars=['DATA_LIMPA', 'TIPO DE OPERAÇÃO'])
            df_ev_l['LEGENDA'] = df_ev_l['TIPO DE OPERAÇÃO'] + " - " + df_ev_l['variable']
            color_map = {"UNITIZAR - 120X270": "#0047AB", "UNITIZAR - 160 X 160": "#4169E1", "CAIXOTE - 120X270": "#FF8C00", "CAIXOTE - 160 X 160": "#FFA500"}
            fig_l = px.line(df_ev_l, x='DATA_LIMPA', y='value', color='LEGENDA', markers=True, text='value', color_discrete_map=color_map)
            fig_l.update_traces(textposition="top center")
            st.plotly_chart(fig_l, use_container_width=True)
            
            st.subheader("📋 Resumo Consolidado do Período")
            tabela_final = df_res.groupby('TIPO DE OPERAÇÃO').agg({'120X270': 'sum', '160 X 160': 'sum', 'PC': 'sum', 'GATILHO': 'sum'}).reset_index()
            tabela_final.rename(columns={'GATILHO': 'TOTAL ACESSOS'}, inplace=True)
            st.table(tabela_final.style.format({'120X270': '{:,.0f}', '160 X 160': '{:,.0f}', 'PC': '{:,.0f}', 'TOTAL ACESSOS': '{:,.0f}'}))
        else:
            st.warning("⚠️ Percursos não encontrados na aba LASTRAS técnica.")
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
        mes_sel = st.selectbox("1. Escolha o Mês", sorted(df_geral['MES_ANO'].unique(), reverse=True))
        
        # Filtro de Dia Específico
        dias_mes = sorted(df_geral[df_geral['MES_ANO'] == mes_sel]['DATA_LIMPA'].dt.strftime('%d/%m/%Y').unique())
        dia_sel = st.selectbox("2. Refinar por Dia (Opcional)", ["Todos"] + dias_mes)
        
        turnos_ok = sorted(df_geral['NOME_TURNO_REF'].unique())
        turnos_sel = st.multiselect("3. Filtro de Turnos", turnos_ok, default=turnos_ok)
        
        # Aplicação dos filtros
        df_f = df_geral[(df_geral['MES_ANO'] == mes_sel) & (df_geral['NOME_TURNO_REF'].isin(turnos_sel))]
        if dia_sel != "Todos":
            df_f = df_f[df_f['DATA_LIMPA'].dt.strftime('%d/%m/%Y') == dia_sel]
    else:
        st.stop()

tab1, tab2 = st.tabs(["🚀 Produção Geral", "📦 Detalhamento Lastras"])

with tab1:
    st.subheader(f"Resumo Operacional - {dia_sel if dia_sel != 'Todos' else mes_sel}")
    mi, me = df_f['MI_VAL'].sum(), df_f['ME_VAL'].sum()
    prod_dia = df_f.groupby(df_f['DATA_LIMPA'].dt.date)[['MI_VAL', 'ME_VAL']].sum()
    dias_count = len(prod_dia)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total (MI+ME)", f"{int(mi+me):,}".replace(',', '.'))
    c2.metric("Dias no Filtro", dias_count)
    c3.metric("Total Acessos", f"{int(df_f['GATILHO'].sum()):,}".replace(',', '.'))
    
    st.write("**📊 Médias e Medianas diárias**")
    col_a, col_b, col_c, col_d = st.columns(4)
    if dias_count > 0:
        col_a.metric("Média MI", f"{(mi/dias_count):.1f}".replace('.', ','))
        col_b.metric("Mediana MI", f"{prod_dia['MI_VAL'].median():.1f}".replace('.', ','))
        col_c.metric("Média ME", f"{(me/dias_count):.1f}".replace('.', ','))
        col_d.metric("Mediana ME", f"{prod_dia['ME_VAL'].median():.1f}".replace('.', ','))

    st.divider()
    evol = df_f.groupby(df_f['DATA_LIMPA'].dt.date)[['MI_VAL', 'ME_VAL']].sum().reset_index()
    fig = px.line(evol, x='DATA_LIMPA', y=['MI_VAL', 'ME_VAL'], markers=True, text='value', title="Evolução Diária")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    df_gat = df_f[df_f['GATILHO'] > 0].copy()
    if df_gat.empty:
        st.info("Nenhuma operação de Lastra detectada para o filtro selecionado.")
    else:
        df_res = pd.merge(df_gat, df_tec, left_on=['PERCURSO_TXT', 'TURNO_NUM'], right_on=['PERCURSO_CHAVE', 'TURNO_CHAVE'], how='inner')
        if df_res.empty:
            df_res = pd.merge(df_gat, df_tec.drop_duplicates('PERCURSO_CHAVE', keep='last'), left_on='PERCURSO_TXT', right_on='PERCURSO_CHAVE', how='inner')
        
        if not df_res.empty:
            d_l = df_res['DATA_LIMPA'].dt.date.nunique()
            st.markdown(f"### 📦 Performance Técnica: Lastras ({dia_sel if dia_sel != 'Todos' else mes_sel})")
            
            # Separação por Tipo de Operação
            df_unit = df_res[df_res['TIPO DE OPERAÇÃO'].fillna('').str.upper().str.contains('UNITIZAR')]
            df_caix = df_res[df_res['TIPO DE OPERAÇÃO'].fillna('').str.upper().str.contains('CAIXOTE')]
            
            # Bloco Unitização
            st.info("🔄 **OPERACAO: UNITIZAR**")
            u1, u2, u3, u4 = st.columns(4)
            u1.metric("Total 120x270", int(df_unit['120X270'].sum()))
            u2.metric("Média/Dia", f"{(df_unit['120X270'].sum()/d_l):.1f}".replace('.', ','))
            u3.metric("Total 160x160", int(df_unit['160 X 160'].sum()))
            u4.metric("Média/Dia", f"{(df_unit['160 X 160'].sum()/d_l):.1f}".replace('.', ','))
            
            # Bloco Caixote
            st.warning("📦 **OPERAÇÃO: CAIXOTE**")
            x1, x2, x3, x4 = st.columns(4)
            x1.metric("Total 120x270", int(df_caix['120X270'].sum()))
            x2.metric("Média/Dia", f"{(df_caix['120X270'].sum()/d_l):.1f}".replace('.', ','))
            x3.metric("Total 160x160", int(df_caix['160 X 160'].sum()))
            x4.metric("Média/Dia", f"{(df_caix['160 X 160'].sum()/d_l):.1f}".replace('.', ','))

            st.divider()
            st.write("**📈 Comparativo Geral de Dificuldade (Medianas do Período)**")
            med_dia = df_res.groupby(df_res['DATA_LIMPA'].dt.date)[['120X270', '160 X 160']].sum()
            m1, m2 = st.columns(2)
            m1.metric("Mediana Geral 120x270", f"{med_dia['120X270'].median():.1f}".replace('.', ','))
            m2.metric("Mediana Geral 160x160", f"{med_dia['160 X 160'].median():.1f}".replace('.', ','))
            
            st.subheader("📋 Resumo Consolidado")
            tabela_final = df_res.groupby('TIPO DE OPERAÇÃO').agg({'120X270': 'sum', '160 X 160': 'sum', 'GATILHO': 'sum'}).reset_index()
            st.table(tabela_final)
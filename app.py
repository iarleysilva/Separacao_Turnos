import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestão Operacional 2026", layout="wide")

# --- SISTEMA DE SENHA ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 Acesso Restrito")
        st.text_input("Insira a senha", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

def password_entered():
    if st.session_state["password"] == "Produtividade_TURNOS":
        st.session_state["password_correct"] = True
    else:
        st.session_state["password_correct"] = False

if not check_password(): st.stop()

# --- CARGA DE DADOS COM NITRO (CACHE) ---
@st.cache_data(ttl=300) 
def carregar_dados():
    links = {
        "TURNO 1": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=0&single=true&output=csv",
        "TURNO 2": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=1250180014&single=true&output=csv",
        "TURNO 3": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=1415290687&single=true&output=csv",
        "LASTRAS": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTS8d44ajH4_Hm7uaAWVbejIzmbMqK8fCbYEPYWddDc4pnbFBhyOye4vs6QmtJ-a51V-b9HDTFPDcSw/pub?gid=1675809741&single=true&output=csv"
    }
    
    lista_turnos = []
    for t_nome in ["TURNO 1", "TURNO 2", "TURNO 3"]:
        try:
            df = pd.read_csv(links[t_nome])
            df.columns = [str(c).strip().upper() for c in df.columns]
            data_col = next(c for c in df.columns if "DATA" in c)
            df['DATA_REF'] = pd.to_datetime(df[data_col], dayfirst=True, errors='coerce')
            df['TURNO_ID'] = t_nome.split()[-1]
            per_col = next(c for c in df.columns if "PERCURSO" in c)
            df['PERCURSO_LIMP'] = df[per_col].astype(str).str.split('.').str[0].str.strip()
            
            c_mi = next((c for c in df.columns if "MI" in c and "TOTAL" in c), None)
            c_me = next((c for c in df.columns if "ME" in c and "TOTAL" in c), None)
            c_gat = next((c for c in df.columns if "LASTRA" in c and "ACESSOS" in c), None)
            
            df['MI_VAL'] = pd.to_numeric(df[c_mi], errors='coerce').fillna(0) if c_mi else 0
            df['ME_VAL'] = pd.to_numeric(df[c_me], errors='coerce').fillna(0) if c_me else 0
            df['GATILHO'] = pd.to_numeric(df[c_gat], errors='coerce').fillna(0) if c_gat else 0
            
            lista_turnos.append(df[['DATA_REF', 'TURNO_ID', 'PERCURSO_LIMP', 'MI_VAL', 'ME_VAL', 'GATILHO']].dropna(subset=['DATA_REF']))
        except: continue
        
    df_realizado = pd.concat(lista_turnos, ignore_index=True)
    df_realizado = df_realizado.sort_values('DATA_REF')
    df_realizado_limpo = df_realizado.drop_duplicates(subset=['PERCURSO_LIMP', 'TURNO_ID'], keep='last')

    df_tec = pd.read_csv(links["LASTRAS"], skiprows=range(1, 22413))
    df_tec.columns = [str(c).strip().upper() for c in df_tec.columns]
    df_tec['DATA_SEQ'] = pd.to_datetime(df_tec['DATA SEQUENCIAMENTO'], dayfirst=True, errors='coerce')
    df_tec['PERCURSO_CHAVE'] = df_tec['PERCURSO / ITEM'].astype(str).str.split('.').str[0].str.strip()
    
    # --- CORREÇÃO DO ERRO .str.split ---
    if 'TURNO' in df_tec.columns:
        df_tec['TURNO_CHAVE'] = df_tec['TURNO'].astype(str).str.split('.').str[0].str.strip()
    else:
        df_tec['TURNO_CHAVE'] = df_tec.iloc[:, 2].astype(str).str.split('.').str[0].str.strip()
    
    for col in ['120X270', '160 X 160', 'PC']:
        if col in df_tec.columns: df_tec[col] = pd.to_numeric(df_tec[col], errors='coerce').fillna(0)
        
    return df_realizado_limpo, df_tec

df_realizado, df_tec = carregar_dados()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("# 📊 BI Gestão")
    df_realizado['MES_ANO'] = df_realizado['DATA_REF'].dt.strftime('%m/%Y')
    meses_disp = sorted(df_realizado['MES_ANO'].unique(), reverse=True)
    mes_sel = st.selectbox("Selecione o Mês", meses_disp)
    dias = sorted(df_realizado[df_realizado['MES_ANO'] == mes_sel]['DATA_REF'].dt.strftime('%d/%m/%Y').unique())
    dia_sel = st.selectbox("Selecione o Dia", ["Todos"] + dias)
    turnos_sel = st.multiselect("Turnos", ["TURNO 1", "TURNO 2", "TURNO 3"], default=["TURNO 1"])

df_f = df_realizado[(df_realizado['MES_ANO'] == mes_sel) & (df_realizado['TURNO_ID'].isin([t.split()[-1] for t in turnos_sel]))]
if dia_sel != "Todos":
    df_f = df_f[df_f['DATA_REF'].dt.strftime('%d/%m/%Y') == dia_sel]

t1, t2, t3 = st.tabs(["🚀 PRODUÇÃO GERAL", "📦 DETALHAMENTO LASTRAS", "🎯 ADERÊNCIA AO PLANO"])

# --- ABA 1 ---
with t1:
    st.markdown(f"## 🚀 Resumo Operacional - {dia_sel if dia_sel != 'Todos' else mes_sel}")
    d_trab = df_f['DATA_REF'].dt.date.nunique()
    mi_t, me_t = df_f['MI_VAL'].sum(), df_f['ME_VAL'].sum()
    res_dia = df_f.groupby(df_f['DATA_REF'].dt.date)[['MI_VAL', 'ME_VAL']].sum().reset_index()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🗓️ Dias Trab.", d_trab)
    c2.metric("MI (Média)", f"{mi_t/d_trab:.1f}" if d_trab > 0 else 0)
    c3.metric("MI (Mediana)", f"{res_dia['MI_VAL'].median():.1f}" if d_trab > 0 else 0)
    c4.metric("ME (Média)", f"{me_t/d_trab:.1f}" if d_trab > 0 else 0)
    c5.metric("ME (Mediana)", f"{res_dia['ME_VAL'].median():.1f}" if d_trab > 0 else 0)
    st.divider()
    fig = px.line(res_dia, x='DATA_REF', y=['MI_VAL', 'ME_VAL'], markers=True, text='value', title="Evolução Diária de Acessos")
    fig.update_traces(textposition="top center", line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)

# --- ABA 2 ---
with t2:
    st.markdown("## 📦 Performance Técnica Realizada")
    df_det = pd.merge(df_f[df_f['GATILHO'] > 0], df_tec, left_on=['PERCURSO_LIMP', 'TURNO_ID'], right_on=['PERCURSO_CHAVE', 'TURNO_CHAVE'], how='inner')
    if df_det.empty:
        st.info("Nenhuma operação técnica registrada no período.")
    else:
        d_lastras = df_det['DATA_REF'].dt.date.nunique()
        l_stats = df_det.groupby([df_det['DATA_REF'].dt.date, 'TIPO DE OPERAÇÃO'])[['120X270', '160 X 160']].sum().reset_index()
        col1, col2, col3, col4 = st.columns(4)
        def render_kpi(cont, label, op, size):
            sub = df_det[df_det['TIPO DE OPERAÇÃO'].str.contains(op, na=False)]
            total = sub[size].sum()
            med = l_stats[l_stats['TIPO DE OPERAÇÃO'].str.contains(op, na=False)][size].median() if not sub.empty else 0
            with cont:
                st.markdown(f"#### {label}")
                st.metric("Total", f"{int(total)} pçs")
                st.caption(f"Média: {total/d_lastras:.1f} | Mediana: {med:.1f}")
        render_kpi(col1, "UNITIZAR 120", "UNITIZAR", "120X270")
        render_kpi(col2, "UNITIZAR 160", "UNITIZAR", "160 X 160")
        render_kpi(col3, "CAIXOTE 120", "CAIXOTE", "120X270")
        render_kpi(col4, "CAIXOTE 160", "CAIXOTE", "160 X 160")
        st.divider()
        st.dataframe(df_det[['DATA_REF', 'TURNO_ID', 'PERCURSO_LIMP', 'TIPO DE OPERAÇÃO', 'PC', '120X270', '160 X 160']], use_container_width=True)

# --- ABA 3 ---
with t3:
    st.markdown("## 🎯 Aderência por Tipo de Operação")
    ids_t = [t.split()[-1] for t in turnos_sel]
    df_plan = df_tec[df_tec['TURNO_CHAVE'].isin(ids_t)]
    if dia_sel != "Todos":
        df_plan = df_plan[df_plan['DATA_SEQ'].dt.strftime('%d/%m/%Y') == dia_sel]
    else:
        df_plan = df_plan[df_plan['DATA_SEQ'].dt.strftime('%m/%Y') == mes_sel]
    df_match = pd.merge(df_plan, df_f, left_on=['PERCURSO_CHAVE', 'DATA_SEQ', 'TURNO_CHAVE'], right_on=['PERCURSO_LIMP', 'DATA_REF', 'TURNO_ID'], how='left', indicator=True)
    def render_farol(tipo):
        sub_p = df_plan[df_plan['TIPO DE OPERAÇÃO'].str.contains(tipo, na=False)]
        sub_m = df_match[df_match['TIPO DE OPERAÇÃO'].str.contains(tipo, na=False)]
        p_pc, r_pc = sub_p['PC'].sum(), sub_m[sub_m['_merge'] == 'both']['PC'].sum()
        ade = (r_pc / p_pc * 100) if p_pc > 0 else 0
        st.markdown(f"### {tipo}")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Planejado", f"{int(p_pc)} PC")
        a2.metric("Atendido", f"{int(r_pc)} PC")
        a3.metric("Pendente", int(p_pc - r_pc), delta=int(r_pc - p_pc), delta_color="inverse")
        a4.metric("Aderência %", f"{ade:.1f}%")
    render_farol("UNITIZAR")
    st.write("")
    render_farol("CAIXOTE")
    st.divider()
    st.markdown("#### ⚠️ Pendências Identificadas")
    st.dataframe(df_match[df_match['_merge'] == 'left_only'][['DATA_SEQ', 'PERCURSO_CHAVE', 'PC', 'TIPO DE OPERAÇÃO']], use_container_width=True)
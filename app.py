import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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

# --- CARGA DE DADOS ---
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
            df['PERCURSO_LIMP'] = df[per_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            c_mi = next((c for c in df.columns if "MI" in c and "TOTAL" in c), None)
            c_me = next((c for c in df.columns if "ME" in c and "TOTAL" in c), None)
            c_gat = next((c for c in df.columns if "LASTRA" in c and "ACESSOS" in c), None)
            
            df['MI_VAL'] = pd.to_numeric(df[c_mi], errors='coerce').fillna(0) if c_mi else 0
            df['ME_VAL'] = pd.to_numeric(df[c_me], errors='coerce').fillna(0) if c_me else 0
            df['GATILHO'] = pd.to_numeric(df[c_gat], errors='coerce').fillna(0) if c_gat else 0
            
            lista_turnos.append(df[['DATA_REF', 'TURNO_ID', 'PERCURSO_LIMP', 'GATILHO', 'MI_VAL', 'ME_VAL']])
        except: continue
        
    df_realizado = pd.concat(lista_turnos, ignore_index=True).dropna(subset=['DATA_REF'])

    df_tec = pd.read_csv(links["LASTRAS"], skiprows=range(1, 22413))
    df_tec.columns = [str(c).strip().upper() for c in df_tec.columns]
    df_tec['DATA_SEQ'] = pd.to_datetime(df_tec['DATA SEQUENCIAMENTO'], dayfirst=True, errors='coerce')
    df_tec['PERCURSO_CHAVE'] = df_tec['PERCURSO / ITEM'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_tec['TURNO_CHAVE'] = df_tec['TURNO'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    for col in ['120X270', '160 X 160', 'PC']:
        df_tec[col] = pd.to_numeric(df_tec[col], errors='coerce').fillna(0)
        
    return df_realizado, df_tec

df_realizado, df_tec = carregar_dados()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("# 📊 BI Gestão")
    df_tec['MES_ANO'] = df_tec['DATA_SEQ'].dt.strftime('%m/%Y')
    meses_disp = sorted(df_tec['MES_ANO'].dropna().unique().tolist(), reverse=True)
    mes_sel = st.selectbox("Selecione o Mês", meses_disp)
    dias = sorted(df_tec[df_tec['MES_ANO'] == mes_sel]['DATA_SEQ'].dt.strftime('%d/%m/%Y').dropna().unique())
    dia_sel = st.selectbox("Selecione o Dia", ["Todos"] + dias)
    turnos_sel = st.multiselect("Turnos", ["TURNO 1", "TURNO 2", "TURNO 3"], default=["TURNO 1", "TURNO 2", "TURNO 3"])

ids_t = [t.split()[-1] for t in turnos_sel]

# --- MOTOR DE REGRAS GLOBAL (CORREÇÃO DA PRECISÃO) ---
# CRÍTICO: O espelho do plano para achar repetidos olha TODO o mês, independente do filtro de turnos da tela
df_p_global = df_tec[df_tec['MES_ANO'] == mes_sel].copy()
df_p_global['DATA_SEQ_COMP'] = df_p_global['DATA_SEQ'].dt.date

peso_turnos = {'3': 1, '1': 2, '2': 3}
df_p_global['ORDEM_TURNO'] = df_p_global['TURNO_CHAVE'].map(peso_turnos).fillna(99)

def julgar_aderencia_exclusiva_lastras(row):
    percurso = row['PERCURSO_CHAVE']
    data_p = row['DATA_SEQ_COMP']
    qtd_p = row['PC']
    ordem_p = row['ORDEM_TURNO']
    
    # Encontra o histórico desse percurso na base global das lastras (vê todos os turnos nos bastidores)
    duplicados_plano = df_p_global[df_p_global['PERCURSO_CHAVE'] == percurso].sort_values(by=['DATA_SEQ_COMP', 'ORDEM_TURNO'])
    
    if len(duplicados_plano) == 1:
        return "REALIZADO", qtd_p
    else:
        qtds_iguais = duplicados_plano['PC'].nunique() == 1
        
        if qtds_iguais:
            ultima_linha = duplicados_plano.iloc[-1]
            ultima_data = ultima_linha['DATA_SEQ_COMP']
            ultima_ordem = ultima_linha['ORDEM_TURNO']
            
            # Se a linha atual está antes do último destino real do fluxo, leva penalidade
            if data_p < ultima_data or (data_p == ultima_data and ordem_p < ultima_ordem):
                return "PENALIDADE (REPETIDO)", 0
            else:
                return "REALIZADO", qtd_p
        else:
            return "REALIZADO (PARCIAL)", qtd_p

# Aplica o julgamento na base do mês completo
df_p_global[['STATUS_FINAL', 'VALOR_VALIDO']] = df_p_global.apply(julgar_aderencia_exclusiva_lastras, axis=1, result_type='expand')

# --- FILTRAGEM VISUAL EXECUTIVA ---
# Agora sim aplicamos o filtro de Turnos selecionados na tela para gerar os blocos e tabelas
df_view_total = df_p_global[df_p_global['TURNO_CHAVE'].isin(ids_t)].copy()

if df_view_total.empty:
    st.info("📌 Sem dados planejados para o filtro selecionado.")
    st.stop()

if dia_sel != "Todos":
    df_view = df_view_total[df_view_total['DATA_SEQ'].dt.strftime('%d/%m/%Y') == dia_sel].copy()
else:
    df_view = df_view_total.copy()

t1, t3 = st.tabs(["🚀 PRODUÇÃO GERAL", "🎯 ADERÊNCIA AO PLANO"])

# --- ABA 1: PRODUÇÃO GERAL ---
with t1:
    st.markdown(f"## 🚀 Resumo Operacional - {dia_sel if dia_sel != 'Todos' else mes_sel}")
    
    df_f_real = df_realizado[df_realizado['TURNO_ID'].isin(ids_t)].copy()
    df_f_real['MES_ANO_R'] = df_f_real['DATA_REF'].dt.strftime('%m/%Y')
    
    if dia_sel != "Todos":
        df_f_real = df_f_real[df_f_real['DATA_REF'].dt.strftime('%d/%m/%Y') == dia_sel]
    else:
        df_f_real = df_f_real[df_f_real['MES_ANO_R'] == mes_sel]
    
    d_trab = df_f_real['DATA_REF'].dt.date.nunique()
    mi_total = df_f_real['MI_VAL'].sum()
    me_total = df_f_real['ME_VAL'].sum()
    
    if not df_f_real.empty:
        res_dia = df_f_real.groupby(df_f_real['DATA_REF'].dt.date)[['MI_VAL', 'ME_VAL']].sum().reset_index()
        mediana_mi = res_dia['MI_VAL'].median()
        mediana_me = res_dia['ME_VAL'].median()
    else:
        res_dia = pd.DataFrame()
        mediana_mi = 0
        mediana_me = 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🗓️ Dias Trab.", d_trab if d_trab > 0 else 0)
    c2.metric("Total MI", f"{int(mi_total)}")
    c3.metric("MI (Média)", f"{mi_total/d_trab:.1f}" if d_trab > 0 else 0)
    c4.metric("Total ME", f"{int(me_total)}")
    c5.metric("ME (Média)", f"{me_total/d_trab:.1f}" if d_trab > 0 else 0)
    
    st.write("")
    cx1, cx2, cx3, cx4 = st.columns([1, 2, 2, 1])
    cx2.metric("📊 MI (Mediana)", f"{mediana_mi:.1f}")
    cx3.metric("📊 ME (Mediana)", f"{mediana_me:.1f}")
    
    st.divider()
    if not res_dia.empty:
        res_dia_melt = res_dia.melt(id_vars='DATA_REF', var_name='Tipo', value_name='Acessos')
        
        fig = px.line(res_dia_melt, 
                     x='DATA_REF', 
                     y='Acessos', 
                     color='Tipo',
                     markers=True, 
                     text='Acessos',
                     title="Evolução Diária de Acessos",
                     color_discrete_map={"MI_VAL": "#00CC96", "ME_VAL": "#636EFA"})
        
        fig.update_traces(textposition="top center", texttemplate='%{text:.0f}')
        
        fig.add_trace(go.Scatter(
            x=res_dia['DATA_REF'], y=[mediana_mi]*len(res_dia),
            mode='lines', name='Mediana MI (Clique p/ ver)',
            line=dict(color='#00CC96', dash='dash', width=2),
            visible="legendonly"
        ))
        fig.add_trace(go.Scatter(
            x=res_dia['DATA_REF'], y=[mediana_me]*len(res_dia),
            mode='lines', name='Mediana ME (Clique p/ ver)',
            line=dict(color='#636EFA', dash='dash', width=2),
            visible="legendonly"
        ))
        
        st.plotly_chart(fig, use_container_width=True)

# --- ABA 3: ADERÊNCIA AO PLANO ---
with t3:
    st.markdown(f"## 🎯 Aderência Operacional - {dia_sel}")
    
    st.markdown("#### 📅 Dias Planejados por Turno no Período")
    c_dias = st.columns(len(turnos_sel) if turnos_sel else 1)
    for index, t_nome in enumerate(turnos_sel):
        t_id = t_nome.split()[-1]
        dias_op = df_view_total[df_view_total['TURNO_CHAVE'] == t_id]['DATA_SEQ_COMP'].nunique()
        c_dias[index].metric(f"⏱️ {t_nome}", f"{dias_op} dias")
    st.write("---")
    
    def render_secao(titulo, filtro):
        st.markdown(f"### {titulo}")
        sub = df_view[df_view['TIPO DE OPERAÇÃO'].str.contains(filtro, na=False)]
        if sub.empty: return

        c1, c2 = st.columns(2)
        for i, formato in enumerate(["120X270", "160 X 160"]):
            p_total = sub[formato].sum()
            v_total = sub[sub['STATUS_FINAL'].str.contains("REALIZADO")][formato].sum()
            ade = (v_total / p_total * 100) if p_total > 0 else 0
            
            with [c1, c2][i]:
                st.info(f"**Formato {formato}**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Plano", int(p_total))
                m2.metric("Válido", int(v_total))
                m3.metric("%", f"{ade:.1f}%")
        st.write("---")

    render_secao("UNITIZAÇÃO", "UNITIZAR")
    render_secao("CAIXOTES", "CAIXOTE")

    aba_ok, aba_bad = st.tabs(["✅ ADERIDOS", "⚠️ PENDÊNCIAS / REPETIÇÕES"])
    with aba_ok:
        st.dataframe(df_view[df_view['STATUS_FINAL'].str.contains("REALIZADO")][['DATA_SEQ', 'TURNO_CHAVE', 'PERCURSO_CHAVE', 'TIPO DE OPERAÇÃO', 'PC', 'STATUS_FINAL']], use_container_width=True)
    with aba_bad:
        st.dataframe(df_view[~df_view['STATUS_FINAL'].str.contains("REALIZADO")][['DATA_SEQ', 'TURNO_CHAVE', 'PERCURSO_CHAVE', 'TIPO DE OPERAÇÃO', 'PC', 'STATUS_FINAL']], use_container_width=True)
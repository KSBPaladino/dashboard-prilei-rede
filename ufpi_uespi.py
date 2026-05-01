import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. CONFIGURAÇÃO DA PÁGINA (Sempre no topo)
st.set_page_config(page_title="Analytics PRILEI - UFPI/UESPI/UNICAP", layout="wide")

# 2. FUNÇÃO DE VERIFICAÇÃO DE SENHA
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Digite a senha para acessar o Dashboard", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Senha incorreta. Tente novamente:", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha inválida")
        return False
    else:
        return True

# 3. BLOCO PROTEGIDO
if check_password():
    # --- Início do conteúdo protegido (Indentaçao de 4 espaços) ---

    if os.path.exists("logo_prilei.png"):
        st.image("logo_prilei.png", width=250)

    st.markdown("<style>[data-testid='stMetricValue'] { font-size: 28px; }</style>", unsafe_allow_html=True)

    st.title("Painel Analítico de Conclusão - PRILEI")
    st.markdown("Rede Nordeste: **UFPI** - **UESPI** - **UNICAP**")

    CORES_INST = {'UFPI': '#003366', 'UESPI': '#cc0000', 'UNICAP': '#1a7a1a'}

    @st.cache_data
    def carregar_dados():
        df = pd.read_csv('formados_prilei_ufpi_uespi.csv')
        df.columns = df.columns.str.strip()
        for col in ['Matrículas Iniciais', 'Formados']:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df['Porcentagem de Formados'] = (df['Formados'] / df['Matrículas Iniciais'] * 100).fillna(0)
        df['Não Formados'] = df['Matrículas Iniciais'] - df['Formados']
        return df

    try:
        df = carregar_dados()

        # Barra lateral com Filtros
        st.sidebar.header("🎯 Filtros de Análise")
        inst_disponiveis = sorted(df['Instituição da Rede'].unique())
        inst_selecionada = st.sidebar.multiselect("Instituição:", options=inst_disponiveis, default=inst_disponiveis)
        df_temp = df[df['Instituição da Rede'].isin(inst_selecionada)]

        cursos_disponiveis = sorted(df_temp['Curso'].unique())
        curso_selecionado = st.sidebar.multiselect("Cursos:", options=cursos_disponiveis, default=cursos_disponiveis)

        municipios_disponiveis = sorted(df_temp[df_temp['Curso'].isin(curso_selecionado)]['Município'].unique())
        municipio_selecionado = st.sidebar.multiselect("Municípios/Polos:", options=municipios_disponiveis, default=municipios_disponiveis)

        df_filtrado = df_temp[(df_temp['Curso'].isin(curso_selecionado)) & (df_temp['Município'].isin(municipio_selecionado))].copy()

        if df_filtrado.empty:
            st.warning("⚠️ Selecione os filtros na barra lateral para visualizar os dados.")
        else:
            # 4. Painel de KPIs
            st.subheader("📈 Principais Indicadores")
            m1, m2, m3, m4 = st.columns(4)
            total_mat = df_filtrado['Matrículas Iniciais'].sum()
            total_for = df_filtrado['Formados'].sum()
            taxa_real_geral = (total_for / total_mat * 100) if total_mat > 0 else 0

            m1.metric("Matrículas Totais", int(total_mat))
            m2.metric("Total de Formados", int(total_for))
            m3.metric("Taxa de Conclusão Geral", f"{taxa_real_geral:.1f}%")
            m4.metric("Qtd. Cursos/Polos", len(df_filtrado))

            st.divider()

            # 5. LINHA 1: Barras por Curso e Pizza Global
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("**Taxa de Conclusão por Curso (%)**")
                fig1 = px.bar(df_filtrado, x='Curso', y='Porcentagem de Formados', color='Instituição da Rede',
                            barmode='group', text_auto='.1f', color_discrete_map=CORES_INST)
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                st.markdown("**Proporção Global (Formados vs Não)**")
                fig2 = px.pie(values=[total_for, total_mat - total_for], names=['Formados', 'Não Formados'],
                            hole=0.5, color_discrete_map={'Formados': '#2ca02c', 'Não Formados': '#d62728'})
                st.plotly_chart(fig2, use_container_width=True)

            # 6. LINHA 2: Ranking Municípios e Volume Institucional
            col3, col4 = st.columns(2)
            with col3:
                st.markdown("**Top 10 Municípios (Ranking Consolidado)**")
                df_mun_rank = df_filtrado.groupby(['Município', 'Instituição da Rede']).agg({'Matrículas Iniciais': 'sum', 'Formados': 'sum'}).reset_index()
                df_mun_rank['Taxa Real'] = (df_mun_rank['Formados'] / df_mun_rank['Matrículas Iniciais'] * 100).fillna(0)
                top_mun = df_mun_rank.nlargest(10, 'Taxa Real')
                fig3 = px.bar(top_mun, x='Taxa Real', y='Município', orientation='h', color='Instituição da Rede',
                             text_auto='.1f', color_discrete_map=CORES_INST)
                fig3.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig3, use_container_width=True)
            with col4:
                st.markdown("**Volume Total por Instituição**")
                df_abs = df_filtrado.groupby('Instituição da Rede')[['Formados', 'Não Formados']].sum().reset_index()
                df_abs_melt = df_abs.melt(id_vars='Instituição da Rede', var_name='Status', value_name='Qtd')
                fig4 = px.bar(df_abs_melt, x='Instituição da Rede', y='Qtd', color='Status', barmode='stack',
                             color_discrete_map={'Formados': '#2ca02c', 'Não Formados': '#d62728'})
                st.plotly_chart(fig4, use_container_width=True)

            # 7. NOVO: LINHA 3 - Treemap e Box Plot (Restaurados)
            st.divider()
            col5, col6 = st.columns(2)
            with col5:
                st.markdown("**Mapa de Hierarquia (Área = Matrículas)**")
                fig5 = px.treemap(df_filtrado, path=['Instituição da Rede', 'Curso', 'Município'],
                                 values='Matrículas Iniciais', color='Porcentagem de Formados',
                                 color_continuous_scale='RdYlGn', range_color=[0, 100])
                st.plotly_chart(fig5, use_container_width=True)
            with col6:
                st.markdown("**Distribuição da Performance**")
                fig6 = px.box(df_filtrado, x='Instituição da Rede', y='Porcentagem de Formados',
                             color='Instituição da Rede', points="all", color_discrete_map=CORES_INST)
                st.plotly_chart(fig6, use_container_width=True)

            # 8. Tabela Detalhada
            st.subheader("📋 Base de Dados Completa")
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Erro ao processar o dashboard: {e}")

    # Rodapé Institucional
    st.divider()
    vazio1, vazio2, col_ufpi, col_uespi, col_unicap = st.columns([4, 1, 1, 1, 1])
    with col_ufpi:
        if os.path.exists("logo_ufpi.png"): st.image("logo_ufpi.png", width=100)
    with col_uespi:
        if os.path.exists("logo_uespi.png"): st.image("logo_uespi.png", width=100)
    with col_unicap:
        if os.path.exists("logo_unicap.png"): st.image("logo_unicap.png", width=100)

    st.markdown("<div style='text-align: right; color: gray; font-size: 12px;'>Programa PRILEI - Coordenação de Avaliação e Acompanhamento - Editais 35 e 66/21</div>", unsafe_allow_html=True)
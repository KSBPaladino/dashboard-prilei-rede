import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Analytics PRILEI - UFPI/UESPI/UNICAP", layout="wide")

# 2. FUNÇÃO DE VERIFICAÇÃO DE SENHA (Centralizada e com botão)
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Interface de login centralizada
    _, col_login, _ = st.columns([1, 2, 1])

    with col_login:
        st.markdown("### 🔐 Acesso Restrito")
        with st.form("login_form"):
            password = st.text_input("Digite a senha para acessar o Dashboard", type="password")
            submit = st.form_submit_button("Acessar")

            if submit:
                if password == st.secrets["password"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("😕 Senha inválida")
    return False

# 3. BLOCO PROTEGIDO
if check_password():

    # CSS: Cor dos indicadores em azul claro (#5dade2)
    st.markdown("""
        <style>
        [data-testid='stMetricValue'] { font-size: 28px; color: #5dade2; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

    if os.path.exists("logo_prilei.png"):
        st.image("logo_prilei.png", width=250)

    st.title("Painel Analítico de Conclusão - PRILEI")
    st.markdown("Rede Nordeste: **UFPI** - **UESPI** - **UNICAP**")

    # Definição de Cores das Instituições
    CORES_INST = {'UFPI': '#003366', 'UESPI': '#cc0000', 'UNICAP': '#1a7a1a'}

    # NOVAS CORES SINCRONIZADAS (Baseadas na imagem do gráfico de Pizza/Donut)
    AZUL_FOR = '#0068c9'  # Azul vibrante da segunda imagem
    AZUL_NAO = '#83c9ff'  # Azul claro celeste da segunda imagem

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

            m1.metric("Matrículas Totais", f"{int(total_mat):,}".replace(",", "."))
            m2.metric("Total de Formados", f"{int(total_for):,}".replace(",", "."))
            m3.metric("Taxa de Conclusão Geral", f"{taxa_real_geral:.1f}%")
            m4.metric("Qtd. Turmas", len(df_filtrado))

            st.divider()

            # 5. LINHA 1: Barras por Curso e Pizza Global
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("**Taxa de Conclusão por Curso (%)**")
                fig1 = px.bar(df_filtrado,
                            x='Curso',
                            y='Porcentagem de Formados',
                            color='Instituição da Rede',
                            barmode='group',
                            text_auto='.1f',
                            color_discrete_map=CORES_INST,
                            hover_data=['Município', 'Matrículas Iniciais', 'Formados'])
                fig1.update_xaxes(type='category', tickangle=45)
                st.plotly_chart(fig1, use_container_width=True)

            with col2:
                st.markdown("**Proporção Global (Formados vs Não)**")
                # Gráfico com as novas cores vibrantes
                fig2 = px.pie(values=[total_for, total_mat - total_for], names=['Formados', 'Não Formados'],
                            hole=0.5, color_discrete_map={'Formados': AZUL_FOR, 'Não Formados': AZUL_NAO})
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

                # Cores agora idênticas às da Pizza/Donut (Vibrantes)
                fig4 = px.bar(df_abs_melt,
                             x='Instituição da Rede',
                             y='Qtd',
                             color='Status',
                             barmode='stack',
                             color_discrete_map={'Formados': AZUL_FOR, 'Não Formados': AZUL_NAO})
                st.plotly_chart(fig4, use_container_width=True)

            # 7. LINHA 3 - Treemap e Box Plot
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

            # 8. Tabela Detalhada e Botão de Download
            st.divider()
            col_tab1, col_tab2 = st.columns([3, 1])
            with col_tab1:
                st.subheader("📋 Base de Dados Completa")
            with col_tab2:
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download dos Dados (CSV)",
                    data=csv,
                    file_name='dados_prilei_filtrados.csv',
                    mime='text/csv',
                    use_container_width=True
                )

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
import pandas as pd, os, streamlit as st, altair as alt
from datetime import date, datetime, timedelta
from calendar import monthrange

# =====================
# funções auxiliares
# =====================
def grafico_combinado(df, metric, titulo):
    # 🔹 Verifica se as colunas "_prev" existem
    metric_prev = f"{metric}_prev"
    if metric_prev not in df.columns:
        st.warning(f"Coluna '{metric_prev}' não encontrada no DataFrame.")
        return

    # 🔹 Prepara o DataFrame longo para o gráfico
    df_long = pd.DataFrame({
        "dia_mes": pd.to_datetime(df["date"]).dt.strftime("%d/%m"),
        "Atual": df[metric],
        "Anterior": df[metric_prev]
    }).melt(id_vars="dia_mes", var_name="Periodo", value_name="Valor")

    # 🔹 Define os tipos de visualização
    bar = alt.Chart(df_long[df_long["Periodo"] == "Atual"]).mark_bar(color="#4C78A8").encode(
        x=alt.X('dia_mes:N', title='Dia'),
        y=alt.Y('Valor:Q', title=titulo),
        tooltip=['dia_mes', 'Valor']
    )

    line = alt.Chart(df_long[df_long["Periodo"] == "Anterior"]).mark_line(color="#F2B701", point=True).encode(
        x='dia_mes:N',
        y='Valor:Q',
        tooltip=['dia_mes', 'Valor']
    )

    # 🔹 Exibe gráfico combinado
    st.altair_chart(alt.layer(bar, line).properties(title=titulo), use_container_width=True)


# ======================
# 🧭 Controle de navegação
# ======================
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

# ======================
# ⚙️ Configurações gerais
# ======================
st.set_page_config(page_title="Dashboard GA4 – WN7", page_icon="📊", layout="wide")

# Caminho do logo
base_dir = os.path.dirname(__file__)
logo_path = os.path.join(base_dir, "assents", "logo.png")

meta_geral = 100000
hoje = pd.Timestamp.today()
dias_passados = hoje.day
total_dias_mes = monthrange(hoje.year, hoje.month)[1]

# ======================
# 🎨 Tema visual
# ======================
st.markdown("""
<style>
    body, .stApp { background-color: #FFFFFF !important; color: #1D1D1B !important; font-family: 'Montserrat', sans-serif !important; }
    h1, h2, h3, h4 { color: #005B82 !important; font-weight: 600 !important; }
    div[data-baseweb="select"], .stTextInput > div > div > input { background-color: #FFFFFF !important; color: #1D1D1B !important; border: 1px solid #ADAFAF !important; border-radius: 6px !important; }
    ::placeholder { color: #6e6e6e !important; }
    button[kind="primary"] { background-color: #005B82 !important; color: white !important; border-radius: 6px !important; }
    .card { background-color: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; padding: 24px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); color: #1D1D1B; }
    .card h4 { color: #005B82; font-size: 22px; margin-bottom: 18px; text-align: left; }
    .receita { font-size: 24px; color: #F39200; font-weight: 700; }
    .positivo { color: #16a34a !important; }
    .negativo { color: #dc2626 !important; }
</style>
""", unsafe_allow_html=True)

# ======================
# Cabeçalho com logo
# ======================
col_logo, col_titulo = st.columns([0.15, 0.85])
with col_logo:
    st.image(logo_path)
with col_titulo:
    st.title("Dashboard de Contas – Google Analytics 4")
    data_extracao = date.today().strftime("%d/%m/%Y")
    st.markdown(f"**🕒 Dados extraídos em:** {data_extracao}")

st.markdown("---")

# ======================
# Função para carregar dados
# ======================
@st.cache_data
def carregar_dados():
    df = pd.read_csv("relatorio_analytics_30dias_tratado.csv", sep=";")
    df.columns = df.columns.str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

df = carregar_dados()

# ======================
# ========== DASHBOARD PRINCIPAL ==========
# ======================
if st.session_state["page"] == "dashboard":
    df_validas = df[df['sessions'] > 0]
    contas_disponiveis = sorted(df_validas['account_display'].unique())

    selecionadas = st.multiselect(
        "Selecione uma ou mais contas:",
        options=contas_disponiveis,
        placeholder="Escolha as contas que deseja visualizar..."
    )

    if selecionadas:
        df_filtrado = df_validas[df_validas['account_display'].isin(selecionadas)]
    else:
        df_filtrado = df_validas

    st.markdown("---")

    colunas = st.columns(3)
    for idx, conta in enumerate(df_filtrado['account_display'].unique()):
        conta_df = df_filtrado[df_filtrado['account_display'] == conta]
        total_sessions = conta_df['sessions'].sum()
        total_revenue = conta_df['purchaseRevenue'].sum()
        var_revenue = conta_df['purchaseRevenue'].pct_change().mean() * 100
        progresso_meta = (total_revenue / meta_geral) * 100
        progresso_meta = min(progresso_meta, 9999)
        cor_meta = "#16a34a" if progresso_meta >= 100 else "#F39200"
        cor_var_rev = "green" if var_revenue >= 0 else "red"

        col = colunas[idx % 3]
        with col:
            st.markdown(
                f"""
                <div class="card" style="cursor:pointer;">
                    <h4 title="{conta}" style="
                        color:#005B82;
                        font-size:34px;
                        font-weight:600;
                        margin-bottom:18px;
                        text-align:left;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        display: block;
                        max-width: 350px;">
                        {conta}
                    </h4>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:24px;">
                        <div>
                            <b>Receita:</b><br>
                            <span style='color:#F39200; font-size:30px; font-weight:700;'>R$ {total_revenue:,.2f}</span><br>
                            <span style="font-size:18px;"><b>Variação:</b>
                            <span style="color:{cor_var_rev}; font-size:16px;">{var_revenue:+.1f}%</span></span>
                        </div>
                        <div>
                            <b>Sessões:</b><br>{total_sessions:,.0f}
                        </div>
                    </div>
                    <div style="margin-top:10px; font-size:18px; display:flex; justify-content:space-between;">
                        <span style="color:{cor_meta};"><b>Atingimento previsto:</b> {progresso_meta:.2f}%</span>
                        <span style="color:{cor_meta};"><b>Meta total:</b> R$ {meta_geral:,.0f}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Abrir detalhes", key=f"btn_{idx}_{hash(conta)}"):
                st.session_state["page"] = "detalhes"
                st.session_state["conta_selecionada"] = conta
                st.rerun()

# ======================
# ========== PÁGINA DE DETALHES ==========
# ======================

if st.session_state["page"] == "detalhes":

    if "conta_selecionada" not in st.session_state:
        st.warning("Selecione uma conta na página principal.")
        st.stop()

    conta = st.session_state["conta_selecionada"]

    if st.button("⬅️ Voltar para o painel principal"):
        st.session_state["page"] = "dashboard"
        st.session_state.pop("conta_selecionada", None)
        st.rerun()

    st.title(f"📊 Detalhes da conta: {conta}")

    # ======================
    # 🔗 Card de links da conta
    # ======================
    df_conta = df[df["account_display"] == conta].copy()
    links_conta = df_conta["links"].dropna().unique()
    links_conta = links_conta[0] if len(links_conta) > 0 else ""
    lista_links = [l.strip() for l in links_conta.split(";") if l.strip()]

    if lista_links:
        html_links = "<ul style='margin:0; padding-left:20px;'>"
        for link in lista_links:
            html_links += f"<li><a href='{link}' target='_blank' style='color:#005B82; text-decoration:none;'>{link}</a></li>"
        html_links += "</ul>"

        st.markdown(
            f"""
            <div class="card">
                <h4>🔗 Links da conta</h4>
                {html_links}
            </div>
            """,
            unsafe_allow_html=True
        )

    # ======================
    # 📊 Gráficos combinados com colunas "_prev"
    # ======================
    st.markdown("---")
    st.subheader("📈 Desempenho – Últimos 30 dias vs Mês anterior")

    col1, col2 = st.columns(2)
    with col1:
        grafico_combinado(df_conta, "purchaseRevenue", "Receita – Atual vs Anterior")
        grafico_combinado(df_conta, "sessions", "Sessões – Atual vs Anterior")

    with col2:
        grafico_combinado(df_conta, "transactions", "Transações – Atual vs Anterior")
        grafico_combinado(df_conta, "conversion_rate", "Taxa de Conversão (%) – Atual vs Anterior")

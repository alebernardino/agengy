import pandas as pd, os, streamlit as st
from datetime import date

# ======================
# ⚙️ Configurações gerais
# ======================
st.set_page_config(page_title="Dashboard GA4 – WN7", page_icon="📊", layout="wide")

# Caminho do logo
base_dir = os.path.dirname(__file__)
logo_path = os.path.join(base_dir, "assents", "logo.png")

# ======================
# 🎨 Tema visual (cores do print)
# ======================
# ======================
# 🎨 Tema visual (ajustado ao padrão da imagem)
# ======================
st.markdown("""
    <style>
        body, .stApp {
            background-color: #FFFFFF !important;
            color: #1D1D1B !important;
            font-family: 'Montserrat', sans-serif !important;
        }

        h1, h2, h3, h4 {
            color: #005B82 !important;
            font-weight: 600 !important;
        }

        div[data-baseweb="select"], .stTextInput > div > div > input {
            background-color: #FFFFFF !important;
            color: #1D1D1B !important;
            border: 1px solid #ADAFAF !important;
            border-radius: 6px !important;
        }

        ::placeholder {
            color: #6e6e6e !important;
        }

        button[kind="primary"] {
            background-color: #005B82 !important;
            color: white !important;
            border-radius: 6px !important;
        }

        /* ======= ESTILO DOS CARDS ======= */
        .card {
            background-color: #FFFFFF;
            border: 1px solid #E5E5E5;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 25px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            color: #1D1D1B;
        }

        .card h4 {
            color: #005B82;
            font-size: 22px;
            margin-bottom: 18px;
            text-align: left;
        }

        /* ======= MÉTRICAS PRINCIPAIS ======= */
        .valor-principal {
            font-size: 26px;
            color: #F39200;
            font-weight: 700;
            line-height: 1.3;
        }

        .receita {
            font-size: 24px;
            color: #F39200;
            font-weight: 700;
        }

        .variacao {
            font-size: 15px;
            font-weight: 600;
            margin-top: -4px;
        }

        .positivo {
            color: #16a34a !important; /* verde */
        }

        .negativo {
            color: #dc2626 !important; /* vermelho */
        }

        .meta {
            font-size: 14px;
            color: #16a34a;
            line-height: 1.4;
        }

        hr {
            border-top: 1px solid #E5E5E5 !important;
        }
    </style>
""", unsafe_allow_html=True)


# ======================
# 🖼️ Cabeçalho com logo
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
# 📦 Carrega dados
# ======================
@st.cache_data
def carregar_dados():
    df = pd.read_csv("relatorio_analytics.csv", sep=";")
    # Converte colunas numéricas
    cols_float = [
        "sessions_now", "sessions_prev",
        "transactions_now", "transactions_prev",
        "purchaseRevenue_now", "purchaseRevenue_prev",
        "conversion_rate_now", "conversion_rate_prev"
    ]
    for c in cols_float:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

df = carregar_dados()

# ======================
# 🔹 Identifica contas zeradas e válidas
# ======================
df_zeradas = df[
    (df['sessions_now'] == 0) &
    (df['transactions_now'] == 0) &
    (df['purchaseRevenue_now'] == 0)
]['account_display'].unique()

df_validas = df[
    ~(
        (df['sessions_now'] == 0) &
        (df['transactions_now'] == 0) &
        (df['purchaseRevenue_now'] == 0)
    )
]

# ======================
# 🔍 Filtro de contas
# ======================
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

# ======================
# 🧱 Cards estilizados (cores do print)
# ======================
meta_geral = 100000

colunas = st.columns(3)

for idx, conta in enumerate(df_filtrado['account_display'].unique()):
    conta_df = df_filtrado[df_filtrado['account_display'] == conta]

    total_sessions = conta_df['sessions_now'].sum()
    total_prev_sessions = conta_df['sessions_prev'].sum()

    total_transactions = conta_df['transactions_now'].sum()
    total_prev_transactions = conta_df['transactions_prev'].sum()

    total_revenue = conta_df['purchaseRevenue_now'].sum()
    total_prev_revenue = conta_df['purchaseRevenue_prev'].sum()

    avg_conversion = (total_transactions / total_sessions * 100) if total_sessions > 0 else 0
    avg_conversion_prev = (total_prev_transactions / total_prev_sessions * 100) if total_prev_sessions > 0 else 0

    # variações percentuais
    var_sessions = ((total_sessions - total_prev_sessions) / total_prev_sessions * 100) if total_prev_sessions > 0 else 0
    var_revenue = ((total_revenue - total_prev_revenue) / total_prev_revenue * 100) if total_prev_revenue > 0 else 0
    var_conversion = ((avg_conversion - avg_conversion_prev) / avg_conversion_prev * 100) if avg_conversion_prev > 0 else 0

    progresso_meta = (total_revenue / meta_geral) * 100
    progresso_meta = min(progresso_meta, 9999)

    cor_meta = "#16a34a" if progresso_meta >= 100 else "#F39200"
    cor_var_sess = "positivo" if var_sessions >= 0 else "negativo"
    cor_var_rev = "positivo" if var_revenue >= 0 else "negativo"
    cor_var_conv = "positivo" if var_conversion >= 0 else "negativo"

    col = colunas[idx % 3]
    with col:
        st.markdown(
            f"""
            <div class="card">
                <h4>{conta}</h4>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; font-size:17px;">
                    <div><b>Sessões:</b><br>{total_sessions:,.0f}<br>
                        <span class="{cor_var_sess}">{var_sessions:+.1f}%</span></div>
                    <div><b>Transações:</b><br>{total_transactions:,.0f}</div>
                    <div><b>Receita:</b><br><span class="receita">R$ {total_revenue:,.2f}</span><br>
                        <span class="{cor_var_rev}">{var_revenue:+.1f}%</span></div>
                    <div><b>Conversão:</b><br>{avg_conversion:.2f}%<br>
                        <span class="{cor_var_conv}">{var_conversion:+.1f}%</span></div>
                </div>
                <div style="margin-top:10px; font-size:14px;">
                    <span style="color:{cor_meta};"><b>Meta:</b> R$ 100K<br>
                    <b>Progresso:</b> {progresso_meta:.2f}%</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ======================
# ⚠️ Contas zeradas
# ======================
if len(df_zeradas) > 0:
    st.markdown("---")
    st.markdown(
        "<h3 style='text-align:center; color:#F39200;'>⚠️ Contas com todos os valores zerados</h3>",
        unsafe_allow_html=True
    )
    colunas = st.columns(4)
    for idx, conta in enumerate(df_zeradas):
        colunas[idx % 4].markdown(f"- {conta}")

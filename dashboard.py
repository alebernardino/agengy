import pandas as pd, os, streamlit as st
from datetime import date

# ======================
# ⚙️ Configurações gerais
# ======================
st.set_page_config(page_title="Dashboard GA4 – WN7", page_icon="📊", layout="wide")
# logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

# Pega o diretório onde o script está
base_dir = os.path.dirname(__file__)
logo_path = os.path.join(base_dir, "assents", "logo.png")



# CSS Global — Tema WN7
st.markdown("""
    <style>
        /* ===========================
           🎨 Tema WN7 Performance Digital
        ============================ */
        body, .stApp {
            background-color: #FFFFFF !important;
            color: #1D1D1B !important;
            font-family: 'Montserrat', sans-serif !important;
        }

        h1, h2, h3, h4 {
            color: #005B82 !important;
            font-weight: 600 !important;
        }

        /* Campos de entrada */
        div[data-baseweb="select"], .stTextInput > div > div > input {
            background-color: #FFFFFF !important;
            color: #1D1D1B !important;
            border: 1px solid #ADAFAF !important;
            border-radius: 6px !important;
        }

        /* Placeholders */
        ::placeholder {
            color: #6e6e6e !important;
        }

        /* Botões */
        button[kind="primary"] {
            background-color: #005B82 !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
        }

        button[kind="secondary"] {
            background-color: #F39200 !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
        }

        /* Cards */
        .card {
            background-color: #FFFFFF;
            border: 1px solid #ADAFAF;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            color: #1D1D1B;
        }

        .card h4 {
            color: #005B82;
            margin-bottom: 12px;
            font-size: 26px;
        }

        .receita {
            color: #F39200 !important;
            font-weight: bold;
        }

        /* Linhas e divisores */
        hr {
            border-top: 1px solid #ADAFAF !important;
        }
    </style>
""", unsafe_allow_html=True)

# ======================
# 🖼️ Cabeçalho com logo
# ======================
col_logo, col_titulo = st.columns([0.15, 0.85])
with col_logo:
    st.image(logo_path)
    # st.image("assets/logown7.jpeg", width="stretch")
    # st.image(logo_path, width="stretch")
    # st.image(r"C:\code\agency_dash\agengy\assents\logo.png")

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
    df['purchaseRevenue'] = df['purchaseRevenue'].astype(float)
    df['sessions'] = df['sessions'].astype(int)
    df['transactions'] = df['transactions'].astype(int)
    df['conversion_rate'] = df['conversion_rate'].astype(float)
    return df

df = carregar_dados()

# ======================
# 🔹 Identifica contas zeradas e válidas
# ======================
df_zeradas = df[
    (df['sessions'] == 0) &
    (df['transactions'] == 0) &
    (df['purchaseRevenue'] == 0)
]['account_display'].unique()

df_validas = df[
    ~(
        (df['sessions'] == 0) &
        (df['transactions'] == 0) &
        (df['purchaseRevenue'] == 0)
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
# 🧱 Cards estilizados WN7
# ======================
colunas = st.columns(3)

for idx, conta in enumerate(df_filtrado['account_display'].unique()):
    conta_df = df_filtrado[df_filtrado['account_display'] == conta]

    total_sessions = conta_df['sessions'].sum()
    total_transactions = conta_df['transactions'].sum()
    total_revenue = conta_df['purchaseRevenue'].sum()
    avg_conversion = (total_transactions / total_sessions * 100) if total_sessions > 0 else 0

    col = colunas[idx % 3]
    with col:
        st.markdown(
            f"""
            <div class="card">
                <h4>{conta}</h4>
                <div style="
                    display:grid;
                    grid-template-columns: 1fr 1fr;
                    gap:10px;
                    font-size:17px;
                ">
                    <div><b>Sessões:</b><br>{total_sessions:,}</div>
                    <div><b>Transações:</b><br>{total_transactions:,}</div>
                    <div><b>Receita:</b><br><span class="receita">R$ {total_revenue:,.2f}</span></div>
                    <div><b>Conversão:</b><br>{avg_conversion:.2f}%</div>
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

    col1, col2, col3, col4 = st.columns(4)
    for idx, conta in enumerate(df_zeradas):
        [col1, col2, col3, col4][idx % 4].markdown(f"- {conta}")

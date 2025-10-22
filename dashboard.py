import pandas as pd
import streamlit as st
from datetime import date

# ======================
# ⚙️ Configurações gerais
# ======================
st.set_page_config(page_title="Dashboard GA4", page_icon="📊", layout="wide")
st.title("📈 Dashboard de Contas – Google Analytics 4")
data_extracao = date.today().strftime("%d/%m/%Y")
st.markdown(f"**🕒 Dados extraídos em:** {data_extracao}")

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
# 🔍 Filtro de contas (multiseleção)
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
# 🧱 Cards responsivos (3 colunas)
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
            <div style="
                background-color:#1e1e1e;
                border-radius:12px;
                padding:20px;
                margin-bottom:20px;
                box-shadow:0 4px 10px rgba(0,0,0,0.25);
                color:white;
                font-family:Arial, sans-serif;
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                height:auto;
            ">
                <h4 style="color:#00bfff; margin-bottom:12px; font-size:30px;">{conta}</h4>
                <div style="
                    display:grid;
                    grid-template-columns: 1fr 1fr;
                    gap:8px;
                    font-size:14px;
                    line-height:1.4;
                ">
                    <div><b>Sessões:</b><br>{total_sessions:,}</div>
                    <div><b>Transações:</b><br>{total_transactions:,}</div>
                    <div><b>Receita:</b><br>R$ {total_revenue:,.2f}</div>
                    <div><b>Conversão:</b><br>{avg_conversion:.2f}%</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ======================
# 📋 Lista de contas zeradas (no final)
# ======================
if len(df_zeradas) > 0:
    st.markdown("---")
    st.markdown(
        "<h3 style='text-align:center; color:#ffcc00;'>⚠️ Contas com todos os valores zerados</h3>",
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)

    for idx, conta in enumerate(df_zeradas):
        if idx % 4 == 0:
            col = col1
        elif idx % 4 == 1:
            col = col2
        elif idx % 4 == 2:
            col = col3
        else:
            col = col4
        col.markdown(f"- {conta}")

import pandas as pd 
import streamlit as st
import altair as alt
import numpy as np
import json, os, ast, base64
from datetime import date, datetime, timedelta
from calendar import monthrange

CSV_PATH = os.path.join(os.path.dirname(__file__), "contas_config.csv")


# =====================
# funções auxiliares
# =====================
if True:
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
        st.altair_chart(alt.layer(bar, line).properties(title=titulo), width="stretch")

    @st.dialog("✏️ Edição da Conta")
    def edit(conta):
        st.markdown(f"### Editar conta: **{conta}**")

        # -----------------------
        # 🔹 Carrega os dados do CSV
        # -----------------------
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH, sep=";")
            
            for i in range(1, 7):
                for col in [f"t_link{i}", f"link{i}"]:
                    if col in df.columns:
                        df[col] = df[col].astype(str)
        else:
            st.error("⚠️ Arquivo de configuração não encontrado.")
            return

        # Tenta localizar a conta no arquivo
        row = df[df["property_display"] == conta]
        if row.empty:
            st.error("Conta não encontrada no arquivo.")
            return

        # -----------------------
        # 🔹 Inicializa dados da sessão
        # -----------------------
        if "edit_data" not in st.session_state:
            status = row["status"].iloc[0] if "status" in row else "Ativo"
            meta = float(row["meta"].iloc[0]) if "meta" in row else 0.0

            # Lê os títulos e links (até 6)
            links = []
            for i in range(1, 7):
                titulo = row[f"t_link{i}"].iloc[0] if f"t_link{i}" in row else ""
                url = row[f"link{i}"].iloc[0] if f"link{i}" in row else ""
                links.append({
                    "titulo": titulo if pd.notna(titulo) else "",
                    "url": url if pd.notna(url) else ""
                })

            st.session_state.edit_data = {
                "status": status,
                "meta": meta,
                "links": links,
            }

        data = st.session_state.edit_data

        # -----------------------
        # 🔹 Interface de edição
        # -----------------------
        data["status"] = st.selectbox(
            "Status da conta",
            ["Ativo", "Inativo"],
            index=0 if data["status"] == "Ativo" else 1
        )

        data["meta"] = st.number_input(
            "Meta mensal",
            value=float(data["meta"]),
            min_value=0.0,
            step=100.0
        )

        st.markdown("#### 🔗 Links associados")

        for i in range(6):
            col1, col2 = st.columns([1, 2])
            with col1:
                data["links"][i]["titulo"] = st.text_input(
                    f"Título {i+1}",
                    value=data["links"][i]["titulo"],
                    placeholder="Ex: Google Analytics"
                )
            with col2:
                data["links"][i]["url"] = st.text_input(
                    f"URL {i+1}",
                    value=data["links"][i]["url"],
                    placeholder="https://..."
                )

        # -----------------------
        # 🔹 Salvar alterações
        # -----------------------
        if st.button("💾 Salvar alterações"):
            idx = df.index[df["property_display"] == conta][0]

            df.at[idx, "status"] = data["status"]
            df.at[idx, "meta"] = data["meta"]

            # Atualiza títulos e URLs no DataFrame
            for i in range(1, 7):
                df.at[idx, f"t_link{i}"] = data["links"][i-1]["titulo"]
                df.at[idx, f"link{i}"] = data["links"][i-1]["url"]

            df.to_csv(CSV_PATH, sep=";", index=False)
            st.success("✅ Alterações salvas com sucesso!")
            st.rerun()
    
    @st.cache_data
    def carregar_dados():
        df = pd.read_csv("base_comparativa.csv", sep=";")
        df.columns = df.columns.str.strip()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    df = carregar_dados()
    # ======================
    # 🔹 Filtrar apenas contas ativas
    # ======================
    if os.path.exists(CSV_PATH):
        df_config = pd.read_csv(CSV_PATH, sep=";")
        if "property_display" in df_config.columns and "status" in df_config.columns:
            contas_ativas = df_config[df_config["status"].str.lower() == "ativo"]["property_display"].unique()
            df = df[df["property_display"].isin(contas_ativas)]
        else:
            st.warning("⚠️ Colunas 'property_display' e/ou 'status' não encontradas no arquivo de configuração.")
    else:
        st.warning("⚠️ Arquivo de configuração de contas não encontrado.")

    def calcular_periodo(tipo_periodo: str):
        hoje = pd.Timestamp.today().normalize()

        if tipo_periodo == "Mês atual":
            inicio_atual = hoje.replace(day=1)
            fim_atual = hoje
            inicio_anterior = (inicio_atual - pd.offsets.MonthBegin(1))
            fim_anterior = inicio_atual - pd.Timedelta(days=1)

        elif tipo_periodo == "Últimos 30 dias":
            fim_atual = hoje
            inicio_atual = fim_atual - pd.Timedelta(days=29)
            fim_anterior = inicio_atual - pd.Timedelta(days=1)
            inicio_anterior = fim_anterior - pd.Timedelta(days=29)

        elif tipo_periodo == "Últimos 15 dias":
            fim_atual = hoje
            inicio_atual = fim_atual - pd.Timedelta(days=14)
            fim_anterior = inicio_atual - pd.Timedelta(days=1)
            inicio_anterior = fim_anterior - pd.Timedelta(days=14)

        elif tipo_periodo == "Últimos 7 dias":
            fim_atual = hoje
            inicio_atual = fim_atual - pd.Timedelta(days=6)
            fim_anterior = inicio_atual - pd.Timedelta(days=1)
            inicio_anterior = fim_anterior - pd.Timedelta(days=6)

        else:
            raise ValueError("Tipo de período inválido")

        return {
            "inicio_atual": inicio_atual,
            "fim_atual": fim_atual,
            "inicio_anterior": inicio_anterior,
            "fim_anterior": fim_anterior
        }

# ======================
# 🧭 Controle de navegação
# ======================
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

# ======================
# ⚙️ Configurações gerais
# ======================
if True:
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
/* 🌟 Efeito de hover nos cards clicáveis */
a > .card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    display: block;
}

a > .card:hover {
    transform: translateY(-6px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
    cursor: pointer;
}

/* Rodapé do card */
.card-footer {
    margin-top: 14px;
    font-size: 14px;
    color: #6b7280;
    text-align: center;
    font-style: italic;
}
            
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
# 🎨 Estilo global dos botões (com cores específicas)
# ======================
st.markdown("""
<style>
/* === BASE GERAL PARA TODOS OS BOTÕES === */
div[data-testid="stButton"] > button {
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    color: #FFFFFF !important;
    padding: 8px 20px !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.15);
    transition: all 0.2s ease-in-out;
    cursor: pointer !important;
    background-color: #005B82 !important; /* azul padrão */
}

/* Hover padrão (azul) */
div[data-testid="stButton"] > button:hover {
    background-color: #0076A3 !important;
    transform: translateY(-2px);
}

/* 🟩 Verde – Botões com "detalhes_" no ID */
button[id*="detalhes_"] {
    background-color: #198754 !important; /* verde */
}
button[id*="detalhes_"]:hover {
    background-color: #28a745 !important; /* verde claro */
}

/* 🟧 Laranja – Botões com "editar_" no ID */
button[id*="editar_"] {
    background-color: #F39200 !important; /* laranja corporativo */
}
button[id*="editar_"]:hover {
    background-color: #ffb347 !important; /* laranja mais claro */
}

/* 🔘 Desabilitados */
div[data-testid="stButton"] > button:disabled {
    background-color: #C5C6C7 !important;
    color: #555 !important;
    opacity: 0.8 !important;
    box-shadow: none !important;
}

/* Margem entre botões em colunas */
div[data-testid="stButton"] {
    margin-top: 8px !important;
}
</style>
""", unsafe_allow_html=True)


# ======================
# Cabeçalho fixo completo
# ======================
if True:
    st.markdown("""
    <style>
    /* === CABEÇALHO FIXO === */
    .fixed-header {
        position: fixed;
        top: 3rem; /* distância da barra preta superior do Streamlit */
        left: 0;
        width: 100%;
        background-color: white;
        z-index: 1000;
        padding: 0.8rem 3rem;
        border-bottom: 1px solid #E5E5E5;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Logo */
    .fixed-header img {
        height: 50px;
        margin-right: 20px;
    }

    /* Título e subtítulo */
    .fixed-header .titulo {
        display: flex;
        flex-direction: column;
    }

    .fixed-header .titulo h1 {
        color: #005B82;
        font-weight: 700;
        font-size: 1.8rem;
        margin: 0;
    }

    .fixed-header .titulo p {
        margin: 0;
        color: #444;
        font-size: 0.9rem;
    }

    /* Ajuste de padding do conteúdo principal */
    .block-container {
        padding-top: 9rem !important;
    }
    </style>
    """, unsafe_allow_html=True)


    # HTML do cabeçalho fixo
    data_extracao = max(df['date']).strftime("%d/%m/%Y")

    st.markdown(
        f"""
        <div class="fixed-header">
            <div style="display: flex; align-items: center;">
                <img src="data:image/png;base64,{base64.b64encode(open(logo_path, 'rb').read()).decode()}" alt="Logo">
                    <div class="titulo">
                    <h1>Dashboard de Contas – Google Analytics 4</h1>
                    <p>🕒 Dados extraídos em: <b>{data_extracao}</b></p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ======================
# ========== DASHBOARD PRINCIPAL ==========
# ======================
if True:
    if st.session_state["page"] == "dashboard":

        # ======================
        # 📅 Botões de período na mesma linha do título
        # ======================
        col_titulo, col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1, 1])

        with col_titulo:
            st.markdown("### 📅 Período de análise")

        # Inicializa o período padrão (mantém ao navegar)
        if "opcao_periodo" not in st.session_state:
            st.session_state.opcao_periodo = "Mês atual"

        periodos = ["Mês atual", "Últimos 30 dias", "Últimos 15 dias", "Últimos 7 dias"]

        # Renderiza os botões na horizontal
        for i, col in enumerate([col1, col2, col3, col4]):
            with col:
                ativo = st.session_state.opcao_periodo == periodos[i]
                if st.button(periodos[i], key=f"btn_dash_{i}"):
                    st.session_state.opcao_periodo = periodos[i]
                    st.rerun()

        # Define o período ativo
        opcao_periodo = st.session_state.opcao_periodo
        periodo = calcular_periodo(opcao_periodo)

        # Feedback visual (opcional)
        st.markdown(
            f"📆 **Filtro ativo:** `{opcao_periodo}` — "
            f"de {periodo['inicio_atual'].strftime('%d/%m/%Y')} até {periodo['fim_atual'].strftime('%d/%m/%Y')}"
        )


        # Filtro de período aplicado ao DataFrame
        df_periodo = df[
            (df["date"] >= periodo["inicio_atual"]) &
            (df["date"] <= periodo["fim_atual"])
        ]

        # Cria a versão anterior para comparação
        df_periodo_prev = df[
            (df["date"] >= periodo["inicio_anterior"]) &
            (df["date"] <= periodo["fim_anterior"])
        ].copy()

        # Marca as colunas com sufixo "_prev" para comparação
        for col in ["purchaseRevenue", "sessions", "transactions", "conversion_rate"]:
            if col in df.columns:
                df_periodo_prev = df_periodo_prev.rename(columns={col: f"{col}_prev"})

        # Faz merge dos dois períodos (baseado em property_display e data relativa)
        df_comparado = pd.merge(
            df_periodo,
            df_periodo_prev,
            on=["property_display", "date"],
            how="left"
        )
        # ======================
        # 🔹 Dados do dashboard
        # ======================
        df_validas = df_comparado[df_comparado['sessions'] > 0]
        contas_disponiveis = sorted(df_validas['property_display'].unique())

        selecionadas = st.multiselect(
            "Selecione uma ou mais contas:",
            options=contas_disponiveis,
            placeholder="Escolha as contas que deseja visualizar..."
        )

        # ======================
        # 🔧 Ajuste de espaçamento do cabeçalho
        # ======================
        st.markdown("""
        <style>
        /* Remove o espaço extra entre o cabeçalho e o conteúdo */
        div.block-container {padding-top: 7rem !important;}

        /* Diminui o espaço entre o título e o próximo elemento (linha horizontal ou multiselect) */
        h1 {margin-bottom: 0.2rem !important;}

        /* Diminui o espaço acima do seletor (multiselect) */
        div[data-baseweb="select"] {margin-top: 0rem !important;}

        /* Opcional: reduz o espaço extra acima da linha horizontal */
        hr {
            margin-top: 0.3rem !important;
            margin-bottom: 0.5rem !important;
        }
        </style>
        """, unsafe_allow_html=True)


        if selecionadas:
            df_filtrado = df_validas[df_validas['property_display'].isin(selecionadas)]
        else:
            df_filtrado = df_validas

        df_atingimento = df_filtrado.groupby('property_display')['purchaseRevenue'].sum().reset_index()
        df_atingimento['atingimento'] = (df_atingimento['purchaseRevenue'] / meta_geral) * 100
        df_atingimento = df_atingimento.sort_values('atingimento', ascending=True)

        st.markdown("---")
        colunas = st.columns(3)

        # ======================
        # 🔹 Cards das contas
        # ======================
        for idx, conta in enumerate(df_atingimento['property_display'].unique()):
            conta_df = df_filtrado[df_filtrado['property_display'] == conta]
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
                    <div class="card" style="
                        padding:10px;
                        border-radius:10px;
                        background:#f9f9f9;
                        box-shadow:0 2px 4px rgba(0,0,0,0.1);
                        margin-bottom:-65px;">
                        <h4 title="{conta}" 
                            style="
                                color:#005B82;
                                font-size:26px;
                                font-weight:600;
                                margin-bottom:16px;
                                white-space: nowrap;
                                overflow: hidden;
                                text-overflow: ellipsis;
                                max-width: 300px;
                                display: inline-block;">
                            {conta}
                        </h4>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:22px;">
                            <div>
                                <b>Receita:</b><br>
                                <span style='color:#F39200; font-size:28px; font-weight:700;'>R$ {total_revenue:,.2f}</span><br>
                                <span style="font-size:16px;"><b>Variação:</b>
                                <span style="color:{cor_var_rev}; font-size:16px;">{var_revenue:+.1f}%</span></span>
                            </div>
                            <div>
                                <b>Sessões:</b><br>{total_sessions:,.0f}
                            </div>
                        </div>
                        <div style="margin-top:10px; font-size:16px; display:flex; justify-content:space-between;">
                            <span style="color:{cor_meta};"><b>Atingimento previsto:</b> {progresso_meta:.2f}%</span>
                            <span style="color:{cor_meta};"><b>Meta total:</b> R$ {meta_geral:,.0f}</span>
                        </div>
                        <br>
                        <div style="margin-top:16px;">
                    """,
                    unsafe_allow_html=True
                )
        
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"🕵️ Ver detalhes", key=f"detalhes_{conta}"):
                        st.session_state["conta_selecionada"] = conta
                        st.session_state["page"] = "detalhes"
                        st.rerun()

                with col_btn2:
                    if st.button("✏️ Editar conta", key=f"editar_{conta}"):
                        edit(conta)
                        st.session_state["editar_conta"] = conta
                        st.session_state["abrir_card_edicao"] = True

                st.markdown("</div></div>", unsafe_allow_html=True)

# ======================
# ========== PÁGINA DE DETALHES ==========
# ======================
if True:
    if st.session_state["page"] == "detalhes":

        conta = st.session_state["conta_selecionada"]
        st.title(f"📊 Detalhes da conta: {conta}")

        # 💅 Estilo dos botões
        st.markdown("""
        <style>
        div[data-testid="stButton"] button {
            background-color: #005B82 !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            border: none !important;
            transition: background-color 0.2s ease-in-out;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #0076A3 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # -----------------------------
        # 🔹 Filtro de período
        # -----------------------------
        # st.markdown("### 📅 Período de análise")

        # inicializa período na sessão (para manter estado)

        # ======================
        # 📅 Botões de período na mesma linha do título
        # ======================
        col_titulo, col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1, 1])

        with col_titulo:
            st.markdown("### 📅 Período de análise")

        # Inicializa período na sessão
        if "opcao_periodo" not in st.session_state:
            st.session_state.opcao_periodo = "Mês atual"

        periodos = ["Mês atual", "Últimos 30 dias", "Últimos 15 dias", "Últimos 7 dias"]

        # Renderiza os botões lado a lado, após o título
        for i, col in enumerate([col1, col2, col3, col4]):
            with col:
                ativo = st.session_state.opcao_periodo == periodos[i]
                if st.button(periodos[i], key=f"btn_{i}"):
                    st.session_state.opcao_periodo = periodos[i]
                    st.rerun()

        # Define o período ativo
        opcao_periodo = st.session_state.opcao_periodo
        periodo = calcular_periodo(opcao_periodo)

        # aplica o período selecionado
        opcao_periodo = st.session_state.opcao_periodo
        periodo = calcular_periodo(opcao_periodo)

        # feedback visual do filtro ativo
        st.markdown(
            f"📆 **Filtro ativo:** `{opcao_periodo}` — "
            f"de {periodo['inicio_atual'].strftime('%d/%m/%Y')} até {periodo['fim_atual'].strftime('%d/%m/%Y')}"
        )

        periodo = calcular_periodo(opcao_periodo)

        # -----------------------------
        # 🔹 Filtra os dados da conta e do período selecionado
        # -----------------------------
        df_conta = df[
            (df["property_display"] == conta) &
            (df["date"] >= periodo["inicio_atual"]) &
            (df["date"] <= periodo["fim_atual"])
        ].copy()

        # Garante que as colunas *_prev* existam (caso alguma esteja ausente)
        colunas_prev = ["purchaseRevenue_prev", "sessions_prev", "transactions_prev", "conversion_rate_prev"]
        for c in colunas_prev:
            if c not in df_conta.columns:
                df_conta[c] = np.nan

        # -----------------------------
        # 📊 Gráficos comparativos
        # -----------------------------
        st.markdown("---")
        st.subheader("📈 Desempenho – Atual vs Período anterior")

        col1, col2 = st.columns(2)
        with col1:
            grafico_combinado(df_conta, "purchaseRevenue", "Receita – Atual vs Anterior")
            grafico_combinado(df_conta, "sessions", "Sessões – Atual vs Anterior")

        with col2:
            grafico_combinado(df_conta, "transactions", "Transações – Atual vs Anterior")
            grafico_combinado(df_conta, "conversion_rate", "Taxa de Conversão (%) – Atual vs Anterior")

        # -----------------------------
        # 🔹 Botões de navegação
        # -----------------------------
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Voltar para o painel principal"):
                st.session_state["page"] = "dashboard"
                st.session_state.pop("conta_selecionada", None)
                st.query_params.clear()
                st.rerun()
        with col2:
            if st.button("✏️ Editar conta", key=f"editar_{conta}"):
                edit(conta)
                st.session_state["editar_conta"] = conta
                st.session_state["abrir_card_edicao"] = True

        # -----------------------------
        # 🔗 Card de links da conta
        # -----------------------------
        if os.path.exists(CSV_PATH):
            df_config = pd.read_csv(CSV_PATH, sep=";")
            df_config_conta = df_config[df_config["property_display"] == conta]

            if not df_config_conta.empty:
                row = df_config_conta.iloc[0]
                links = []
                for i in range(1, 7):
                    titulo = row.get(f"t_link{i}", "")
                    url = row.get(f"link{i}", "")
                    if pd.notna(url) and str(url).strip():
                        titulo_exibicao = titulo if pd.notna(titulo) and str(titulo).strip() else f"Link {i}"
                        links.append({"titulo": titulo_exibicao, "url": url})

                if links:
                    html_links = "<ul style='margin:0; padding-left:20px;'>"
                    for link in links:
                        html_links += f"<li><a href='{link['url']}' target='_blank' style='color:#005B82; text-decoration:none;'>{link['titulo']}</a></li>"
                    html_links += "</ul>"

                    st.markdown(
                        f"""
                        <div class="card" style="background-color:#F7F9FB; padding:10px; border-radius:10px;">
                            <h4 style="margin-bottom:6px;">🔗 Links da conta</h4>
                            {html_links}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.info("Nenhum link configurado para esta conta.")
            else:
                st.warning("Conta não encontrada no arquivo de configuração.")
        else:
            st.error("⚠️ Arquivo de configuração não encontrado.")


# ======================
# ⚙️ Gerenciamento de Contas (no final do dashboard)
# ======================
with st.expander("🧩 Gerenciar Contas", expanded=False):
    st.markdown("### Lista de Contas – Configurações e Status")

    st.markdown("""
    <style>
    /* Corrige o fundo e cor do botão do expander */
    div.streamlit-expanderHeader {
        background-color: #FFFFFF !important;
        color: #005B82 !important;
        font-weight: 600 !important;
    }

    /* Mantém a cor ao abrir o expander */
    div.streamlit-expanderHeader:hover {
        background-color: #F5F7FA !important;
    }

    /* Corrige o ícone e título quando expandido */
    details[open] > summary {
        background-color: #FFFFFF !important;
        color: #005B82 !important;
        border-bottom: 1px solid #E5E5E5 !important;
    }
    </style>
    """, unsafe_allow_html=True)


    # 🔹 Carrega os dois arquivos
    try:
        df_ga4 = pd.read_csv("ga4_100.csv", sep=";")
    except FileNotFoundError:
        st.warning("⚠️ Arquivo `ga4_100.csv` não encontrado.")
        df_ga4 = pd.DataFrame(columns=["property_display"])

    if os.path.exists(CSV_PATH):
        df_config = pd.read_csv(CSV_PATH, sep=";")
    else:
        st.warning("⚠️ Arquivo de configuração não encontrado.")
        df_config = pd.DataFrame(columns=["property_display", "status", "meta"])

    # 🔹 Junta todas as contas e ordena alfabeticamente
    contas_todas = sorted(set(df_ga4["property_display"].dropna().unique()) | set(df_config["property_display"].dropna().unique()))

    if not contas_todas:
        st.info("Nenhuma conta encontrada nos arquivos.")
    else:
        # 🔍 Campo de busca
        filtro = st.text_input("🔎 Buscar conta", placeholder="Digite parte do nome da conta...").strip().lower()
        contas_filtradas = [c for c in contas_todas if filtro in c.lower()] if filtro else contas_todas

        if not contas_filtradas:
            st.warning("Nenhuma conta corresponde à sua busca.")
        else:
            # CSS visual
            st.markdown(
                """
                <style>
                .linha-conta {
                    display: grid;
                    grid-template-columns: 2fr 0.8fr 1fr 1fr;
                    align-items: center;
                    padding: 8px 12px;
                    border-bottom: 1px solid #eee;
                }
                .linha-conta:nth-child(even) {
                    background-color: #f9f9f9;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # Cabeçalho da tabela
            st.markdown(
                "<div style='display:grid; grid-template-columns:2fr 0.8fr 1fr 1fr; font-weight:700; padding:4px 12px; border-bottom:2px solid #ccc;'>"
                "<div>Conta</div><div>Status</div><div>Meta mensal</div><div>Ações</div></div>",
                unsafe_allow_html=True
            )

            for conta in contas_filtradas:
                # 🔹 Obtém dados da conta no config
                if conta in df_config["property_display"].values:
                    row = df_config[df_config["property_display"] == conta].iloc[0]
                    status_atual = row.get("status", "Ativo")
                    meta_valor = row.get("meta", 0.0)
                else:
                    # Adiciona conta que ainda não existe no config
                    status_atual = "Ativo"
                    meta_valor = 0.0
                    df_config = pd.concat(
                        [df_config, pd.DataFrame([{"property_display": conta, "status": status_atual, "meta": meta_valor}])],
                        ignore_index=True
                    )
                    df_config.to_csv(CSV_PATH, sep=";", index=False)

                cor_tag = "#198754" if str(status_atual).lower() == "ativo" else "#dc3545"
                emoji_tag = "🟢" if str(status_atual).lower() == "ativo" else "🔴"

                col1, col2, col3, col4 = st.columns([2, 0.8, 1, 1])

                with col1:
                    st.markdown(f"**{conta}**")

                with col2:
                    st.markdown(
                        f"<span style='color:{cor_tag}; font-weight:600;'>{emoji_tag} {status_atual}</span>",
                        unsafe_allow_html=True,
                    )

                with col3:
                    nova_meta = st.number_input(
                        f"meta_{conta}",
                        value=float(meta_valor),
                        step=100.0,
                        label_visibility="collapsed"
                    )

                with col4:
                    c1, c2 = st.columns(2)
                    with c1:
                        # Atualiza meta
                        if st.button("💾 Salvar meta", key=f"salvar_meta_{conta}"):
                            df_config.loc[df_config["property_display"] == conta, "meta"] = nova_meta
                            df_config.to_csv(CSV_PATH, sep=";", index=False)
                            st.success(f"Meta da conta **{conta}** atualizada para R$ {nova_meta:,.0f}!")
                            st.rerun()
                    with c2:
                        # Alterna status
                        if str(status_atual).lower() == "ativo":
                            if st.button("🔻 Inativar", key=f"inativar_{conta}"):
                                df_config.loc[df_config["property_display"] == conta, "status"] = "Inativo"
                                df_config.to_csv(CSV_PATH, sep=";", index=False)
                                st.success(f"Conta **{conta}** inativada com sucesso!")
                                st.rerun()
                        else:
                            if st.button("🔺 Ativar", key=f"ativar_{conta}"):
                                df_config.loc[df_config["property_display"] == conta, "status"] = "Ativo"
                                df_config.to_csv(CSV_PATH, sep=";", index=False)
                                st.success(f"Conta **{conta}** ativada com sucesso!")
                                st.rerun()

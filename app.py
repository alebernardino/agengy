import os
import json
import ast
import base64
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
from datetime import date, datetime, timedelta
from calendar import monthrange


# ============================================================
# ⚙️ CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="Dashboard GA4 – WN7", page_icon="📊", layout="wide")

CSV_PATH = os.path.join(os.path.dirname(__file__), "contas_config.csv")
BASE_DIR = os.path.dirname(__file__)
LOGO_PATH = os.path.join(BASE_DIR, "assents", "logo.png")

# ============================================================
# 🎨 FUNÇÃO PARA CARREGAR CSS
# ============================================================
def load_css(file_path: str):
    """Carrega um arquivo CSS externo e aplica ao Streamlit."""
    with open(file_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# ============================================================
# 🧮 FUNÇÕES AUXILIARES
# ============================================================
@st.cache_data
def carregar_dados():
    """Carrega e prepara o DataFrame principal."""
    df = pd.read_csv("base_comparativa.csv", sep=";")
    df.columns = df.columns.str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

def calcular_periodo(tipo_periodo: str):
    """Calcula datas de início e fim do período atual e anterior."""
    hoje = pd.Timestamp.today().normalize()

    if tipo_periodo == "Mês atual":
        inicio_atual = hoje.replace(day=1)
        fim_atual = hoje
        inicio_anterior = inicio_atual - pd.offsets.MonthBegin(1)
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

def grafico_combinado(df, metric, titulo):
    """Cria gráfico combinado de barras e linhas (período atual vs anterior)."""
    metric_prev = f"{metric}_prev"
    if metric_prev not in df.columns:
        st.warning(f"Coluna '{metric_prev}' não encontrada no DataFrame.")
        return

    df_long = pd.DataFrame({
        "dia_mes": pd.to_datetime(df["date"]).dt.strftime("%d/%m"),
        "Atual": df[metric],
        "Anterior": df[metric_prev]
    }).melt(id_vars="dia_mes", var_name="Periodo", value_name="Valor")

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

    st.altair_chart(alt.layer(bar, line).properties(title=titulo), use_container_width=True)

# ============================================================
# ✏️ FUNÇÃO DE EDIÇÃO DE CONTA
# ============================================================
@st.dialog("✏️ Edição da Conta")
def edit(conta):
    """Abre modal para editar status, meta e links da conta."""
    st.markdown(f"### Editar conta: **{conta}**")

    # Carrega o arquivo de configuração
    if not os.path.exists(CSV_PATH):
        st.error("⚠️ Arquivo de configuração não encontrado.")
        return

    df = pd.read_csv(CSV_PATH, sep=";")
    for i in range(1, 7):
        for col in [f"t_link{i}", f"link{i}"]:
            if col in df.columns:
                df[col] = df[col].astype(str)

    row = df[df["property_display"] == conta]
    if row.empty:
        st.error("Conta não encontrada no arquivo.")
        return

    # Inicializa dados da sessão
    if "edit_data" not in st.session_state:
        status = row.get("status", pd.Series(["Ativo"])).iloc[0]
        meta = float(row.get("meta", pd.Series([0])).iloc[0])
        links = [
            {
                "titulo": row.get(f"t_link{i}", pd.Series([""])).iloc[0] or "",
                "url": row.get(f"link{i}", pd.Series([""])).iloc[0] or ""
            }
            for i in range(1, 7)
        ]

        st.session_state.edit_data = {"status": status, "meta": meta, "links": links}

    data = st.session_state.edit_data

    # Campos de edição
    data["status"] = st.selectbox("Status da conta", ["Ativo", "Inativo"],
                                  index=0 if data["status"] == "Ativo" else 1)

    data["meta"] = st.number_input("Meta mensal", value=float(data["meta"]),
                                   min_value=0.0, step=100.0)

    st.markdown("#### 🔗 Links associados")
    for i in range(6):
        col1, col2 = st.columns([1, 2])
        with col1:
            data["links"][i]["titulo"] = st.text_input(f"Título {i+1}",
                                                       value=data["links"][i]["titulo"],
                                                       placeholder="Ex: Google Analytics")
        with col2:
            data["links"][i]["url"] = st.text_input(f"URL {i+1}",
                                                    value=data["links"][i]["url"],
                                                    placeholder="https://...")

    # Botão de salvar
    if st.button("💾 Salvar alterações"):
        idx = df.index[df["property_display"] == conta][0]
        df.at[idx, "status"] = data["status"]
        df.at[idx, "meta"] = data["meta"]

        for i in range(1, 7):
            df.at[idx, f"t_link{i}"] = data["links"][i-1]["titulo"]
            df.at[idx, f"link{i}"] = data["links"][i-1]["url"]

        df.to_csv(CSV_PATH, sep=";", index=False)
        st.success("✅ Alterações salvas com sucesso!")
        st.rerun()

# ============================================================
# 📊 CARREGAMENTO DE DADOS E CONFIGURAÇÃO
# ============================================================
df = carregar_dados()

if os.path.exists(CSV_PATH):
    df_config = pd.read_csv(CSV_PATH, sep=";")
    if {"property_display", "status"}.issubset(df_config.columns):
        contas_ativas = df_config[df_config["status"].str.lower() == "ativo"]["property_display"].unique()
        df = df[df["property_display"].isin(contas_ativas)]
    else:
        st.warning("⚠️ Colunas 'property_display' e/ou 'status' não encontradas no arquivo de configuração.")
else:
    st.warning("⚠️ Arquivo de configuração de contas não encontrado.")

# ============================================================
# 🧭 CONTROLE DE NAVEGAÇÃO
# ============================================================
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

# ============================================================
# 🧾 CABEÇALHO FIXO
# ============================================================
meta_geral = 100000
hoje = pd.Timestamp.today()
data_extracao = max(df['date']).strftime("%d/%m/%Y")

st.markdown(
    f"""
    <div class="fixed-header">
        <div class="header-left">
            <img src="data:image/png;base64,{base64.b64encode(open(LOGO_PATH, 'rb').read()).decode()}" alt="Logo">
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

        # === seleção e controle (colunas) ===
        c1, c2 = st.columns([2, 1])

        with c1:
            st.markdown("### Selecione as contas que deseja visualizar no dashboard:",
                unsafe_allow_html=True
            )
            selecionadas = st.multiselect(
                label="",  # <---- vazio
                options=contas_disponiveis,
                placeholder="Escolha as contas que deseja visualizar..."
            )

        with c2:
            st.markdown("### Critério de ordenação:",
                unsafe_allow_html=True
            )
            criterio_ordenacao = st.selectbox(
                label="",  # <---- vazio
                options=[
                    "Atingimento (%)",
                    "Receita total (R$)",
                    "Sessões",
                    "Nome da conta (A-Z)"
                ],
                index=0
            )

        # === aplica filtro conforme seleção ===
        if selecionadas:
            df_filtrado = df_validas[df_validas['property_display'].isin(selecionadas)]
        else:
            df_filtrado = df_validas

        # === monta df_atingimento base (receita total por conta) ===
        df_atingimento = df_filtrado.groupby('property_display')['purchaseRevenue'].sum().reset_index()
        df_atingimento['atingimento'] = (df_atingimento['purchaseRevenue'] / meta_geral) * 100

        # === aplicação da ordenação (IMPORTANTE: feito ANTES do loop) ===
        if criterio_ordenacao == "Atingimento (%)":
            df_atingimento = df_atingimento.sort_values("atingimento", ascending=False)

        elif criterio_ordenacao == "Receita total (R$)":
            df_atingimento = df_atingimento.sort_values("purchaseRevenue", ascending=False)

        elif criterio_ordenacao == "Sessões":
            # soma de sessões por conta
            df_sessoes = df_filtrado.groupby("property_display")["sessions"].sum().reset_index().rename(columns={"sessions": "total_sessions"})
            # junta para ordenar por total_sessions (se houver contas sem sessões, ficarão NaN -> 0)
            df_atingimento = df_atingimento.merge(df_sessoes, on="property_display", how="left")
            df_atingimento["total_sessions"] = df_atingimento["total_sessions"].fillna(0)
            df_atingimento = df_atingimento.sort_values("total_sessions", ascending=False)

        elif criterio_ordenacao == "Nome da conta (A-Z)":
            df_atingimento = df_atingimento.sort_values("property_display", ascending=True)

        # garante ordem estável e índice limpo
        df_atingimento = df_atingimento.reset_index(drop=True)

        # === gera cards na ordem definida ===
        st.markdown("---")
        colunas = st.columns(3)

        for idx, conta in enumerate(df_atingimento['property_display'].unique()):
            conta_df = df_filtrado[df_filtrado['property_display'] == conta]
            total_sessions = conta_df['sessions'].sum()
            total_revenue = conta_df['purchaseRevenue'].sum()
            rev_series = conta_df['purchaseRevenue'].fillna(0)
            var_revenue = rev_series.pct_change().mean() * 100 if len(rev_series) > 1 else 0.0
            progresso_meta = (total_revenue / meta_geral) * 100
            progresso_meta = min(progresso_meta, 9999)
            cor_meta = "#16a34a" if progresso_meta >= 100 else "#F39200"

            col = colunas[idx % 3]
            with col:
                with st.container():
                    # Card visual
                    st.markdown(
                        f"""
                        <div class="card custom">
                            <h4 title="{conta}">{conta}</h4>
                            <div class="card-grid">
                                <div>
                                    <b>Receita:</b><br>
                                    <span class="receita-valor">R$ {total_revenue:,.2f}</span><br>
                                    <span style="font-size:16px;"><b>Variação:</b>
                                    <span class="{ 'var-positivo' if var_revenue >= 0 else 'var-negativo' }">{var_revenue:+.1f}%</span></span>
                                </div>
                                <div>
                                    <b>Sessões:</b><br>{total_sessions:,.0f}
                                </div>
                            </div>
                            <div class="meta-row">
                                <span style="color:{cor_meta};"><b>Atingimento previsto:</b> {progresso_meta:.2f}%</span>
                                <span style="color:{cor_meta};"><b>Meta total:</b> R$ {meta_geral:,.0f}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # 🔹 Botões reais dentro do card
                    st.markdown('<div class="card-buttons">', unsafe_allow_html=True)

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🕵️ Ver detalhes", key=f"detalhes_{conta}"):
                            st.session_state["conta_selecionada"] = conta
                            st.session_state["page"] = "detalhes"
                            st.rerun()

                    with col_btn2:
                        if st.button("✏️ Editar conta", key=f"editar_{conta}"):
                            edit(conta)
                            st.session_state["editar_conta"] = conta
                            st.session_state["abrir_card_edicao"] = True

                    st.markdown('</div>', unsafe_allow_html=True)
    # ======================
    # ⚙️ Gerenciamento de Contas (no final do dashboard)
    # ======================
    with st.expander("🧩 Gerenciar Contas", expanded=False):
        st.markdown("### Lista de Contas – Configurações e Status")

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
                # Cabeçalho da tabela
                st.markdown("<div class='linha-conta header'>...</div>", unsafe_allow_html=True)

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


# ======================
# ========== PÁGINA DE DETALHES ==========
# ======================
if True:
    if st.session_state["page"] == "detalhes":

        conta = st.session_state["conta_selecionada"]
        st.title(f"📊 Detalhes da conta: {conta}")

        # -----------------------------
        # 🔹 Filtro de período
        # -----------------------------
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
                        <div class="card links-card">
                            <h4>🔗 Links da conta</h4>
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


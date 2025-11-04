import pandas as pd, os
from datetime import timedelta

pd.set_option('future.no_silent_downcasting', True)

# ==========================
# 📥 Carregar base dos 65 dias
# ==========================
df = pd.read_csv('ga4_100.csv', sep=';')
df['date'] = pd.to_datetime(df['date'])

# ==========================
# 📅 Definir períodos
# ==========================
fim_atual = df['date'].max()
inicio_atual = fim_atual - timedelta(days=49)
fim_anterior = inicio_atual - timedelta(days=1)
inicio_anterior = fim_anterior - timedelta(days=49)

print(f"Período atual: {inicio_atual.date()} a {fim_atual.date()}")
print(f"Período anterior: {inicio_anterior.date()} a {fim_anterior.date()}")

metrics = ['sessions','transactions','purchaseRevenue','conversion_rate']

# ==========================
# 🔗 Links padrão das contas
# ==========================
link1 = 'https://analytics.google.com/analytics/web/#/p'
link2 = 'reports/reportinghub?params=_u..nav%3Dmaui'
link3 = 'explorer-table.plotKeys=%5B%5D&_r.drilldown=analytics.dateHourHourDay%3A'

# ==========================
# 🔹 Preparar base diária
# ==========================
base_dados = []

for (account, property_id), group in df.groupby(['account_display','property_display']):
    # Dados atuais e anteriores
    df_now = group[(group['date'] >= inicio_atual) & (group['date'] <= fim_atual)].copy()
    df_prev = group[(group['date'] >= inicio_anterior) & (group['date'] <= fim_anterior)].copy()
    
    # Renomeia colunas do mês anterior
    df_prev = df_prev[['date'] + metrics].copy()
    df_prev = df_prev.rename(columns={m: f"{m}_prev" for m in metrics})
    
    # Ordena por data
    df_now = df_now.sort_values('date').reset_index(drop=True)
    df_prev = df_prev.sort_values('date').reset_index(drop=True)
    
    # Concatena lado a lado
    df_combined = pd.concat([df_now, df_prev[[f"{m}_prev" for m in metrics]]], axis=1)
    
    # Adiciona colunas de conta e propriedade
    df_combined['account_display'] = account
    df_combined['property_display'] = property_id
    
    # Seleciona colunas na ordem desejada
    df_combined = df_combined[['date','account_display','property_display'] +
                              metrics +
                              [f"{m}_prev" for m in metrics]]
    
    # Adiciona os links na mesma coluna
    df_combined['links'] = ';'.join([link1, link2, link3])
    
    df_combined = df_combined[['date','account_display','property_display'] +
                              metrics +
                              [f"{m}_prev" for m in metrics] +
                              ['links']]
    
    base_dados.append(df_combined)

# ==========================
# 💾 Concatena todas as propriedades e salva CSV
# ==========================
df_final = pd.concat(base_dados, ignore_index=True)
df_final = df_final.sort_values(['account_display','property_display','date'])

df_final.to_csv('base_comparativa.csv', index=False, sep=';')
print(f"✅ Base tratada salva: {len(df_final)} linhas")

# ==========================
# 🛠️ Atualizar ou criar contas_config.csv
# ==========================
config_path = "contas_config.csv"
contas_existentes = df_final[['account_display','property_display']].drop_duplicates()

# Se o arquivo já existir
if os.path.exists(config_path) and os.path.getsize(config_path) > 0:
    df_conf = pd.read_csv(config_path, sep=';')
    df_conf.columns = df_conf.columns.str.strip()  # remove espaços extras
else:
    # Arquivo inexistente ou vazio
    df_conf = pd.DataFrame(columns=["account_display","property_display","ativa","meta","link"])

# Garante que todas as contas novas estejam no config
for _, row in contas_existentes.iterrows():
    account = row['account_display']
    property_id = row['property_display']
    
    if property_id not in df_conf['property_display'].values:
        df_conf.loc[len(df_conf)] = [account, property_id, True, 100000, ';'.join([link1, link2, link3])]

# Remove duplicados
df_conf = df_conf.drop_duplicates(subset=['property_display'], keep='first')

# Salva novamente
df_conf.to_csv(config_path, index=False, sep=';')
print(f"🧩 Configurações atualizadas: {len(df_conf)} contas em contas_config.csv")

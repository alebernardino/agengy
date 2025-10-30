import pandas as pd
from datetime import timedelta

pd.set_option('future.no_silent_downcasting', True)

# ==========================
# 📥 Carregar base dos 65 dias
# ==========================
df = pd.read_csv('relatorio_analytics_65dias.csv', sep=';')
df['date'] = pd.to_datetime(df['date'])

# ==========================
# 📅 Definir períodos
# ==========================
fim_atual = df['date'].max()
inicio_atual = fim_atual - timedelta(days=29)
fim_anterior = inicio_atual - timedelta(days=1)
inicio_anterior = fim_anterior - timedelta(days=29)

print(f"Período atual: {inicio_atual.date()} a {fim_atual.date()}")
print(f"Período anterior: {inicio_anterior.date()} a {fim_anterior.date()}")

metrics = ['sessions','transactions','purchaseRevenue','conversion_rate']

#==========================
# definição de variaveis das contas
#=========================

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
    
    # Concatena lado a lado, mantendo colunas renomeadas
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

df_final.to_csv('relatorio_analytics_30dias_tratado.csv', index=False, sep=';')
print(f"✅ Base tratada salva: {len(df_final)} linhas")

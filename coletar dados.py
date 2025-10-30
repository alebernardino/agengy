import os
import pandas as pd
from datetime import date, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# ==========================
# ⚙️ Configuração de autenticação
# ==========================
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
CLIENT_SECRETS_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

analytics_data = build('analyticsdata', 'v1beta', credentials=creds)
analytics_admin = build('analyticsadmin', 'v1beta', credentials=creds)
print("✅ Autenticado com sucesso!")

# ==========================
# Listar contas e propriedades
# ==========================
accounts = []
request = analytics_admin.accounts().list()
while request:
    response = request.execute()
    accounts.extend(response.get('accounts', []))
    request = analytics_admin.accounts().list_next(previous_request=request, previous_response=response)

all_properties = []
for acc in accounts:
    account_name = acc['name']
    account_display_name = acc['displayName']
    props_response = analytics_admin.properties().list(filter=f"parent:{account_name}").execute()
    props = props_response.get('properties', [])
    for prop in props:
        all_properties.append({
            'account_display': account_display_name,
            'property_display': prop['displayName'],
            'property_id': prop['name']
        })

# ==========================
# Período de extração: últimos 65 dias
# ==========================
today = date.today()
inicio_total = today - timedelta(days=65)
fim_total = today

# ==========================
# Função para coletar dados diários
# ==========================
def run_ga_daily(property_id, start_date, end_date):
    try:
        response = analytics_data.properties().runReport(
            property=property_id,
            body={
                "dateRanges": [{"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}],
                "dimensions": [{"name": "date"}],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "transactions"},
                    {"name": "purchaseRevenue"}
                ]
            }
        ).execute()

        rows = response.get("rows", [])
        print(f"Propriedade {property_id} - Período {start_date} a {end_date} - Linhas retornadas: {len(rows)}")

        data = []
        for row in rows:
            d = row["dimensionValues"][0]["value"]
            sessions = int(row["metricValues"][0]["value"])
            transactions = int(row["metricValues"][1]["value"])
            revenue = float(row["metricValues"][2]["value"])
            data.append({
                "date": pd.to_datetime(d),
                "sessions": sessions,
                "transactions": transactions,
                "purchaseRevenue": revenue,
                "conversion_rate": (transactions / sessions * 100) if sessions > 0 else 0
            })

        if not data:
            return pd.DataFrame(columns=["date","sessions","transactions","purchaseRevenue","conversion_rate"])
        return pd.DataFrame(data)

    except Exception as e:
        print(f"Erro ao coletar dados para {property_id}: {e}")
        return pd.DataFrame(columns=["date","sessions","transactions","purchaseRevenue","conversion_rate"])

# ==========================
# Coleta de dados
# ==========================
base_dados = []

for idx, prop in enumerate(all_properties, start=1):
    print(f"[{idx}/{len(all_properties)}] Coletando dados da propriedade: {prop['property_display']} - {prop['property_id']}")
    df_total = run_ga_daily(prop['property_id'], inicio_total, fim_total)

    # Adiciona colunas de conta e propriedade
    df_total['account_display'] = prop['account_display']
    df_total['property_display'] = prop['property_display']

    base_dados.append(df_total)

# ==========================
# Concatena e salva CSV
# ==========================
df_final = pd.concat(base_dados, ignore_index=True)
df_final = df_final.sort_values(['account_display','property_display','date'])

df_final.to_csv('relatorio_analytics_65dias.csv', index=False, sep=';')
print(f"✅ Relatório de 65 dias salvo: {len(df_final)} linhas")

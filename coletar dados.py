import os, pandas as pd
from datetime import date
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

CLIENT_SECRETS_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

creds = None

# Se já existir token salvo, carrega
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# Se não houver token ou estiver expirado, faz login
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    # Salva o token para reutilizar
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

# Agora pode usar as APIs sem relogar
analytics_data = build('analyticsdata', 'v1beta', credentials=creds)
# analytics_admin = build('analyticsadmin', 'v1alpha', credentials=creds)
analytics_admin = build('analyticsadmin', 'v1beta', credentials=creds)
print("✅ Autenticado com sucesso!")

# accounts_response = analytics_admin.accounts().list().execute()

accounts = []
request = analytics_admin.accounts().list()
while request is not None:
    response = request.execute()
    accounts.extend(response.get('accounts', []))
    request = analytics_admin.accounts().list_next(previous_request=request, previous_response=response)

all_properties = []

# for i in accounts_response['accounts']:
for i in accounts:
    account_name = i['name']
    account_display_name = i['displayName']
    properties_response = analytics_admin.properties().list(
        filter=f"parent:{account_name}"
    ).execute()

    props = properties_response.get('properties', [])

    for prop in props:
        property_id = prop['name']
        property_display = prop['displayName']
        all_properties.append({
            'account_name': account_name,
            'account_display': account_display_name,
            'property_id': property_id,
            'property_display': property_display
        })

base_dados = []

start_of_month = date.today().replace(day=1).isoformat()
end_of_month = date.today().isoformat()

for i in all_properties:
    response = analytics_data.properties().runReport(
        property=i['property_id'],
        body={
            "dateRanges": [{"startDate": start_of_month, "endDate": end_of_month}],
            "metrics": [
                {"name": "sessions"},
                {"name": "transactions"},
                {"name": "purchaseRevenue"}
            ]
        }
    ).execute()

    if "rows" not in response:
        # print(f"Nenhum dado para {i['property_display']} ({i['property_id']})")
        base_dados.append({
            'account_name': i['account_name'],
            'account_display': i['account_display'],
            'property_id': i['property_id'],
            'property_display': i['property_display'],
            'sessions': 0,
            'transactions': 0,
            'purchaseRevenue': 0.0,
            'conversion_rate': 0.0
        })
        continue

    # Extrai os valores
    sessions = int(response["rows"][0]["metricValues"][0]["value"])
    transactions = int(response["rows"][0]["metricValues"][1]["value"])
    purchaseRevenue = float(response["rows"][0]["metricValues"][2]["value"])

    # Calcula a taxa de conversão (%)
    conversion_rate = (transactions / sessions) * 100 if sessions > 0 else 0
    base_dados.append({
        'account_name': i['account_name'],
        'account_display': i['account_display'],
        'property_id': i['property_id'],
        'property_display': i['property_display'],
        'sessions': sessions,
        'transactions': transactions,
        'purchaseRevenue': purchaseRevenue,
        'conversion_rate': conversion_rate
    })

print(f"Total de propriedades analisadas: {len(base_dados)}")

df = pd.DataFrame(base_dados)
df.to_csv('relatorio_analytics.csv', index=False, sep=';')
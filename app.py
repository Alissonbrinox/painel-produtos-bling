# app.py - Painel online com Streamlit para visualizar produtos do Bling

import requests
import base64
import pandas as pd
import streamlit as st
import time

# =================== CONFIGURAÇÕES ===================
client_id = "9838ab2d65a8f74ab1c780f76980272dd66dcfb9"
client_secret = "a1ffcf45d3078aaffab7d0746dc3513d583a432277e41ca80eff03bf7275"
refresh_token = "4878abd356326ec7b3b114c76391322dab81adb6"
authorization_code = "789f76867d6f6e5f097ef2e3231078381138845c"

# =================== TOKEN ===================
def refresh_access_token(refresh_token):
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

# =================== GERAR NOVO REFRESH TOKEN ===================
def obter_novo_refresh_token(auth_code):
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": "https://localhost"
    }
    response = requests.post(url, headers=headers, data=data)
    if response.ok:
        tokens = response.json()
        novo_token = tokens["refresh_token"]
        st.success("✅ Novo refresh token gerado com sucesso!")
        st.code(novo_token, language='text')
        return novo_token
    else:
        st.error(f"❌ Erro ao obter tokens: {response.status_code} - {response.text}")
        return None

# =================== COLETAR PRODUTOS ===================
def coletar_produtos(access_token):
    url = "https://www.bling.com.br/Api/v3/produtos"
    limit = 100
    params = {
        "page": 1,
        "limit": limit
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 429:
        time.sleep(10)
        response = requests.get(url, headers=headers, params=params)

    response.raise_for_status()
    return response.json().get("data", [])

# =================== MOSTRAR PAINEL ===================
def mostrar_painel(produtos):
    df = pd.json_normalize(produtos)
    df_produtos = df.filter(regex=r"^produto\.")
    df_produtos.columns = [col.replace("produto.", "") for col in df_produtos.columns]

    st.dataframe(df_produtos, use_container_width=True)

# =================== STREAMLIT APP ===================
st.set_page_config(page_title="Painel de Produtos Bling", layout="wide")
st.title("📦 Produtos Cadastrados no Bling")

# Botão para gerar novo refresh token manualmente
with st.expander("🔄 Atualizar Refresh Token (manual)"):
    if st.button("Gerar novo refresh token"):
        obter_novo_refresh_token(authorization_code)

try:
    with st.spinner("🔐 Atualizando token..."):
        access_token = refresh_access_token(refresh_token)
    with st.spinner("📥 Carregando produtos..."):
        produtos = coletar_produtos(access_token)
    mostrar_painel(produtos)
except Exception as e:
    st.error(f"Erro: {e}")

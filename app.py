# app.py - Painel online com Streamlit para visualizar produtos do Bling

import requests
import base64
import pandas as pd
import streamlit as st
import time

# =================== CONFIGURAÇÕES ===================
client_id = "9838ab2d65a8f74ab1c780f76980272dd66dcfb9"
client_secret = "a1ffcf45d3078aaffab7d0746dc3513d583a432277e41ca80eff03bf7275"
refresh_token = "3fb1cde76502690d170d309fab20f48e5c22b71e"

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

try:
    with st.spinner("🔐 Atualizando token..."):
        access_token = refresh_access_token(refresh_token)
    with st.spinner("📥 Carregando produtos..."):
        produtos = coletar_produtos(access_token)
    mostrar_painel(produtos)
except Exception as e:
    st.error(f"Erro: {e}")Q

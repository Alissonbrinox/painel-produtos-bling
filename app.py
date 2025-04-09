# app.py - Painel online com Streamlit para visualizar pedidos do Bling

import requests
import base64
import pandas as pd
import streamlit as st
import time
from datetime import datetime

# =================== CONFIGURAÇÕES ===================
client_id = "9838ab2d65a8f74ab1c780f76980272dd66dcfb9"
client_secret = "a1ffcf45d3078aaffab7d0746dc3513d583a432277e41ca80eff03bf7275"
authorization_code = "a203d52ad157654d6aa5d51f40d4feb87c0b16b4"

if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = "3fb1cde76502690d170d309fab20f48e5c22b71e"

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
    tokens = response.json()
    st.session_state.refresh_token = tokens.get("refresh_token", refresh_token)  # atualiza token, se retornado
    return tokens["access_token"]

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
        st.session_state.refresh_token = novo_token
        st.success("✅ Novo refresh token gerado com sucesso!")
        st.code(novo_token, language='text')
        return novo_token
    else:
        st.error(f"❌ Erro ao obter tokens: {response.status_code} - {response.text}")
        return None

# =================== COLETAR PEDIDOS ===================
def coletar_pedidos(access_token, log_area, data_inicio, data_fim):
    url = "https://www.bling.com.br/Api/v3/pedidos/vendas"
    limit = 100
    pagina = 1
    todos = []
    ids_vistos = set()

    inicio = datetime.now()
    log_area.text(f"⏳ Iniciando busca de pedidos em {inicio.strftime('%H:%M:%S')}...")

    while True:
        params = {
            "page": pagina,
            "limit": limit,
            "dataEmissao[de]": data_inicio,
            "dataEmissao[ate]": data_fim
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 429:
            log_area.text("⚠️ Limite de requisições atingido. Aguardando...")
            time.sleep(10)
            response = requests.get(url, headers=headers, params=params)

        response.raise_for_status()
        json_response = response.json()
        dados = json_response.get("data", [])
        log_area.text(f"📄 Página {pagina} carregada com {len(dados)} pedidos.")

        if not dados:
            break

        novos = [p for p in dados if p['id'] not in ids_vistos]
        todos.extend(novos)
        ids_vistos.update(p['id'] for p in novos)

        pagination = json_response.get("page", {})
        pagina_atual = int(pagination.get("current", pagina))
        ultima_pagina = int(pagination.get("last", pagina))

        if pagina_atual >= ultima_pagina:
            log_area.text(f"✅ Todas as {pagina_atual} páginas carregadas.")
            break

        pagina += 1
        time.sleep(0.5)

    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    log_area.text(f"✅ {len(todos)} pedidos recebidos em {duracao:.2f} segundos.")
    return todos

# =================== RESTANTE DO CÓDIGO PERMANECE INALTERADO ===================

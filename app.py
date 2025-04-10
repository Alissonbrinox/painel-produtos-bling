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
authorization_code = "8bfc2a5f0ce3a9e2864680bca38d21ecb251b501"

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
    st.session_state.refresh_token = tokens.get("refresh_token", refresh_token)
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

# =================== INTERFACE STREAMLIT ===================
st.set_page_config(page_title="Pedidos Bling", layout="wide")
st.title("📄 Pedidos de Venda")

with st.expander("🔄 Atualizar Refresh Token (manual)"):
    if st.button("Gerar novo refresh token"):
        obter_novo_refresh_token(authorization_code)

data_inicio = st.text_input("Data inicial", value="2025/04/01")
data_fim = st.text_input("Data final", value="2025/04/30")

if st.button("📥 Carregar Pedidos do Bling"):
    log_area = st.empty()
    try:
        with st.spinner("🔐 Atualizando token..."):
            access_token = refresh_access_token(st.session_state.refresh_token)
        with st.spinner("📥 Coletando pedidos..."):
            pedidos = coletar_pedidos(access_token, log_area, data_inicio, data_fim)
        if pedidos:
            df = pd.DataFrame([{
                "ID": p.get("id"),
                "Número": p.get("numero"),
                "Data": p.get("data"),
                "Cliente": p.get("cliente", {}).get("nome"),
                "Valor Total": p.get("valorTotal"),
                "Situação": p.get("situacao"),
                "Tipo": p.get("tipo")
            } for p in pedidos])
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar pedidos como CSV", data=csv, file_name="pedidos.csv", mime="text/csv")
        else:
            st.warning("Nenhum pedido encontrado.")
    except Exception as e:
        st.error(f"Erro: {e}")

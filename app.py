# app.py - Painel online com Streamlit para visualizar produtos do Bling

import requests
import base64
import pandas as pd
import streamlit as st
import time
from datetime import datetime
from io import StringIO

# =================== CONFIGURAÇÕES ===================
client_id = "9838ab2d65a8f74ab1c780f76980272dd66dcfb9"
client_secret = "a1ffcf45d3078aaffab7d0746dc3513d583a432277e41ca80eff03bf7275"
st.session_state.refresh_token = st.session_state.get("refresh_token", "3fb1cde76502690d170d309fab20f48e5c22b71e")
authorization_code = "f1f87e220eaa3fa80db9c9a2a35d7c0779b9af5f"

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
        st.session_state.refresh_token = novo_token  # Atualiza token na sessão
        st.success("✅ Novo refresh token gerado com sucesso!")
        st.code(novo_token, language='text')
        return novo_token
    else:
        st.error(f"❌ Erro ao obter tokens: {response.status_code} - {response.text}")
        return None

# =================== COLETAR PRODUTOS ===================
def coletar_produtos(access_token, log_area):
    url = "https://www.bling.com.br/Api/v3/produtos"
    limit = 100
    pagina = 1
    todos = []
    ids_vistos = set()

    inicio = datetime.now()
    log_area.text(f"⏳ Iniciando busca de produtos em {inicio.strftime('%H:%M:%S')}...")

    while True:
        params = {
            "page": pagina,
            "limit": limit
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        log_area.text(f"📡 Carregando página {pagina}...")
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 429:
            log_area.text("⚠️ Limite de requisições atingido. Aguardando...")
            time.sleep(10)
            response = requests.get(url, headers=headers, params=params)

        response.raise_for_status()
        dados = response.json().get("data", [])

        if not dados or pagina > 53:
            break

        novos = [p for p in dados if p['id'] not in ids_vistos]
        ids_duplicados = [p for p in dados if p['id'] in ids_vistos]

        if ids_duplicados:
            log_area.text(f"⚠️ Página {pagina} contém {len(ids_duplicados)} itens duplicados e foram ignorados.")

        todos.extend(novos)
        ids_vistos.update(p['id'] for p in novos)

        pagina += 1
        time.sleep(0.2)

    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    log_area.text(f"✅ {len(todos)} produtos únicos recebidos em {duracao:.2f} segundos.")
    return todos

# =================== MOSTRAR PAINEL ===================
def mostrar_painel(produtos):
    if not produtos:
        st.warning("Nenhum produto retornado.")
        return

    # Constrói DataFrame personalizado
    registros = []
    for p in produtos:
        registros.append({
            "ID": p.get("id"),
            "Nome": p.get("nome"),
            "Código": p.get("codigo"),
            "Preço": p.get("preco"),
            "Custo": p.get("precoCusto"),
            "Estoque Virtual": p.get("estoque", {}).get("saldoVirtualTotal"),
            "Tipo": p.get("tipo"),
            "Situação": p.get("situacao"),
            "Formato": p.get("formato"),
        })

    df = pd.DataFrame(registros)
    st.dataframe(df, use_container_width=True)

    # Adiciona botão para exportar CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📤 Baixar como CSV",
        data=csv,
        file_name=f"produtos_bling_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
        mime="text/csv"
    )

# =================== STREAMLIT APP ===================
st.set_page_config(page_title="Painel de Produtos Bling", layout="wide")
st.title("📦 Produtos Cadastrados no Bling")

# Botão para gerar novo refresh token manualmente
with st.expander("🔄 Atualizar Refresh Token (manual)"):
    if st.button("Gerar novo refresh token"):
        obter_novo_refresh_token(authorization_code)

# Botão para carregar produtos
if st.button("📥 Carregar Produtos do Bling"):
    log_area = st.empty()  # Área de log dinâmica
    try:
        with st.spinner("🔐 Atualizando token..."):
            access_token = refresh_access_token(st.session_state.refresh_token)
        with st.spinner("📥 Coletando produtos..."):
            produtos = coletar_produtos(access_token, log_area)
        mostrar_painel(produtos)
    except Exception as e:
        log_area.text("")
        st.error(f"Erro: {e}")

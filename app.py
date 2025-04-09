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
authorization_code = "52d25090c93f137b3bd2ed3b3dab0f649dc50b30"

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
        log_area.text(f"📄 Página {pagina} carregada com {len(json_response.get('data', []))} pedidos.")
        dados = json_response.get("data", [])

        if not dados:
            break

        novos = [p for p in dados if p['id'] not in ids_vistos]
        todos.extend(novos)
        ids_vistos.update(p['id'] for p in novos)

        pagination = json_response.get("page", {})
        pagina_atual = int(pagination.get("current", 1))
        ultima_pagina = int(pagination.get("last", 1))

        if pagina_atual >= ultima_pagina:
            break

        pagina += 1
        time.sleep(0.5)

    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    log_area.text(f"✅ {len(todos)} pedidos recebidos em {duracao:.2f} segundos.")
    return todos

# =================== MOSTRAR PAINEL ===================
def mostrar_pedidos(pedidos):
    commit_push_automatico("Atualização de pedidos coletados")
    if not pedidos:
        st.warning("Nenhum pedido retornado.")
        return

    registros = []
    for p in pedidos:
        registros.append({
            "ID": p.get("id"),
            "Número": p.get("numero"),
            "Data": p.get("data"),
            "Cliente": p.get("contato", {}).get("nome"),
            "Valor Total": p.get("total"),
            "Situação": p.get("situacao", {}).get("descricao", ""),
            "Tipo": p.get("tipo")
        })

    df = pd.DataFrame(registros)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📤 Baixar pedidos como CSV",
        data=csv,
        file_name=f"pedidos_bling_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
        mime="text/csv"
    )

# =================== GIT PUSH AUTOMÁTICO ===================
import subprocess
import os

def commit_push_automatico(mensagem="Atualização via painel"):
    try:
        subprocess.run(["git", "config", "--global", "user.name", os.environ["GITHUB_USER"]])
        subprocess.run(["git", "config", "--global", "user.email", f"{os.environ['GITHUB_USER']}@users.noreply.github.com"])
        subprocess.run(["git", "add", "app.py"])
        subprocess.run(["git", "commit", "-m", mensagem])
        subprocess.run([
            "git", "push",
            f"https://{os.environ['GITHUB_USER']}:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['GITHUB_USER']}/{os.environ['GITHUB_REPO']}.git",
            "main"
        ])
        st.success("🚀 Código atualizado no GitHub com sucesso!")
    except Exception as e:
        st.warning(f"⚠️ Falha ao enviar para o GitHub: {e}")


# =================== STREAMLIT APP ===================
st.set_page_config(page_title="Painel Bling", layout="wide")
st.title("📊 Painel Bling - Pedidos e Produtos")

aba = st.sidebar.radio("Selecione a aba:", ["Pedidos", "Produtos"])

with st.expander("🔄 Atualizar Refresh Token (manual)"):
    if st.button("Gerar novo refresh token"):
        obter_novo_refresh_token(authorization_code)

if aba == "Pedidos":
    data_inicio = st.date_input("Data inicial", value=datetime(2025, 4, 1))
    data_fim = st.date_input("Data final", value=datetime(2025, 4, 30))
    st.header("📄 Pedidos de Venda")
    if st.button("📥 Carregar Pedidos do Bling"):
        log_area = st.empty()
        try:
            with st.spinner("🔐 Atualizando token..."):
                access_token = refresh_access_token(st.session_state.refresh_token)
            with st.spinner("📥 Coletando pedidos..."):
                pedidos = coletar_pedidos(access_token, log_area, data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d'))
            mostrar_pedidos(pedidos)
        except Exception as e:
            log_area.text("")
            st.error(f"Erro: {e}")  # erro genérico
        # st.warning("❌ Push automático não executado devido a erro anterior.")  # Removido pois não houve erro

elif aba == "Produtos":
    st.header("📦 Produtos Cadastrados")
    if st.button("📥 Carregar Produtos do Bling"):
        log_area = st.empty()
        try:
            with st.spinner("🔐 Atualizando token..."):
                access_token = refresh_access_token(st.session_state.refresh_token)

            url = "https://www.bling.com.br/Api/v3/produtos"
            pagina = 1
            limit = 100
            todos = []
            ids_vistos = set()
            inicio = datetime.now()

            while True:
                params = {"page": pagina, "limit": limit}
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                json_response = response.json()
                dados = json_response.get("data", [])

                novos = [p for p in dados if p['id'] not in ids_vistos]
                todos.extend(novos)
                ids_vistos.update(p['id'] for p in novos)

                pagination = json_response.get("page")
                if not pagination or pagination.get("current") >= pagination.get("last"):
                    break

                pagina += 1
                time.sleep(0.3)

            fim = datetime.now()
            duracao = (fim - inicio).total_seconds()
            log_area.success(f"✅ {len(todos)} produtos recebidos em {duracao:.2f} segundos.")

            registros = []
            for p in todos:
                registros.append({
                    "ID": p.get("id"),
                    "Nome": p.get("nome"),
                    "Código": p.get("codigo"),
                    "Preço": p.get("preco"),
                    "Custo": p.get("precoCusto"),
                    "Estoque Virtual": p.get("estoque", {}).get("saldoVirtualTotal"),
                    "Tipo": p.get("tipo"),
                    "Situação": p.get("situacao"),
                    "Formato": p.get("formato")
                })

            df = pd.DataFrame(registros)
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📤 Baixar produtos como CSV",
                data=csv,
                file_name=f"produtos_bling_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                mime="text/csv"
            )
        except Exception as e:
            log_area.text("")
            st.error(f"Erro: {e}")

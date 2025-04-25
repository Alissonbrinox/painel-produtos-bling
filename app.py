import requests
import base64
import pandas as pd
import streamlit as st
import time
from datetime import datetime
from io import BytesIO
import json

# =================== CONFIGURAÇÕES ===================
client_id = "9838ab2d65a8f74ab1c780f76980272dd66dcfb9"
client_secret = "a1ffcf45d3078aaffab7d0746dc3513d583a432277e41ca80eff03bf7275"
authorization_code = "c11a0f779fd409b7a8c58a7c8cf087b2656032b2"

if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = "3fb1cde76502690d170d309fab20f48e5c22b71e"

if "json_pedidos" not in st.session_state:
    st.session_state["json_pedidos"] = None

# =================== TOKEN ===================
def refresh_access_token(refresh_token):
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {encoded}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    tokens = response.json()
    st.session_state.refresh_token = tokens.get("refresh_token", refresh_token)
    return tokens["access_token"]

# =================== GERAR NOVO REFRESH TOKEN ===================
def obter_novo_refresh_token(code):
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {encoded}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": "https://localhost"}
    response = requests.post(url, headers=headers, data=data)
    if response.ok:
        tokens = response.json()
        novo = tokens["refresh_token"]
        st.session_state.refresh_token = novo
        st.success("✅ Novo refresh token gerado com sucesso!")
        st.code(novo)
        return novo
    else:
        st.error(f"Erro ao obter tokens: {response.status_code} - {response.text}")
        return None

# =================== BUSCAR PEDIDOS POR ID ===================
def buscar_pedidos_por_ids(access_token, ids):
    url_base = "https://www.bling.com.br/Api/v3/pedidos/vendas/"
    headers = {"Authorization": f"Bearer {access_token}"}
    pedidos = []

    for id_pedido in ids:
        url = f"{url_base}{id_pedido}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            dados = response.json().get("data")
            if dados:
                pedidos.append(dados)
        else:
            st.warning(f"Pedido {id_pedido} não encontrado. Código {response.status_code}")

    return pedidos

# =================== EXIBIR PEDIDOS E EXPORTAR ===================
def mostrar_pedidos(pedidos):
    if not pedidos:
        st.warning("Nenhum pedido retornado.")
        return

    registros = []
    for item in pedidos:
        cliente_data = item.get("contato", {})
        situacao_data = item.get("situacao", {})

        registros.append({
            "ID": item.get("id", ""),
            "Número": item.get("numero", ""),
            "Data": item.get("data", ""),
            "Cliente": cliente_data.get("nome", ""),
            "Valor Total": item.get("total", ""),
            "Situação": situacao_data.get("descricao", ""),
            "Tipo": item.get("tipo", "")
        })

    df = pd.DataFrame(registros)
    df["ID"] = df["ID"].astype(str)
    st.dataframe(df, use_container_width=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Pedidos")
    output.seek(0)

    nome_arquivo = f"pedidos_bling_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"

    st.download_button(
        "📅 Baixar pedidos como Excel",
        data=output,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_excel"
    )

    json_str = json.dumps(pedidos, ensure_ascii=False, indent=2)
    st.download_button(
        "📄 Baixar JSON bruto",
        data=json_str,
        file_name="debug_pedidos.json",
        mime="application/json",
        key="download_json"
    )

# =================== STREAMLIT INTERFACE ===================
st.set_page_config("Pedidos Bling", layout="wide")
st.title("📄 Pedidos de Venda por ID")

with st.expander("🔐 Atualizar Refresh Token"):
    if st.button("Gerar novo refresh token"):
        obter_novo_refresh_token(authorization_code)

# Campo para entrada dos IDs dos pedidos
ids_texto = st.text_input("IDs dos pedidos separados por vírgula", "6426,6425,6381")

if st.button("🔍 Buscar pedidos por ID"):
    try:
        ids_list = [int(x.strip()) for x in ids_texto.split(",") if x.strip().isdigit()]
        token = refresh_access_token(st.session_state.refresh_token)
        pedidos = buscar_pedidos_por_ids(token, ids_list)
        st.session_state["json_pedidos"] = pedidos
        mostrar_pedidos(pedidos)
    except Exception as e:
        st.error(f"Erro ao buscar pedidos: {e}")

# Se já houver pedidos armazenados
if st.session_state.get("json_pedidos"):
    mostrar_pedidos(st.session_state["json_pedidos"])

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
authorization_code = "817ecb2a79fbd3829c5a65f75f6a0c81ce414de2"

if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = "3fb1cde76502690d170d309fab20f48e5c22b71e"

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

# =================== COLETAR PEDIDOS (com paginação) ===================
def coletar_pedidos(access_token, data_inicio, data_fim, log_area):
    url = "https://www.bling.com.br/Api/v3/pedidos/vendas"
    headers = {"Authorization": f"Bearer {access_token}"}
    pagina = 1
    todos_pedidos = []

    log_area.text("Iniciando coleta de pedidos...")

    while True:
        params = {
            "page": pagina,
            "limit": 100,
            "dataEmissao[de]": data_inicio,
            "dataEmissao[ate]": data_fim
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 429:
            time.sleep(5)
            continue

        response.raise_for_status()
        resultado = response.json()
        pedidos = resultado.get("data", [])

        if not pedidos:
            break

        for pedido in pedidos:
            todos_pedidos.append(pedido)

        log_area.text(f"Página {pagina}: {len(pedidos)} pedidos coletados.")

        atual = resultado.get("page", {}).get("current", pagina)
        total = resultado.get("page", {}).get("last", pagina)
        if atual >= total:
            break

        pagina += 1
        time.sleep(0.5)

    with open("debug_pedidos.json", "w", encoding="utf-8") as f:
        json.dump(todos_pedidos, f, ensure_ascii=False, indent=2)

    log_area.success(f"{len(todos_pedidos)} pedidos recebidos com sucesso!")
    return todos_pedidos

# =================== EXIBIR PEDIDOS ===================
def mostrar_pedidos(pedidos):
    if not pedidos:
        st.warning("Nenhum pedido retornado.")
        return

    registros = []
    for item in pedidos:
        p = item.get("pedido", {})
        cliente = p.get("cliente", {})
        registros.append({
            "ID": item.get("id", ""),
            "Número": p.get("numero", ""),
            "Data": p.get("data", ""),
            "Cliente": cliente.get("nome", ""),
            "Valor Total": p.get("valor", ""),
            "Situação": str(p.get("situacao", {})),
            "Tipo": p.get("tipo", "")
        })

    df = pd.DataFrame(registros)
    st.dataframe(df, use_container_width=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Pedidos")
    output.seek(0)

    nome_arquivo = f"pedidos_bling_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
    st.download_button(
        "📥 Baixar pedidos como Excel",
        data=output,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    with open("debug_pedidos.json", "rb") as f:
        st.download_button("📤 Baixar JSON bruto", f, "debug_pedidos.json", mime="application/json")

# =================== STREAMLIT ===================
st.set_page_config("Pedidos Bling", layout="wide")
st.title("📄 Pedidos de Venda")

with st.expander("🔐 Atualizar Refresh Token"):
    if st.button("Gerar novo refresh token"):
        obter_novo_refresh_token(authorization_code)

data_inicio = st.text_input("Data inicial", "2025/04/01")
data_fim = st.text_input("Data final", "2025/04/30")

log = st.empty()

if st.button("📥 Carregar Pedidos do Bling"):
    try:
        token = refresh_access_token(st.session_state.refresh_token)
        pedidos = coletar_pedidos(token, data_inicio, data_fim, log)
        mostrar_pedidos(pedidos)
    except Exception as e:
        st.error(f"Erro ao coletar pedidos: {e}")

        novos = [p for p in pedidos if p['id'] not in ids_vistos]
        todos_pedidos.extend(novos)
        ids_vistos.update(p['id'] for p in novos)
        pagina += 1
        log_area.text(f"Página {pagina}: {len(pedidos)} pedidos coletados.")
        time.sleep(0.5)

    st.session_state["json_pedidos"] = todos_pedidos
    log_area.success(f"{len(todos_pedidos)} pedidos recebidos com sucesso!")
    return todos_pedidos

# =================== EXIBIR PEDIDOS ===================
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
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    json_str = json.dumps(st.session_state["json_pedidos"], ensure_ascii=False, indent=2)
    st.download_button(
        "📄 Baixar JSON bruto",
        data=json_str,
        file_name="debug_pedidos.json",
        mime="application/json",
        key="download_json"
    )

# =================== STREAMLIT ===================
st.set_page_config("Pedidos Bling", layout="wide")
st.title("📄 Pedidos de Venda")

with st.expander("🔐 Atualizar Refresh Token"):
    if st.button("Gerar novo refresh token"):in
        obter_novo_refresh_token(authorization_code)

data_inicio = st.text_input("Data inicial", "2025/04/01")
data_fim = st.text_input("Data final", "2025/04/30")

log = st.empty()

if st.button("📅 Carregar Pedidos do Bling"):
    try:
        token = refresh_access_token(st.session_state.refresh_token)
        pedidos = coletar_pedidos(token, data_inicio, data_fim, log)
        mostrar_pedidos(pedidos)
    except Exception as e:
        st.error(f"Erro ao coletar pedidos: {e}")

if st.session_state.get("json_pedidos"):
    mostrar_pedidos(st.session_state["json_pedidos"])

import os
import socket
import datetime
from typing import Any, Dict, List, Tuple, Optional

import httpx
import streamlit as st

# =========================
# Configuração da página
# =========================
st.set_page_config(
    page_title="IViagem – Planejamento Inteligente",
    page_icon="🌍",
    layout="wide"
)
st.title("🌍 IViagem – Planejamento Inteligente")

# =========================
# Utilidades
# =========================
def brl(valor: Optional[float]) -> str:
    """Formata número como BRL (pt-BR) sem depender de locale/babel."""
    try:
        if valor is None:
            valor = 0.0
        s = f"{float(valor):,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return "R$ 0,00"

def check_tcp(host: str, port: int, timeout: float = 2.0) -> Tuple[bool, str]:
    """Testa se há alguém escutando em host:port (útil para WinError 10061)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except Exception as e:
        return False, str(e)

def safe_get(d: Dict, key: str, default: Any):
    """Leitura segura de d[key] com default."""
    try:
        v = d.get(key, default)
        return default if v is None else v
    except Exception:
        return default

def to_list_of_dicts(x: Any) -> List[Dict[str, Any]]:
    """Garante estrutura em lista de dicts para exibição em tabela."""
    if x is None:
        return []
    if isinstance(x, list):
        if all(isinstance(i, dict) for i in x):
            return x
        return [{"item": str(i)} for i in x]
    if isinstance(x, dict):
        return [x]
    return [{"valor": str(x)}]

def parse_url_host_port(url: str) -> Tuple[str, int]:
    """Extrai host/porta de uma URL http(s) simples."""
    try:
        if "://" in url:
            _, rest = url.split("://", 1)
        else:
            rest = url
        host_port = rest.split("/")[0]
        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 443 if url.startswith("https") else 80
        return host, port
    except Exception:
        return "127.0.0.1", 8000

def post_with_retries(url: str, json: Dict[str, Any], timeout: float = 60.0, retries: int = 2) -> httpx.Response:
    """POST com pequenas tentativas extras em caso de erro transitório."""
    last_exc = None
    for _ in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(url, json=json)
                res.raise_for_status()
                return res
        except Exception as e:
            last_exc = e
    raise last_exc

# =========================
# Config API (sidebar)
# =========================
DEFAULT_API_URL = "http://127.0.0.1:8000/plan"
env_api_url = os.getenv("IVIAGEM_API_URL", "").strip()
API_URL = env_api_url if env_api_url else DEFAULT_API_URL

with st.sidebar:
    st.subheader("⚙️ Configurações")
    api_url_input = st.text_input("API URL", value=API_URL, help="Ex.: http://127.0.0.1:8000/plan")
    if api_url_input.strip():
        API_URL = api_url_input.strip()

    # Diagnóstico de conectividade até host/porta
    host, port = parse_url_host_port(API_URL)
    ok, err = check_tcp(host, port)
    st.caption("Diagnóstico de Conexão")
    st.write(f"• Endpoint: `{API_URL}`")
    st.write(f"• TCP {host}:{port}: **{'OK' if ok else 'FALHOU'}**")
    if not ok:
        st.code(f"{err}")

    st.markdown("---")
    st.caption("Dicas se falhar:")
    st.markdown(
        "- Garanta que seu backend esteja **escutando** nessa porta/host.\n"
        "- Se o backend for FastAPI: `uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload`.\n"
        "- Se usar outra porta, ajuste ali em cima.\n"
        "- Cheque antivírus/firewall/VPN/proxy."
    )

# =========================
# Formulário
# =========================
with st.form(key="travel_form"):
    col1, col2 = st.columns(2)
    from_city = col1.text_input("Cidade de origem:", value="São Paulo")
    destination_city = col2.text_input("Cidade de destino:", value="Manaus")

    col3, col4 = st.columns(2)
    date_from = col3.date_input("Data de partida:", value=datetime.date.today())
    date_to = col4.date_input("Data de retorno:", value=datetime.date.today() + datetime.timedelta(days=7))

    interests = st.text_area("Interesses e preferências:", value="cultura, gastronomia, natureza")
    col5, col6 = st.columns(2)
    numero_viajantes = col5.number_input("Nº de viajantes:", min_value=1, value=1)
    perfil = col6.selectbox("Perfil:", ["econômico", "equilibrado", "premium"], index=1)

    col7, col8 = st.columns(2)
    teto_orcamento = col7.number_input("Teto de orçamento (opcional):", min_value=0.0, value=0.0, help="0 = sem teto")
    moeda = col8.text_input("Moeda:", value="BRL")

    submitted = st.form_submit_button("Gerar roteiro 🚀")

# =========================
# Envio para a API
# =========================
if submitted:
    if not from_city or not destination_city:
        st.error("Informe **origem** e **destino**.")
        st.stop()
    if date_to < date_from:
        st.error("A data de retorno não pode ser **anterior** à data de partida.")
        st.stop()

    payload = {
        "cidade_origem": from_city,
        "destino": destination_city,
        "data_inicio": str(date_from),
        "data_fim": str(date_to),
        "temas": [s.strip() for s in interests.split(",") if s.strip()],
        "numero_viajantes": int(numero_viajantes),
        "perfil": perfil,
        "teto_orcamento": float(teto_orcamento),
        "moeda": moeda
    }

    with st.spinner("Planejando viagem..."):
        try:
            res = post_with_retries(API_URL, json=payload, timeout=60, retries=1)
            plan = res.json()
        except Exception as e:
            st.error(f"Erro na API: {e}")
            st.info("Verifique se o backend está rodando nesse endereço/porta e tente novamente.")
            st.stop()

    # =========================
    # Renderização dos resultados
    # =========================
    total_estimado = safe_get(plan, "orcamento_estimado_total", 0.0)
    periodo_ajustado = safe_get(plan, "periodo_ajustado", None)

    st.header("Sumário Executivo")
    colA, colB = st.columns([2,1])
    with colA:
        st.markdown(
            f"**Origem:** {from_city}  \n"
            f"**Destino:** {destination_city}  \n"
            f"**Período solicitado:** {date_from} a {date_to}  \n"
            f"**Perfil:** {perfil.capitalize()}  \n"
            f"**Nº Viajantes:** {numero_viajantes}  \n"
            f"**Total Estimado:** {brl(total_estimado)}"
        )
    with colB:
        if periodo_ajustado:
            st.success(f"Período ajustado: {periodo_ajustado.get('data_inicio')} → {periodo_ajustado.get('data_fim')}")
        teto_util = safe_get(plan, "teto_orcamento_utilizado", None)
        if teto_util:
            st.metric("Teto de orçamento", brl(teto_util))
        economia_prevista = safe_get(plan, "economia_vs_base", None)
        if economia_prevista is not None:
            st.metric("Saldo vs. teto", brl(economia_prevista))

    ajustes = safe_get(plan, "ajustes_aplicados", [])
    if ajustes:
        with st.expander("Ajustes aplicados para caber no orçamento"):
            for a in ajustes:
                st.markdown(f"- {a}")

    sugestoes = safe_get(plan, "sugestoes", [])
    if sugestoes:
        st.warning("Sugestões para fechar a conta:")
        for s in sugestoes:
            st.markdown(f"- {s}")

    observacoes = safe_get(plan, "observacoes_gerais", "")
    if observacoes:
        st.info(observacoes)

    st.subheader("Logística")
    legs = to_list_of_dicts(safe_get(plan, "legs", []))
    if legs:
        st.dataframe(legs, use_container_width=True, height=240)
    else:
        st.warning("Não foi possível encontrar rotas de transporte.")

    st.subheader("Orçamento Detalhado")
    custos_itens = to_list_of_dicts(safe_get(plan, "custos_itens", []))
    if custos_itens:
        for row in custos_itens:
            for k in list(row.keys()):
                if "custo" in k.lower() or "preco" in k.lower() or "valor" in k.lower():
                    try:
                        row[k] = brl(float(row[k]))
                    except Exception:
                        pass
        st.dataframe(custos_itens, use_container_width=True, height=320)
    else:
        st.caption("Sem itens detalhados de orçamento.")

    st.subheader("Itinerário (Dia a Dia)")
    roteiro = safe_get(plan, "roteiro", [])
    if roteiro and isinstance(roteiro, list):
        for dia in roteiro:
            data_label = safe_get(dia, "data", "")
            custo_dia = safe_get(dia, "custo_estimado_dia", 0.0)
            manha = safe_get(dia, "manha", "---")
            tarde = safe_get(dia, "tarde", "---")
            noite = safe_get(dia, "noite", "---")
            narrativa = safe_get(dia, "narrativa", "")

            st.markdown(f"**{data_label or 'Dia'}** — Custo do dia: {brl(custo_dia)}")
            st.markdown(f"- **Manhã:** {manha}")
            st.markdown(f"- **Tarde:** {tarde}")
            st.markdown(f"- **Noite:** {noite}")
            if narrativa:
                st.info(narrativa)
            st.divider()
    else:
        st.warning("Roteiro detalhado não disponível.")

    colx, coly, colz = st.columns(3)
    with colx:
        tempo_voo_total = safe_get(plan, "tempo_voo_total", None)
        if tempo_voo_total:
            st.metric("Tempo total de voo/deslocamento", str(tempo_voo_total))
    with coly:
        risco_climatico = safe_get(plan, "risco_climatico", None)
        if risco_climatico:
            st.metric("Risco climático", risco_climatico)
    with colz:
        st.empty()

    with st.expander("Ver plano JSON completo"):
        st.json(plan)

st.caption("IViagem • v2 – Frontend Streamlit para o endpoint /plan")

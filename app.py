"""ProjectFlow AI: dashboard gerencial (dados demo ou Supabase)."""
from datetime import date
import hmac
import streamlit as st
from farol import calcular_farol

st.set_page_config(page_title="ProjectFlow AI", page_icon="📊", layout="wide")
st.title("📊 ProjectFlow AI")
st.caption("Gestão inteligente de projetos • Visão executiva")

def configuracao_disponivel():
    return all(k in st.secrets for k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "APP_PASSWORD"))

def dados_demo():
    return [
        {"nome": "Implantação ERP", "responsavel": "Ana Souza", "prazo": "2026-11-30", "pendencias": 1, "status": "em_andamento"},
        {"nome": "Dashboard Executivo", "responsavel": "Bruno Lima", "prazo": "2026-11-15", "pendencias": 0, "status": "em_andamento"},
        {"nome": "Integração de APIs", "responsavel": "Carla Mendes", "prazo": "2026-10-10", "pendencias": 1, "status": "em_andamento"},
        {"nome": "Automação de Processos", "responsavel": "Diego Costa", "prazo": "2026-10-15", "pendencias": 0, "status": "em_andamento"},
    ]

def buscar_projetos():
    # Consultas REST evitam conflitos entre versões do SDK Python do Supabase.
    # A chave secreta permanece somente no servidor do Streamlit.
    import requests
    base = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1"
    headers = {"apikey": str(st.secrets["SUPABASE_SECRET_KEY"])}
    resposta_projetos = requests.get(
        base + "/projetos",
        headers=headers,
        params={"select": "id,nome,responsavel,prazo,status"},
        timeout=15,
    )
    resposta_projetos.raise_for_status()
    projetos = resposta_projetos.json()
    resposta_pendencias = requests.get(
        base + "/pendencias",
        headers=headers,
        params={"select": "projeto_id", "status": "eq.aberta"},
        timeout=15,
    )
    resposta_pendencias.raise_for_status()
    pendencias = resposta_pendencias.json()
    contagem = {}
    for item in pendencias:
        contagem[item["projeto_id"]] = contagem.get(item["projeto_id"], 0) + 1
    for projeto in projetos:
        projeto["pendencias"] = contagem.get(projeto["id"], 0)
    return projetos

if configuracao_disponivel():
    if not st.session_state.get("autorizado", False):
        with st.form("login"):
            senha = st.text_input("Senha de acesso ao painel", type="password")
            entrar = st.form_submit_button("Entrar")
        if entrar:
            st.session_state["autorizado"] = hmac.compare_digest(senha, str(st.secrets["APP_PASSWORD"]))
            if st.session_state["autorizado"]:
                st.rerun()
            st.error("Senha incorreta.")
        st.stop()
    try:
        projetos = buscar_projetos()
        st.success("Conectado ao Supabase")
    except Exception as erro:
        tipo_erro = type(erro).__name__
        if isinstance(erro, ModuleNotFoundError):
            # O nome do módulo ausente não contém credenciais.
            modulo = erro.name or "desconhecido"
            print(f"ProjectFlow AI: módulo ausente: {modulo}")
            st.error("Não foi possível consultar o Supabase.")
            st.info(f"Tipo do erro: {tipo_erro} | Módulo ausente: {modulo}")
        else:
            print(f"ProjectFlow AI: falha de consulta ({tipo_erro})")
            st.error("Não foi possível consultar o Supabase.")
            st.info(f"Tipo do erro: {tipo_erro}")
        st.stop()
else:
    projetos = dados_demo()
    st.info("Modo demonstração: configure os segredos no Streamlit Cloud para usar o Supabase.")

for p in projetos:
    p["farol"] = calcular_farol(date.fromisoformat(str(p["prazo"])), p["pendencias"], p["status"])

with st.sidebar:
    st.header("Navegação")
    st.write("📊 Dashboard")
    filtro = st.selectbox("Farol", ["Todos", "Verde", "Amarelo", "Vermelho"])
    if configuracao_disponivel() and st.button("Sair"):
        st.session_state["autorizado"] = False
        st.rerun()

a, b, c, d = st.columns(4)
a.metric("Projetos", len(projetos))
b.metric("🟢 Em dia", sum(p["farol"] == "verde" for p in projetos))
c.metric("🟡 Atenção", sum(p["farol"] == "amarelo" for p in projetos))
d.metric("🔴 Atrasados", sum(p["farol"] == "vermelho" for p in projetos))

st.subheader("Farol dos projetos")
icones = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴"}
filtrados = [p for p in projetos if filtro == "Todos" or p["farol"] == filtro.lower()]
for p in filtrados:
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 2])
        col1.markdown(f"**{p['nome']}**")
        col1.caption(f"Responsável: {p['responsavel'] or 'Não definido'}")
        col2.write(f"Prazo: {date.fromisoformat(str(p['prazo'])).strftime('%d/%m/%Y')}")
        col2.write(f"Pendências abertas: {p['pendencias']}")
        col3.markdown(f"### {icones[p['farol']]} {p['farol'].capitalize()}")


st.divider()
st.subheader("🔎 Detalhamento do projeto")
if not filtrados:
    st.info("Nenhum projeto corresponde ao filtro selecionado.")
else:
    escolhido = st.selectbox("Selecione um projeto", [p["nome"] for p in filtrados])
    projeto = next(p for p in filtrados if p["nome"] == escolhido)
    st.markdown(f"### {icones[projeto['farol']]} {projeto['nome']}")
    x, y, z = st.columns(3)
    x.metric("Farol", projeto["farol"].capitalize())
    y.metric("Pendências abertas", projeto["pendencias"])
    z.metric("Prazo", date.fromisoformat(str(projeto["prazo"])).strftime("%d/%m/%Y"))
    st.write(f"**Responsável:** {projeto['responsavel'] or 'Não definido'}")
    st.write(f"**Status:** {projeto['status'].replace('_', ' ').capitalize()}")

    if configuracao_disponivel():
        import requests

        def buscar_registros(tabela, campos, identificador):
            base = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1"
            resposta = requests.get(
                f"{base}/{tabela}",
                headers={"apikey": str(st.secrets["SUPABASE_SECRET_KEY"])},
                params={"select": campos, "projeto_id": f"eq.{identificador}", "order": "id.desc"},
                timeout=15,
            )
            resposta.raise_for_status()
            return resposta.json()

        abas = st.tabs(["📋 Pendências", "🚧 Gargalos", "📝 Atas", "🕓 Histórico"])
        configuracoes = [
            ("pendencias", "descricao,responsavel,prazo,status,origem,id"),
            ("gargalos", "descricao,impacto,status,id"),
            ("atas", "titulo,data_reuniao,resumo,decisoes,id"),
            ("historico", "descricao,origem,criado_em,id"),
        ]
        for aba, (tabela, campos) in zip(abas, configuracoes):
            with aba:
                try:
                    registros = buscar_registros(tabela, campos, projeto["id"])
                    if registros:
                        for registro in registros:
                            registro.pop("id", None)
                        st.dataframe(registros, use_container_width=True, hide_index=True)
                    else:
                        st.info("Ainda não há registros nesta seção.")
                except requests.RequestException:
                    st.warning("Não foi possível carregar esta seção. Tente novamente.")
    else:
        st.info("Detalhes de pendências, gargalos, atas e histórico estarão disponíveis após conectar o Supabase.")

st.caption("ProjectFlow AI • Gestão de projetos integrada ao Supabase")


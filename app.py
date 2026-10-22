"""ProjectFlow AI — painel executivo com navegação entre páginas."""
from datetime import date
import hmac
import html

import altair as alt
import pandas as pd
import requests
import streamlit as st

from farol import calcular_farol

st.set_page_config(page_title="ProjectFlow AI", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1240px; padding-top: 2rem;}
[data-testid="stSidebar"] {background: #111c31;}
[data-testid="stSidebar"] * {color: #eef3fa !important;}
.project-card {padding: 1.25rem 1.3rem; border-radius: 16px; background: #fff;
  border: 1px solid #e5eaf2; box-shadow: 0 5px 20px rgba(22,34,55,.05);
  min-height: 170px; margin-bottom: .5rem;}
.project-card h3 {margin: .65rem 0 .5rem; font-size: 1.2rem; color: #152238;}
.project-card p {margin: .25rem 0; color: #56647a;}
.pill {display: inline-block; padding: .28rem .7rem; border-radius: 999px;
  font-size: .8rem; font-weight: 700;}
.green {background:#e5f7ed; color:#12663b;}
.yellow {background:#fff3d6; color:#956300;}
.red {background:#ffe6e6; color:#a92c36;}
.subtitle {color: #64748b; margin-top: -.5rem;}
</style>
""", unsafe_allow_html=True)

CORES = {"verde": "#1d9b64", "amarelo": "#e3a324", "vermelho": "#dc4b56"}
ROTULOS = {"verde": "Em dia", "amarelo": "Atenção", "vermelho": "Atrasado"}
CLASSES_FAROL = {"verde": "green", "amarelo": "yellow", "vermelho": "red"}

def configurado():
    return all(k in st.secrets for k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "APP_PASSWORD"))

def consultar(tabela, campos, filtros=None):
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1/" + tabela
    params = {"select": campos}
    params.update(filtros or {})
    resposta = requests.get(
        url, headers={"apikey": str(st.secrets["SUPABASE_SECRET_KEY"])},
        params=params, timeout=15,
    )
    resposta.raise_for_status()
    return resposta.json()

def dados_demo():
    return [
        {"id": 1, "nome": "Implantação ERP", "responsavel": "Ana Souza",
         "inicio": "2026-10-01", "prazo": "2026-11-30", "status": "em_andamento", "pendencias": 1},
        {"id": 2, "nome": "Dashboard Executivo", "responsavel": "Bruno Lima",
         "inicio": "2026-10-05", "prazo": "2026-11-15", "status": "em_andamento", "pendencias": 0},
        {"id": 3, "nome": "Integração de APIs", "responsavel": "Carla Mendes",
         "inicio": "2026-09-01", "prazo": "2026-10-10", "status": "em_andamento", "pendencias": 1},
        {"id": 4, "nome": "Automação de Processos", "responsavel": "Diego Costa",
         "inicio": "2026-09-10", "prazo": "2026-10-15", "status": "em_andamento", "pendencias": 0},
    ]

def carregar_projetos():
    if not configurado():
        return dados_demo()
    projetos = consultar("projetos", "id,nome,responsavel,inicio,prazo,status")
    abertas = consultar("pendencias", "projeto_id", {"status": "eq.aberta"})
    contagem = {}
    for item in abertas:
        pid = item["projeto_id"]
        contagem[pid] = contagem.get(pid, 0) + 1
    for projeto in projetos:
        projeto["pendencias"] = contagem.get(projeto["id"], 0)
    return projetos

def preparar(projetos):
    for p in projetos:
        p["farol"] = calcular_farol(
            date.fromisoformat(str(p["prazo"])), p["pendencias"], p["status"]
        )
    return projetos

def dias_restantes(p):
    return (date.fromisoformat(str(p["prazo"])) - date.today()).days

def formatar_data(valor):
    return date.fromisoformat(str(valor)).strftime("%d/%m/%Y") if valor else "—"

def pagina_dashboard():
    st.title("Visão executiva")
    st.markdown('<p class="subtitle">Portfólio de projetos • Indicadores e entregas</p>', unsafe_allow_html=True)
    if not configurado():
        st.info("Ambiente de demonstração — dados fictícios.")
    filtro = st.selectbox("Situação", ["Todos", "Em dia", "Atenção", "Atrasado"])
    total = len(projetos)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Projetos", total)
    k2.metric("Em dia", sum(p["farol"] == "verde" for p in projetos))
    k3.metric("Em atenção", sum(p["farol"] == "amarelo" for p in projetos))
    k4.metric("Atrasados", sum(p["farol"] == "vermelho" for p in projetos))

    st.subheader("Projetos")
    filtrados = [p for p in projetos if filtro == "Todos" or ROTULOS[p["farol"]] == filtro]
    if not filtrados:
        st.info("Nenhum projeto para este filtro.")
    for i in range(0, len(filtrados), 2):
        colunas = st.columns(2, gap="large")
        for coluna, p in zip(colunas, filtrados[i:i + 2]):
            with coluna:
                situacao = p["farol"]
                nome = html.escape(str(p["nome"]))
                responsavel = html.escape(str(p.get("responsavel") or "Não definido"))
                st.markdown(
                    f'<div class="project-card" style="border-top: 5px solid {CORES[situacao]}">'
                    f'<span class="pill {CLASSES_FAROL[situacao]}">'
                    f'{ROTULOS[situacao]}</span><h3>{nome}</h3>'
                    f'<p>Responsável: {responsavel}</p>'
                    f'<p>Entrega: {formatar_data(p["prazo"])} · Pendências: {p["pendencias"]}</p>'
                    f'</div>', unsafe_allow_html=True
                )
                if st.button("Ver detalhes →", key=f"abrir_{p['id']}", use_container_width=True):
                    st.session_state["projeto_id"] = p["id"]
                    st.switch_page(pagina_detalhe)

    st.subheader("Cronograma de entregas")
    if projetos:
        linhas = []
        for p in projetos:
            if p.get("inicio") and p.get("prazo"):
                linhas.append({
                    "Projeto": p["nome"],
                    "Início": pd.to_datetime(p["inicio"]),
                    "Prazo": pd.to_datetime(p["prazo"]),
                    "Situação": ROTULOS[p["farol"]],
                })
        if linhas:
            df = pd.DataFrame(linhas)
            barras = alt.Chart(df).mark_bar(cornerRadius=5, size=20).encode(
                y=alt.Y("Projeto:N", sort=None, title=None),
                x=alt.X("Início:T", title="Calendário"),
                x2="Prazo:T",
                color=alt.Color("Situação:N", scale=alt.Scale(
                    domain=["Em dia", "Atenção", "Atrasado"],
                    range=[CORES["verde"], CORES["amarelo"], CORES["vermelho"]]
                ), legend=alt.Legend(orient="bottom")),
                tooltip=["Projeto:N", "Início:T", "Prazo:T", "Situação:N"],
            )
            hoje = alt.Chart(pd.DataFrame({"hoje": [pd.Timestamp(date.today())]})).mark_rule(
                color="#26344c", strokeDash=[5, 4], strokeWidth=2
            ).encode(x="hoje:T")
            st.altair_chart((barras + hoje).properties(height=max(180, len(df) * 52)),
                            use_container_width=True)
            st.caption("Cada barra representa o período planejado. A linha tracejada marca a data de hoje.")

    st.subheader("Próximos deadlines")
    for p in sorted(projetos, key=lambda item: item["prazo"]):
        dias = dias_restantes(p)
        texto = f"Vencido há {abs(dias)} dia(s)" if dias < 0 else (
            "Vence hoje" if dias == 0 else f"Faltam {dias} dia(s)"
        )
        st.markdown(f"**{html.escape(str(p['nome']))}** — {formatar_data(p['prazo'])} · {texto}")

def pagina_detalhes():
    pid = st.session_state.get("projeto_id")
    projeto = next((p for p in projetos if p["id"] == pid), None)
    if st.button("← Voltar ao dashboard"):
        st.switch_page(pagina_principal)
    if not projeto:
        st.info("Selecione um projeto na página Visão executiva.")
        return
    st.title(projeto["nome"])
    st.markdown(f'<span class="pill {CLASSES_FAROL[projeto["farol"]]}">'
                f'{ROTULOS[projeto["farol"]]}</span>', unsafe_allow_html=True)
    st.write(f"**Responsável:** {projeto.get('responsavel') or 'Não definido'}")
    a, b, c = st.columns(3)
    a.metric("Início", formatar_data(projeto.get("inicio")))
    b.metric("Deadline", formatar_data(projeto["prazo"]))
    c.metric("Pendências abertas", projeto["pendencias"])

    st.subheader("Linha do tempo")
    inicio = date.fromisoformat(str(projeto.get("inicio") or projeto["prazo"]))
    prazo = date.fromisoformat(str(projeto["prazo"]))
    duracao = max(1, (prazo - inicio).days)
    decorrido = (date.today() - inicio).days
    percentual = max(0, min(100, round(decorrido / duracao * 100)))
    st.progress(percentual / 100, text=f"{percentual}% do prazo planejado transcorrido")
    st.caption(f"Início: {formatar_data(inicio)}  →  Hoje: {date.today().strftime('%d/%m/%Y')}  →  Entrega: {formatar_data(prazo)}")
    st.caption("O indicador mostra o tempo transcorrido, não o percentual real de execução.")

    st.subheader("Acompanhamento")
    abas = st.tabs(["Pendências", "Gargalos", "Atas de reunião", "Histórico"])
    tabelas = [
        ("pendencias", "descricao,responsavel,prazo,status,origem,id"),
        ("gargalos", "descricao,impacto,status,id"),
        ("atas", "titulo,data_reuniao,resumo,decisoes,id"),
        ("historico", "descricao,origem,criado_em,id"),
    ]
    for aba, (tabela, campos) in zip(abas, tabelas):
        with aba:
            if not configurado():
                st.info("Disponível quando conectado ao Supabase.")
                continue
            try:
                registros = consultar(tabela, campos, {
                    "projeto_id": f"eq.{projeto['id']}", "order": "id.desc"
                })
                if registros:
                    for registro in registros:
                        registro.pop("id", None)
                    st.dataframe(registros, hide_index=True, use_container_width=True)
                else:
                    st.info("Nenhum registro cadastrado nesta seção.")
            except requests.RequestException:
                st.warning("Não foi possível carregar esta seção.")

def pagina_atas_ia():
    from atas_github import atas_do_projeto, extrair_trechos, consolidar_atas

    st.title("🤖 Inteligência das atas")
    st.caption("Leitura automática da pasta centralizada de atas fictícias no GitHub")
    st.info("Protótipo com extração baseada em regras. A interpretação por IA virá depois.")
    if not projetos:
        st.warning("Não há projetos cadastrados.")
        return
    nome = st.selectbox("Selecione o projeto", [p["nome"] for p in projetos])
    if st.button("Buscar atas do projeto", type="primary"):
        with st.spinner("Consultando pasta de atas no GitHub..."):
            try:
                st.session_state["atas_encontradas"] = {
                    "projeto": nome,
                    "atas": atas_do_projeto(nome),
                }
            except requests.RequestException:
                st.error("Não foi possível consultar a pasta no GitHub. Tente novamente.")
                return
    resultado = st.session_state.get("atas_encontradas", {})
    if resultado.get("projeto") != nome:
        st.info("Clique em 'Buscar atas do projeto' para consultar os documentos.")
        return
    atas = resultado.get("atas", [])
    st.metric("Atas encontradas", len(atas))
    if not atas:
        st.info("Nenhuma ata identificada para este projeto.")
        return
    consolidado = consolidar_atas(atas)
    st.subheader("Resumo consolidado do projeto")
    st.caption("Reúne evidências de todas as atas, em ordem cronológica. "
               "Não usa modelo de IA e não confirma automaticamente o status das tarefas.")
    st.write(f"**Última reunião identificada:** {consolidado['ultima_reuniao']}")
    for categoria, itens in consolidado["categorias"].items():
        with st.expander(f"{categoria} · {len(itens)} registro(s)", expanded=categoria == "Pendências"):
            if not itens:
                st.caption("Nenhum registro identificado.")
            for item in itens:
                st.write(f"**{item['data']}** — {item['texto']}")
                st.caption(f"Fonte: {item['arquivo']}")
    st.info("Compare os registros acima para verificar mudanças entre reuniões. "
            "Uma atualização pode indicar que um risco foi resolvido, mas isso "
            "não encerra automaticamente uma pendência no banco de dados.")
    st.subheader("Linha do tempo das reuniões")
    for ata in atas:
        with st.expander(f"{ata['data']} · {ata['arquivo']}", expanded=True):
            grupos = extrair_trechos(ata["texto"])
            for categoria, trechos in grupos.items():
                if trechos:
                    st.markdown(f"**{categoria}**")
                    for trecho in trechos:
                        st.write("• " + trecho)
            with st.expander("Ver ata completa"):
                st.text(ata["texto"])
    st.caption("Fonte: pasta dados_exemplo/atas no GitHub. Nenhuma informação foi gravada no Supabase.")
    st.warning("A leitura automática não determina sozinha se uma pendência foi concluída. "
               "Mudanças entre atas ainda precisam de revisão humana.")

if configurado() and not st.session_state.get("autorizado", False):
    st.title("ProjectFlow AI")
    with st.form("acesso"):
        senha = st.text_input("Senha de acesso", type="password")
        enviar = st.form_submit_button("Entrar")
    if enviar:
        if hmac.compare_digest(senha, str(st.secrets["APP_PASSWORD"])):
            st.session_state["autorizado"] = True
            st.rerun()
        st.error("Senha incorreta.")
    st.stop()

try:
    projetos = preparar(carregar_projetos())
except Exception as erro:
    st.error("Não foi possível consultar o Supabase.")
    st.info(f"Tipo do erro: {type(erro).__name__}")
    st.stop()

pagina_principal = st.Page(pagina_dashboard, title="Visão executiva", icon="📊", default=True)
pagina_detalhe = st.Page(pagina_detalhes, title="Detalhes do projeto", icon="📁")
pagina_atas = st.Page(pagina_atas_ia, title="Análise de atas", icon="🤖")
with st.sidebar:
    st.markdown("## ProjectFlow AI")
    st.caption("PROJECT PORTFOLIO")
    if configurado() and st.button("Sair"):
        st.session_state["autorizado"] = False
        st.rerun()

navegacao = st.navigation([pagina_principal, pagina_detalhe, pagina_atas])
navegacao.run()

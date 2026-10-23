"""ProjectFlow AI — painel executivo com navegação entre páginas."""
from datetime import date
import time
import html

import altair as alt
import pandas as pd
import requests
import streamlit as st

from farol import calcular_farol

st.set_page_config(page_title="ProjectFlow AI", page_icon="📊", layout="wide")

st.markdown("""
<style>
:root {color-scheme:dark; --pf-bg:#0C0B18; --pf-panel:#18152B; --pf-border:#39304F; --pf-text:#F4F1FF; --pf-muted:#C0B7D4; --pf-purple:#A78BFA; --pf-blue:#60A5FA;}
html,body,[data-testid="stApp"],[data-testid="stMain"] {background:#0C0B18!important;color:#F4F1FF!important;}
[data-testid="stApp"] {background:radial-gradient(ellipse at 95% 0%,#25204C 0%,#0C0B18 48%)!important;}
.block-container {max-width:1280px;padding-top:2rem;padding-bottom:3rem;}
.block-container h1 {color:#F4F1FF!important;font-weight:800;letter-spacing:-.035em;}
.block-container h2,.block-container h3 {color:#E5DAFF!important;letter-spacing:-.02em;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#19132F,#100F22)!important;border-right:1px solid #39304F;}
[data-testid="stSidebar"] * {color:#F4F1FF!important;}
[data-testid="stSidebarNav"] a[aria-current="page"] {background:#352658!important;border-radius:10px;}
[data-testid="stSidebarNav"] a:hover {background:#2B2345!important;border-radius:10px;}
p,li,label,[data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"],[data-testid="stMetricLabel"] {color:#E9E3F5;}
[data-testid="stCaptionContainer"],small {color:#C0B7D4!important;}
.project-card {padding:1.25rem 1.3rem;border-radius:16px;background:#1B1731;border:1px solid #403654;box-shadow:0 8px 24px #07061244;min-height:170px;margin-bottom:.5rem;}
.project-card h3 {margin:.65rem 0 .5rem;font-size:1.2rem;color:#F4F1FF!important;}
.project-card p {margin:.25rem 0;color:#CFC6E1;}
.pill {display:inline-block;padding:.28rem .7rem;border-radius:999px;font-size:.8rem;font-weight:700;}
.green {background:#123F36;color:#A7F3D0;}
.yellow {background:#4B3514;color:#FDE68A;}
.red {background:#4A2035;color:#FDA4AF;}
.subtitle {color:#C0B7D4;margin-top:-.5rem;}
div[data-testid="stMetric"],div[data-testid="stExpander"],[data-testid="stForm"],[data-testid="stDataFrame"] {background:#1B1731!important;border:1px solid #403654!important;border-radius:14px!important;}
div[data-testid="stMetric"] {padding:14px 18px;min-height:100px;}
[data-testid="stMetricValue"] {color:#F4F1FF!important;}
[data-testid="stMetricDelta"] {font-weight:650;}
div[data-testid="stButton"] button,div[data-testid="stFormSubmitButton"] button {border-radius:11px!important;font-weight:700!important;min-height:42px;background:#302648!important;color:#F4F1FF!important;border:1px solid #6C5B8E!important;}
div[data-testid="stButton"] button[kind="primary"],div[data-testid="stFormSubmitButton"] button[kind="primary"] {background:linear-gradient(110deg,#6041C8,#4338CA)!important;color:#FFFFFF!important;border:1px solid #8B76EA!important;}
div[data-testid="stButton"] button:hover,div[data-testid="stFormSubmitButton"] button:hover {background:#473569!important;border-color:#A78BFA!important;color:#FFFFFF!important;}
div[data-testid="stButton"] button[kind="primary"]:hover,div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {background:#6D4DD7!important;}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {background:#402136!important;border:1px solid #BE607E!important;color:#FFE3EC!important;}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"]:hover {background:#633048!important;color:#FFFFFF!important;}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"],[data-baseweb="popover"],[data-baseweb="menu"],[data-baseweb="calendar"] {background:#211B36!important;color:#F4F1FF!important;border-color:#57496D!important;}
input,textarea {color:#F4F1FF!important;caret-color:#C4B5FD!important;}
input::placeholder,textarea::placeholder {color:#AFA5C5!important;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stTabs"] [data-baseweb="tab"] {color:#D8CFF0!important;}
[data-testid="stTabs"] [aria-selected="true"] {color:#C4B5FD!important;border-bottom-color:#A78BFA!important;}
a {color:#BDA7FF!important;}
*:focus-visible {outline:3px solid #A78BFA!important;outline-offset:3px;}
@media(max-width:700px){.block-container{padding:1rem .8rem 2rem;}.project-card{min-height:auto;padding:1rem;}.block-container h1{font-size:1.8rem;}div[data-testid="stMetric"]{min-height:85px;padding:10px;}}
</style>
""", unsafe_allow_html=True)

CORES = {"verde": "#1d9b64", "amarelo": "#e3a324", "vermelho": "#dc4b56"}
ROTULOS = {"verde": "Em dia", "amarelo": "Atenção", "vermelho": "Atrasado"}
CLASSES_FAROL = {"verde": "green", "amarelo": "yellow", "vermelho": "red"}

def configurado():
    return all(k in st.secrets for k in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"))

def cabecalhos_usuario():
    token = st.session_state.get("access_token")
    if not token:
        raise PermissionError("Faça login para consultar os dados.")
    if time.time() >= st.session_state.get("token_expira_em", 0) - 60:
        renovar_sessao()
        token = st.session_state["access_token"]
    return {"apikey": str(st.secrets["SUPABASE_PUBLISHABLE_KEY"]),
            "Authorization": "Bearer " + token}

def renovar_sessao():
    refresh = st.session_state.get("refresh_token")
    if not refresh:
        st.session_state.clear()
        raise PermissionError("Sessão encerrada. Entre novamente.")
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/auth/v1/token"
    resposta = requests.post(url, params={"grant_type": "refresh_token"},
        headers={"apikey": str(st.secrets["SUPABASE_PUBLISHABLE_KEY"])},
        json={"refresh_token": refresh}, timeout=15)
    if not resposta.ok:
        st.session_state.clear()
        raise PermissionError("Sessão expirada. Entre novamente.")
    salvar_sessao(resposta.json())

def salvar_sessao(dados):
    st.session_state["access_token"] = dados["access_token"]
    st.session_state["refresh_token"] = dados["refresh_token"]
    st.session_state["token_expira_em"] = time.time() + int(dados.get("expires_in", 3600))
    st.session_state["email_usuario"] = dados.get("user", {}).get("email", "")
    st.session_state["auth_user_id"] = dados.get("user", {}).get("id")

def entrar(email, senha):
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/auth/v1/token"
    resposta = requests.post(url, params={"grant_type": "password"},
        headers={"apikey": str(st.secrets["SUPABASE_PUBLISHABLE_KEY"])},
        json={"email": email, "password": senha}, timeout=15)
    if not resposta.ok:
        return False
    salvar_sessao(resposta.json())
    return True

def validar_nova_senha(senha, confirmacao):
    if len(senha) < 12:
        return "Use pelo menos 12 caracteres."
    if senha != confirmacao:
        return "As senhas informadas são diferentes."
    return None

def solicitar_recuperacao(email):
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/auth/v1/recover"
    headers = {"apikey":str(st.secrets["SUPABASE_PUBLISHABLE_KEY"]),
               "Content-Type":"application/json"}
    return requests.post(url, headers=headers,
        json={"email":email}, timeout=15)

def redefinir_senha(senha):
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/auth/v1/user"
    return requests.put(url, headers=cabecalhos_usuario(),
                        json={"password":senha}, timeout=15)

def pagina_conta():
    st.title("🔒 Minha conta")
    st.caption("Atualize sua senha de acesso ao ProjectFlow AI.")
    st.write("**E-mail:** " + st.session_state.get("email_usuario",""))
    with st.form("alterar_senha"):
        nova = st.text_input("Nova senha (mínimo 12 caracteres)",type="password")
        confirmar = st.text_input("Confirme a nova senha",type="password")
        enviar = st.form_submit_button("Alterar senha",type="primary")
    if enviar:
        erro = validar_nova_senha(nova,confirmar)
        if erro:
            st.warning(erro)
        else:
            try:
                resposta = redefinir_senha(nova)
                resposta.raise_for_status()
            except requests.RequestException:
                st.error("Não foi possível alterar a senha. Tente novamente ou utilize a recuperação por e-mail.")
            else:
                st.success("Senha atualizada. Entre novamente com sua nova senha.")
                st.session_state.clear()
                st.stop()


def consultar(tabela, campos, filtros=None):
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1/" + tabela
    params = {"select": campos}
    params.update(filtros or {})
    resposta = requests.get(url, headers=cabecalhos_usuario(), params=params, timeout=15)
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
        raise RuntimeError("Configure a chave publicável do Supabase.")
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
    filtro = st.selectbox("Situação", ["Todos", "Em dia", "Atenção", "Atrasado"])
    total = len(projetos)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Projetos", total)
    k2.metric("Em dia", sum(p["farol"] == "verde" for p in projetos))
    k3.metric("Em atenção", sum(p["farol"] == "amarelo" for p in projetos))
    k4.metric("Atrasados", sum(p["farol"] == "vermelho" for p in projetos))

    st.subheader("📋 Acompanhamento de tarefas")
    st.caption("Indicadores e prioridades atualizados a partir das pendências que você tem permissão para consultar.")
    try:
        tarefas = consultar("pendencias",
            "id,projeto_id,descricao,responsavel,prazo,status,prioridade,progresso")
    except (requests.RequestException, PermissionError):
        st.warning("Não foi possível carregar as tarefas. Tente atualizar a página.")
        tarefas = None
    if tarefas is not None:
        hoje = date.today()
        tarefas_ativas = [t for t in tarefas if t.get("status") != "concluida"]
        vencidas = [t for t in tarefas_ativas if t.get("prazo") and
                    date.fromisoformat(str(t["prazo"])) < hoje]
        proximas = [t for t in tarefas_ativas if t.get("prazo") and
                    hoje <= date.fromisoformat(str(t["prazo"])) <=
                    date.fromordinal(hoje.toordinal() + 7)]
        bloqueadas = [t for t in tarefas_ativas if t.get("status") == "bloqueada"]
        concluidas = [t for t in tarefas if t.get("status") == "concluida"]
        indicadores = st.columns(5)
        for coluna, titulo, valor in zip(indicadores,
            ["Tarefas", "Atrasadas", "Bloqueadas", "Concluídas", "Próximos 7 dias"],
            [len(tarefas), len(vencidas), len(bloqueadas), len(concluidas), len(proximas)]):
            coluna.metric(titulo, valor)
        st.caption("Atrasadas = não concluídas com prazo vencido. Próximos 7 dias = não concluídas com vencimento entre hoje e sete dias.")
        nomes_projetos = {p["id"]: p["nome"] for p in projetos}
        rotulos_prioridade = {"baixa": "🟢 Baixa", "media": "🟡 Média",
                             "alta": "🟠 Alta", "critica": "🔴 Crítica"}
        rotulos_status = {"aberta": "Não iniciada", "em_andamento": "Em andamento",
                          "bloqueada": "Bloqueada", "concluida": "Concluída"}
        opcoes_projetos = ["Todos"] + sorted(set(nomes_projetos.values()))
        col_filtro_projeto, col_filtro_prioridade, col_filtro_status = st.columns(3)
        with col_filtro_projeto:
            filtro_projeto_t = st.selectbox("Projeto das tarefas", opcoes_projetos, key="filtro_tarefas_projeto")
        with col_filtro_prioridade:
            filtro_prioridade_t = st.selectbox("Prioridade", ["Todas", "Crítica", "Alta", "Média", "Baixa"], key="filtro_tarefas_prioridade")
        with col_filtro_status:
            filtro_status_t = st.selectbox("Status", ["Todos", "Não iniciada", "Em andamento", "Bloqueada", "Concluída"], key="filtro_tarefas_status")
        linhas_tarefas = []
        for t in tarefas:
            prioridade = rotulos_prioridade.get(t.get("prioridade"), "🟡 Média")
            situacao_t = rotulos_status.get(t.get("status"), str(t.get("status") or "Não definida"))
            nome_projeto = nomes_projetos.get(t["projeto_id"], "Projeto indisponível")
            if filtro_projeto_t != "Todos" and nome_projeto != filtro_projeto_t:
                continue
            if filtro_prioridade_t != "Todas" and not prioridade.endswith(filtro_prioridade_t):
                continue
            if filtro_status_t != "Todos" and situacao_t != filtro_status_t:
                continue
            linhas_tarefas.append({
                "Projeto": nome_projeto,
                "Tarefa": t.get("descricao") or "",
                "Responsável": t.get("responsavel") or "Não definido",
                "Prioridade": prioridade,
                "Status": situacao_t,
                "Progresso (%)": int(t.get("progresso") or 0),
                "Prazo": str(t.get("prazo") or "Não definido"),
            })
        if linhas_tarefas:
            st.dataframe(pd.DataFrame(linhas_tarefas), hide_index=True, use_container_width=True,
                column_config={"Progresso (%)": st.column_config.ProgressColumn(
                    "Progresso (%)", min_value=0, max_value=100, format="%d%%")})
        else:
            st.info("Nenhuma tarefa encontrada para os filtros selecionados.")
        st.caption("Legenda de prioridades: 🔴 Crítica · 🟠 Alta · 🟡 Média · 🟢 Baixa. Os indicadores gerais respeitam os acessos do usuário.")

    st.subheader("Resumo para tomada de decisão")
    st.caption("Três perguntas para entender o portfólio rapidamente. "
               "Indicadores calculados com os dados atuais dos projetos.")
    atrasados = [p for p in projetos if p["farol"] == "vermelho"]
    atencao = [p for p in projetos if p["farol"] == "amarelo"]
    em_dia = [p for p in projetos if p["farol"] == "verde"]
    criticos = sorted(atrasados + atencao, key=lambda p: (p["farol"] != "vermelho", p["prazo"]))
    proxima_entrega = min(projetos, key=lambda p: p["prazo"]) if projetos else None
    cor_fundo = "#fff0f0" if atrasados else ("#fff7e5" if atencao else "#eaf8f0")
    situacao_resumo = (
        f"{len(atrasados)} projeto(s) atrasado(s)" if atrasados
        else f"{len(atencao)} projeto(s) em atenção" if atencao
        else "Todos os projetos em dia"
    )
    col_estado, col_alerta, col_acao = st.columns(3, gap="medium")
    with col_estado:
        st.markdown("#### 📍 Onde estamos?")
        st.markdown(
            '<div style="background:' + cor_fundo +
            ';border-radius:12px;padding:16px;min-height:115px;">' +
            '<strong>' + html.escape(situacao_resumo) + '</strong><br>' +
            '<span style="color:#475569">' + str(len(em_dia)) +
            ' em dia de ' + str(total) + ' projeto(s)</span></div>',
            unsafe_allow_html=True,
        )
    with col_alerta:
        st.markdown("#### ⚠️ O que exige atenção?")
        if criticos:
            for p in criticos[:3]:
                st.markdown("🔴 " if p["farol"] == "vermelho" else "🟡 ", unsafe_allow_html=False)
                st.write(p["nome"] + " · entrega " + formatar_data(p["prazo"]))
            if len(criticos) > 3:
                st.caption("E mais " + str(len(criticos) - 3) + " projeto(s) no portfólio.")
        else:
            st.success("Nenhum projeto em alerta pelo indicador atual.")
    with col_acao:
        st.markdown("#### 🎯 Qual o próximo passo?")
        if criticos:
            prioridade = criticos[0]
            st.write("**Revisar o projeto prioritário:** " + prioridade["nome"])
            st.caption("Prioridade sugerida pelo farol e prazo. Confirme com o responsável.")
            if st.button("Abrir projeto prioritário →", key="prioridade_executiva",
                         use_container_width=True):
                st.session_state["projeto_id"] = prioridade["id"]
                st.switch_page(pagina_detalhe)
        elif proxima_entrega:
            st.write("**Acompanhar a próxima entrega:** " + proxima_entrega["nome"])
            st.caption("Prazo: " + formatar_data(proxima_entrega["prazo"]))
        else:
            st.info("Cadastre projetos para receber orientações.")
    st.caption("**Legenda:** 🟢 Em dia · 🟡 Atenção · 🔴 Atrasado. "
               "A recomendação é baseada em regras, não em análise por IA.")

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
    from atas_github import atas_do_projeto, extrair_trechos, consolidar_atas, comparar_reunioes

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
    st.caption("💡 **Como ler esta página:** primeiro veja o comparativo ANTES × AGORA, "
               "depois explore o gráfico de evolução e, se precisar, consulte as atas completas.")

    if not atas:
        st.info("Nenhuma ata identificada para este projeto.")
        return
    consolidado = consolidar_atas(atas)
    st.subheader("🔄 Sincronizar informações da ata com o projeto")
    st.caption("Revise os registros encontrados. Nada será gravado sem sua aprovação. "
               "A extração é baseada em regras, não interpreta automaticamente compromissos ambíguos.")
    projeto_ata = next((p for p in projetos if p["nome"] == nome), None)
    if perfil[0].get("perfil_global") != "admin":
        st.info("Somente administradores podem aprovar alterações nas informações dos projetos.")
    elif projeto_ata:
        from atas_github import normalizar
        ata_selecionada = st.selectbox("Ata para revisão", atas,
            format_func=lambda a: a["data"] + " · " + a["arquivo"],
            key="ata_para_sincronizar")
        categorias_ata = extrair_trechos(ata_selecionada["texto"])
        st.info("Fonte: " + ata_selecionada["arquivo"] + " · Reunião: " +
                ata_selecionada["data"] + ". O documento de demonstração está no GitHub público.")
        try:
            atuais_pendencias = consultar("pendencias", "descricao", {"projeto_id":"eq." + str(projeto_ata["id"])})
            atuais_gargalos = consultar("gargalos", "descricao", {"projeto_id":"eq." + str(projeto_ata["id"])})
        except (requests.RequestException, PermissionError):
            st.error("Não foi possível verificar registros existentes. Sincronização indisponível.")
            return
        ja_pendencias = {normalizar(x["descricao"].strip()) for x in atuais_pendencias}
        ja_gargalos = {normalizar(x["descricao"].strip()) for x in atuais_gargalos}
        for tipo, categoria, prefixos, existentes in [
            ("pendencia", "Pendências", ("pendência:", "pendente:", "ação:"), ja_pendencias),
            ("gargalo", "Riscos e gargalos", ("gargalo:", "risco:"), ja_gargalos),
        ]:
            st.markdown("**" + categoria + " identificados**")
            encontrados = categorias_ata[categoria]
            if not encontrados:
                st.caption("Nenhum registro explícito nesta ata.")
            for i, trecho in enumerate(encontrados):
                descricao_original = trecho.split(":", 1)[-1].strip()
                if not descricao_original:
                    continue
                if normalizar(descricao_original) in existentes:
                    st.caption("Já cadastrado: " + descricao_original)
                    continue
                chave = tipo + "_" + str(i) + "_" + str(projeto_ata["id"])
                with st.expander("Revisar: " + descricao_original[:110]):
                    with st.form("aprovar_ata_" + chave):
                        descricao_revista = st.text_area("Descrição", value=descricao_original)
                        if tipo == "pendencia":
                            responsavel_ata = st.text_input("Responsável (confirme conforme a ata)")
                            prazo_ata = st.date_input("Prazo (confirme conforme a ata)", value=None)
                            prioridade_ata = st.selectbox("Prioridade",
                                ["media", "alta", "critica", "baixa"],
                                format_func=lambda x: {"media":"Média", "alta":"Alta",
                                                       "critica":"Crítica", "baixa":"Baixa"}[x])
                        else:
                            impacto_ata = st.selectbox("Impacto", ["medio", "alto", "baixo"],
                                format_func=lambda x: {"medio":"Médio", "alto":"Alto", "baixo":"Baixo"}[x])
                        confirmado = st.checkbox("Conferi o trecho na ata e aprovo o cadastro")
                        aprovar = st.form_submit_button("Aplicar ao projeto", type="primary")
                    if aprovar:
                        if not confirmado or not descricao_revista.strip():
                            st.warning("Confirme a revisão e preencha a descrição.")
                        elif normalizar(descricao_revista.strip()) in existentes:
                            st.warning("Este registro já está cadastrado no projeto.")
                        else:
                            try:
                                if tipo == "pendencia":
                                    criar_registro("pendencias", {
                                        "projeto_id":projeto_ata["id"],
                                        "descricao":descricao_revista.strip(),
                                        "responsavel":responsavel_ata.strip() or None,
                                        "prazo":prazo_ata.isoformat() if prazo_ata else None,
                                        "status":"aberta", "origem":"ata",
                                        "prioridade":prioridade_ata, "progresso":0})
                                else:
                                    criar_registro("gargalos", {
                                        "projeto_id":projeto_ata["id"],
                                        "descricao":descricao_revista.strip(),
                                        "impacto":impacto_ata, "status":"aberto"})
                            except (requests.RequestException, PermissionError, ValueError):
                                st.error("Não foi possível aplicar a alteração. Verifique as permissões.")
                            else:
                                st.success("Informação registrada no projeto e auditada.")
                                st.rerun()
        st.markdown("**Prazos, entregáveis e responsáveis mencionados**")
        st.caption("Esses registros precisam de interpretação contextual. Revise antes de alterar "
                   "o prazo geral do projeto ou substituir responsáveis.")
        for categoria in ("Prazos", "Decisões", "Atualizações"):
            for trecho in categorias_ata[categoria]:
                st.write("• " + trecho)
        st.caption("Para editar datas e responsáveis do projeto, use Gerenciar projetos → Editar projeto. "
                   "Para tarefas existentes, use Editar pendências. Nenhuma data é sobrescrita automaticamente.")
    st.subheader("Evolução entre as últimas reuniões")
    st.caption("Comparativo visual dos registros das duas reuniões mais recentes.")
    comparacao = comparar_reunioes(atas)
    if not comparacao["comparavel"]:
        st.info("Com duas ou mais atas, o comparativo visual aparecerá aqui.")
    else:
        anterior = consolidado["atas"][-2]
        recente = consolidado["atas"][-1]
        antes = extrair_trechos(anterior["texto"])
        depois = extrair_trechos(recente["texto"])
        linhas = [
            ("Decisões", "Decisões", "#0d9488"),
            ("Atualizações", "Atualizações", "#84b72a"),
            ("Pendências", "Pendências", "#e4a11b"),
            ("Riscos e gargalos", "Riscos e gargalos", "#e2534d"),
            ("Prazos", "Prazos", "#a63875"),
        ]
        st.markdown("""
        <style>
        .meeting-compare {border:1px solid #e3e8ef;border-radius:18px;padding:20px;
          background:#fff;box-shadow:0 5px 20px rgba(22,34,55,.05);margin:12px 0 20px;}
        .mc-head {display:grid;grid-template-columns:minmax(0,1fr) 70px minmax(0,1fr);
          align-items:center;gap:8px;text-align:center;margin-bottom:12px;}
        .mc-head strong {font-size:1.1rem;color:#0c688a;}
        .mc-head span {color:#7c899b;font-weight:800;font-size:1.35rem;}
        .mc-date {color:#64748b;font-size:.82rem;}
        .mc-row {display:grid;grid-template-columns:minmax(0,1fr) 70px minmax(0,1fr);
          align-items:stretch;gap:8px;margin:12px 0;}
        .mc-cell {padding:12px 14px;border-top:4px solid var(--row-color);
          background:#f8fafc;border-radius:8px;min-width:0;}
        .mc-cell b {display:block;color:#253449;margin-bottom:5px;font-size:.86rem;}
        .mc-cell p {margin:0;color:#4b5b70;font-size:.88rem;overflow-wrap:anywhere;}
        .mc-mid {display:flex;align-items:center;justify-content:center;}
        .mc-mid span {background:var(--row-color);color:white;font-weight:800;
          border-radius:9px;padding:10px 8px;min-width:38px;text-align:center;}
        .mc-note {font-size:.8rem;color:#64748b;margin-top:12px;}
        @media(max-width:700px) {
          .meeting-compare {padding:10px;}
          .mc-head,.mc-row {grid-template-columns:minmax(0,1fr) 38px minmax(0,1fr);gap:4px;}
          .mc-cell {padding:8px;}
          .mc-cell p {font-size:.76rem;}
          .mc-head strong {font-size:.9rem;}
          .mc-mid span {min-width:28px;padding:7px 3px;}
        }
        </style>
        """, unsafe_allow_html=True)
        def resumo_curto(registros):
            if not registros:
                return "Não mencionado nesta ata."
            trecho = registros[0].split(":", 1)[-1].strip()
            return html.escape(trecho[:175] + ("…" if len(trecho) > 175 else ""))
        partes = [
            '<div class="meeting-compare">',
            '<div class="mc-head"><div><strong>ANTES</strong><br><span class="mc-date">' +
            html.escape(anterior["data"]) + '</span></div><span>VS</span>' +
            '<div><strong>AGORA</strong><br><span class="mc-date">' +
            html.escape(recente["data"]) + '</span></div></div>',
        ]
        for numero, (categoria, rotulo, cor) in enumerate(linhas, 1):
            partes.append(
                '<div class="mc-row" style="--row-color:' + cor + ';">' +
                '<div class="mc-cell"><b>' + rotulo + '</b><p>' +
                resumo_curto(antes[categoria]) + '</p></div>' +
                '<div class="mc-mid"><span>' + str(numero).zfill(2) + '</span></div>' +
                '<div class="mc-cell"><b>' + rotulo + '</b><p>' +
                resumo_curto(depois[categoria]) + '</p></div></div>'
            )
        partes.append('</div>')
        st.markdown("".join(partes), unsafe_allow_html=True)
        st.caption("**Legenda:** verde-água = decisões · verde = atualizações · "
                   "amarelo = pendências · vermelho = riscos · rosa = prazos. "
                   "Cada linha mostra o primeiro registro daquela categoria em cada ata.")
        with st.expander("Ver todos os registros usados no comparativo"):
            col_antes, col_depois = st.columns(2)
            for coluna, ata, grupos in [(col_antes, anterior, antes),
                                        (col_depois, recente, depois)]:
                with coluna:
                    st.markdown("**Reunião de " + ata["data"] + "**")
                    st.caption("Fonte: " + ata["arquivo"])
                    for categoria, _, _ in linhas:
                        if grupos[categoria]:
                            st.markdown("**" + categoria + "**")
                            for trecho in grupos[categoria]:
                                st.write("• " + trecho)
        st.info("O comparativo mostra registros presentes em cada ata. "
                "Ausência de menção não significa conclusão ou resolução. "
                "A comparação ainda é baseada em regras, não em um modelo de IA.")
    st.subheader("Evolução histórica das reuniões")
    st.caption("Linha do tempo dos registros das atas. Os pontos não representam percentual de execução.")
    eventos = []
    for categoria, tipo in [
        ("Decisões", "Decisão"),
        ("Atualizações", "Atualização"),
        ("Pendências", "Pendência"),
        ("Riscos e gargalos", "Risco ou gargalo"),
    ]:
        for item in consolidado["categorias"][categoria]:
            data_evento = pd.to_datetime(item["data"], format="%d/%m/%Y", errors="coerce")
            if pd.notna(data_evento):
                eventos.append({
                    "Data": data_evento,
                    "Tipo": tipo,
                    "Descrição": item["texto"],
                    "Ata": item["arquivo"],
                    "Data da reunião": item["data"],
                })
    if eventos:
        df_eventos = pd.DataFrame(eventos)
        ordem = ["Decisão", "Atualização", "Pendência", "Risco ou gargalo"]
        grafico = alt.Chart(df_eventos).mark_circle(size=170).encode(
            x=alt.X("Data:T", title="Data da reunião", axis=alt.Axis(format="%d/%m/%Y")),
            y=alt.Y("Tipo:N", title=None, sort=ordem),
            color=alt.Color("Tipo:N", legend=alt.Legend(title="Legenda · tipo de acontecimento", orient="bottom"),
                            scale=alt.Scale(domain=ordem,
                                            range=["#2563eb", "#0d9488", "#d97706", "#dc2626"])),
            tooltip=["Data da reunião:N", "Tipo:N", "Descrição:N", "Ata:N"],
        )
        st.altair_chart(grafico.properties(height=250).interactive(),
                        use_container_width=True)
        st.markdown("**Principais decisões por reunião**")
        decisoes = df_eventos[df_eventos["Tipo"] == "Decisão"].sort_values("Data")
        if decisoes.empty:
            st.info("Nenhuma decisão identificada nas atas.")
        else:
            for _, decisao in decisoes.iterrows():
                st.markdown("**" + html.escape(decisao["Data da reunião"]) +
                            "** · " + html.escape(decisao["Descrição"]))
                st.caption("Fonte: " + decisao["Ata"])
    else:
        st.info("Não há eventos com datas válidas para exibir no gráfico.")
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

def alterar_vinculo(tabela, acao, dados):
    """Operação autenticada; RLS e auditoria são aplicadas no banco."""
    if tabela not in ("projeto_acessos", "squad_membros") or acao not in ("adicionar", "remover"):
        raise ValueError("Operação inválida.")
    base = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1/" + tabela
    cabecalhos = dict(cabecalhos_usuario())
    cabecalhos["Prefer"] = "return=minimal"
    if acao == "adicionar":
        resposta = requests.post(base, headers=cabecalhos, json=dados, timeout=15)
    else:
        filtros = {chave: "eq." + str(valor) for chave, valor in dados.items()}
        resposta = requests.delete(base, headers=cabecalhos, params=filtros, timeout=15)
    resposta.raise_for_status()


def pagina_administracao():
    st.title("🛡️ Administração de usuários")
    st.caption("Acesso restrito a administradores · Permissões auditadas no banco")
    if perfil[0].get("perfil_global") != "admin":
        st.error("Acesso restrito.")
        return
    try:
        usuarios = consultar("perfis_usuarios", "id,nome,perfil_global,ativo")
        acessos = consultar("projeto_acessos", "usuario_id,projeto_id,papel")
        equipes = consultar("squads", "id,nome")
        membros = consultar("squad_membros", "usuario_id,squad_id,papel")
    except (requests.RequestException, PermissionError):
        st.error("Não foi possível consultar o cadastro administrativo.")
        return
    if len(usuarios) < 2:
        st.warning("A consulta administrativa não retornou os usuários esperados. Verifique as permissões RLS.")
        return
    a,b,c = st.columns(3)
    a.metric("Usuários cadastrados", len(usuarios))
    b.metric("Usuários ativos", sum(bool(u["ativo"]) for u in usuarios))
    c.metric("Squads", len(equipes))
    mapa_projetos = {p["id"]: p["nome"] for p in projetos}
    mapa_equipes = {e["id"]: e["nome"] for e in equipes}
    st.subheader("Cadastro central")
    st.caption("Somente nome, perfil e situação são exibidos. E-mails, senhas e tokens não aparecem neste painel.")
    st.dataframe([{"Nome":u["nome"], "Perfil":u["perfil_global"],
                   "Situação":"Ativo" if u["ativo"] else "Inativo"}
                  for u in sorted(usuarios,key=lambda x:x["nome"])],
                 hide_index=True,use_container_width=True)
    st.subheader("Permissões por usuário")
    selecionado = st.selectbox("Selecione o usuário", usuarios,
                              format_func=lambda u:u["nome"])
    identificador = selecionado["id"]
    linhas = [{"Projeto":mapa_projetos.get(a["projeto_id"],"Projeto indisponível"),
               "Papel":a["papel"]} for a in acessos if a["usuario_id"]==identificador]
    st.markdown("**Projetos autorizados**")
    if linhas:
        st.dataframe(linhas,hide_index=True,use_container_width=True)
    else:
        st.info("Nenhum projeto vinculado.")
    linhas_squad = [{"Squad":mapa_equipes.get(m["squad_id"],"Squad indisponível"),
                     "Papel":m["papel"]} for m in membros if m["usuario_id"]==identificador]
    st.markdown("**Squads vinculadas**")
    if linhas_squad:
        st.dataframe(linhas_squad,hide_index=True,use_container_width=True)
    else:
        st.info("Nenhuma squad vinculada.")
    st.divider()
    st.subheader("Gerenciar vínculos")
    st.caption("Alterações aplicadas imediatamente. Cada inclusão ou remoção gera registro de auditoria no banco.")
    tipo = st.radio("Tipo de acesso", ["Projetos", "Squads"], horizontal=True)
    if tipo == "Projetos":
        tabela, coluna = "projeto_acessos", "projeto_id"
        opcoes = sorted(projetos, key=lambda p:p["nome"])
        rotulo = lambda p:p["nome"]
        registros = acessos
        papeis = ["gerente", "lider", "membro", "leitor"]
    else:
        tabela, coluna = "squad_membros", "squad_id"
        opcoes = sorted(equipes, key=lambda e:e["nome"])
        rotulo = lambda e:e["nome"]
        registros = membros
        papeis = ["lider", "membro"]
    existentes = {r[coluna]:r["papel"] for r in registros if r["usuario_id"]==identificador}
    operacao = st.radio("Operação", ["Conceder acesso", "Revogar acesso"], horizontal=True)
    if operacao == "Conceder acesso":
        disponiveis = [p for p in opcoes if p["id"] not in existentes]
        if not disponiveis:
            st.info("Este usuário já possui acesso a todos os itens deste tipo.")
        else:
            item = st.selectbox("Conceder acesso a", disponiveis, format_func=rotulo)
            papel_novo = st.selectbox("Papel", papeis)
            confirmar = st.checkbox("Confirmo a concessão deste acesso", key="confirma_concessao")
            if st.button("Conceder acesso", disabled=not confirmar, type="primary"):
                try:
                    alterar_vinculo(tabela, "adicionar",
                        {"usuario_id":identificador, coluna:item["id"], "papel":papel_novo})
                except requests.RequestException:
                    st.error("Operação não autorizada ou indisponível. Nenhuma confirmação de alteração.")
                else:
                    st.success("Acesso concedido e registrado para auditoria.")
                    st.rerun()
    else:
        revogaveis = [p for p in opcoes if p["id"] in existentes]
        if selecionado.get("perfil_global") == "admin":
            st.warning("A revogação de vínculos de administradores está bloqueada nesta interface.")
        elif not revogaveis:
            st.info("Este usuário não possui vínculos deste tipo.")
        else:
            item = st.selectbox("Revogar acesso a", revogaveis, format_func=rotulo)
            st.warning("A revogação retira imediatamente a visibilidade deste item.")
            confirmar = st.checkbox("Confirmo a revogação deste acesso", key="confirma_revogacao")
            if st.button("Revogar acesso", disabled=not confirmar, type="primary"):
                try:
                    alterar_vinculo(tabela, "remover",
                        {"usuario_id":identificador, coluna:item["id"]})
                except requests.RequestException:
                    st.error("Operação não autorizada ou indisponível. Nenhuma confirmação de alteração.")
                else:
                    st.success("Acesso revogado e registrado para auditoria.")
                    st.rerun()


def atualizar_registro(tabela, registro_id, dados):
    """PATCH restrito a campos permitidos; Supabase aplica RLS e auditoria."""
    campos_permitidos = {
        "projetos": {"nome", "responsavel", "inicio", "prazo", "status"},
        "pendencias": {"descricao", "responsavel", "prazo", "status", "prioridade", "progresso"},
    }
    if tabela not in campos_permitidos or not dados or not set(dados).issubset(campos_permitidos[tabela]):
        raise ValueError("Campos não permitidos.")
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1/" + tabela
    cabecalhos = dict(cabecalhos_usuario())
    cabecalhos["Prefer"] = "return=representation"
    resposta = requests.patch(url, headers=cabecalhos,
        params={"id":"eq." + str(registro_id), "select":"id"}, json=dados, timeout=15)
    resposta.raise_for_status()
    if len(resposta.json()) != 1:
        raise PermissionError("Registro não atualizado ou acesso não autorizado.")


def criar_registro(tabela, dados):
    permitidos = {"projetos": {"nome", "responsavel", "inicio", "prazo", "status"},
                  "pendencias": {"projeto_id", "descricao", "responsavel", "prazo", "status", "origem", "prioridade", "progresso"},
                  "gargalos": {"projeto_id", "descricao", "impacto", "status"}}
    if tabela not in permitidos or not dados or not set(dados).issubset(permitidos[tabela]):
        raise ValueError("Campos não permitidos.")
    url = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1/" + tabela
    headers = dict(cabecalhos_usuario())
    headers["Prefer"] = "return=representation"
    resposta = requests.post(url, headers=headers, params={"select":"id"}, json=dados, timeout=15)
    resposta.raise_for_status()
    if len(resposta.json()) != 1:
        raise PermissionError("Cadastro não confirmado.")


def pagina_gerenciar_portfolio():
    st.title("📝 Gestão de projetos e pendências")
    st.caption("Edição administrativa · Dados protegidos por RLS e alterações auditadas")
    if perfil[0].get("perfil_global") != "admin":
        st.error("Acesso restrito.")
        return
    st.caption("Legenda: 🔴 Crítica | 🟠 Alta | 🟡 Média | 🟢 Baixa")
    aba_novo, aba_nova_pend, aba_projeto, aba_pendencias = st.tabs(
        ["Novo projeto", "Nova pendência", "Editar projeto", "Editar pendências"])
    with aba_novo:
        with st.form("form_novo_projeto"):
            nome_novo = st.text_input("Nome do projeto")
            responsavel_novo = st.text_input("Responsável pelo projeto")
            inicio_novo = st.date_input("Data de início", value=date.today())
            prazo_novo = st.date_input("Data de entrega", value=date.today())
            status_novo = st.selectbox("Situação inicial", ["em_andamento", "pausado"])
            confirma_novo = st.checkbox("Confirmo a criação do projeto")
            salvar_novo = st.form_submit_button("Criar projeto", type="primary")
        if salvar_novo and not confirma_novo:
            st.warning("Marque a confirmação antes de salvar.")
        if salvar_novo and confirma_novo:
            if not nome_novo.strip() or not responsavel_novo.strip() or prazo_novo < inicio_novo:
                st.error("Informe nome, responsável e prazo válido.")
            else:
                try:
                    criar_registro("projetos", {"nome": nome_novo.strip(),
                        "responsavel": responsavel_novo.strip(), "inicio": inicio_novo.isoformat(),
                        "prazo": prazo_novo.isoformat(), "status": status_novo})
                except (requests.RequestException, PermissionError, ValueError):
                    st.error("Não foi possível criar o projeto. Confira os dados e se o nome já existe.")
                else:
                    st.success("Projeto criado e auditado.")
                    st.rerun()
    with aba_nova_pend:
        if not projetos:
            st.info("Cadastre um projeto primeiro.")
        else:
            with st.form("form_nova_pendencia"):
                destino = st.selectbox("Projeto", projetos, format_func=lambda p:p["nome"])
                descricao_nova = st.text_area("Descrição da pendência")
                responsavel_pnovo = st.text_input("Responsável pela pendência")
                prazo_pnovo = st.date_input("Prazo previsto", value=date.today())
                prioridade_nova = st.selectbox("Prioridade", ["media", "alta", "critica", "baixa"], format_func=lambda x: {"media":"🟡 Média","alta":"🟠 Alta","critica":"🔴 Crítica","baixa":"🟢 Baixa"}[x])
                confirma_pnovo = st.checkbox("Confirmo a criação da pendência")
                salvar_pnovo = st.form_submit_button("Criar pendência", type="primary")
            if salvar_pnovo and not confirma_pnovo:
                st.warning("Marque a confirmação antes de salvar.")
            if salvar_pnovo and confirma_pnovo:
                if not descricao_nova.strip():
                    st.error("Informe a descrição.")
                else:
                    try:
                        criar_registro("pendencias", {"projeto_id": destino["id"],
                            "descricao": descricao_nova.strip(),
                            "responsavel": responsavel_pnovo.strip() or None,
                            "prazo": prazo_pnovo.isoformat(), "status": "aberta", "origem": "manual",
                            "prioridade": prioridade_nova, "progresso": 0})
                    except (requests.RequestException, PermissionError, ValueError):
                        st.error("Não foi possível criar a pendência.")
                    else:
                        st.success("Pendência criada e auditada.")
                        st.rerun()
    if not projetos:
        return
    with aba_projeto:
        escolhido = st.selectbox("Projeto", projetos, format_func=lambda p:p["nome"], key="editar_projeto")
        with st.form("form_edicao_projeto"):
            nome = st.text_input("Nome", value=escolhido["nome"])
            responsavel = st.text_input("Responsável", value=escolhido["responsavel"])
            inicio = st.date_input("Início", value=date.fromisoformat(str(escolhido["inicio"])))
            prazo = st.date_input("Prazo", value=date.fromisoformat(str(escolhido["prazo"])))
            opcoes_status = ["em_andamento", "pausado", "concluido"]
            status = st.selectbox("Situação", opcoes_status,
                index=opcoes_status.index(escolhido["status"]))
            confirmar = st.checkbox("Confirmo a atualização deste projeto")
            salvar = st.form_submit_button("Salvar projeto", type="primary")
        if salvar and not confirmar:
            st.warning("Marque a confirmação antes de salvar.")
        if salvar and confirmar:
            if not nome.strip() or not responsavel.strip() or prazo < inicio:
                st.error("Informe nome e responsável; o prazo não pode ser anterior ao início.")
            else:
                try:
                    atualizar_registro("projetos", escolhido["id"], {
                        "nome":nome.strip(), "responsavel":responsavel.strip(),
                        "inicio":inicio.isoformat(), "prazo":prazo.isoformat(), "status":status})
                except (requests.RequestException, PermissionError, ValueError):
                    st.error("Não foi possível salvar. Verifique os dados e suas permissões.")
                else:
                    st.success("Projeto atualizado e alteração auditada.")
                    st.rerun()
    with aba_pendencias:
        escolhido_p = st.selectbox("Projeto das pendências", projetos,
                                  format_func=lambda p:p["nome"], key="projeto_pendencias")
        try:
            pendencias = consultar("pendencias", "id,descricao,responsavel,prazo,status,prioridade,progresso",
                                  {"projeto_id":"eq." + str(escolhido_p["id"])})
        except (requests.RequestException, PermissionError):
            st.error("Não foi possível carregar as pendências.")
            return
        if not pendencias:
            st.info("Nenhuma pendência cadastrada para este projeto.")
        else:
            pendencia = st.selectbox("Pendência", pendencias,
                format_func=lambda p:p["descricao"][:90])
            with st.form("form_edicao_pendencia"):
                descricao = st.text_area("Descrição", value=pendencia["descricao"])
                responsavel_p = st.text_input("Responsável", value=pendencia.get("responsavel") or "")
                prazo_p = st.date_input("Prazo da pendência",
                    value=date.fromisoformat(str(pendencia["prazo"])) if pendencia.get("prazo") else None)
                opcoes = ["aberta", "em_andamento", "bloqueada", "concluida"]
                nomes_status = {"aberta":"Não iniciada", "em_andamento":"Em andamento",
                                "bloqueada":"Bloqueada", "concluida":"Concluída"}
                status_p = st.selectbox("Situação da pendência", opcoes,
                    index=opcoes.index(pendencia["status"]), format_func=lambda x: nomes_status[x])
                prioridades = ["baixa", "media", "alta", "critica"]
                nomes_prioridade = {"baixa":"🟢 Baixa", "media":"🟡 Média",
                                    "alta":"🟠 Alta", "critica":"🔴 Crítica"}
                prioridade_p = st.selectbox("Prioridade", prioridades,
                    index=prioridades.index(pendencia.get("prioridade") or "media"),
                    format_func=lambda x: nomes_prioridade[x])
                progresso_p = st.slider("Progresso (%)", 0, 100,
                    value=int(pendencia.get("progresso") or 0), step=5)
                st.caption("Ao concluir a pendência, o progresso será automaticamente 100%.")
                confirmar_p = st.checkbox("Confirmo a atualização desta pendência")
                salvar_p = st.form_submit_button("Salvar pendência", type="primary")
            if salvar_p and not confirmar_p:
                st.warning("Marque a confirmação antes de salvar.")
            if salvar_p and confirmar_p:
                if not descricao.strip():
                    st.error("A descrição é obrigatória.")
                elif status_p != "concluida" and progresso_p == 100:
                    st.error("Para marcar 100%, selecione Concluída.")
                else:
                    try:
                        atualizar_registro("pendencias", pendencia["id"], {
                            "descricao":descricao.strip(),
                            "responsavel":responsavel_p.strip() or None,
                            "prazo":prazo_p.isoformat() if prazo_p else None,
                            "status":status_p, "prioridade":prioridade_p,
                            "progresso":100 if status_p == "concluida" else progresso_p})
                    except (requests.RequestException, PermissionError, ValueError):
                        st.error("Não foi possível salvar. Verifique os dados e suas permissões.")
                    else:
                        st.success("Pendência atualizada e alteração auditada.")
                        st.rerun()


def pagina_central_atas():
    """Fila central de propostas de todas as atas de demonstração acessíveis."""
    import hashlib
    from atas_github import atas_do_projeto, extrair_trechos

    st.title("📥 Central de aprovações das atas")
    st.caption("Todos os projetos em um só lugar · aprovação, ajustes e rejeição")
    if perfil[0].get("perfil_global") != "admin":
        st.error("Acesso restrito a administradores.")
        return
    st.warning("Nesta versão, a fonte é a pasta de atas fictícias do GitHub público. "
               "Não coloque atas reais ou confidenciais nesse repositório.")
    base = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1/sugestoes_atas"
    @st.cache_data(ttl=600, show_spinner=False)
    def buscar_todas_atas(lista_projetos):
        propostas = []
        erros = []
        categorias = {"Pendências":"pendencia", "Riscos e gargalos":"gargalo",
                      "Prazos":"prazo", "Atualizações":"atualizacao", "Decisões":"decisao"}
        for pid, nome in lista_projetos:
            try:
                atas = atas_do_projeto(nome)
                for ata in atas:
                    for categoria, trechos in extrair_trechos(ata["texto"]).items():
                        if categoria not in categorias:
                            continue
                        for trecho in trechos:
                            descricao = trecho.split(":", 1)[-1].strip()
                            if not descricao:
                                continue
                            origem = "|".join([str(pid), ata["arquivo"], categoria, trecho])
                            chave = hashlib.sha256(origem.encode("utf-8")).hexdigest()
                            propostas.append({
                                "projeto_id":pid, "fonte_arquivo":ata["arquivo"],
                                "fonte_data":ata["data"], "tipo":categorias[categoria],
                                "texto_original":trecho, "texto_proposto":descricao,
                                "chave_fonte":chave, "status":"pendente"})
            except (requests.RequestException, ValueError) as erro:
                erros.append(nome + " (" + type(erro).__name__ + ")")
        return propostas, erros

    if st.button("🔄 Verificar todas as atas novamente"):
        buscar_todas_atas.clear()
        st.rerun()
    with st.spinner("Verificando atas de todos os projetos..."):
        propostas, erros = buscar_todas_atas(tuple((p["id"], p["nome"]) for p in projetos))
    if erros:
        st.warning("Não foi possível verificar: " + ", ".join(erros) +
                   ". As propostas desses projetos podem estar incompletas.")
    if propostas:
        try:
            headers = dict(cabecalhos_usuario())
            headers["Prefer"] = "resolution=ignore-duplicates,return=minimal"
            resposta = requests.post(base, headers=headers, json=propostas, timeout=30)
            resposta.raise_for_status()
        except requests.RequestException:
            st.warning("Não foi possível sincronizar todas as propostas. A fila existente continua disponível.")
    try:
        fila = consultar("sugestoes_atas",
            "id,projeto_id,fonte_arquivo,fonte_data,tipo,texto_original,texto_proposto,status,responsavel,prazo,prioridade,impacto",
            {"order":"id.desc"})
    except (requests.RequestException, PermissionError):
        st.error("Não foi possível consultar a fila de aprovações.")
        return
    pendentes = [item for item in fila if item["status"] == "pendente"]
    aprovadas = [item for item in fila if item["status"] == "aprovada"]
    rejeitadas = [item for item in fila if item["status"] == "rejeitada"]
    c1,c2,c3 = st.columns(3)
    c1.metric("Aguardando revisão",len(pendentes))
    c2.metric("Aprovadas",len(aprovadas))
    c3.metric("Rejeitadas",len(rejeitadas))
    nomes = {p["id"]:p["nome"] for p in projetos}
    filtro = st.selectbox("Filtrar projetos", ["Todos"] + sorted(nomes.values()))
    tipos = {"pendencia":"Pendência", "gargalo":"Gargalo", "prazo":"Prazo",
             "atualizacao":"Atualização / entrega", "decisao":"Decisão"}
    visiveis = [item for item in pendentes
                if filtro == "Todos" or nomes.get(item["projeto_id"]) == filtro]
    st.caption("As sugestões são detectadas automaticamente ao abrir a central; "
               "a atualização dos projetos depende de aprovação.")
    if not visiveis:
        st.success("Nenhuma sugestão pendente para os filtros selecionados.")
    for item in visiveis:
        titulo = nomes.get(item["projeto_id"], "Projeto") + " · " + tipos.get(item["tipo"], item["tipo"])
        with st.expander(titulo + " · " + str(item.get("fonte_data") or "")):
            st.caption("Fonte: " + item["fonte_arquivo"])
            st.write("**Trecho original:** " + item["texto_original"])
            tarefas_do_projeto = []
            if item["tipo"] in ("pendencia","prazo","atualizacao","decisao"):
                try:
                    tarefas_do_projeto = consultar("pendencias",
                        "id,descricao,responsavel,prazo,prioridade",
                        {"projeto_id":"eq." + str(item["projeto_id"])})
                except (requests.RequestException, PermissionError):
                    st.warning("Não foi possível carregar as tarefas para vinculação.")
            alvos = {"pendencia":["Criar nova pendência","Atualizar tarefa existente"],
                     "gargalo":["Criar novo gargalo"],
                     "prazo":["Alterar prazo do projeto","Atualizar tarefa existente"],
                     "atualizacao":["Atualizar tarefa existente","Alterar responsável do projeto"],
                     "decisao":["Atualizar tarefa existente","Alterar responsável do projeto"]}
            with st.form("revisao_" + str(item["id"])):
                descricao = st.text_area("Texto revisado", value=item["texto_proposto"])
                alvo_label = st.selectbox("O que esta informação deve atualizar?",
                    alvos.get(item["tipo"], []))
                alvo = {"Criar nova pendência":"novo","Criar novo gargalo":"novo",
                        "Alterar prazo do projeto":"projeto_prazo",
                        "Alterar responsável do projeto":"projeto_responsavel",
                        "Atualizar tarefa existente":"tarefa"}[alvo_label]
                tarefa_escolhida = None
                if "Atualizar tarefa existente" in alvos.get(item["tipo"], []):
                    tarefa_escolhida = st.selectbox("Tarefa existente (para atualização)",
                        [None] + tarefas_do_projeto,
                        format_func=lambda t: t["descricao"][:100] if t else "Selecione a tarefa",
                        key="tarefa_ata_" + str(item["id"]))
                responsavel = st.text_input("Responsável (preencha ou confirme)",
                    value=item.get("responsavel") or "")
                prazo = st.date_input("Prazo (se aplicável)",
                    value=date.fromisoformat(item["prazo"]) if item.get("prazo") else None)
                prioridade = st.selectbox("Prioridade", ["media","alta","critica","baixa"],
                    index=["media","alta","critica","baixa"].index(item.get("prioridade") or "media"))
                impacto = st.selectbox("Impacto", ["medio","alto","baixo"],
                    index=["medio","alto","baixo"].index(item.get("impacto") or "medio"))
                acao = st.radio("Decisão", ["Aprovar", "Rejeitar"], horizontal=True)
                confirma = st.checkbox("Conferi a ata, os campos e o destino da alteração")
                enviar = st.form_submit_button("Registrar decisão", type="primary")
            if enviar:
                if not confirma or not descricao.strip():
                    st.warning("Confirme a decisão e preencha o texto revisado.")
                    continue
                if acao == "Aprovar" and alvo == "tarefa" and not tarefa_escolhida:
                    st.warning("Selecione uma tarefa existente para atualizar.")
                    continue
                if acao == "Aprovar" and alvo == "projeto_prazo" and not prazo:
                    st.warning("Informe a nova data do projeto.")
                    continue
                if acao == "Aprovar" and alvo == "projeto_responsavel" and not responsavel.strip():
                    st.warning("Informe o novo responsável pelo projeto.")
                    continue
                if acao == "Aprovar" and alvo == "tarefa":
                    st.warning("Atenção: a descrição, o responsável, o prazo e a prioridade "
                               "serão substituídos pelos valores deste formulário.")
                try:
                    url_rpc = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/rest/v1/rpc/aplicar_sugestao_ata"
                    resposta = requests.post(url_rpc, headers=cabecalhos_usuario(),
                        json={"p_id":item["id"],
                              "p_decisao":"aprovada" if acao=="Aprovar" else "rejeitada",
                              "p_texto":descricao.strip(),
                              "p_responsavel":responsavel.strip() or None,
                              "p_prazo":prazo.isoformat() if prazo else None,
                              "p_prioridade":prioridade,"p_impacto":impacto,
                              "p_alvo":alvo,
                              "p_tarefa_id":tarefa_escolhida["id"] if tarefa_escolhida and alvo=="tarefa" else None},
                        timeout=15)
                    resposta.raise_for_status()
                except (requests.RequestException, PermissionError, ValueError):
                    st.error("Não foi possível aplicar a decisão. Nenhuma atualização parcial "
                             "é confirmada pela operação transacional.")
                else:
                    st.success("Decisão aplicada com histórico e atualização do projeto.")
                    st.rerun()
    with st.expander("Histórico de decisões"):
        for item in fila:
            if item["status"] != "pendente":
                st.write(("✅ " if item["status"]=="aprovada" else "❌ ") +
                         nomes.get(item["projeto_id"],"Projeto") + " · " +
                         tipos.get(item["tipo"],item["tipo"]) + ": " + item["texto_proposto"])


def pagina_squads():
    st.title("👥 Minhas squads e acessos")
    st.caption("Equipes e projetos autorizados para sua conta · Dados do Supabase")
    try:
        equipes = consultar("squads", "id,nome,descricao", {"ativo": "eq.true"})
        membros = consultar("squad_membros", "squad_id,papel")
        vinculos = consultar("projeto_squads", "squad_id,projeto_id")
        acessos = consultar("projeto_acessos", "projeto_id,papel")
    except (requests.RequestException, PermissionError):
        st.error("Não foi possível consultar as squads e permissões.")
        return
    ids_visiveis = {p["id"] for p in projetos}
    acesso_por_projeto = {a["projeto_id"]: a["papel"] for a in acessos}
    st.caption("Os números consideram somente os registros que você tem permissão para consultar.")
    a, b, c = st.columns(3)
    a.metric("Minhas squads", len(equipes))
    b.metric("Projetos autorizados", len(ids_visiveis))
    c.metric("Vínculos com squads", len(membros))
    st.markdown("**Legenda dos papéis:** gerente = gestão do projeto · líder = liderança · membro = participante · leitor = consulta.")
    if not equipes:
        st.info("Nenhuma squad vinculada ao seu usuário.")
        return
    for equipe in equipes:
        with st.container(border=True):
            st.subheader("🧩 " + equipe["nome"])
            if equipe.get("descricao"):
                st.caption(equipe["descricao"])
            papeis = [m["papel"] for m in membros if m["squad_id"] == equipe["id"]]
            st.write("**Seu papel na squad:** " + (", ".join(papeis) if papeis else "Não informado"))
            projetos_equipe = [p for p in projetos if p["id"] in ids_visiveis and
                any(v["squad_id"] == equipe["id"] and v["projeto_id"] == p["id"] for v in vinculos)]
            if not projetos_equipe:
                st.caption("Nenhum projeto autorizado vinculado a esta squad.")
            for p in projetos_equipe:
                st.write("📁 **" + p["nome"] + "** · Acesso: " +
                         acesso_por_projeto.get(p["id"], "não informado"))
    st.info("Esta página é de consulta. A administração de membros e permissões será habilitada somente após configurar o perfil Administradora/PMO.")

if not configurado():
    st.error("Configuração pendente: adicione SUPABASE_PUBLISHABLE_KEY aos Secrets do Streamlit.")
    st.stop()

if not st.session_state.get("access_token"):
    st.title("🔐 Gerenciamento de Projetos com IA")
    st.caption("Acesso individual · Entre com seu usuário do Supabase")
    with st.form("acesso_individual"):
        email = st.text_input("E-mail").strip()
        senha = st.text_input("Senha", type="password")
        enviar = st.form_submit_button("Entrar", type="primary")
    if enviar:
        try:
            if entrar(email, senha):
                st.session_state["ir_para_visao_executiva"] = True
                st.rerun()
            st.error("E-mail ou senha inválidos.")
        except requests.RequestException:
            st.error("Não foi possível conectar ao serviço de autenticação.")
    with st.expander("🔑 Esqueci minha senha / Primeiro acesso"):
        st.caption("Informe o e-mail cadastrado. Se a conta existir e o envio estiver habilitado, você receberá instruções de recuperação.")
        with st.form("recuperar_senha"):
            email_recuperacao = st.text_input("E-mail cadastrado para recuperação").strip()
            recuperar = st.form_submit_button("Enviar instruções")
        if recuperar:
            if "@" not in email_recuperacao or len(email_recuperacao) > 254:
                st.warning("Informe um e-mail válido.")
            else:
                try:
                    resultado = solicitar_recuperacao(email_recuperacao)
                    resultado.raise_for_status()
                except requests.RequestException:
                    st.error("Não foi possível processar a solicitação agora. Tente novamente.")
                else:
                    st.success("Se o e-mail estiver cadastrado, as instruções de recuperação serão enviadas.")
    st.stop()

try:
    if not st.session_state.get("auth_user_id"):
        url_usuario = str(st.secrets["SUPABASE_URL"]).rstrip("/") + "/auth/v1/user"
        resposta_usuario = requests.get(url_usuario, headers=cabecalhos_usuario(), timeout=15)
        resposta_usuario.raise_for_status()
        st.session_state["auth_user_id"] = resposta_usuario.json()["id"]
    perfil = consultar("perfis_usuarios", "nome,perfil_global",
                      {"ativo": "eq.true", "auth_user_id": "eq." + st.session_state["auth_user_id"]})
    if not perfil:
        st.session_state.clear()
        st.error("Seu usuário não tem um perfil ativo neste aplicativo.")
        st.stop()
except (requests.RequestException, PermissionError):
    st.session_state.clear()
    st.warning("Sessão inválida ou acesso não autorizado. Entre novamente.")
    st.stop()

try:
    projetos = preparar(carregar_projetos())
except Exception as erro:
    st.error("Não foi possível consultar o Supabase.")
    st.info(f"Tipo do erro: {type(erro).__name__}")
    st.stop()

pagina_conta_usuario = st.Page(pagina_conta, title="Minha conta", icon="🔒")
pagina_principal = st.Page(pagina_dashboard, title="Visão executiva", icon="📊", default=True)
pagina_detalhe = st.Page(pagina_detalhes, title="Detalhes do projeto", icon="📁")
pagina_atas = st.Page(pagina_atas_ia, title="Análise de atas", icon="🤖")
pagina_equipes = st.Page(pagina_squads, title="Squads e acessos", icon="👥")
pagina_admin = st.Page(pagina_administracao, title="Administração", icon="🛡️")
pagina_central = st.Page(pagina_central_atas, title="Central de aprovações", icon="📥")
pagina_gestao = st.Page(pagina_gerenciar_portfolio, title="Gerenciar projetos", icon="📝")
with st.sidebar:
    st.markdown("## ProjectFlow AI")
    st.caption("PROJECT PORTFOLIO")
    st.caption("Conectado: " + st.session_state.get("email_usuario", ""))
    st.caption("Perfil: " + str(perfil[0].get("perfil_global", "não identificado")))
    st.caption("Versão: purple-midnight-20261023-01")
    if st.button("🚪 Sair", key="logout_button", use_container_width=True):
        st.session_state.clear()
        st.rerun()

paginas = [pagina_principal, pagina_detalhe, pagina_atas, pagina_equipes, pagina_conta_usuario]
if perfil[0].get("perfil_global") == "admin":
    paginas.extend([pagina_central, pagina_gestao, pagina_admin])
navegacao = st.navigation(paginas)
if st.session_state.pop("ir_para_visao_executiva", False):
    st.switch_page(pagina_principal)
navegacao.run()

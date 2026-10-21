import streamlit as st
from datetime import date

st.set_page_config(page_title="ProjectFlow AI", page_icon="📊", layout="wide")
st.title("ProjectFlow AI")
st.caption("Painel de gestão de projetos • Protótipo com dados fictícios")

projects = [
    {"nome": "Implantação ERP", "responsavel": "Ana Souza", "prazo": "2026-11-30", "pendencias": 1, "status": "em_andamento"},
    {"nome": "Dashboard Executivo", "responsavel": "Bruno Lima", "prazo": "2026-11-15", "pendencias": 0, "status": "em_andamento"},
    {"nome": "Integração de APIs", "responsavel": "Carla Mendes", "prazo": "2026-10-10", "pendencias": 1, "status": "em_andamento"},
    {"nome": "Automação de Processos", "responsavel": "Diego Costa", "prazo": "2026-10-15", "pendencias": 0, "status": "em_andamento"},
]

from farol import calcular_farol

for p in projects:
    p["farol"] = calcular_farol(date.fromisoformat(p["prazo"]), p["pendencias"], p["status"])

with st.sidebar:
    st.header("ProjectFlow AI")
    st.write("Visão executiva")
    filtro = st.selectbox("Filtrar por farol", ["Todos", "Verde", "Amarelo", "Vermelho"])
    st.info("Modo demonstração: nenhum dado real é utilizado.")

visible = [p for p in projects if filtro == "Todos" or p["farol"] == filtro.lower()]
cols = st.columns(4)
cols[0].metric("Projetos", len(projects))
cols[1].metric("🟢 Em dia", sum(p["farol"] == "verde" for p in projects))
cols[2].metric("🟡 Atenção", sum(p["farol"] == "amarelo" for p in projects))
cols[3].metric("🔴 Atrasados", sum(p["farol"] == "vermelho" for p in projects))

st.subheader("Farol dos projetos")
icons = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴"}
for p in visible:
    with st.container(border=True):
        a, b, c = st.columns([3, 2, 2])
        a.markdown(f"**{p['nome']}**")
        a.caption(f"Responsável: {p['responsavel']}")
        b.write(f"Entrega: {date.fromisoformat(p['prazo']).strftime('%d/%m/%Y')}")
        b.write(f"Pendências abertas: {p['pendencias']}")
        c.markdown(f"### {icons[p['farol']]} {p['farol'].capitalize()}")

st.divider()
st.caption("Próximas etapas: integração segura com Supabase, leitura de atas, IA, e-mail diário e PPT semanal.")

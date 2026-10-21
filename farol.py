"""Regras de negócio do farol de projetos."""
from datetime import date


def calcular_farol(prazo: date, pendencias_abertas: int, status: str = "em_andamento", hoje: date | None = None) -> str:
    """Retorna verde, amarelo ou vermelho. Projetos concluídos não são tratados como atrasados."""
    hoje = hoje or date.today()
    if status == "concluido":
        return "verde"
    if prazo < hoje:
        return "vermelho"
    if pendencias_abertas > 0:
        return "amarelo"
    return "verde"

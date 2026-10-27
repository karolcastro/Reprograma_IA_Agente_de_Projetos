"""Cálculos puros de capacidade e FTE, sem dependência do Streamlit ou Supabase."""
from typing import Iterable


def summarize_capacity(capacity_percent: int | None, allocations_percent: Iterable[int | None]) -> dict:
    """Resume a capacidade de um recurso e suas alocações planejadas.

    None representa dado não informado e nunca é convertido silenciosamente em zero.
    100 pontos percentuais equivalem a 1,0 FTE.
    """
    allocations = list(allocations_percent)
    missing = sum(value is None for value in allocations)
    assigned_percent = sum(int(value) for value in allocations if value is not None)
    assigned_fte = round(assigned_percent / 100, 2)
    available_fte = round(capacity_percent / 100, 2) if capacity_percent is not None else None
    remaining_fte = (
        round((capacity_percent - assigned_percent) / 100, 2)
        if capacity_percent is not None and missing == 0
        else None
    )

    if capacity_percent is None:
        status = "Capacidade não definida"
    elif missing:
        status = "Alocações incompletas"
    elif assigned_percent > capacity_percent:
        status = "Sobrealocado"
    elif assigned_percent == capacity_percent:
        status = "Capacidade completa"
    else:
        status = "Capacidade disponível"

    return {
        "assigned_percent": assigned_percent,
        "assigned_fte": assigned_fte,
        "available_percent": capacity_percent,
        "available_fte": available_fte,
        "remaining_fte": remaining_fte,
        "missing_allocations": missing,
        "status": status,
    }

from datetime import date
from farol import calcular_farol


def test_verde():
    assert calcular_farol(date(2026, 12, 1), 0, hoje=date(2026, 10, 20)) == "verde"


def test_amarelo():
    assert calcular_farol(date(2026, 12, 1), 2, hoje=date(2026, 10, 20)) == "amarelo"


def test_vermelho_com_pendencia():
    assert calcular_farol(date(2026, 10, 1), 1, hoje=date(2026, 10, 20)) == "vermelho"


def test_vermelho_sem_pendencia():
    assert calcular_farol(date(2026, 10, 1), 0, hoje=date(2026, 10, 20)) == "vermelho"

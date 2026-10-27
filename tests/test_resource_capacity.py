from resource_capacity import summarize_capacity


def test_full_time_resource_fully_allocated():
    result = summarize_capacity(100, [60, 40])
    assert result["assigned_fte"] == 1.0
    assert result["available_fte"] == 1.0
    assert result["remaining_fte"] == 0.0
    assert result["status"] == "Capacidade completa"


def test_overallocated_resource():
    result = summarize_capacity(80, [60, 40])
    assert result["assigned_fte"] == 1.0
    assert result["remaining_fte"] == -0.2
    assert result["status"] == "Sobrealocado"


def test_unknown_capacity_is_not_assumed():
    result = summarize_capacity(None, [25])
    assert result["available_fte"] is None
    assert result["remaining_fte"] is None
    assert result["status"] == "Capacidade não definida"


def test_missing_allocation_makes_balance_incomplete():
    result = summarize_capacity(100, [50, None])
    assert result["assigned_percent"] == 50
    assert result["missing_allocations"] == 1
    assert result["remaining_fte"] is None
    assert result["status"] == "Alocações incompletas"


def test_empty_allocations_means_full_capacity_available():
    result = summarize_capacity(100, [])
    assert result["assigned_fte"] == 0.0
    assert result["remaining_fte"] == 1.0
    assert result["status"] == "Capacidade disponível"

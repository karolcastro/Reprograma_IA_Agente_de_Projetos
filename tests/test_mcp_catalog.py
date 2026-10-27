from mcp_projectflow.catalog import DemoRepository


def test_demo_projects_only_for_demo_actor():
    repo = DemoRepository()
    assert len(repo.list_projects("demo-user")) == 2
    assert repo.list_projects("outro-usuario") == []


def test_demo_project_isolation():
    repo = DemoRepository()
    assert repo.get_project("demo-user", "demo-001").nome.startswith("Migração")
    assert repo.get_project("outro-usuario", "demo-001") is None
    assert repo.get_project("demo-user", "inexistente") is None

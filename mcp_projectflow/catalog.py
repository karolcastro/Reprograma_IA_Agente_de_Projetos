"""Contratos e adaptadores testáveis, independentes de credenciais externas."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Project:
    id: str
    nome: str
    status: str


class ProjectRepository(Protocol):
    def list_projects(self, actor_id: str) -> list[Project]: ...
    def get_project(self, actor_id: str, project_id: str) -> Project | None: ...


class DemoRepository:
    """Dados sintéticos para validar MCP sem Supabase, Teams ou SharePoint."""

    _projects = (
        Project("demo-001", "Migração de dados (demonstração)", "em_dia"),
        Project("demo-002", "Integração de sistemas (demonstração)", "atencao"),
    )

    def list_projects(self, actor_id: str) -> list[Project]:
        if actor_id != "demo-user":
            return []
        return list(self._projects)

    def get_project(self, actor_id: str, project_id: str) -> Project | None:
        return next((p for p in self.list_projects(actor_id) if p.id == project_id), None)

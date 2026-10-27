"""Servidor MCP local, somente leitura e com dados fictícios.

Execução: python -m mcp_projectflow.server
Transporte: stdio (não expõe porta HTTP).
Nunca conectar diretamente este servidor demo ao banco de produção.
"""
from dataclasses import asdict
from mcp.server.fastmcp import FastMCP
from .catalog import DemoRepository

mcp = FastMCP("projectflow-ai-demo")
repository = DemoRepository()


@mcp.tool()
def listar_projetos() -> list[dict]:
    """Lista projetos fictícios autorizados para o usuário de demonstração."""
    return [asdict(p) for p in repository.list_projects("demo-user")]


@mcp.tool()
def consultar_projeto(projeto_id: str) -> dict:
    """Consulta projeto fictício pelo identificador; não permite alterações."""
    project = repository.get_project("demo-user", projeto_id)
    return asdict(project) if project else {"erro": "Projeto não encontrado ou sem acesso"}


@mcp.resource("projectflow://demo/capabilities")
def capacidades() -> str:
    """Capacidades demonstradas e integrações ainda não conectadas."""
    return (
        "Modo: demonstração local; dados sintéticos; ferramentas somente leitura. "
        "Supabase de produção, SharePoint e Teams não conectados. "
        "Escrita exige autenticação, autorização e aprovação humana futuras."
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""Cliente MCP de prova de conceito usando stdio, sem credenciais externas.

Execução: python -m mcp_projectflow.client
"""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_demo() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_projectflow.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {"listar_projetos", "consultar_projeto"} <= names
            result = await session.call_tool("listar_projetos", arguments={})
            if result.isError:
                raise RuntimeError("Falha ao consultar o servidor MCP")
            print("MCP validado: ferramentas descobertas e listar_projetos executada.")
            for item in result.content:
                if getattr(item, "text", None):
                    print(item.text)


if __name__ == "__main__":
    asyncio.run(run_demo())

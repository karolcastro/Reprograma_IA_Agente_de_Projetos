"""Teste de contrato real cliente-servidor via MCP/stdio."""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _check():
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_projectflow.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {"listar_projetos", "consultar_projeto"} <= {t.name for t in tools.tools}
            result = await session.call_tool("consultar_projeto", {"projeto_id": "demo-001"})
            assert not result.isError
            assert any("demo-001" in getattr(item, "text", "") for item in result.content)


def test_stdio_contract():
    asyncio.run(_check())

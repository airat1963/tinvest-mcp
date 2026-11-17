"""MCP-сервер: регистрирует три инструмента и обслуживает stdio."""

from __future__ import annotations

import asyncio
import importlib
import json
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .schemas import HANDLERS, TOOLS


server = Server("tinvest-mcp")


def _load_handler(path: str):
    module_name, func_name = path.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(**t) for t in TOOLS]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler_path = HANDLERS.get(name)
    if not handler_path:
        return [TextContent(type="text", text=f"Неизвестный инструмент: {name}")]

    handler = _load_handler(handler_path)
    try:
        # handlers синхронные (t_tech.invest sync) — уводим в поток
        result = await asyncio.to_thread(handler, **arguments)
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": type(e).__name__, "message": str(e)}, ensure_ascii=False),
        )]

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    # подхватываем .env, если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    if not os.getenv("T_SANDBOX_TOKEN"):
        raise SystemExit("T_SANDBOX_TOKEN не задан (см. .env.example)")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
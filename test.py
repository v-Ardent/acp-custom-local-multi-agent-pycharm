import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from ollama import AsyncClient

URL = "http://127.0.0.1:64462/stream"   # confirm the port in Settings > Tools > MCP Server

async def main():
    async with asyncio.timeout(15):
        async with streamable_http_client(URL) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                print([t.name for t in tools.tools])

    r = await asyncio.wait_for(
        AsyncClient().chat(model="qwen3:8b", messages=[{"role": "user", "content": "Hi"}]),
        timeout=120,
    )
    print(r.message.content)

asyncio.run(main())
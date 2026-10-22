import asyncio
import logging

import chromadb
from chromadb import WhereDocument
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
import json

TOOLS = "tools"
CHAT_HISTORY = "chat_history"

class rag:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./memoire")


    def add_to_collection(self, document: str, id: str,metadata: dict[str, str | int | float | bool] | None = None) -> str:
        """Store a new memory. Chroma metadata must be flat scalars and non-empty."""
        col = self.client.get_or_create_collection(CHAT_HISTORY)
        col.add(ids=[id], documents=[document], metadatas=[metadata] if metadata else None)
        return f"stored {id}"


    def update_collection(self, document: str, id: str) -> str:
        col = self.client.get_collection(CHAT_HISTORY)
        col.update(ids=[id], documents=[document])
        return f"updated {id}"


    def search_memory(self, query: str, collection:str, contains: str | None = None, n_results: int = 3):
        """Semantic search. Returns a flat, JSON-safe list of hits."""
        if collection not in (TOOLS, CHAT_HISTORY):
            raise ValueError(f"Unknown collection '{collection}'")
        try:
            col = self.client.get_collection(collection)
        except Exception as e:
            raise ValueError(f"Collection '{collection}' not found") from e

        where_document: WhereDocument | None = None

        if contains:
            where_document = {"$contains": contains}

        return col.query(
            query_texts=[query],
            n_results=n_results,
            where_document=where_document
        )

async def add_mcp_tools_to_collection(collection):
    MCP_URL = "http://127.0.0.1:64462/stream"
    async with streamable_http_client(MCP_URL) as streams:
        async with ClientSession(streams[0], streams[1]) as mcp:
            await mcp.initialize()

            tool_result = await mcp.list_tools()
            """print("tool_result:")
            print(json.dumps(
                tool_result.model_dump(mode="json"),
                indent=2,
                ensure_ascii=False
            ))"""


            for tool in tool_result.tools:
                collection.add(
                    ids=[tool.name],
                    documents=[
                        f"Tool name: {tool.name}\n"
                        f"Description: {tool.description or ''}"
                    ],
                    metadatas=[{
                        "title": getattr(tool, "title", None) or "",
                        "input_schema": json.dumps(
                            getattr(tool, "inputSchema", {}),
                            ensure_ascii=False
                        ),
                        "execution": json.dumps(
                            getattr(tool, "execution", None),
                            ensure_ascii=False,
                            default=str
                        ),
                        "output_schema": json.dumps(
                            getattr(tool, "outputSchema", None),
                            ensure_ascii=False,
                            default=str
                        ),
                        "icons": json.dumps(
                            getattr(tool, "icons", None),
                            ensure_ascii=False,
                            default=str
                        ),
                        "annotations": json.dumps(
                            getattr(tool, "annotations", None),
                            ensure_ascii=False,
                            default=str
                        ),
                        "meta": json.dumps(
                            getattr(tool, "meta", None),
                            ensure_ascii=False,
                            default=str
                        ),
                    }]
                )

if __name__ == "__main__":
    rag = rag()
    collection = rag.client.get_or_create_collection(TOOLS)
    asyncio.run(add_mcp_tools_to_collection(collection))
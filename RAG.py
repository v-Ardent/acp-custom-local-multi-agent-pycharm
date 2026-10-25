import asyncio
from typing import cast
import chromadb
from chromadb import WhereDocument
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
import json
from config import pycharm_MCP_URL

TOOLS = "tools"
CHAT_HISTORY = "chat_history"


class rag:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./memoire")


    def add_to_collection(self, document: str, id: str,metadata: dict[str, str | int | float | bool] | None = None) -> str:
        """Store a new memory. Chroma metadata must be flat scalars and non-empty."""
        col = self.client.get_or_create_collection(CHAT_HISTORY)
        col.upsert(ids=[id], documents=[document], metadatas=[metadata] if metadata else None)
        return f"stored {id}"


    def update_collection(self, document: str, id: str) -> str:
        col = self.client.get_collection(CHAT_HISTORY)
        col.update(ids=[id], documents=[document])
        return f"updated {id}"


    def search_memory(self, query: str, collection:str, n_results: int = 3, contains: str | None = None):
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

        res = col.query(
            query_texts=[query],
            n_results=min(n_results, col.count()),
            where_document=where_document
        )

        hits = []
        for i, doc_id in enumerate(res["ids"][0]):
            hit = {
                "id": doc_id,
                "text": res["documents"][0][i],
                "distance": res["distances"][0][i],
            }
            if collection == TOOLS:
                hit["input_schema"] = json.loads(cast(str, res["metadatas"][0][i]["input_schema"]))
            hits.append(hit)
        return hits


async def add_mcp_tools_to_collection(store: rag) -> None:
    async with streamable_http_client(pycharm_MCP_URL) as streams:
        async with ClientSession(streams[0], streams[1]) as mcp:
            await mcp.initialize()
            tools = (await mcp.list_tools()).tools

    try:
        store.client.delete_collection(TOOLS)
    except Exception:
        pass
    collection = store.client.create_collection(TOOLS)

    collection.add(
        ids=[t.name for t in tools],
        documents=[f"{t.name}: {t.description or ''}".strip() for t in tools],
        metadatas=[
            {
                "title": getattr(t, "title", None) or "",
                "description": t.description or t.name,
                "input_schema": json.dumps(
                    t.input_schema or {"type": "object", "properties": {}},
                    ensure_ascii=False,
                ),
            }
            for t in tools
        ],
    )
    print(f"Indexed {len(tools)} tools: {[t.name for t in tools]}")


if __name__ == "__main__":
    res = asyncio.run(rag().search_memory(query="read", collection=TOOLS))
    print([res["id"] for res in res])
    #asyncio.run(add_mcp_tools_to_collection(rag()))
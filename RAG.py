import asyncio
from typing import Any
import chromadb
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
import json
from config import PYCHARM_MCP_URL, CHROMA_DB_PATH

TOOLS = "tools"
CHAT_HISTORY = "chat_history"


class rag:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)


    def add_to_collection(self, document: str, id: str,metadata: dict[str, str | int | float | bool] | None = None) -> str:
        """Store a new memory. Chroma metadata must be flat scalars and non-empty."""
        col = self.client.get_or_create_collection(CHAT_HISTORY)
        col.upsert(ids=[id], documents=[document], metadatas=[metadata] if metadata else None)
        return f"stored {id}"


    def update_collection(self, document: str, id: str) -> str:
        col = self.client.get_collection(CHAT_HISTORY)
        col.update(ids=[id], documents=[document])
        return f"updated {id}"


    def search_memory(self, query: list[str], collection: str, n_results: int = 6, contains: str | None = None):
        """Semantic search per query. Returns a list of hit lists: list[list[dict]]."""
        if collection not in (TOOLS, CHAT_HISTORY):
            raise ValueError(f"Unknown collection '{collection}'")
        try:
            col = self.client.get_collection(collection)
        except Exception as e:
            raise ValueError(f"Collection '{collection}' not found") from e

        if col.count() == 0:
            return [[] for _ in query]

        where_document: dict | None = None
        if contains:
            where_document = {"$contains": contains}

        all_hits: list[list[dict]] = []
        actual_n_results = min(n_results, col.count())

        for q in query:
            res = col.query(
                query_texts=[q],
                n_results=actual_n_results,
                where_document=where_document
            )

            query_hits: list[dict] = []

            if res and res.get("ids") and res["ids"][0]:
                for i, doc_id in enumerate(res["ids"][0]):
                    hit: dict[str, Any] = {
                        "id": doc_id,
                        "text": res["documents"][0][i],
                        "distance": res["distances"][0][i],
                    }

                    if collection == TOOLS and res.get("metadatas") and res["metadatas"][0]:
                        meta = res["metadatas"][0][i]
                        if meta and meta.get("input_schema"):
                            schema_val = meta["input_schema"]
                            hit["input_schema"] = json.loads(schema_val) if isinstance(schema_val, str) else schema_val

                    query_hits.append(hit)

            all_hits.append(query_hits)

        seen_ids = set()
        flat_hits: list[dict] = []

        for sublist in all_hits:
            for hit in sublist:
                if hit["id"] not in seen_ids:
                    seen_ids.add(hit["id"])
                    flat_hits.append(hit)

        return flat_hits


async def add_mcp_tools_to_collection(store: rag) -> None:
    async with streamable_http_client(PYCHARM_MCP_URL) as streams:
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
    pass
    """
    run this one time to store the pycharm_MCP into the chromaDB : asyncio.run(add_mcp_tools_to_collection(rag()))
    """
    #asyncio.run(add_mcp_tools_to_collection(rag()))
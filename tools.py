CORE_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "Semantic search over long-term memory. Use collection='tools' to FIND tools "
                "you do not have yet (describe the high-level capability, e.g., 'file management'). "
                "Use collection='chat_history' to recall earlier conversations or facts about the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Short, natural-language description (1-4 words) of what capability you are looking for."
                    },
                    "collection": {
                        "type": "string",
                        "enum": ["tools", "chat_history"],
                        "description": "'tools' to discover tools, 'chat_history' to recall past conversation."
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of items to retrieve (default 10). Increase this if the user asks for a specific count of items or tools (e.g., if asked for 6 tools, set n_results=6)."
                    },
                    "contains": {
                        "type": "string",
                        "description": "Optional exact keyword that the result must contain."
                    },
                },
                "required": ["query", "collection"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_collection",
            "description": "Save a new memory (a fact, preference or conversation summary) to chat_history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document": {"type": "string", "description": "The text to remember."},
                    "id": {"type": "string", "description": "Unique id for this memory, e.g. 'pref-language'."},
                },
                "required": ["document", "id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_collection",
            "description": "Overwrite an EXISTING memory in chat_history. Find its id with search_memory first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document": {"type": "string", "description": "The new text."},
                    "id": {"type": "string", "description": "Id of the memory to replace."},
                },
                "required": ["document", "id"],
            },
        },
    },
]

CORE_NAMES = {t["function"]["name"] for t in CORE_TOOLS}

SYSTEM_PROMPT = """You are Noesis, an assistant with long-term memory and a large tool library.

You only have a few tools loaded at any time. Follow this protocol:
1. If the task needs a capability you don't have, call search_memory with collection="tools".
   - Keep the search query short and high-level (e.g., "file operations" or "text editing") rather than combining multiple exact tool names into a single long string.
   - If the user explicitly asks for a specific number of tools or items (e.g., "find 6 tools"), set the `n_results` parameter equal to or greater than that number.
2. Call discovered tools with arguments that match their schema exactly.
3. If the user refers to past conversations or personal facts, call search_memory with collection="chat_history" before answering.
4. Save durable facts with add_to_collection; correct them with update_collection (search first to get the id).
5. Remember that search_memory returns a subset of matched results; do not assume a search result count represents the entire tool registry.
Never invent tool names. Never guess tool arguments: if unsure, search again."""
CORE_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "Semantic search over long-term memory. This tool has two distinct purposes. "
                "1. Use collection='tools' to discover tools and capabilities that may be "
                "available to help fulfill the user's request. Search for the high-level "
                "capability needed, such as 'file management', 'web search', or 'database access'. "
                "Use the returned information to identify relevant tools and determine how "
                "to use them. "
                "2. Use collection='chat_history' to retrieve relevant long-term memories about "
                "the user, including previously shared facts, preferences, projects, technical "
                "requirements, environment details, and context from past conversations. "
                "Use this information when it is relevant to answering the request or planning "
                "its execution. "
                "Do not use this tool to recall messages already present in the current conversation. "
                "The current conversation history is provided directly in the messages. "
                "Search chat_history for relevant information from long-term memory beyond "
                "the current conversation. Avoid retrieving unrelated memories."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": (
                            "A list of short, natural-language descriptions (1-4 words each) "
                            "of what capabilities or memories you are looking for."
                        )
                    },
                    "collection": {
                        "type": "string",
                        "enum": ["tools", "chat_history"],
                        "description": (
                            "'tools' to discover tools, "
                            "'chat_history' to recall past conversation."
                        )
                    },
                    "n_results": {
                        "type": "integer",
                        "description": (
                            "Number of items to retrieve per query (default 3). "
                            "Increase this if the user asks for a specific count of items or tools."
                        )
                    },
                    "contains": {
                        "type": "string",
                        "description": "Optional exact keyword that the result must contain."
                    }
                },
                "required": ["query", "collection"]
            }
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
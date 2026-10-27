import asyncio
from typing import Any
from mcp.client.streamable_http import streamable_http_client
from ollama import AsyncClient
import json
from mcp import ClientSession
import logging
from tools import CORE_TOOLS
from RAG import rag, TOOLS
from agent_workflow import run_workflow, AgentHistory
from config import PYCHARM_MCP_URL, MAX_ACTIVE_DISCOVERED
from acp import (
    PROTOCOL_VERSION,
    Agent,
    InitializeResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    SetSessionModeResponse,
    run_agent,
    update_agent_message_text,
)
from acp.interfaces import Client
from acp.schema import (
    ClientCapabilities,
    HttpMcpServer,
    Implementation,
    McpServerStdio,
    SseMcpServer,
    AgentCapabilities, PromptCapabilities, McpCapabilities, SessionCapabilities,
    AgentAuthCapabilities, LogoutCapabilities, SessionDeleteCapabilities,
)


def extract_text(block: Any) -> str:
    """Extract text from a dictionary or an object containing a text attribute."""
    if isinstance(block, dict):
        return str(block.get("text", ""))

    text = getattr(block, "text", None)

    return text if isinstance(text, str) else ""


class NoesisAgent(Agent):
    """Manage agent sessions, MCP connections, tool discovery, and workflow execution."""
    _conn: Client

    def __init__(self) -> None:
        """Initialize the LLM client, MCP state, RAG system, and session history."""
        self._next_session_id = 0
        self._sessions: set[str] = set()

        self._llm = AsyncClient()
        self._mcp: ClientSession | None = None
        self._ollama_tools: list[dict[str, Any]] = []
        self._mcp_ready = asyncio.Event()
        self._mcp_stop = asyncio.Event()
        self._mcp_task: asyncio.Task | None = None
        self._mcp_error: Exception | None = None
        self._rag = rag()
        self._discovered: dict[str, dict[str, dict]] = {}
        self._mcp_cfg: HttpMcpServer | None = None
        self.context_size = 0
        self.session_history: dict[str, AgentHistory] = {}


    async def _run_mcp(self) -> None:
        """Establish the MCP connection, initialize tools, and wait for shutdown."""
        try:
            cfg = self._mcp_cfg
            url = cfg.url if cfg and cfg.name == "pycharm_MCP" else PYCHARM_MCP_URL
            async with streamable_http_client(url) as streams:
                async with ClientSession(streams[0], streams[1]) as mcp:
                    await mcp.initialize()
                    self._ollama_tools = list(CORE_TOOLS)
                    self._mcp = mcp
                    self._mcp_ready.set()
                    await self._mcp_stop.wait()
        except Exception as exc:
            logging.exception("MCP connection failed")
            self._mcp_error = exc
        finally:
            self._mcp = None
            self._mcp_ready.set()


    def _active_tools(self, session_id: str) -> list[dict]:
        return self._ollama_tools + list(self._discovered.get(session_id, {}).values())


    async def _get_mcp(self) -> ClientSession:
        """Start the MCP connection if necessary and return the active session."""
        if self._mcp_task is None:
            self._mcp_task = asyncio.create_task(self._run_mcp())
        await self._mcp_ready.wait()
        if self._mcp is None:
            self._mcp_task = None
            raise RuntimeError(f"MCP unavailable: {self._mcp_error}")
        return self._mcp


    async def close(self) -> None:
        """Signal the MCP connection to stop and wait for its task to finish."""
        self._mcp_stop.set()
        if self._mcp_task:
            await self._mcp_task


    def on_connect(self, conn: Client) -> None:
        """Store the ACP client connection used to send session updates."""
        self._conn = conn


    async def initialize(self, protocol_version: int, client_capabilities: ClientCapabilities | None = None, client_info: Implementation | None = None, **kwargs: Any) -> InitializeResponse:
        """Negotiate protocol capabilities and return the agent's metadata."""
        agent_capabilities = AgentCapabilities(
            load_session=True,
            prompt_capabilities=PromptCapabilities(
                image=True,
                audio=True,
                embeddedContext=True,
                _meta=None
            ),
            mcp_capabilities=McpCapabilities(
                http=True,
                _meta=None
            ),
            auth=AgentAuthCapabilities(
                logout=LogoutCapabilities(_meta=None),
                _meta=None
            ),
            session_capabilities=SessionCapabilities(
                delete=SessionDeleteCapabilities(_meta=None),
                additionalDirectories=None,
                _meta=None
            ),
            position_encoding=None,
            field_meta=None
        )
        return InitializeResponse(
            protocolVersion=PROTOCOL_VERSION,
            agent_capabilities=agent_capabilities,
            agentInfo=Implementation(
                name="Noesis",
                title="example",
                version="0.1.0",
                _meta=None
            ),
            authMethods=None,
            _meta=None
        )


    async def new_session(
            self,
            cwd: str,
            additional_directories: list[str] | None = None,
            mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
            **kwargs: Any,
    ) -> NewSessionResponse:
        """Create a session, assign its ID, and configure the requested HTTP MCP server."""
        logging.info("Received new session request")
        session_id = str(self._next_session_id)
        self._next_session_id += 1
        self._sessions.add(session_id)

        for s in mcp_servers or []:
            if isinstance(s, HttpMcpServer):
                self._mcp_cfg = s
                break

        return NewSessionResponse(sessionId=session_id, configOptions=None, _meta=None)


    async def load_session(
            self,
            cwd: str,
            session_id: str,
            mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
            additional_directories: list[str] | None = None,
            **kwargs: Any,
    ) -> LoadSessionResponse | None:
        """Register an existing session so it can continue processing requests."""
        logging.info("Received load session request %s", session_id)
        self._sessions.add(session_id)
        return LoadSessionResponse(_meta=None, configOptions=None)


    async def set_session_mode(self, session_id: str, mode_id: str, **kwargs: Any) -> SetSessionModeResponse | None:
        """Handle a session mode change notification."""
        logging.info("Received set session mode request %s -> %s", session_id, mode_id)
        return SetSessionModeResponse(_meta=None)

    async def _call_tool(self, session_id: str, name: str, args: dict[str, Any]) -> str:
        """Execute a RAG or MCP tool and return its result."""
        discovered = self._discovered.setdefault(session_id, {})

        try:
            if name == "search_memory":
                hits = await asyncio.to_thread(self._rag.search_memory, **args)
                if args.get("collection") == TOOLS:
                    for h in hits:
                        discovered[h["id"]] = {
                            "type": "function",
                            "function": {
                                "name": h["id"],
                                "description": h.get("description") or h["text"],
                                "parameters": h["input_schema"],
                            },
                        }
                    while len(discovered) > MAX_ACTIVE_DISCOVERED:
                        discovered.pop(next(iter(discovered)))
                    return json.dumps({"tools_now_available": [h["id"] for h in hits]})
                return json.dumps(hits, ensure_ascii=False)

            if name == "add_to_collection":
                return await asyncio.to_thread(self._rag.add_to_collection, **args)
            if name == "update_collection":
                return await asyncio.to_thread(self._rag.update_collection, **args)

            if name in discovered and self._mcp:
                result = await self._mcp.call_tool(name, args)
                if result.structured_content is not None:
                    out = json.dumps(result.structured_content, ensure_ascii=False)
                else:
                    out = "\n".join(getattr(b, "text", "") for b in result.content)
                return f"Tool error: {out}" if result.is_error else out

            return f"Error: unknown tool '{name}'. Use search_memory(collection='tools') to find it."
        except Exception as e:
            logging.exception("tool %s failed (args=%s)", name, args)
            return f"Error calling {name}: {e}"


    async def prompt(self, session_id: str, prompt: Any, **kwargs: Any) -> PromptResponse:
        """Process a user prompt through the workflow and return the completion response."""
        self._sessions.add(session_id)
        text = "\n".join(extract_text(b) for b in prompt)

        try:
            await self._get_mcp()
            await run_workflow(text, self._send, session_id, self._call_tool, self._active_tools, self.session_history)

        except Exception as exc:
            await self._send(
                session_id, update_agent_message_text(str(exc))
            )

        return PromptResponse(stop_reason="end_turn", usage=None, field_meta=None)


    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        """Handle a cancellation notification for the specified session."""
        logging.info("Received cancel notification for session %s", session_id)


    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle an extension method call and return a placeholder response."""
        logging.info("Received extension method call: %s", method)
        return {"example": "response"}


    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        """Handle an extension notification."""
        logging.info("Received extension notification: %s", method)


    async def _send(self, session_id: str, update: Any) -> None:
        """Send an agent update to the connected ACP client."""
        await self._conn.session_update(session_id, update)


async def main() -> None:
    """Configure logging, run the agent, and clean up its resources."""
    logging.basicConfig(level=logging.INFO)
    agent = NoesisAgent()

    try:
        await run_agent(agent)
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
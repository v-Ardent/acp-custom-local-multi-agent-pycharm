import asyncio
from typing import Any
from pathlib import Path
from dotenv import load_dotenv
from ollama import AsyncClient
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import logging
from acp import update_user_message_text
from RAG import search_memory
from acp import (
    PROTOCOL_VERSION,
    Agent,
    InitializeResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    SetSessionModeResponse,
    run_agent,
)
from acp.interfaces import Client
from acp.schema import (
    ClientCapabilities,
    HttpMcpServer,
    Implementation,
    McpServerStdio,
    SseMcpServer,
    UserMessageChunk, AgentCapabilities, PromptCapabilities, McpCapabilities, SessionCapabilities,
    AgentAuthCapabilities, LogoutCapabilities, SessionDeleteCapabilities,
)

RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / ".env")

MCP_URL = "http://127.0.0.1:64462/stream"
OLLAMA_MODEL = "gemma4:e4b"


def extract_text(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("text", ""))

    text = getattr(block, "text", None)

    return text if isinstance(text, str) else ""


class NoesisAgent(Agent):
    _conn: Client

    def __init__(self) -> None:
        self._next_session_id = 0
        self._sessions: set[str] = set()

        self._llm = AsyncClient()
        self._mcp: ClientSession | None = None
        self._ollama_tools: list[dict[str, Any]] = []
        self._mcp_ready = asyncio.Event()
        self._mcp_stop = asyncio.Event()
        self._mcp_task: asyncio.Task | None = None
        self._mcp_error: Exception | None = None


    async def _run_mcp(self) -> None:
        try:
            async with streamable_http_client(MCP_URL) as streams:
                async with ClientSession(streams[0], streams[1]) as mcp:
                    await mcp.initialize()

                    tool_result = await mcp.list_tools()
                    selected = tool_result.tools[:2]
                    self._ollama_tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": t.name,
                                "description": t.description or t.name,
                                "parameters": t.input_schema,
                            },
                        }
                        for t in selected
                    ]
                    logging.info("MCP ready, tools: %s", [t.name for t in selected])

                    self._mcp = mcp
                    self._mcp_ready.set()
                    await self._mcp_stop.wait()
        except Exception as exc:
            logging.exception("MCP connection failed")
            self._mcp_error = exc
        finally:
            self._mcp = None
            self._mcp_ready.set()


    async def _get_mcp(self) -> ClientSession:
        if self._mcp_task is None:
            self._mcp_task = asyncio.create_task(self._run_mcp())
        await self._mcp_ready.wait()
        if self._mcp is None:
            raise RuntimeError(f"MCP unavailable: {self._mcp_error}")
        return self._mcp


    async def close(self) -> None:
        self._mcp_stop.set()
        if self._mcp_task:
            await self._mcp_task


    def on_connect(self, conn: Client) -> None:
        self._conn = conn


    async def _send_agent_message(self, session_id: str, content: Any) -> None:
        update = content if isinstance(content, UserMessageChunk) else UserMessageChunk(content=content, _meta=None, messageId=None, sessionUpdate="user_message_chunk")
        await self._conn.session_update(session_id, update)


    async def initialize(self, protocol_version: int, client_capabilities: ClientCapabilities | None = None, client_info: Implementation | None = None, **kwargs: Any) -> InitializeResponse:
        logging.info("Received initialize request")
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
        logging.info("Received new session request")
        session_id = str(self._next_session_id)
        self._next_session_id += 1
        self._sessions.add(session_id)
        return NewSessionResponse(sessionId=session_id, configOptions=None, _meta=None)


    async def load_session(
            self,
            cwd: str,
            session_id: str,
            mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
            additional_directories: list[str] | None = None,
            **kwargs: Any,
    ) -> LoadSessionResponse | None:
        logging.info("Received load session request %s", session_id)
        self._sessions.add(session_id)
        return LoadSessionResponse(_meta=None, configOptions=None)


    async def set_session_mode(self, session_id: str, mode_id: str, **kwargs: Any) -> SetSessionModeResponse | None:
        logging.info("Received set session mode request %s -> %s", session_id, mode_id)
        return SetSessionModeResponse(_meta=None)


    async def prompt(self, session_id, prompt, **kwargs):
        self._sessions.add(session_id)
        user_message = "".join(extract_text(b) for b in prompt)

        messages = [
            {"role": "system", "content": "You are Noesis. Use the available tools when needed to answer."},
            {"role": "user", "content": user_message},
        ]

        try:
            mcp = await self._get_mcp()

            for _ in range(5):
                response = await self._llm.chat(
                    model=OLLAMA_MODEL,
                    messages=messages,
                    tools=self._ollama_tools,
                    think=True,
                    options={"num_ctx": 16384},
                )
                msg = response.message
                messages.append(msg.model_dump(exclude_none=True))

                calls = msg.tool_calls or []
                if not calls:
                    await self._conn.session_update(
                        session_id, update_user_message_text(msg.content or "")
                    )
                    break

                for call in calls:
                    result = await mcp.call_tool(call.function.name, dict(call.function.arguments))
                    if result.structured_content is not None:
                        out = json.dumps(result.structured_content, ensure_ascii=False)
                    else:
                        out = "\n".join(getattr(b, "text", "") for b in result.content)
                    if result.is_error:
                        out = f"Tool error: {out}"
                    messages.append({"role": "tool", "tool_name": call.function.name, "content": out})
            else:
                await self._conn.session_update(session_id, update_user_message_text("tools calling ended"))

        except Exception as exc:
            await self._conn.session_update(session_id, update_user_message_text(str(exc)))

        return PromptResponse(stop_reason="end_turn", usage=None, field_meta=None)


    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        logging.info("Received cancel notification for session %s", session_id)


    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        logging.info("Received extension method call: %s", method)
        return {"example": "response"}


    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        logging.info("Received extension notification: %s", method)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    agent = NoesisAgent()

    try:
        await run_agent(agent)
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
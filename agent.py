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

MCP_URL = "[URL]"
OLLAMA_MODEL = "qwen3:8b"


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
        logging.info("Received prompt request for session %s", session_id)

        if session_id not in self._sessions:
            self._sessions.add(session_id)

        user_message = "".join(extract_text(block) for block in prompt)

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are Noesis. Your name is Noesis. Use the available tools when needed to answer."
                ),
            },
            {"role": "user", "content": user_message},
        ]

        try:
            async with streamable_http_client(MCP_URL) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as mcp:
                    await mcp.initialize()

                    tool_result = await mcp.list_tools()
                    selected_tools = tool_result.tools[:2]

                    logging.info("Total available tools: %d", len(tool_result.tools))
                    logging.info("Selected tools: %d", len(selected_tools))
                    logging.info(
                        "Selected tool names: %s",
                        [tool.name for tool in selected_tools],
                    )

                    ollama_tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description or tool.name,
                                "parameters": tool.input_schema,
                            },
                        }
                        for tool in selected_tools
                    ]

                    logging.info("Tools sent to Ollama: %d", len(ollama_tools))
                    logging.info(
                        "Tool names sent to Ollama: %s",
                        [tool["function"]["name"] for tool in ollama_tools],
                    )

                    llm = AsyncClient()

                    for _ in range(5):
                        response = await llm.chat(
                            model=OLLAMA_MODEL,
                            messages=messages,
                            tools=ollama_tools,
                            think=True,
                            options={"num_ctx": 16384},
                        )

                        assistant_message = response.message
                        messages.append(assistant_message.model_dump(exclude_none=True))

                        calls = assistant_message.tool_calls or []
                        logging.info(f"Thinking: {response.message.thinking}")                        # No more tool calls: return the final answer via ACP.
                        if not calls:
                            answer = assistant_message.content or ""
                            await self._conn.session_update(session_id, update_user_message_text(answer))
                            break

                        # 4. Execute each requested tool through MCP.
                        for call in calls:
                            name = call.function.name
                            arguments = dict(call.function.arguments)
                            result = await mcp.call_tool(name, arguments)

                            # 5. Feed the tool result back to the model.
                            if result.structured_content is not None:
                                tool_output = json.dumps(
                                    result.structured_content,
                                    ensure_ascii=False,
                                )
                            else:
                                tool_output = "\n".join(
                                    getattr(block, "text", "")
                                    for block in result.content
                                )

                            if result.is_error:
                                tool_output = f"Tool error: {tool_output}"

                            messages.append({
                                "role": "tool",
                                "tool_name": name,
                                "content": tool_output,
                            })
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
    await run_agent(NoesisAgent())

if __name__ == "__main__":
    asyncio.run(main())
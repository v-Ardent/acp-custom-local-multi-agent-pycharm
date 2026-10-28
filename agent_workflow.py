import json
import logging
from typing import Annotated, List, Callable, Any, Coroutine, TypedDict
import operator
from uuid import uuid4
from acp import update_agent_thought, update_agent_message_text, start_tool_call, update_tool_call, tool_content, text_block
from acp.schema import TextContentBlock, UsageUpdate, Cost, SessionNotification, SessionInfoUpdate
from langchain_core.messages import ToolMessage, AIMessage, AnyMessage, ToolCall
from pydantic import BaseModel, Field, ValidationError
from langgraph.graph import StateGraph, START, END
from langchain.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from config import MAX_CONTEXT_SIZE, LLM, MAX_ITERATIONS

llm = ChatOllama(
    model=LLM,
    reasoning=True,
    temperature=1,
    num_ctx = MAX_CONTEXT_SIZE,
)

class Verdict(BaseModel):
    """Submit the final review verdict once the code has been reviewed and tested."""
    is_validated: bool = Field(description="True only if all acceptance criteria are met.")
    feedback: str = Field(description="Review findings, test results, and required fixes.")


class Plan(BaseModel):
    """Submit the final execution plan. Call this once you have gathered all the
    information you need. Do not write the plan as plain text."""
    objective: str = Field(
        description="The overall goal derived from the user's prompt."
    )
    coder_instructions: List[str] = Field(
        description="Specific implementation tasks for the coder agent."
    )
    validator_instructions: List[str] = Field(
        description="Specific testing, security, and review tasks for the validator."
    )
    acceptance_criteria: List[str] = Field(
        description="Measurable conditions that must be satisfied before completion."
    )


class State(BaseModel):
    user_prompt: str
    plan: Plan | None = None
    completed_task: Annotated[list, operator.add] = Field(default_factory=list)
    response: Annotated[list[str], operator.add] = Field(default_factory=list)
    is_validated: bool = False
    iterations: int = 0
    session_id: str

class Turn(TypedDict):
    prompt: str
    answer: str

class AgentHistory(TypedDict, total=False):
    content: Any
    tool_messages: list[ToolMessage]
    turns: list[Turn]
    context_used: int


def format_plan(obj: BaseModel) -> str:
    def bullets(items): return "\n".join(f"- {i}" for i in items)
    if isinstance(obj, Plan):
        return (
            f"**Objective**\n{obj.objective}\n\n"
            f"**Coder instructions**\n{bullets(obj.coder_instructions)}\n\n"
            f"**Validator instructions**\n{bullets(obj.validator_instructions)}\n\n"
            f"**Acceptance criteria**\n{bullets(obj.acceptance_criteria)}"
        )
    elif isinstance(obj, Verdict):
        return (
            f"**is_validated**\n{obj.is_validated}\n\n"
            f"**feedback**\n{obj.feedback}\n\n"
        )
    return obj.model_dump_json(indent=2)


async def tool_call(
    max_tool_iterations: int,
    base_llm,
    tools: Callable[[str], list[dict[Any, Any]]],
    messages: list,
    session_id: str,
    tool_call_rag,
    send_to_acp,
    output_schema: type[BaseModel] | None = None,
    require_schema: bool = False,
    session_history: dict[str, AgentHistory] | None = None,
    agent_name: str = "",
):
    """Tool loop. If output_schema is given, the model submits its final answer by
    calling a tool named after the schema, so no extra structured-output call is needed."""
    schema_tool = output_schema.__name__ if output_schema else None

    if session_history is None:
        session_history = {}

    agent_history = session_history.setdefault(agent_name, {})
    tool_messages = agent_history.setdefault("tool_messages", [])

    for _ in range(max_tool_iterations):
        bound = tools(session_id) + ([output_schema] if output_schema else [])
        response = await base_llm.bind_tools(bound).ainvoke(messages)

        if not response.tool_calls:
            if output_schema and require_schema:
                messages.append(response)
                messages.append(
                    HumanMessage(content=f"Submit your answer by calling the {schema_tool} tool, not as plain text."))
                continue
            agent_history["content"] = response.content
            return response

        final: ToolCall | None = next((c for c in response.tool_calls if c["name"] == schema_tool), None)
        if final:
            final_id = final["id"] or f"{final['name']}-{uuid4()}"
            try:
                answer = output_schema(**final["args"])
                await send_to_acp(session_id, start_tool_call(final_id, f"Running {final['name']}", kind=None, status="in_progress", raw_input=final["args"]))
                logging.info(answer)
            except ValidationError as exc:
                messages.append(response)
                for c in response.tool_calls:
                    messages.append(ToolMessage(
                        content=f"Invalid {schema_tool}: {exc}. Call {schema_tool} again with valid fields.",
                        tool_call_id=c["id"],
                        name=c["name"],
                        status="error",
                    ))
                continue
            payload = answer.model_dump()
            logging.info(payload)

            await send_to_acp(
                session_id,
                update_tool_call(
                    final_id,
                    title=f"{final['name']} submitted",
                    status="completed",
                    raw_output=payload,
                    content=[tool_content(text_block(format_plan(answer)))],
                ),
            )
            agent_history["content"] = str(answer)
            return answer

        messages.append(response)
        for call in response.tool_calls:
            tool_name, arguments, call_id = call["name"], call["args"], call["id"]
            status = "success"

            await send_to_acp(
                session_id,
                start_tool_call(call_id, f"Running {tool_name}", kind="other",
                                status="in_progress", raw_input=arguments),
            )

            try:
                tool_result = await tool_call_rag(session_id, tool_name, arguments)
            except Exception as exc:
                status = "error"
                tool_result = f"Error executing tool {tool_name}: {exc}"

            result_text = tool_result if isinstance(tool_result, str) else json.dumps(tool_result, default=str)

            await send_to_acp(
                session_id,
                update_tool_call(
                    call_id,
                    title=f"Tool {tool_name} {'completed successfully' if status == 'success' else 'failed'}",
                    status="completed" if status == "success" else "failed",
                    raw_output=tool_result if status == "success" else result_text,
                    content=[tool_content(text_block(result_text[:5000]))],
                ),
            )

            tool_message = ToolMessage(
                content=result_text,
                artifact={"tool": tool_name, "args": arguments, "raw": tool_result},
                tool_call_id=call_id,
                name=tool_name,
                status=status,
            )
            messages.append(tool_message)
            tool_messages.append(tool_message)

    await send_to_acp(session_id, SessionNotification(sessionId=session_id, update=SessionInfoUpdate(title="max iteration exceeded", _meta=None,sessionUpdate="session_info_update", updatedAt=None),_meta=None))
    messages.append(HumanMessage(content="Answer now with the information you have."))
    answer = await base_llm.ainvoke(messages)
    agent_history["content"] = answer.content
    return answer


async def run_workflow(
    user_prompt: str,
    send_to_acp: Callable[[str, Any], Coroutine[Any, Any, None]],
    session_id: str,
    tool_call_rag: Callable[[str, str, dict[str, Any]], Coroutine[Any, Any, str]],
    tools: Callable[[str], list[dict[Any, Any]]],
    session_history : dict[str, AgentHistory]
):
    session_history = session_history if session_history is not None else {}
    turns = session_history.setdefault("orchestrator", {}).setdefault("turns", [])

    def render_tool_history(history: dict[str, AgentHistory]) -> str:
        """Compact text view of every tool call made so far, for the orchestrator."""
        lines = []
        for agent, data in history.items():
            for tm in data.get("tool_messages", []):
                art = tm.artifact or {}
                lines.append(
                    f"[{agent}] {tm.name}({art.get('args', {})}) -> {tm.status}: {str(tm.content)[:500]}"
                )
        return "\n".join(lines)

    async def orchestrator(state: State):
        """Orchestrator that generates a structured plan."""
        messages: list[AnyMessage] = [
            SystemMessage(
                content=(
                    "You are an expert AI orchestrator and technical project manager. "
                    "You live and operate within an IDE environment, which gives you unique capabilities: "
                    "you can interact with systems and accomplish complex tasks directly by calling specialized tools "
                    "Your job is to analyze the user's request, break it down into a clear, logical, "
                    "and structured execution plan, and provide explicit, actionable instructions "
                    "for both the Coder and Validator agents. "

                    "You have access to a search_memory tool that can search both the available tool "
                    "catalog and long-term memory about the user. Use it proactively whenever relevant "
                    "to identify tools you do not currently have access to, discover capabilities "
                    "needed to fulfill the request, or retrieve relevant facts, preferences, context, "
                    "and information about the user from previous conversations. "

                    "The search_memory tool accepts a LIST of search queries in a single tool call (e.g. query=['capability 1', 'capability 2']). "
                    "Whenever you need to look up multiple capabilities or distinct topics at once, pass all of your search terms together in a single tool call rather than making multiple sequential calls. "
                    "When using search_memory with collection='tools', maximize your discovery rate by diversifying your list of queries: "
                    "1. Decompose complex user requests into separate functional pillars or sub-tasks. "
                    "2. Use both high-level categories and specific action verbs (e.g., instead of just 'manage files', query ['file management', 'read write files', 'directory listing']). "
                    "3. Include technical synonyms or alternative naming conventions since tool descriptions vary. "
                    "4. Keep each query short (1-4 words) to optimize embedding similarity."
                    "Example: If the user asks 'Can you fetch my recent GitHub issues and save them to a CSV?', "
                    "do not search a single broad phrase. Instead, call search_memory with a diverse list: "
                    "query=['github issues api', 'repository tracker', 'csv export', 'file generation']."

                    "Use search_memory with collection='tools' to discover tools and capabilities "
                    "that may help accomplish the task. Search using concise descriptions of the "
                    "required capability, then use the discovered tool information to determine "
                    "which tools are available and how they can be used. "

                    "Use search_memory with collection='chat_history' to retrieve relevant long-term "
                    "memories about the user, including their preferences, projects, requirements, "
                    "technical environment, and previously shared information. Search memory when "
                    "personalization, continuity, or missing context could improve the answer or "
                    "execution plan. Do not assume that relevant information is absent just because "
                    "it is not included in the current messages. However, do not retrieve or use "
                    "memories that are irrelevant to the current request. "

                    "The earlier conversation is provided as chat messages before the current request. "
                    "Use those messages directly to answer questions about previous prompts, answers, "
                    "and events within the current conversation. Never use search_memory to recall "
                    "information that is already available in the provided conversation history. "
                    "Use search_memory with collection='chat_history' for relevant long-term memories "
                    "and information about the user beyond the current conversation. "

                    "The last message is the CURRENT request; 'the last prompt' means the user "
                    "message immediately before it. "

                    "When you have everything you need and the request requires writing or modifying "
                    "code that needs implementation and validation, submit your final answer by "
                    "calling the Plan tool. Do not write the implementation plan as plain text "
                    "instead of calling Plan. Provide explicit, actionable instructions for both "
                    "the Coder and Validator agents. "

                    "If the request is a question, a conversation, or something you can answer directly, "
                    "optionally after using your tools or searching memory, answer in plain text "
                    "and do not call Plan. "

                    "Call Plan only when the task requires writing or modifying code that needs "
                    "implementation and validation. Do not call Plan for general questions, "
                    "conversations, explanations, or tasks that can be completed directly."
                ),
            )
        ]
        for t in turns[-10:]:
            messages.append(HumanMessage(content=t["prompt"]))
            messages.append(AIMessage(content=t["answer"]))

        tool_context = render_tool_history(session_history)
        if tool_context:
            messages.append(HumanMessage(
                content=f"Tool results gathered so far (by all agents):\n{tool_context}"))

        messages.append(HumanMessage(content=state.user_prompt))

        if state.completed_task:
            last = state.completed_task[-1]
            messages.append(HumanMessage(content=f"Previous validation feedback: {last['output']}"))

        result = await tool_call(MAX_ITERATIONS, llm, tools, messages, session_id, tool_call_rag, send_to_acp,
                                 output_schema=Plan, require_schema=False, agent_name="orchestrator", session_history=session_history)

        if isinstance(result, Plan):
            return {"plan": result, "iterations": state.iterations + 1}

        text = result.content if isinstance(result.content, str) else str(result.content)
        return {"plan": None, "response": [text], "iterations": state.iterations + 1}


    async def coder(state: State):
        """Worker writes code based on orchestrator instructions with tool support."""
        if state.plan is None:
            raise ValueError("The orchestrator must generate a plan before coding.")

        messages = [
            SystemMessage(
                content="You are an expert senior software engineer and coder. "
                        "Your task is to write clean, efficient, robust, well-documented, and production-ready code "
                        "following the specific instructions provided by the orchestrator.\n\n"
                        "You have access to the `search_memory` tool, which you can use to:\n"
                        "1. Discover and retrieve tools/capabilities by setting `collection='tools'` when you need additional functions to fulfill a request.\n"
                        "2. Retrieve relevant long-term memories, preferences, technical requirements, or context from past conversations by setting `collection='chat_history'`."
            ),
            HumanMessage(content=f"Instructions: {state.plan.coder_instructions}"),
        ]

        result = await tool_call(MAX_ITERATIONS, llm, tools, messages, session_id, tool_call_rag, send_to_acp, require_schema=False, agent_name="coder", session_history=session_history)
        return {"completed_task": [{"agent": "coder", "output": result.content}]}


    async def validator(state: State):
        """Worker validates the implemented code with tool support and structured judgment."""
        if state.plan is None:
            raise ValueError("The orchestrator must generate a plan before validation.")

        code = state.completed_task[-1]["output"]
        messages = [
            SystemMessage(
                content="You are an expert QA, security, and test engineer. "
                "Your task is to rigorously review, test, and audit the code produced by the coder agent."
                "When you have everything you need, submit your final answer by calling the Verdict tool."
                "Do not write the answer as plain text."
                "You have access to the `search_memory` tool, which you can use to:\n"
                "1. Discover and retrieve tools/capabilities by setting `collection='tools'` when you need additional functions to fulfill a request.\n"
                "2. Retrieve relevant long-term memories, preferences, technical requirements, or context from past conversations by setting `collection='chat_history'`."
            ),
            HumanMessage(content=(
                f"Instructions: {state.plan.validator_instructions}\n\n"
                f"Acceptance criteria: {state.plan.acceptance_criteria}\n\n"
                f"Code to review:\n{code}"
            )),
        ]

        verdict = await tool_call(MAX_ITERATIONS, llm, tools, messages, session_id, tool_call_rag, send_to_acp, output_schema=Verdict, require_schema=True, agent_name="validator", session_history=session_history)

        return {
            "is_validated": verdict.is_validated if isinstance(verdict, Verdict) else False,
            "completed_task": [{"agent": "validator", "output": verdict.feedback if isinstance(verdict, Verdict) else "No feedback"}],
        }


    async def synthesizer(state: State):
        """Synthesizer that crafts the final user-facing response."""
        latest_code = next(
            (t["output"] for t in reversed(state.completed_task) if t["agent"] == "coder"),
            "No code available.",
        )

        messages = [
            SystemMessage(
                content="You are an expert technical communicator and final-response synthesizer. "
                        "Use the Original User Request as the primary prompt to determine what the "
                        "final response should accomplish, and treat the Final Implemented Code as the "
                        "solution you wrote and the source of truth for what was implemented."
            ),
            HumanMessage(
                content=(
                    f"Original User Request: {state.user_prompt}\n\n"
                    f"Final Implemented Code:\n{latest_code}"
                )
            ),
        ]

        response = await llm.ainvoke(messages)
        return {"response": [response.content]}


    def route_validation(state: State):
        if state.is_validated:
            return "Accepted"
        elif state.iterations >= MAX_ITERATIONS:
            return END
        return "Rejected"

    def route_orchestrator(state: State):
        return "coder" if state.plan is not None else "no_plan_needed"

    async def send_usage(used: int):
        await send_to_acp(
            session_id,
            UsageUpdate(
                used=used,
                size=MAX_CONTEXT_SIZE,
                cost=Cost(amount=0, currency="EUR", _meta=None),
                field_meta=None,
                session_update="usage_update",
            ),
        )

    # Build and compile graph
    builder = StateGraph(State)
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("coder", coder)
    builder.add_node("validator", validator)
    builder.add_node("synthesizer", synthesizer)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", route_orchestrator, {"coder": "coder", "no_plan_needed": END})
    builder.add_edge("coder", "validator")
    builder.add_conditional_edges(
        "validator", route_validation,
        {"Accepted": "synthesizer", "Rejected": "orchestrator"},
    )
    builder.add_edge("synthesizer", END)
    graph = builder.compile()

    current_node = None
    answer_parts: list[str] = []

    try:
        async for chunk, metadata in graph.astream({"user_prompt": user_prompt, "session_id": session_id}, stream_mode="messages"):
            node = metadata.get("langgraph_node")

            if node != current_node:
                current_node = node
                await send_to_acp(session_id, update_agent_message_text(f"Agent {current_node} is generating his answer."))

            reasoning = chunk.additional_kwargs.get("reasoning_content")
            if reasoning:
                await send_to_acp(
                    session_id,
                    update_agent_thought(TextContentBlock(text=reasoning, type="text", field_meta=None)),
                )

            if current_node not in ("coder", "validator") and isinstance(chunk.content, str) and chunk.content:
                await send_to_acp(
                    session_id, update_agent_message_text(chunk.content)
                )

            if current_node in ("orchestrator", "synthesizer") and isinstance(chunk.content, str) and chunk.content:
                answer_parts.append(chunk.content)

            if getattr(chunk, "usage_metadata", None) and current_node == "orchestrator":
                um = chunk.usage_metadata
                used = (um.get("input_tokens") or 0) + (um.get("output_tokens") or 0)

                if current_node == "orchestrator":
                    session_history["orchestrator"]["context_used"] = used
                    await send_usage(used)
    finally:
        turns.append({"prompt": user_prompt, "answer": "".join(answer_parts)})
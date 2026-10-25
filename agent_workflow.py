from typing import Annotated, List, Callable, Any, Coroutine
import operator
from acp import update_agent_thought, update_agent_message_text, start_tool_call, update_tool_call
from acp.schema import TextContentBlock, UsageUpdate, Cost, SessionNotification, SessionInfoUpdate
from langchain_core.messages import ToolMessage
from pydantic import BaseModel, Field
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
    is_validated: bool = Field(description="True only if all acceptance criteria are met.")
    feedback: str = Field(description="Review findings, test results, and required fixes.")


class Plan(BaseModel):
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


async def tool_call(
    max_tool_iterations: int,
    llm_with_tools,
    messages: list,
    session_id: str,
    tool_call_rag: Callable[[str, str, dict[str, Any]], Coroutine[Any, Any, str]],
    worker_llm,
    send_to_acp: Callable[[str, Any], Coroutine[Any, Any, None]]
):
    """Generic helper to handle multi-turn tool calling loops with RAG execution."""
    response = None
    tools_were_called = False

    for _ in range(max_tool_iterations):
        response = await llm_with_tools.ainvoke(messages)

        if not response.tool_calls:
            break

        tools_were_called = True
        messages.append(response)

        for call in response.tool_calls:
            tool_name, arguments, call_id = call["name"], call["args"], call["id"]

            try:
                await send_to_acp(
                    session_id,
                    start_tool_call(
                        call_id,
                        f"Running {tool_name}",
                        kind="execute",
                        status="in_progress",
                        raw_input=arguments,
                    ),
                )
                tool_result = await tool_call_rag(session_id, tool_name, arguments)
                await send_to_acp(
                    session_id,
                    update_tool_call(
                        call_id,
                        title=f"Tool {tool_name} completed successfully",
                        status="completed",
                        raw_output=tool_result,
                    ),
                )
            except Exception as exc:
                tool_result = f"Error executing tool {tool_name}: {str(exc)}"
                await send_to_acp(
                    session_id,
                    update_tool_call(
                        call_id,
                        title=f"Tool {tool_name} failed",
                        status="failed",
                        raw_output=str(exc),
                    ),
                )
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=call_id
                )
            )
    else:
        await send_to_acp(
            session_id,
            SessionNotification(
                sessionId=session_id,
                update=SessionInfoUpdate(title="max iteration exceeded", _meta=None, sessionUpdate="session_info_update", updatedAt=None),
                _meta=None
            ),
        )

    if tools_were_called:
        if worker_llm:
            return await worker_llm.ainvoke(messages)
        return await llm_with_tools.ainvoke(messages)

    if worker_llm:
        return await worker_llm.ainvoke(messages)
    return response


async def run_workflow(
    user_prompt: str,
    send_to_acp: Callable[[str, Any], Coroutine[Any, Any, None]],
    session_id: str,
    tool_call_rag: Callable[[str, str, dict[str, Any]], Coroutine[Any, Any, str]],
    tools: Callable[[str], list[dict[Any, Any]]]
):
    tools = tools(session_id)
    planner = llm.with_structured_output(Plan)
    orchestrator_llm = llm.bind_tools(tools)

    coder_llm = llm.bind_tools(tools)

    judge = llm.with_structured_output(Verdict)
    validator_llm = llm.bind_tools(tools)

    async def orchestrator(state: State):
        """Orchestrator that generates a structured plan."""
        messages = [
            SystemMessage(
                content="You are an expert AI orchestrator and technical project manager. "
                "Your job is to analyze the user's request, break it down into a clear, logical, "
                "and structured execution plan, and provide explicit, actionable instructions "
                "for both the Coder and Validator agents."
            ),
            HumanMessage(content=state.user_prompt),
        ]
        if state.completed_task:
            last = state.completed_task[-1]
            messages.append(HumanMessage(content=f"Previous validation feedback: {last['output']}"))

        result = await tool_call(
            max_tool_iterations=5,
            llm_with_tools=orchestrator_llm,
            messages=messages,
            session_id=session_id,
            tool_call_rag=tool_call_rag,
            worker_llm=planner,
            send_to_acp=send_to_acp
        )

        return {"plan": result, "iterations": state.iterations + 1}


    async def coder(state: State):
        """Worker writes code based on orchestrator instructions with tool support."""
        if state.plan is None:
            raise ValueError("The orchestrator must generate a plan before coding.")

        messages = [
            SystemMessage(
                content="You are an expert senior software engineer and coder. "
                "Your task is to write clean, efficient, robust, well-documented, and production-ready code "
                "following the specific instructions provided by the orchestrator."
            ),
            HumanMessage(content=f"Instructions: {state.plan.coder_instructions}"),
        ]

        result = await tool_call(
            max_tool_iterations=5,
            llm_with_tools=coder_llm,
            messages=messages,
            session_id=session_id,
            tool_call_rag=tool_call_rag,
            worker_llm=None,
            send_to_acp=send_to_acp
        )

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
            ),
            HumanMessage(content=(
                f"Instructions: {state.plan.validator_instructions}\n\n"
                f"Acceptance criteria: {state.plan.acceptance_criteria}\n\n"
                f"Code to review:\n{code}"
            )),
        ]

        verdict = await tool_call(
            max_tool_iterations=3,
            llm_with_tools=validator_llm,
            messages=messages,
            session_id=session_id,
            tool_call_rag=tool_call_rag,
            worker_llm=judge,
            send_to_acp=send_to_acp
        )

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
                content="You are an expert technical communicator and final review synthesizer. "
                "Your task is to create a clear, polished, and comprehensive final response for the user."
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

    # Build and compile graph
    builder = StateGraph(State)
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("coder", coder)
    builder.add_node("validator", validator)
    builder.add_node("synthesizer", synthesizer)

    builder.add_edge(START, "orchestrator")
    builder.add_edge("orchestrator", "coder")
    builder.add_edge("coder", "validator")
    builder.add_conditional_edges(
        "validator", route_validation,
        {"Accepted": "synthesizer", "Rejected": "orchestrator"},
    )
    builder.add_edge("synthesizer", END)
    graph = builder.compile()

    current_node = None
    usage = 0

    async for chunk, metadata in graph.astream({"user_prompt": user_prompt, "session_id": session_id}, stream_mode="messages"):
        node = metadata.get("langgraph_node")
        if node != current_node:
            current_node = node

        reasoning = chunk.additional_kwargs.get("reasoning_content")
        if reasoning:
            await send_to_acp(
                session_id,
                update_agent_thought(TextContentBlock(text=reasoning, type="text", field_meta=None)),
            )
        if chunk.content:
            await send_to_acp(
                session_id, update_agent_message_text(chunk.content)
            )

        if getattr(chunk, "usage_metadata", None):
            usage += chunk.usage_metadata.get("total_tokens")
            await send_to_acp(
                session_id,
                UsageUpdate(
                    used=usage,
                    size=MAX_CONTEXT_SIZE,
                    cost=Cost(amount=0, currency="EUR", _meta=None),
                    field_meta=None,
                    session_update="usage_update",
                ),
            )
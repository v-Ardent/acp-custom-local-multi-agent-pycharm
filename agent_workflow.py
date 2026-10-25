from typing import Annotated, List, Callable, Any, Coroutine
import operator
from acp import update_agent_thought, update_agent_message_text, start_tool_call, update_tool_call
from acp.schema import TextContentBlock, UsageUpdate, Cost, SessionNotification, SessionInfoUpdate
from langchain_core.messages import ToolMessage
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


async def tool_call(
    max_tool_iterations: int,
    base_llm,
    tools: Callable[[str], list[dict[Any, Any]]],
    messages: list,
    session_id: str,
    tool_call_rag,
    send_to_acp,
    output_schema: type[BaseModel] | None = None,
    require_schema: bool = False
):
    """Tool loop. If output_schema is given, the model submits its final answer by
    calling a tool named after the schema, so no extra structured-output call is needed."""
    schema_tool = output_schema.__name__ if output_schema else None

    for _ in range(max_tool_iterations):
        bound = tools(session_id) + ([output_schema] if output_schema else [])
        response = await base_llm.bind_tools(bound).ainvoke(messages)

        if not response.tool_calls:
            if output_schema and require_schema:
                messages.append(response)
                messages.append(
                    HumanMessage(content=f"Submit your answer by calling the {schema_tool} tool, not as plain text."))
                continue
            return response

        final = next((c for c in response.tool_calls if c["name"] == schema_tool), None)
        if final:
            try:
                return output_schema(**final["args"])
            except ValidationError as exc:
                messages.append(response)
                for c in response.tool_calls:
                    messages.append(ToolMessage(content=f"Invalid {schema_tool}: {exc}. Call {schema_tool} again with valid fields.", tool_call_id=c["id"]))
                continue

        messages.append(response)
        for call in response.tool_calls:
            tool_name, arguments, call_id = call["name"], call["args"], call["id"]
            try:
                await send_to_acp(session_id, start_tool_call(call_id, f"Running {tool_name}", kind="execute", status="in_progress", raw_input=arguments))
                tool_result = await tool_call_rag(session_id, tool_name, arguments)
                await send_to_acp(session_id, update_tool_call(call_id, title=f"Tool {tool_name} completed successfully", status="completed", raw_output=tool_result))
            except Exception as exc:
                tool_result = f"Error executing tool {tool_name}: {exc}"
                await send_to_acp(session_id, update_tool_call(call_id, title=f"Tool {tool_name} failed", status="failed", raw_output=str(exc)))
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=call_id))

    await send_to_acp(session_id, SessionNotification(sessionId=session_id, update=SessionInfoUpdate(title="max iteration exceeded", _meta=None,sessionUpdate="session_info_update", updatedAt=None),_meta=None))
    messages.append(HumanMessage(content="Answer now with the information you have."))
    return await base_llm.ainvoke(messages)


async def run_workflow(
    user_prompt: str,
    send_to_acp: Callable[[str, Any], Coroutine[Any, Any, None]],
    session_id: str,
    tool_call_rag: Callable[[str, str, dict[str, Any]], Coroutine[Any, Any, str]],
    tools: Callable[[str], list[dict[Any, Any]]]
):
    synthesizer_llm = llm.bind(think=False)

    async def orchestrator(state: State):
        """Orchestrator that generates a structured plan."""
        messages = [
            SystemMessage(
                content="You are an expert AI orchestrator and technical project manager. "
                "Your job is to analyze the user's request, break it down into a clear, logical, "
                "and structured execution plan, and provide explicit, actionable instructions "
                "for both the Coder and Validator agents. "
                "When you have everything you need, submit your final answer by calling the "
                "Plan tool. Do not write the answer as plain text. "
                "If the request is a question, a conversation, or something you can answer directly "
                "(optionally after using your tools), answer in plain text and do not call Plan. "
                "Call Plan only when the task requires writing or modifying code that needs implementation and validation."
            ),
            HumanMessage(content=state.user_prompt),
        ]
        if state.completed_task:
            last = state.completed_task[-1]
            messages.append(HumanMessage(content=f"Previous validation feedback: {last['output']}"))

        result = await tool_call(5, llm, tools, messages, session_id, tool_call_rag, send_to_acp,
                                 output_schema=Plan, require_schema=False)

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
                "following the specific instructions provided by the orchestrator."
            ),
            HumanMessage(content=f"Instructions: {state.plan.coder_instructions}"),
        ]

        result = await tool_call(5, llm, tools, messages, session_id, tool_call_rag, send_to_acp, require_schema=False)
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
            ),
            HumanMessage(content=(
                f"Instructions: {state.plan.validator_instructions}\n\n"
                f"Acceptance criteria: {state.plan.acceptance_criteria}\n\n"
                f"Code to review:\n{code}"
            )),
        ]

        verdict = await tool_call(3, llm, tools, messages, session_id, tool_call_rag, send_to_acp, output_schema=Verdict, require_schema=True)

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

        response = await synthesizer_llm.ainvoke(messages)
        return {"response": [response.content]}


    def route_validation(state: State):
        if state.is_validated:
            return "Accepted"
        elif state.iterations >= MAX_ITERATIONS:
            return END
        return "Rejected"

    def route_orchestrator(state: State):
        return "coder" if state.plan is not None else "no_plan_needed"

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

        if current_node not in ("coder", "validator") and isinstance(chunk.content, str) and chunk.content:
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
from typing import Annotated, List
import operator
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

SYSTEM_PROMPT_ORCHESTRATOR = (
    "You are an expert AI orchestrator and technical project manager."
    "Your job is to analyze the user's request, break it down into a clear, logical,"
    "and structured execution plan, and provide explicit, actionable instructions"
    "for both the Coder and Validator agents. Ensure that all technical requirements,"
    "edge cases, and safety standards are addressed in your plan."
)

SYSTEM_PROMPT_CODER = (
    "You are an expert senior software engineer and coder."
    "Your task is to write clean, efficient, robust, well-documented, and production-ready code"
    "following the specific instructions provided by the orchestrator."
    "Always include proper type hints, error handling, and clean code principles."
)

SYSTEM_PROMPT_VALIDATOR = (
    "You are an expert QA, security, and test engineer."
    "Your task is to rigorously review, test, and audit the code produced by the coder agent."
    "Check for correctness, code smells, security vulnerabilities, edge cases, and adherence"
    "to the acceptance criteria. Provide detailed feedback, test results, or security assessments."
)

SYSTEM_PROMPT_SYNTHESIZER = (
    "You are an expert technical communicator and final review synthesizer."
    "Your task is to take the original user request and the final code implementation,"
    "to create a clear, polished, and comprehensive final response"
    "for the user. Present the final code cleanly and explain how it fulfills the requirements."
)

USER_PROMPT = (
    "just say this word 'Bonjour'"
)
LLM = "gemma4:e4b"
MAX_ITERATIONS = 3
MAX_CONTEXT_SIZE = 131072

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


planner = llm.with_structured_output(Plan)
judge = llm.with_structured_output(Verdict)

class State(BaseModel):
    user_prompt: str
    plan: Plan | None = None
    completed_task: Annotated[list, operator.add] = Field(default_factory=list)
    response: Annotated[list[str], operator.add] = Field(default_factory=list)
    is_validated: bool = False
    iterations: int = 0


async def orchestrator(state: State):
    """Orchestrator that generates a plan"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_ORCHESTRATOR),
        HumanMessage(content=state.user_prompt),
    ]
    if state.completed_task:
        last = state.completed_task[-1]
        messages.append(HumanMessage(content=f"Previous validation feedback: {last['output']}"))
    plan = await planner.ainvoke(messages)
    return {"plan": plan, "iterations": state.iterations + 1}


async def coder(state: State):
    """Worker writes code based on orchestrator instructions"""
    if state.plan is None:
        raise ValueError("The orchestrator must generate a plan before coding.")

    task = [
        SystemMessage(content=SYSTEM_PROMPT_CODER),
        HumanMessage(content=f"Instructions: {state.plan.coder_instructions}"),
    ]
    task = await llm.ainvoke(task)

    return {"completed_task": [{"agent": "coder", "output": task}]}


async def validator(state: State):
    """Worker validates the implemented code (async + token streaming)."""
    if state.plan is None:
        raise ValueError("The orchestrator must generate a plan before validation.")

    code = state.completed_task[-1]["output"]
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_VALIDATOR),
        HumanMessage(content=(
            f"Instructions: {state.plan.validator_instructions}\n\n"
            f"Acceptance criteria: {state.plan.acceptance_criteria}\n\n"
            f"Code to review:\n{code}"
        )),
    ]

    verdict = await judge.ainvoke(messages)

    return {
        "is_validated": verdict.is_validated if isinstance(verdict, Verdict) else None,
        "completed_task": [{"agent": "validator", "output": verdict.feedback if isinstance(verdict, Verdict) else None}],
    }


async def synthesizer(state: State):
    """Synthesizer that crafts the final user-facing response (async + streaming)."""
    latest_code = next(
        (t["output"] for t in reversed(state.completed_task) if t["agent"] == "coder"),
        "No code available.",
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT_SYNTHESIZER),
        HumanMessage(
            content=(
                f"Original User Request: {state.user_prompt}\n\n"
                f"Final Implemented Code:\n{latest_code}"
            )
        ),
    ]

    response = await llm.ainvoke(messages)

    return {"response": [response]}


def route_validation(state: State):
    if state.is_validated:
        return "Accepted"
    elif state.iterations >= MAX_ITERATIONS:
        return END
    return "Rejected"


async def main():
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
    one_time = True
    async for message_chunk, metadata in graph.astream({"user_prompt": USER_PROMPT}, stream_mode="messages"):
        node = metadata.get("langgraph_node")

        if one_time:
            print(f"{message_chunk}", flush=True)
            one_time = False

        if node != current_node:
            current_node = node
            print(f"\n\n=== {node.upper()} ===\n", flush=True)
            print(f"\n\n=== Thinking ===\n", flush=True)

        reasoning = message_chunk.additional_kwargs.get("reasoning_content")
        if reasoning:
            print(reasoning, end="", flush=True)

        if message_chunk.content:
            print(message_chunk.content, end="", flush=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
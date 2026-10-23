# project

- agent 1 = the validator (test, security, etc.)
- agent 2 = the coder (write code)
- agent 3 = orchestrator (create from a prompt a plan with instructions for the others agents)

- loop : agent 3 to agent 2 to agent 1 if not pass back to agent 3


## details

---

## 1. Enhanced Agent Roles & Responsibilities

Instead of treating them as simple prompt chains, give each agent specialized tools, system prompts, and strict boundaries.

| Agent | Core Function | Key Inputs | Key Outputs |
| --- | --- | --- | --- |
| **Agent 3: Orchestrator** | Task decomposition, roadmap generation, and macro-state tracking. | User prompt, repository state, past execution logs. | JSON-based Execution Plan (Task breakdown, dependencies, acceptance criteria). |
| **Agent 2: Coder** | Writing, refactoring, and fixing code based on atomic tasks. | Specific task instructions, file context, error reports from Agent 1. | Code patches, diffs, new files, and local test drafts. |
| **Agent 1: Validator** | Automated testing, code quality checks, and security auditing. | Generated code, test suites, acceptance criteria. | Pass/Fail status, structured error logs, stack traces, and security warnings. |

---

## 2. Refining the Execution Loop & State Machine

Your idea of routing back to **Agent 3** on failure is powerful because it allows for **re-planning** rather than just blind retries. Here is how the loop should flow step-by-step:

1. **Initialization (Agent 3):**
* Parses the user prompt.
* Generates a multi-step task list (e.g., `Task 1: Setup DB schema`, `Task 2: Build API endpoint`).


2. **Execution (Agent 2):**
* Picks the highest-priority open task from Agent 3's plan.
* Writes the code and saves it to a workspace directory.


3. **Validation (Agent 1):**
* Runs linters, type checkers, and unit tests against Agent 2's code.
* **If Pass:** Agent 3 marks the task complete and moves to the next task in the plan. If all tasks are done, the project finishes.
* **If Fail:** Agent 1 packages the exact error logs, test failures, and offending file paths and sends them back to **Agent 3**.


4. **Re-planning (Agent 3 on Failure):**
* Agent 3 analyzes *why* it failed. It can either:
* *Option A:* Update the task instructions and send it back to Agent 2 for a targeted fix.
* *Option B:* Modify the overall plan if a fundamental architectural flaw was discovered.


* *Safety Guard:* Implement a **max retry limit** (e.g., 3 loops per task) to prevent infinite loops and runaway token costs.



---

## 3. Recommended Technical Stack & Infrastructure

To bring this to life cleanly, consider building it on top of a state-machine or agent framework:

* **Framework Layer:** **LangGraph** or **CrewAI** (both excel at cyclic graphs where agents loop back to an orchestrator).
* **Workspace Isolation:** Run Agent 2's generated code inside a **Docker container** or a secure sandbox. This prevents Agent 2 from accidentally modifying your host machine's filesystem or running dangerous system commands during testing.
* **State Store:** Use a simple JSON or SQLite database to maintain a **Shared Context Board** (current file tree, completed tasks, active errors, conversation history).

---

## 4. Production-Grade Additions

* **Artifact Memory:** Give Agent 3 and Agent 2 access to a vector database or document retriever (RAG) containing your project's existing codebase documentation or style guides, ensuring the generated code matches your project's conventions.
* **Human-in-the-Loop (HITL) Gate:** Add a conditional checkpoint before Agent 2 applies major changes or before deployment where the system pauses and asks: `Approve changes? (y/n)`.


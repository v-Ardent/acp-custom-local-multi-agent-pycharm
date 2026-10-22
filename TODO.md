- create RAG for MCP tools
- chat historic
- initialise MCP one time for the prompt loop



Combining a **Sandbox Test-Writer Agent**, a **Performance & HPO Agent**, and a **Security Agent** into a unified multi-agent orchestration layer creates a production-grade ML engineering pipeline. Because your agents run via **ACP** inside PyCharm and access tools through **MCP**, they can safely write, test, profile, and harden code without risking your local environment or blowing up your machine's GPU memory.

Here is how you can architect and coordinate this 3-agent swarm for maximum efficiency.

---

### 1. The 3-Agent Swarm Breakdown

#### **Agent 1: The Sandbox Test-Writer Agent (The Validator)**

* **Role:** Ensures that any code modification doesn't break tensor shapes, data loader batches, or mathematical correctness.
* **How it works via MCP:**
* It intercepts code changes made in PyCharm, writes comprehensive unit tests (using `pytest`, `Hypothesis` for property-based testing of tensor shapes, or integration tests), and dispatches them to a secure **Sandbox MCP server** (backed by isolated containers or microVMs like E2B/Modal).
* It returns execution traces, stack traces, and assertion failures back to the orchestrator if a test fails.



#### **Agent 2: The Performance & HPO Agent (The Speedster)**

* **Role:** Handles bottleneck identification, execution profiling, and automatic code refactoring for hyperparameter optimization and hardware speedups.
* **How it works via MCP:**
* **Profiling Trigger:** Triggers profiling tools (PyTorch Profiler, `nsight`) via the Sandbox MCP to locate CPU/GPU bottlenecks or memory bloat.
* **Hyperparameter & Code Refactoring:** Automatically refactors training loops to integrate hyperparameter tuning frameworks (e.g., Optuna sweeps) or switches out unoptimized primitives (e.g., standard attention to FlashAttention, or eager mode to `torch.compile`).



#### **Agent 3: The Security Agent (The Guardrail)**

* **Role:** Screens code changes and model artifacts for supply chain vulnerabilities, data leakage, and unsafe serialization.
* **How it works via MCP:**
* Runs static analysis (e.g., `bandit`, custom AST checkers) via MCP tools to catch insecure deserialization (`torch.load` without `weights_only=True`).
* Verifies that the sandbox tests and HPO loops aren't accidentally leaking sensitive PII or training data logs to external endpoints.



---

### 2. The Orchestration Lifecycle: Step-by-Step Scenario

Imagine you ask your PyCharm ACP agent: *"Optimize our fine-tuning script for speed and set up proper hyperparameter tuning."*

1. **Phase 1 (Performance):** The **Performance Agent** analyzes your script via PyCharm MCP, identifies an inefficient batch processing loop, and refactors it to use multi-GPU data loading and an Optuna search space.
2. **Phase 2 (Security Check):** Before executing anything, the **Security Agent** scans the refactored diff to ensure no insecure dynamic code execution or hardcoded credentials were introduced.
3. **Phase 3 (Sandbox Execution & Testing):** The **Sandbox Test-Writer Agent** auto-generates a suite of mock-data tests to verify that the Optuna trial loop runs properly. It ships the code to the **Sandbox MCP** server (running in an isolated container with GPU acceleration).
4. **Phase 4 (IDE Review):** Once the sandbox execution passes all tests and returns a successful speedup benchmark, the master orchestrator formats a clean, multi-file review diff directly inside your **PyCharm** editor window via ACP, waiting for your final click to approve.

---

### Implementation Blueprint for Your Stack

1. **State Machine Framework:** Use **LangGraph** or a custom state graph to enforce strict sequencing: *Refactor (Performance) $\rightarrow$ Audit (Security) $\rightarrow$ Generate Tests $\rightarrow$ Execute in Sandbox $\rightarrow$ Human Gate (ACP)*.
2. **Sandbox Infrastructure:** Implement or plug into an existing **Sandbox MCP server** (such as E2B or Modal-backed MCP endpoints) that supports ephemeral, isolated execution environments with Python and CUDA support.
3. **ACP Protocol Hooks:** Leverage ACP's session permission handlers (`session/request_permission`) so that whenever the Sandbox Test-Writer agent wants to spin up a heavy container or the Performance agent wants to write a large refactor, PyCharm cleanly prompts you instead of executing blindly.
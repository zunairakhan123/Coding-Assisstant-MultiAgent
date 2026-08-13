# 🤖 Autonomous Multi-Agent Coding Assistant

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C)](https://www.langchain.com/langgraph)
[![Docker](https://img.shields.io/badge/Sandbox-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, self-healing, multi-agent AI coding framework orchestrated via **LangGraph**

The system autonomously **plans, writes, tests, and reviews code** inside a secure, ephemeral Docker sandbox — using structured error fingerprinting, fuzzy-match code patching, and live end-to-end simulations to detect, diagnose, and repair its own bugs without human intervention.

---

##  Table of Contents

- [Overview](#-overview)
- [System Architecture](#️-system-architecture)
- [Core Features](#-core-features)
- [Directory Structure](#-directory-structure)
- [The Agent Roster](#-the-agent-roster)
- [Prerequisites](#️-prerequisites)
- [Installation](#-installation--setup)
- [Configuration](#️-configuration)
- [Usage](#-usage)
- [Observability & Artifacts](#-observability--artifacts)
- [Error Fingerprinting & Patching](#-error-fingerprinting--patching)
- [Security Model](#️-security-model)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

##  Overview

Traditional single-shot LLM code generation fails silently on non-trivial tasks — it hallucinates imports, produces code that doesn't run, and has no mechanism to verify its own output.

This framework solves that by decomposing the coding task into a team of **specialized agents**, each with a narrow responsibility, coordinated by a stateful **LangGraph orchestrator** with cyclic, conditional routing.

The system runs on **two nested control loops**, fully accessible via an asynchronous API:

| Loop | Owner | Purpose |
|---|---|---|
| **Global Agentic Loop** | LangGraph | Hands off state between `Planner → Coder → Tester → Reviewer`, with conditional routing back to earlier nodes on failure. |
| **Deterministic Execution Loop** | Coder Node | A fast, internal loop where the Coder validates its own syntax and runtime execution before handing off to the formal Tester node. |

This two-tier design keeps cheap, mechanical failures (syntax errors, bad imports) inside the fast inner loop, while reserving the expensive, LLM-driven outer loop for genuine logic or architectural failures.

---

##  System Architecture

```
                                                    
┌───────────────┐      ┌───────────────┐      ┌──────────────────┐
│  1. Planner   │─────▶│   2. Coder    │─────▶│  3. Tester      │
│ (Architecture)│      │ (Inner Loop)  │      │  (PyTest QA)     │
└───────────────┘      └──────┬────────┘      └──────┬───────────┘
         ──────────────── ▲   ▲                      │
        │                     │   [Tests Failed]     │
        │  [Trigger]          └──────────────────────┘
        │                                            │ [Tests Passed]
        │                                            ▼
        │                                    ┌───────────────┐
        │         [Audit Failed]             │ 4. Reviewer   │
        └────────────────────────────────────│ (E2E Gate)    │
                                             └──────┬────────┘
                                                    │ [Audit Passed]
                                                    ▼
                                             ┌───────────────┐       ┌───────────────┐
                                             │  5. Cleanup   │──────▶│ Global Ledger │
                                             │ (Export/Drop) │       └───────────────┘
                                             └───────────────┘
```

---

##  Core Features

- **State-Driven Cyclic Routing** — LangGraph conditional edges route tasks dynamically. Repeated test failures trigger a full Reflexion-style replan rather than looping indefinitely on the same broken approach.
- **SmartPatcher Editing** — A progressive, 3-tier fallback strategy (Exact Match → Normalized Whitespace → Fuzzy Sliding Window) to surgically edit AST nodes and blocks without failing due to minor LLM hallucinations.
- **Strict Linting & Tech-Debt Prevention** — QA tests dynamically leverage strict warning filters (e.g., `-W error::DeprecationWarning`) to reject deprecated frameworks and force the Coder to use modern syntax.
- **Live E2E Simulations** — The Reviewer acts as an active QA Engineer, issuing real interactive CLI inputs, `curl` commands, and evaluating expected exit codes (`0` vs `1`) for both happy paths and edge cases.
- **Harness & Path Validation** — A dedicated strict validation harness sanitizes LLM-generated file paths, intercepting path traversal, hallucinated paths, and command injection attempts before they reach the sandbox
- **Structured Error Fingerprinting** — Execution logs are normalized (UUIDs, timestamps, and memory addresses scrubbed) into deterministic error signatures, preventing false negatives when line numbers shift and detecting "stuck" conceptual errors across iterations.
- **Comprehensive Observability** — Every run emits execution_trace.json (low-level LLM thoughts/actions) and workflow_state.json (high-level multi-agent lifecycle metrics), suitable for CI/CD ingestion and post-mortem debugging.
- **Secure Docker Sandboxing** — All generated code and tests execute inside isolated, ephemeral `python:3.11-slim` containers with stripped privileges to prevent host compromise.

---

## 📂 Directory Structure

The project follows a modular, domain-driven design.

```
coding_assistant/
├── main.py                 # Main entry point for the LangGraph orchestrator
├── tasks_ledger.json       # Global database of all executed agentic tasks
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables (LLM API keys, Docker limits)
├── artifacts/              # Auto-generated outputs (workspace, traces, state)
│   └── <task_id>/
│       ├── workspace/            # Final, passing source code
│       ├── execution_trace.json  # Step-by-step reasoning and commands
│       └── workflow_state.json   # Graph iteration counts, error signatures
└── src/
    ├── tests/               ## Framework-level tests (not generated project tests)
    ├── core/                # System config, logger, ledger, and exceptions
    │   ├── ledger.py        # Global task recording utility
    ├── sandbox/             # Docker container lifecycle and execution manager
    ├── graph/               # LangGraph state definitions and cyclic routing logic
    └── agents/
        ├── planner/         # Generates architectural blueprints and target files
        ├── coder/           # Inner-loop coding agent, strict harness, and context
        ├── tester/          # PyTest generation and edge-case execution
        └── reviewer/        # Live E2E application simulation and final audit
```

---

##  The Agent Roster

| Agent | Role | Responsibilities |
|---|---|---|
| **Planner** | Chief Architect | Analyzes the initial prompt and produces a strict, file-by-file architectural blueprint that downstream agents treat as source of truth. |
| **Coder** | Implementer | Interprets the plan, uses the SmartPatcher for surgical edits, and executes rapid micro-loops to self-correct `SyntaxError`s instantly. |
| **Tester** | QA Automation | Generates robust `pytest` suites explicitly split into Happy Paths and Edge Cases. Mocks inputs to prevent hanging scripts and enforces strict deprecation rules. |
| **Reviewer** | Principal QA | Bypasses standard execution constraints to simulate human user interaction via shell commands, piped stdin, and `curl`, evaluating code against expected system exit codes. |

---

## ⚙️ Prerequisites

- Python 3.10+
- Docker Engine (running natively — not required to be Docker Desktop, but the daemon must be reachable from the host)
- A local LLM API (e.g., Ollama) or any OpenAI-compatible endpoint

---

##  Installation & Setup

**1. Clone the repository**

```bash
git clone <repository-url>
cd coding_assistant
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Verify Docker is reachable**

```bash
docker info
```

---

##  Configuration

All runtime configuration is supplied via a `.env` file in the project root.

```env
# LLM endpoint (local or OpenAI-compatible)
LLM_BASE_URL="http://localhost:11434/v1"
LLM_MODEL="qwen2.5-coder:latest"
OPENAI_API_KEY="your-api-key"

# Sandbox resource limits
SANDBOX_MEM_LIMIT="512m"
SANDBOX_CPU_LIMIT="1.0"
SANDBOX_TIMEOUT_SECONDS="120"
SANDBOX_IMAGE="python:3.11-slim"

# Reflexion / retry ceilings
MAX_ITERATIONS="5"
MAX_REPLAN_COUNT="2"
```

| Variable | Description | Default |
|---|---|---|
| `LLM_BASE_URL` | Base URL of the LLM inference endpoint (local or OpenAI-compatible) | `http://localhost:11434/v1` |
| `LLM_MODEL` | Model identifier used for all agent nodes | `qwen2.5-coder:latest` |
| `OPENAI_API_KEY` | API key for the configured LLM endpoint | — |
| `SANDBOX_MEM_LIMIT` | Memory ceiling per Docker sandbox container | `512m` |
| `SANDBOX_CPU_LIMIT` | CPU core allocation per sandbox container | `1.0` |
| `SANDBOX_TIMEOUT_SECONDS` | Hard timeout for sandbox execution before force-kill | `120` |
| `SANDBOX_IMAGE` | Base Docker image used for ephemeral execution | `python:3.11-slim` |
| `MAX_ITERATIONS` | Max inner-loop self-correction attempts before escalation | `5` |
| `MAX_REPLAN_COUNT` | Max full Planner replans before a task is marked failed | `2` |

---

##  Usage

Run the script:

```bash
python main.py
```
view task history & ledger in root dir.
---

##  Observability & Artifacts

All completed runs populate the central `tasks_ledger.json` file in the project root. Additionally, individual run data is exported to `artifacts/<task_id>/`:

| File / Folder | Contents |
|---|---|
| `workspace/` | The final, passing source code generated by the agent. |
| `execution_trace.json` | Complete step-by-step reasoning — every LLM thought, tool invocation, patch applied, and sandbox error. |
| `workflow_state.json` | High-level graph iteration counts, final Reviewer feedback, and error signatures. |

---

##  Error Fingerprinting & Patching

**Fingerprinting** — Raw stack traces are normalized (UUIDs, timestamps, and memory addresses scrubbed) into deterministic error signatures. If the same fingerprint recurs across multiple attempts, the graph treats it as a stuck conceptual error and escalates to the Planner for a full architectural overhaul.

**SmartPatcher** — Traditional LLM block-replacement fails when the model forgets a newline or alters a docstring. SmartPatcher resolves this via a 3-tier algorithm, ultimately deploying Python's `difflib.SequenceMatcher` to find and patch the closest AST block (>85% similarity) in the target file.

---

##  Security Model

| Layer | Control |
|---|---|
| **Execution isolation** | All code executes inside ephemeral `python:3.11-slim` Docker containers, forcibly killed by the Cleanup node. |
| **Harness constraints** | The strict validation harness rejects chained commands (`&&`, `\|`, `;`) to prevent command-injection-style escapes. |
| **Privilege stripping** |	Containers run with reduced Linux capabilities and no access to the host filesystem outside the mounted workspace |
|**Resource ceilings** |	SANDBOX_MEM_LIMIT, SANDBOX_CPU_LIMIT, and SANDBOX_TIMEOUT_SECONDS bound worst-case resource consumption per contain |
| **Path validation** | Rejects path traversal (`../`) and absolute paths outside the workspace root. |

> ⚠️ **Production note:** The sandbox trust boundary assumes LLM output is adversarial-by-default. Treat any relaxation of path validation or network isolation as a security regression.

---

##  Testing

Run the framework's own test suite (evaluates the patching logic, harness validation, and state machine):

```bash
pytest tests/ -v
```

To test the Reviewer Node and Coder Node in isolated sandbox mode without triggering the full multi-agent pipeline, use the included utility:

```bash
python test_reviewer.py
python test_controller.py
```

---

##  Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `docker.errors.DockerException` | Docker daemon not reachable | Run `docker info`; on Linux ensure your user is in the `docker` group. |
| `search_block_not_found` | LLM hallucinated code during an edit action | SmartPatcher typically handles this. If it still fails, the Coder loop catches the exception and forces the LLM to rewrite the block correctly in the next iteration. |
| Simulation fails with Exit Code `127` | Pathing or shell execution error | Ensure the Reviewer prompt retains the strict instruction to execute commands directly (e.g., `python script.py`) without using `cd /workspace &&`. |
| Infinite Testing Loop | False-positive warnings causing PyTest failures | Ensure the Tester retains `-W error::DeprecationWarning` rather than `-W error` to prevent third-party library noise from crashing the build. |
| LLM endpoint timeouts | Inference server overloaded | Reduce concurrency, check tunnels/proxies, or point `LLM_BASE_URL` to a higher-throughput endpoint. |
---

##  Contributing

Contributions are welcome. Please open an issue describing the proposed change before submitting a pull request, particularly for anything that alters the graph routing logic or sandbox security boundary.

---

##  License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
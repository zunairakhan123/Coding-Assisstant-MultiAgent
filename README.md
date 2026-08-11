# 🤖 Autonomous Multi-Agent Coding Assistant

**An enterprise-grade, self-healing, multi-agent AI coding framework orchestrated via LangGraph.**

This system autonomously plans, writes, tests, and reviews code within a secure, ephemeral Docker sandbox — using structured error fingerprinting and reflection loops to detect, diagnose, and repair its own bugs without human intervention.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-1c3d5a)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/sandbox-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](#-license)
[![Status](https://img.shields.io/badge/status-active--development-orange)](#-roadmap-upcoming-phases)

---

##  Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Core Features](#-core-features)
- [Directory Structure](#-directory-structure)
- [The Agent Roster](#-the-agent-roster)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation--setup)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Observability & Artifacts](#-observability--artifacts)
- [Error Fingerprinting](#-error-fingerprinting)
- [Security Model](#-security-model)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap-upcoming-phases)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧠 Overview

Traditional single-shot LLM code generation fails silently on non-trivial tasks — it hallucinates imports, produces code that doesn't run, and has no mechanism to verify its own output. This framework solves that by decomposing the coding task into a **team of specialized agents**, each with a narrow responsibility, coordinated by a stateful LangGraph orchestrator with cyclic, conditional routing.

The system runs on two nested control loops:

| Loop | Owner | Purpose |
|---|---|---|
| **Global Agentic Loop** | LangGraph | Hands off state between Planner → Coder → Tester → Reviewer, with conditional routing back to earlier nodes on failure |
| **Deterministic Execution Loop** | Coder Node | A fast, internal loop where the Coder validates its own syntax and runtime execution *before* handing off to the formal Tester node |

This two-tier design keeps cheap, mechanical failures (syntax errors, bad imports) inside the fast inner loop, while reserving the expensive, LLM-driven outer loop for genuine logic or architectural failures.

---

##  System Architecture

```text
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  1. Planner   │─────▶│   2. Coder    │─────▶│  3. Tester    │
│ (Architecture)│      │ (Inner Loop)  │      │  (PyTest QA)  │
└───────────────┘      └──────┬────────┘      └──────┬────────┘
        ▲                     ▲                       │
        │                     │   [Tests Failed]      │
        │  [Replan Trigger]   └───────────────────────┘
        │                                             │ [Tests Passed]
        │                                             ▼
        │                                      ┌───────────────┐
        │         [Audit Failed]                │ 4. Reviewer   │
        └────────────────────────────────────── │ (Final Gate)  │
                                                 └──────┬────────┘
                                                        │ [Audit Passed]
                                                        ▼
                                                 ┌───────────────┐
                                                 │  5. Cleanup   │
                                                 │ (Export/Drop) │
                                                 └───────────────┘
```

### Routing Logic

| Trigger | Source Node | Destination | Condition |
|---|---|---|---|
| Syntax / import failure | Coder (inner loop) | Coder (self) | Immediate, no LLM re-planning required |
| Test suite failure | Tester | Coder | Bug is isolated and fixable without redesign |
| Repeated test failure (same fingerprint) | Tester | Planner | Error signature indicates an architectural flaw (Reflexion) |
| Audit failure | Reviewer | Planner | Code passes tests but violates DRY/security/requirement constraints |
| Audit passed | Reviewer | Cleanup | Final export and sandbox teardown |


---

##  Core Features

- **State-Driven Cyclic Routing** — LangGraph conditional edges route tasks dynamically. Repeated test failures trigger a full Reflexion-style replan rather than looping indefinitely on the same broken approach.
- **Structured Error Fingerprinting** — Execution logs are normalized (UUIDs, timestamps, and memory addresses scrubbed) into deterministic error signatures, preventing false negatives when line numbers shift and detecting "stuck" conceptual errors across iterations.
- **Secure Docker Sandboxing** — All generated code and tests execute inside isolated, ephemeral `python:3.11-slim` containers with stripped privileges to prevent host compromise.
- **Harness & Path Validation** — A dedicated strict validation harness sanitizes LLM-generated file paths, intercepting path traversal, hallucinated paths, and command injection attempts before they reach the sandbox.
- **Comprehensive Observability** — Every run emits `execution_trace.json` (low-level LLM thoughts/actions) and `workflow_state.json` (high-level multi-agent lifecycle metrics), suitable for CI/CD ingestion and post-mortem debugging.

---

## 📂 Directory Structure

The project follows a modular, domain-driven design, separating the orchestration graph, the Docker sandbox, and individual agent logic.

```text
coding_assistant/
├── main.py                 # Main entry point for the LangGraph orchestrator
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables (LLM API keys, Docker limits)
├── artifacts/               # Auto-generated outputs (workspace, traces, state)
│   └── <task_id>/
│       ├── workspace/            # Final, passing source code
│       ├── execution_trace.json  # Step-by-step reasoning and commands
│       └── workflow_state.json   # Graph iteration counts, error signatures
├── tests/                  # Framework-level tests (not generated project tests)
└── src/
    ├── core/               # System configuration, custom logging, and exceptions
    ├── sandbox/            # Docker container lifecycle and execution manager
    ├── graph/              # LangGraph state definitions and cyclic routing logic
    └── agents/
        ├── planner/        # Generates architectural blueprints and target files
        ├── coder/          # Inner-loop coding agent, harness, and context engine
        ├── tester/         # PyTest generation and error fingerprinting parser
        └── reviewer/       # Final codebase audit and requirement validation
```

---

##  The Agent Roster

| Agent | Role | Responsibilities |
|---|---|---|
| **Planner** | Chief Architect | Analyzes the initial prompt and produces a strict, file-by-file architectural blueprint that downstream agents treat as source of truth |
| **Coder** | Implementer | Interprets the plan, generates code, and executes it inside the sandbox. Runs a deterministic micro-loop to self-correct `SyntaxError` and `ImportError` instantly, without escalating to the outer graph |
| **Tester** | QA Engineer | Reads the Coder's workspace, writes a comprehensive PyTest suite, injects it into the container, and extracts structured results |
| **Reviewer** | Principal Engineer | Audits the final, passing codebase for DRY principles, requirement adherence, and security vulnerabilities before allowing deployment |

---
##  Prerequisites

- Python 3.10+
- Docker Engine (running natively — not required to be Docker Desktop, but the daemon must be reachable from the host)
- A local LLM API (e.g., [Ollama](https://ollama.com/)) or any OpenAI-compatible endpoint

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

If this fails, the sandbox manager cannot provision containers — see [Troubleshooting](#-troubleshooting).

---

##  Configuration

All runtime configuration is supplied via `.env` in the project root.

```dotenv
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
MAX_CODER_INNER_LOOP_ITERATIONS="5"
MAX_TESTER_RETRIES_BEFORE_REPLAN="3"
MAX_REPLAN_COUNT="2"
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_BASE_URL` | Yes | — | Base URL of the LLM inference endpoint |
| `LLM_MODEL` | Yes | — | Model identifier passed to the endpoint |
| `OPENAI_API_KEY` | If using OpenAI-compatible auth | — | API key/token for the endpoint |
| `SANDBOX_MEM_LIMIT` | No | `512m` | Hard memory ceiling per container |
| `SANDBOX_CPU_LIMIT` | No | `1.0` | CPU share cap per container |
| `SANDBOX_TIMEOUT_SECONDS` | No | `120` | Kill switch for hung executions |
| `MAX_REPLAN_COUNT` | No | `2` | Ceiling on Reviewer/Tester → Planner escalations before the run is marked failed, to prevent infinite Reflexion loops |

---

##  Usage

Execute the LangGraph orchestrator:

```bash
python run.py
```

The orchestrator will:
1. Prompt for a `task_id` and the natural-language coding request
2. Provision an ephemeral Docker sandbox
3. Run the Planner → Coder → Tester → Reviewer loop autonomously
4. Export final artifacts on success, or a failure report if `MAX_REPLAN_COUNT` is exceeded

---

##  Observability & Artifacts

Once the workflow hits the **Cleanup** node, all assets are exported to `artifacts/<task_id>/`:

| File / Folder | Contents |
|---|---|
| `workspace/` | The final, passing source code |
| `execution_trace.json` | Complete step-by-step reasoning and commands from the Coder — every LLM call, tool invocation, and sandbox command |
| `workflow_state.json` | High-level graph iteration counts, error signatures, and Reviewer feedback — designed for CI/CD ingestion and dashboarding |

These artifacts are intended to be consumed by external tooling (CI pipelines, internal dashboards) rather than read manually — `workflow_state.json` in particular is structured for programmatic diffing across runs of the same task.

---

##  Error Fingerprinting

Raw stack traces are noisy across runs — memory addresses, UUIDs, and line numbers shift even when the underlying bug is unchanged. The fingerprinting layer normalizes each failure into a stable signature before comparing it against prior attempts:

```text
Raw traceback
   │
   ▼
Strip UUIDs, timestamps, memory addresses
   │
   ▼
Normalize file paths and line numbers
   │
   ▼
Hash (exception type + normalized message + call-site shape)
   │
   ▼
Deterministic error fingerprint
```

If the same fingerprint recurs across `MAX_TESTER_RETRIES_BEFORE_REPLAN` consecutive Coder attempts, the graph treats it as a **stuck conceptual error** rather than a transient bug, and escalates to the Planner for a full architectural overhaul instead of continuing to patch symptoms.

---

##  Security Model

| Layer | Control |
|---|---|
| **Execution isolation** | All generated code and tests run inside ephemeral `python:3.11-slim` Docker containers, destroyed after each task |
| **Privilege stripping** | Containers run with reduced Linux capabilities and no access to the host filesystem outside the mounted workspace |
| **Resource ceilings** | `SANDBOX_MEM_LIMIT`, `SANDBOX_CPU_LIMIT`, and `SANDBOX_TIMEOUT_SECONDS` bound worst-case resource consumption per container |
| **Path validation** | The harness sanitizes all LLM-generated file paths, rejecting path traversal (`../`) and absolute paths outside the workspace root |
| **Command injection defense** | LLM-generated shell commands are parsed and allow-listed before execution rather than passed to a shell verbatim |
| **Network isolation** | Sandboxes should be run with `--network=none` or an isolated bridge network in production to prevent exfiltration or external calls from generated code |
| **Secrets hygiene** | `.env` is git-ignored; API keys are never passed into the sandbox environment unless explicitly required by the task |

> ⚠️ **Production note:** the sandbox trust boundary assumes the LLM output is adversarial-by-default. Treat any relaxation of path validation or network isolation as a security regression, not a convenience trade-off.

---

##  Testing

| Test Layer | Tool | Scope |
|---|---|---|
| Framework unit tests | PyTest | `src/` modules — graph routing logic, fingerprinting, harness validation |
| Generated-code QA | PyTest (dynamically generated by the Tester agent) | Runs *inside* the sandbox against the Coder's output, not part of the framework's own test suite |
| Sandbox lifecycle tests | PyTest + Docker SDK | Container provisioning, teardown, and resource-limit enforcement |

Run the framework's own test suite:

```bash
pytest tests/ -v
```

---

##  Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `docker.errors.DockerException` on startup | Docker daemon not running or not reachable | Run `docker info`; on Linux ensure your user is in the `docker` group |
| Coder stuck in inner loop, never reaching Tester | `MAX_CODER_INNER_LOOP_ITERATIONS` too low for task complexity, or LLM repeating the same syntax mistake | Raise the iteration ceiling; inspect `execution_trace.json` for the repeated error pattern |
| Same bug keeps recurring after a "fix" | Error fingerprint isn't actually changing — normalization may be too aggressive or too weak | Review the fingerprinting rules in `src/agents/tester/`; confirm the signature reflects the real root cause |
| Graph terminates with "max replans exceeded" | Planner's blueprint is architecturally incompatible with the request | Inspect `workflow_state.json` Reviewer notes from each replan cycle; the request itself may need clarification |
| Sandbox container hangs indefinitely | Generated code enters an infinite loop or blocking I/O call | Confirm `SANDBOX_TIMEOUT_SECONDS` is set; the sandbox manager should force-kill on timeout |
| `ImportError` for packages not in `requirements.txt` | LLM hallucinated a dependency, or the sandbox image lacks it | Harness should reject unlisted imports; otherwise extend the base sandbox image's installed packages |
| LLM endpoint timeouts under load | Local inference endpoint (e.g., Ollama) undersized for concurrent agent calls | Reduce agent concurrency, or point `LLM_BASE_URL` at a higher-throughput endpoint |

---

##  Roadmap (Upcoming Phases)
- **Phase 7 — AST/Regex Block Patching**: Upgrade the `CoderAction` schema from full-file overwrites to surgical SEARCH/REPLACE blocks for efficient large-scale codebase modifications.
- **Phase 8 — Advanced QA Synthesis**: Expand the Tester node to explicitly define and validate Edge Cases and Happy Paths prior to test generation, rather than generating tests reactively.
- **Phase 9 — Functional Reviewer Simulation**: Enable the Reviewer agent to execute live interactive commands against the running application (`curl`, `bash`, UI interaction) to simulate real human QA rather than static code audit alone.

---

## Contributing

Contributions are welcome. Please open an issue describing the proposed change before submitting a pull request for anything beyond a minor fix, since changes to the graph routing logic or sandbox security boundary require design discussion.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
# Memoria Code Documentation Implementation Plan

> **For agentic workers:** Execute this plan inline. Do not add or modify tests; the repository-level Test Addition Policy permits running existing checks only.

**Goal:** Improve comments and docstrings across `app/mneme/memoria` without changing runtime behavior.

**Architecture:** Add concise module docstrings to hand-written Python modules, then add detailed public API docstrings and high-value inline comments to the runtime, retrieval, Multi-Agent, memory-governance, service, persistence, and background-task boundaries. Declarative ORM/Pydantic fields keep their existing self-describing names instead of receiving redundant line-by-line comments.

**Tech Stack:** Python 3, FastAPI, Pydantic, SQLAlchemy, asyncio, Celery, PostgreSQL/pgvector, Redis.

---

### Task 1: Establish documentation coverage and behavior-preservation gates

**Files:**
- Inspect: `app/mneme/memoria/**/*.py`
- Modify: none

- [x] Record module and public-definition docstring coverage with an AST scan.
- [x] Record the clean Git status before edits.
- [x] Define exclusions: Alembic migrations, `__pycache__`, generated artifacts, trivial field-by-field comments.
- [x] Define verification: compile all Memoria modules, run Ruff on the changed package, compare normalized ASTs with `HEAD` after removing docstrings, and run relevant existing Memoria tests.

### Task 2: Document the Mneme-side Memoria boundary

**Files:**
- Modify: `app/mneme/memoria/orchestrator.py`
- Modify: `app/mneme/memoria/service.py`
- Modify: `app/mneme/memoria/run_service.py`
- Modify: `app/mneme/memoria/run_submission.py`
- Modify: `app/mneme/memoria/context_governance.py`
- Modify: `app/mneme/memoria/contracts.py`
- Modify: `app/mneme/memoria/events.py`
- Modify: `app/mneme/memoria/ports.py`
- Modify: `app/mneme/memoria/clients/memory_agent.py`
- Modify: `app/mneme/memoria/chat_bridge.py`
- Modify: `app/mneme/memoria/memory_gateway.py`

- [x] Add module docstrings that explain ownership boundaries between Mneme and the independent Memoria service.
- [x] Add detailed class/function docstrings for request submission, durable-run execution, context compaction, event conversion, and HTTP client behavior.
- [x] Comment non-obvious idempotency, retry, cancellation, scope, and persistence ordering.

### Task 3: Document the independent answer runtime

**Files:**
- Modify: `app/mneme/memoria/server/runtime/*.py`
- Modify: `app/mneme/memoria/server/providers/llm.py`
- Modify: `app/mneme/memoria/server/api/answers.py`

- [x] Document retrieval-plan selection, phase timeouts, bounded reasoning, tool execution, prompt construction, citation validation, streaming, and model fallback.
- [x] Explain why model output is validated before answer deltas are emitted.
- [x] Explain what information may be persisted or logged and what must remain excluded.

### Task 4: Document retrieval and bounded Multi-Agent execution

**Files:**
- Modify: `app/mneme/memoria/server/retrieval/*.py`
- Modify: `app/mneme/memoria/server/multi_agent/*.py`
- Modify: `app/mneme/memoria/server/multi_agent/roles/*.py`

- [x] Document owner/knowledge-base filtering before ranking.
- [x] Document vector, keyword, memory, profile, relation, and RRF semantics.
- [x] Document Coordinator eligibility, static source allocation, shared budgets, role timeouts, degraded bundles, supplemental retrieval, Judge limitations, and the no-spawn capability boundary.

### Task 5: Document governed memory lifecycle

**Files:**
- Modify: `app/mneme/memoria/server/memory/*.py`
- Modify: `app/mneme/memoria/server/services/memory_events.py`
- Modify: `app/mneme/memoria/server/services/memory_commands.py`
- Modify: `app/mneme/memoria/server/api/memories.py`
- Modify: `app/mneme/memoria/server/repositories/memories.py`

- [x] Document extraction, exact-evidence validation, sensitivity handling, promotion policy, identity/fingerprints, slot locking, reconciliation, revision history, user confirmation, rejection, and deletion.
- [x] Explain transaction ownership and stale-candidate protection.
- [x] Avoid comments that merely restate ORM/Pydantic field names.

### Task 6: Document projections, automation, persistence, APIs, and tasks

**Files:**
- Modify: `app/mneme/memoria/projections/*.py`
- Modify: `app/mneme/memoria/automation/*.py`
- Modify: `app/mneme/memoria/persistence/*.py`
- Modify: `app/mneme/memoria/api/*.py`
- Modify: `app/mneme/memoria/tasks/*.py`
- Modify: `app/mneme/memoria/subscribers/*.py`
- Modify: `app/mneme/memoria/server/services/*.py`
- Modify: `app/mneme/memoria/server/repositories/*.py`
- Modify: `app/mneme/memoria/server/tasks/*.py`

- [x] Add module-level responsibility and transaction-boundary documentation.
- [x] Add public docstrings where callers need to understand durability, queueing, projection swaps, outbox delivery, retries, or scope.
- [x] Add inline comments only where ordering or failure semantics are not obvious from the code.

### Task 7: Fill remaining module-level gaps

**Files:**
- Modify: remaining hand-written `app/mneme/memoria/**/*.py`

- [x] Add concise package/module docstrings to remaining configuration, schema, contract, model, CLI, observability, security, and bootstrap modules.
- [x] Keep declarative modules concise and avoid duplicating field names in comments.
- [x] Re-run the AST coverage scan and review modules still lacking documentation.

### Task 8: Verify comments-only behavior preservation

**Files:**
- Verify: `app/mneme/memoria/**/*.py`
- Test: existing tests only

- [x] Run `python -m compileall app/mneme/memoria`.
- [x] Run `python -m ruff check app/mneme/memoria`.
- [x] Compare each changed Python file with `HEAD` after stripping module/class/function docstrings; require normalized AST equality.
- [x] Run `python -m pytest -q -p no:cacheprovider tests/memoria tests/test_memory_agent_boundary.py tests/test_agent_module_boundary.py`.
- [x] Re-run documentation coverage and report the before/after counts.

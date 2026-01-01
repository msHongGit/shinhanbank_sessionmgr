---
title: Agent Coding Standards & Secret Management
created: 2026-01-01
updated: 2026-01-01
status: Active
valid_until: 2026-04-01
priority: High
tags: [cicd, coding-standards, security]
---

# Agent Coding Standards & Secret Management

> **Purpose**
>
> This document defines **mandatory coding instructions, conventions, and secret‑management rules** for all engineers and AI coding agents (Copilot / Claude / Codex / Gemini).
>
> It also defines **GitHub Actions PRD requirements** that *enforce* these rules automatically.
>
> ❗ These rules are **non‑negotiable**. Violations must fail CI.

---

# Part 1. Instruction Prompt for Agent Coding (Human + AI)

This section **must be used verbatim** as a *System / Instruction Prompt* when using AI agents for code generation.

---

## 1. Agent Coding Instruction Prompt

```text
You are an expert software engineer working in a regulated, security‑critical environment.

You MUST follow the coding standards and security rules defined below.

=== GENERAL RULES ===
- Follow the defined code conventions exactly.
- Prefer clarity over brevity.
- Separate pure logic from side‑effects.
- All code must be testable.

=== CODE CONVENTIONS ===
- Follow project directory structure strictly.
- Do NOT mix responsibilities in a single function.
- State transitions must be explicit.
- Functions must be deterministic unless explicitly marked otherwise.
- Extract magic numbers to named constants (improves maintainability).
- Keep lines under 140 characters for readability.
- Place all imports at the top of files (except fixture-scoped lazy imports).
- Run linter (ruff/flake8) before committing code.

=== SECRET MANAGEMENT (CRITICAL) ===
- NEVER inline secrets, tokens, or credentials.
- NEVER generate fake or example secrets.
- NEVER include secrets in prompts, logs, tests, or comments.
- ALWAYS read secrets from environment variables.
- If a secret is required, use placeholders like ${API_KEY}.

=== FAILURE CONDITIONS ===
- If any rule is unclear, STOP and ask for clarification.
- If a requested change violates these rules, REFUSE and explain why.
```

---

## 1.1 Code Conventions

### 1.1.1 General (All Languages)

**Principles**
1. Explicit state > implicit context
2. Composition > inheritance
3. Small functions with single responsibility
4. Deterministic logic first, I/O last

**Naming**
| Element | Rule |
|---|---|
| Files | snake_case |
| Classes / Structs | PascalCase |
| Functions | snake_case |
| Constants | UPPER_CASE |

---

### 1.1.2 Python (FastAPI / LangGraph)

**Directory Structure (Mandatory)**
```text
app/
  graph/
    graph.py      # graph wiring only
    nodes.py      # pure node functions
  models/
    state.py      # Pydantic models only
  adapters/
    mock_llm.py
    mock_subagent.py
  main.py
```

**Rules**
- No global mutable state
- No logic inside FastAPI route handlers
- All LangGraph nodes must:
  - accept AgentState
  - return AgentState

**Linting & Formatting**
- **Preferred**: Ruff (fast, all-in-one linter + formatter)
- **Alternative**: Black (formatter) + flake8/pylint (linter)
- PEP8 compliance mandatory

**Ruff Configuration (Recommended)**
```toml
[tool.ruff]
line-length = 140
target-version = "py312"  # or your Python version

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "S",      # flake8-bandit (security)
    "PL",     # pylint
]

ignore = [
    "S101",     # Allow assert in tests
    "PLR0913",  # Allow many function arguments (common in configs)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "PLR2004", "PLC0415", "S603", "S607"]
# S101: asserts, PLR2004: magic numbers, PLC0415: imports in fixtures
# S603/S607: subprocess calls in integration tests
```

**Ruff Best Practices**
1. **Extract magic numbers to constants** (except in tests/config)
   ```python
   # ❌ Bad
   if queue_count > 3:
       handle_overflow()
   
   # ✅ Good
   MAX_QUEUE_SIZE = 3
   if queue_count > MAX_QUEUE_SIZE:
       handle_overflow()
   ```

2. **Imports at top of file** (except fixture-scoped imports in tests)
   ```python
   # ✅ Good - module level
   import os
   from app.models import State
   
   # ✅ Also acceptable in pytest fixtures
   @pytest.fixture
   def mock_client():
       from app.client import Client  # lazy load
       return Client()
   ```

3. **Security-sensitive patterns require justification**
   - `0.0.0.0` binding: Allowed for containerized apps (suppress with S104)
   - Subprocess calls: Require explicit review (suppress with S603/S607 only in tests)
   - Global statements: Use only for singleton patterns (suppress with PLW0603)

4. **Line length**: Keep under 140 characters (configurable)

5. **Auto-fix workflow**
   ```bash
   # Check for issues
   ruff check .
   
   # Auto-fix safe issues
   ruff check . --fix
   
   # Format code
   ruff format .
   ```

---



## 1.2 Secret Management

### 1.2.1 Absolute Prohibitions 🚫

| Item | Reason |
|---|---|
| Secrets in code | Guaranteed leak |
| Secrets in prompts | Logged / traced |
| Secrets in tests | CI log exposure |
| .env committed | Permanent compromise |

---

### 1.2.2 Approved Secret Sources

| Environment | Method |
|---|---|
| Local Dev | .env (gitignored) |
| CI/CD | GitHub Actions Secrets |
| Runtime | Cloud Secret Store |

---

### 1.2.3 Code Patterns

**Python**
```python
import os
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not set")
```

go
apiKey := os.Getenv("API_KEY")
if apiKey == "" {
    return errors.New("API_KEY not set")
}
```

---

# Part 2. PRD – GitHub Actions Pipeline Requirements

> This section defines **mandatory CI enforcement rules**.
>
> Any PR that violates these rules **must fail**.

---

## 2.1 Code Convention Enforcement

### 2.1.1 Python Linting & Formatting

**Required Tools (Choose One)**

**Option A: Ruff (Recommended - Fast & Modern)**
```yaml
- name: Lint with Ruff
  run: |
    pip install ruff
    ruff check .

- name: Format Check with Ruff
  run: ruff format --check .
```

**Option B: Traditional (Black + Flake8)**
```yaml
- name: Lint (flake8)
  run: flake8 app

- name: Format Check (black)
  run: black --check app
```

**PRD Requirements**
- CI must fail on linting errors (Ruff/flake8)
- CI must fail if formatting is incorrect (Ruff/black)
- Line length violations must be caught
- Security warnings (S-series) must be reviewed before suppression
- Magic numbers must be extracted to constants (except in allowed files)

**Ruff-Specific Requirements**
- All errors must pass or be explicitly suppressed with rationale
- Per-file ignores must be documented in `pyproject.toml`
- Suppressions require code review approval
- Security suppressions (S104, S603, S607) require security team review

---



## 2.2 Secret Management Enforcement

### 2.2.1 Secret Scanning (Mandatory)

**Approved Tools**
- GitHub Advanced Security (preferred)
- gitleaks (OSS alternative)

```yaml
- name: Secret Scan
  uses: gitleaks/gitleaks-action@v2
```

---

### 2.2.2 Environment Variable Injection Rules

- Secrets MUST be injected at job‑level
- Secrets MUST NOT be echoed

```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}
```

---

## 2.3 PR Gate Rules

**PR must be blocked if:**
- Lint fails
- Formatting fails
- Secret scan fails
- Tests fail

## 2.4 Reference CI/CD Pipelines (reuse across repos)

**Lint & Tests (fast feedback, no Docker)**
- Trigger: PRs to non-main/non-dev branches
- Steps: `uv sync` → `ruff check . --fix` → `ruff check .` → `mypy .` (continue-on-error) → `pytest -m "function or scenario or service"`
- Rationale: keep feature PRs fast; lint fixed automatically; type drift visible but non-blocking; no Docker dependency.

**Docker Smoke (runtime sanity)**
- Trigger: PRs to main/dev
- Steps: build image → `docker run -e PORT=5000 -p 5000:5000 ...` → retry `/health` on port 5000 (25 attempts, 1s) → log on failure.
- Rationale: validates container start with chart-aligned port (5000) and root/health probes.

**Deploy (ACR + chart bump)**
- Trigger: push to main/dev
- Steps: `uv sync` → build & push image → checkout chart repo → update `tag` in `values.yaml` → commit/push.
- Respect chart values: do **not** override `containerPort`; image listens on `$PORT` (default 5000); ensure service `targetPort` maps to 5000 and liveness/readiness use `/` or `/health` on 5000.

## 2.5 Branch Strategy & Workflow Triggers

- **Lint + Tests (non-blocking)**: runs on `push` to all branches except `main` and `dev`; results are informative only and do not block merges.
- **Docker Smoke**: build and runtime health check run on `pull_request` into `dev` or `main` to validate the container on port 5000 before merge.
- **Deploy**: image build/push and chart tag bump run on `push` to `dev` or `main`; relies on chart defaults for ports and probes.

**Kubernetes probes & ports (implementation phase)**
- App exposes `/` and `/health` on `$PORT` (default 5000); Docker exposes 5000.
- Helm service typically exposes port 8000 → targetPort 5000 (confirm in chart).
- Liveness/readiness: HTTP GET `/` on port 5000; initial delays per chart defaults.

---

# Final Declaration

> This document is the **single source of truth** for:
> - Agent coding behavior
> - Code quality standards
> - Secret management
> - CI enforcement

🚫 Any deviation is a security and quality defect.

✅ Compliance is mandatory.


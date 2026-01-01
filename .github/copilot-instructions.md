# Copilot Instructions for Session Manager

> 이 문서는 GitHub Copilot이 코드 생성 시 반드시 따라야 하는 규칙입니다.

---

## GENERAL RULES

- Follow the defined code conventions exactly.
- Prefer clarity over brevity.
- Separate pure logic from side-effects.
- All code must be testable.

---

## CODE CONVENTIONS

### Naming
| Element | Rule |
|---------|------|
| Files | snake_case |
| Classes / Structs | PascalCase |
| Functions | snake_case |
| Constants | UPPER_CASE |

### Python (FastAPI)
- No global mutable state
- No logic inside FastAPI route handlers
- Keep lines under 140 characters
- Place all imports at the top of files
- Extract magic numbers to named constants
- PEP8 compliance mandatory

### Directory Structure
```text
app/
  api/          # API routes only
  core/         # exceptions, utilities
  db/           # database connections
  schemas/      # Pydantic models
  services/     # business logic
  main.py
```

---

## SECRET MANAGEMENT (CRITICAL) 🚫

### Absolute Prohibitions
- NEVER inline secrets, tokens, or credentials in code
- NEVER generate fake or example secrets
- NEVER include secrets in prompts, logs, tests, or comments
- NEVER commit .env files

### Required Pattern
```python
import os

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not set")
```

- ALWAYS read secrets from environment variables
- If a secret is required, use placeholders like `${API_KEY}` or `os.getenv("API_KEY")`

---

## LINTING

- Use Ruff for linting and formatting
- Run `ruff check .` before committing
- Run `ruff format .` for formatting

---

## FAILURE CONDITIONS

- If any rule is unclear, STOP and ask for clarification.
- If a requested change violates these rules, REFUSE and explain why.

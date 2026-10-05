# NOOK backend

Collaboration-matching service for local shop owners (Python 3.12+, FastAPI).

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

```bash
cp .env.example .env
```

```bash
uvicorn app.main:app --reload
```

Check: `curl -i http://127.0.0.1:8000/health` → `{"status":"ok"}`

## Development

```bash
pip install -r requirements-dev.txt
```

```bash
ruff check .
```

```bash
pytest -q
```

CI (`.github/workflows/ci.yml`) runs the same lint and tests on every push and pull request.

## Folders

- `app/main.py` – FastAPI entrypoint.
- `app/core/` – settings and cross-cutting config.
- `app/api/` – HTTP routers and request/response schemas.
- `app/domain/` – business logic, independent of web and storage.
- `app/infra/` – external integrations (LLM, and later the database layer).
- `tests/` – automated tests.
- `docs/` – project documentation.

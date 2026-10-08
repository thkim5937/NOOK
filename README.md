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

## API contract

`api/openapi.yaml` is the **DRAFT** OpenAPI 3.1 contract derived from `docs/endpoints.md`. It needs agreement with the frontend and UI teammates; no endpoint is implemented yet. `tests/test_openapi_contract.py` keeps it consistent with the endpoint table, error codes and domain enums.

## Mock server

`tools/mock_server.py` serves placeholder data generated from the DRAFT contract so the frontend can try the API before the real server exists. It performs no real authentication: any non-empty Bearer token is accepted.

```bash
uvicorn tools.mock_server:app --port 8001
curl -s http://127.0.0.1:8001/v1/recommendations -H "Authorization: Bearer test"
curl -s -X POST http://127.0.0.1:8001/v1/collab-requests/req_001/cancel -H "Authorization: Bearer test" -H "X-Mock-Status: 409"
```

## Folders

- `app/main.py` – FastAPI entrypoint.
- `app/core/` – settings and cross-cutting config.
- `app/api/` – HTTP routers and request/response schemas.
- `app/domain/` – business logic, independent of web and storage.
- `app/infra/` – external integrations (LLM, and later the database layer).
- `tests/` – automated tests.
- `docs/` – project documentation.

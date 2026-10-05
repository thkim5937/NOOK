# Architecture (DRAFT)

Layers, with dependencies pointing inward:

    app/api  ->  app/domain  <-  app/infra

- **app/api** — HTTP layer (FastAPI). Not built yet. Calls domain rules and
  repository interfaces; never touches storage directly.
- **app/domain** — business rules (e.g. the collaboration request state machine)
  and repository interfaces (`app/domain/repositories.py`). No framework,
  database or `app.infra` imports.
- **app/infra** — implementations of the domain interfaces. Today:
  `app/infra/memory/` (in-memory, for development and tests). Later: a
  database-backed implementation.

Contract tests (`tests/contract/`) run the same suite against every repository
implementation. A new implementation is added to the `FACTORIES` list and must
pass unchanged.

## Ownership and scope

- The **database schema is owned by the data teammate** and is not delivered yet.
  The database-backed repository waits for that schema.
- This repository abstraction covers **CollabRequest only** for now.
- Client choice (app vs web) is undecided; domain and repository work does not depend on it.

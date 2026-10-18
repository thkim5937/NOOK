from fastapi import FastAPI

from app.api import collab_requests
from app.api.domain_errors import register_domain_error_handlers
from app.core.errors import register_exception_handlers

app = FastAPI(title="NOOK")
register_exception_handlers(app)
register_domain_error_handlers(app)
app.include_router(collab_requests.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

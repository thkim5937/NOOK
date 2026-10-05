from fastapi import FastAPI

from app.core.errors import register_exception_handlers

app = FastAPI(title="NOOK")
register_exception_handlers(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

from fastapi import FastAPI

app = FastAPI(title="NOOK")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

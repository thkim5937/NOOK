from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError, ErrorCode, register_exception_handlers


class Item(BaseModel):
    n: int


def make_client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    def app_error():
        raise AppError(ErrorCode.REQUEST_INVALID_STATE, "bad state", [{"x": 1}])

    @app.post("/items")
    def items(item: Item):
        return item

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret-internal-detail")

    return TestClient(app, raise_server_exceptions=False)


def test_app_error():
    r = make_client().get("/app-error")
    assert r.status_code == 409
    assert r.json() == {
        "error": {"code": "REQUEST_INVALID_STATE", "message": "bad state", "details": [{"x": 1}]}
    }


def test_validation_error():
    r = make_client().post("/items", json={"n": "abc"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert set(r.json()) == {"error"}
    assert set(err) == {"code", "message", "details"}
    assert err["code"] == "REQUEST_VALIDATION_FAILED"
    assert err["details"][0]["field"] == "body.n"


def test_not_found():
    r = make_client().get("/nope")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "NOT_FOUND", "message": "Not Found", "details": []}}


def test_method_not_allowed():
    r = make_client().post("/app-error")
    assert r.status_code == 405
    assert r.json() == {
        "error": {"code": "HTTP_ERROR", "message": "Method Not Allowed", "details": []}
    }


def test_unhandled_exception():
    r = make_client().get("/boom")
    assert r.status_code == 500
    assert r.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "Internal server error.", "details": []}
    }
    assert "secret-internal-detail" not in r.text

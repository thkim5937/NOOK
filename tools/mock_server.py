"""Contract-driven mock server for the DRAFT OpenAPI contract (development tooling only).

Run: uvicorn tools.mock_server:app --port 8001
Serves placeholder data from api/openapi.yaml; no real authentication.
"""

from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from jsonschema import Draft202012Validator

SPEC_PATH = Path(__file__).resolve().parent.parent / "api" / "openapi.yaml"
SPEC = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
METHODS = ("get", "post", "put", "patch", "delete")


def resolve(node):
    """Follow local $ref pointers until a concrete object is reached."""
    while isinstance(node, dict) and "$ref" in node:
        target = SPEC
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def error_body(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details or []}}


def error(status, code, message, details=None):
    return JSONResponse(error_body(code, message, details), status_code=status)


def generate(schema):
    """Smallest value that satisfies a schema (required properties only)."""
    schema = resolve(schema)
    if "example" in schema:
        return schema["example"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("oneOf", "anyOf"):
        if key in schema:
            return generate(schema[key][0])
    if "allOf" in schema:
        parts = [generate(s) for s in schema["allOf"]]
        return {k: v for p in parts for k, v in p.items()}
    kind = schema.get("type")
    if isinstance(kind, list):
        if "null" in kind:
            return None
        kind = kind[0]
    if kind == "object" or (kind is None and "properties" in schema):
        props = schema.get("properties", {})
        return {k: generate(props[k]) for k in schema.get("required", []) if k in props}
    if kind == "array":
        return [generate(schema["items"])] if "items" in schema else []
    return {"string": "string", "integer": 1, "number": 1, "boolean": True}.get(kind)


def media_body(response):
    """(has_body, body) for a response object: example, first examples value, or generated."""
    media = resolve(response).get("content", {}).get("application/json")
    if media is None:
        return False, None
    if "example" in media:
        return True, media["example"]
    if media.get("examples"):
        return True, resolve(next(iter(media["examples"].values())))["value"]
    return True, generate(media["schema"]) if "schema" in media else None


def respond(status, response):
    has_body, body = media_body(response)
    if not has_body:
        return Response(status_code=status)
    return JSONResponse(body, status_code=status)


def body_validator(op):
    """Draft 2020-12 validator for the JSON request body, or None."""
    media = resolve(op.get("requestBody", {})).get("content", {}).get("application/json")
    if not media or "schema" not in media:
        return None
    # Embedding components at the root lets "#/components/..." refs resolve.
    return Draft202012Validator({**media["schema"], "components": SPEC["components"]})


def make_handler(op, protected, validator):
    responses = {code: resolve(r) for code, r in op["responses"].items()}
    success = next(c for c in sorted(responses) if c.startswith("2"))
    documented = sorted(responses)

    async def handler(request: Request):
        auth = request.headers.get("authorization", "")
        if protected and not (auth.startswith("Bearer ") and auth[7:].strip()):
            return error(401, "AUTH_REQUIRED", "Authentication required.")

        forced = request.headers.get("x-mock-status")
        if forced:
            if forced not in responses or forced.startswith("2"):
                return error(
                    422,
                    "REQUEST_VALIDATION_FAILED",
                    f"Status {forced} is not a documented failure; documented: "
                    + ", ".join(documented),
                )
            response = responses[forced]
            if media_body(response)[0]:
                return respond(int(forced), response)
            return error(int(forced), "HTTP_ERROR", response.get("description", "Mock error."))

        if validator is not None:
            try:
                payload = await request.json()
            except ValueError:
                return error(422, "REQUEST_VALIDATION_FAILED", "Body is not valid JSON.")
            details = [
                {
                    "field": "body." + ".".join(map(str, e.path)),
                    "message": e.message,
                    "type": e.validator,
                }
                for e in validator.iter_errors(payload)
            ]
            if details:
                return error(
                    422, "REQUEST_VALIDATION_FAILED", "Request validation failed.", details
                )

        return respond(int(success), responses[success])

    return handler


app = FastAPI(title="NOOK mock server", version=SPEC["info"]["version"])

# Local development only: lets a browser-based frontend call the mock from any origin.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for path, item in SPEC["paths"].items():
    for method in METHODS:
        if method in item:
            op = item[method]
            protected = bool(op.get("security", SPEC.get("security", [])))
            app.add_api_route(
                path,
                make_handler(op, protected, body_validator(op)),
                methods=[method.upper()],
                name=op["operationId"],
                include_in_schema=False,
            )

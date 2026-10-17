import ast
import dataclasses
import uuid
from pathlib import Path

import pytest

import app.domain.auth as auth_module
from app.domain.auth import AuthenticatedUser, TokenError


def test_authenticated_user_is_frozen():
    user = AuthenticatedUser(user_id=uuid.uuid4())
    with pytest.raises(dataclasses.FrozenInstanceError):
        user.user_id = uuid.uuid4()  # type: ignore[misc]


def test_token_error_is_plain_exception():
    assert issubclass(TokenError, Exception)


def test_auth_domain_imports_no_jwt_infra_or_api():
    tree = ast.parse(Path(auth_module.__file__).read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    bad = [m for m in imported if m.split(".")[0] == "jwt" or m.startswith(("app.infra", "app.api"))]
    assert not bad

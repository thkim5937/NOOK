from app.core.config import Settings


def make(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_urls_without_trailing_slash():
    s = make(SUPABASE_URL="https://example.test")
    assert s.supabase_issuer == "https://example.test/auth/v1"
    assert s.supabase_jwks_url == "https://example.test/auth/v1/.well-known/jwks.json"


def test_urls_with_trailing_slash():
    s = make(SUPABASE_URL="https://example.test/")
    assert s.supabase_issuer == "https://example.test/auth/v1"
    assert s.supabase_jwks_url == "https://example.test/auth/v1/.well-known/jwks.json"


def test_urls_none_when_unset(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    s = make()
    assert s.SUPABASE_URL is None
    assert s.supabase_issuer is None
    assert s.supabase_jwks_url is None


def test_audience_default(monkeypatch):
    monkeypatch.delenv("SUPABASE_JWT_AUDIENCE", raising=False)
    assert make().SUPABASE_JWT_AUDIENCE == "authenticated"

# Authentication: Supabase access token verification

Code: `app/infra/auth/supabase_jwt.py` (verifier), `app/domain/auth.py` (`AuthenticatedUser`,
`TokenError`, `TokenVerifier`), `app/core/config.py` (settings). FastAPI wiring is a later task.

## Verification rules

A token is accepted only if all of these hold; any failure raises `TokenError` with a generic
message that never contains the token or library detail.

- Signature verifies against the public key whose `kid` matches the token header, fetched from
  `<project-url>/auth/v1/.well-known/jwks.json`.
- Algorithm is in the hard-coded list `("ES256",)`. The token header never chooses the algorithm,
  so `alg: none` and HS256-with-public-key-as-secret are rejected.
- Required claims present: `exp`, `iat`, `sub`, `iss`, `aud`.
- `iss` equals `<project-url>/auth/v1`; `aud` equals `SUPABASE_JWT_AUDIENCE` (default `authenticated`).
- `exp` not passed, allowing 10 seconds of leeway.
- `role` equals `authenticated` (`anon` and `service_role` are rejected).
- `is_anonymous` is not `true`.
- `sub` parses as a UUID; it becomes `AuthenticatedUser.user_id`.
- The token is a non-empty string.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `SUPABASE_URL` | unset | `<project-url>`; when unset, issuer and JWKS URL are `None` |
| `SUPABASE_JWT_AUDIENCE` | `authenticated` | expected `aud` |

## Key cache policy

`JwksKeyProvider` wraps `jwt.PyJWKClient`: key set cached at most 5 minutes (`lifespan=300`),
at most one refresh per 30 seconds when an unknown `kid` is seen (`cooldown_duration=30`),
5 second fetch timeout. After a key rotation, new keys are picked up within the cache lifetime;
to force it sooner, restart the process.

## Assumptions

- ES256 only (assumption): the project's JWKS currently exposes one ES256 (P-256) key. A rotation to
  another algorithm needs a code change to `ALLOWED_ALGORITHMS`.
- Leeway of 10 seconds (assumption).
- Anonymous-sign-in tokens are rejected (assumption).
- `role` must be `authenticated` (assumption).

## Unverified

- That real access tokens carry the `kid` published in the JWKS: check a real token header once
  available.
- Legacy HS256-only projects are not supported.

## Sources

- Supabase documentation: JWTs and the JWT claims reference.
- PyJWT documentation: `jwt.decode`, `PyJWKClient`, `PyJWK`.

## Request flow

1. The client sends `Authorization: Bearer <access token>`.
2. `extract_credentials` (`app/api/deps.py`) is the only code that reads the header. It checks the
   scheme case-insensitively and passes the bare token on, or `None` when the header is missing,
   has another scheme, or has no token.
3. `get_authenticator` picks the implementation from settings: `SupabaseAuthenticator` when the
   JWKS URL and issuer are both available (i.e. `SUPABASE_URL` is set), otherwise
   `NotConfiguredAuthenticator`, which denies everything. The Supabase authenticator is built once
   per process so the JWKS key cache survives across requests.
4. `SupabaseAuthenticator` rejects `None`, empty or whitespace-containing tokens, then calls
   `SupabaseJwtVerifier.verify`. Any `TokenError` becomes `AuthenticationFailed` with a generic
   message that never contains the token.
5. `current_owner` turns `AuthenticationFailed` into HTTP 401 with code `AUTH_REQUIRED` in the
   standard `{"error": {...}}` envelope.

`business_id` on the returned `AuthenticatedOwner` is intentionally `None`: a user may own several
businesses, so ownership of a given business is checked later in the service layer.

A JWKS outage (fetch error) surfaces as `TokenError` and therefore as 401 (assumption). Clients
cannot tell it apart from a bad token.

## Current contract state

At the time of writing, `api/openapi.yaml` already declares `components.securitySchemes.bearerAuth`
(`type: http`, `scheme: bearer`) and lists `bearerAuth` as `security` on the protected operations.
No current route in `app/` uses `current_owner` yet, so the flow above is covered by tests with a
test-only route. Adding bearer security to the remaining operations that lack it, and replacing the
"login method undecided" description, is a contract change (proposal, needs team agreement).

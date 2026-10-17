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

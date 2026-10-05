# Auth options for shop-owner login

**DRAFT - decision pending: app vs web**

Backend isolates this behind two plug-in points: `extract_credentials` (where credentials come
from) and an `Authenticator` (how they are verified). Routers only use `current_owner`.

## A. Bearer token (JWT access + refresh)
- Pros: natural for native/hybrid; no CORS-credential or CSRF issues; easy for non-browser clients.
- Cons: client must store tokens safely; refresh rotation/revocation is our job; XSS can steal
  tokens held in web JS storage.
- Native/hybrid: Keychain/Keystore storage; push and deep-link flows can carry/refresh tokens.
- Web: tokens in JS memory/localStorage (XSS exposure) or a BFF; plain CORS with `Authorization`.

## B. HttpOnly cookie session
- Pros: token not readable by JS (XSS-resistant); browser handles sending and expiry; simple
  server-side revocation.
- Cons: needs CSRF protection (SameSite + token); CORS must allow credentials with exact origins;
  awkward outside browsers.
- Native/hybrid: cookie jar handling differs per webview/HTTP stack; deep links and push taps
  opening a webview may lack the session.
- Web: best fit; same-site deployment avoids most CORS pain.

## C. Support both
- Pros: one backend serves app and web, each with its idiomatic transport.
- Cons: two code paths to secure and test; CSRF rules must apply only to the cookie path; larger
  attack surface.
- Impact: `extract_credentials` checks the header first, then the cookie; CSRF check applies only
  when the cookie was used.

## Decision question for the team
Will the shop-owner client be a native/hybrid app, a web page, or both at launch?

The choice only changes `extract_credentials` and the Authenticator implementation, not the routers.

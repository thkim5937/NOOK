# Collaboration request states

> **DRAFT - needs agreement with the UI/frontend teammate**

Implemented in `app/domain/collab_request.py` (pure logic, no web/DB code).
Aligned with the Supabase `collab_requests` table; where UI and DB conflict, the UI wins.

## Sources
All entry paths create the same request object; only `source` differs.

| Source | Meaning | `post_id` |
|---|---|---|
| `ai_recommendation` | Started from an AI-recommended business | must be absent |
| `collab_post` | Started from a collaboration post | required (int) |
| `profile` | Started from a business profile | must be absent |

## Fields
| Field | Type | Notes |
|---|---|---|
| `id` | int | positive integer (database bigint) |
| `sender_business_id` | int | must differ from `receiver_business_id` |
| `receiver_business_id` | int | |
| `source` | enum | see above |
| `status` | enum | see below |
| `post_id` | int \| None | only for `collab_post` |
| `message` | str \| None | |
| `match_id` | int \| None | |
| `collab_type` | enum \| None | **PROVISIONAL** - values (`limited_product`, `popup`, `joint_event`, `sns_collab`) are not final until the data teammate fixes the DB catalog |
| `desired_timing` | str \| None | |
| `responded_at` | datetime \| None | set to the `now` passed to accept/reject/cancel |

**Not persistable yet:** `collab_type` and `desired_timing` are kept in the domain and in the contract because the UI needs them (assumption), but the database table `collab_requests` has no such columns, so they cannot be persisted until proposal P4 in `docs/db-change-proposals.md` is applied.

The domain never reads the clock; callers pass a timezone-aware `now`.

## States and transitions

```
            accept (receiver)
        +--------------------> accepted
        |  reject (receiver)
pending +--------------------> rejected
        |  cancel (sender)
        +--------------------> cancelled
```

| From | To | Triggered by |
|---|---|---|
| (new) | `pending` | Sender (`sender_business_id` must differ from `receiver_business_id`) |
| `pending` | `accepted` | Receiver only |
| `pending` | `rejected` | Receiver only |
| `pending` | `cancelled` | Sender only |
| `accepted` | - | Final |
| `rejected` | - | Final |
| `cancelled` | - | Final |

Wrong actor raises `NotRecipient` (accept/reject) or `NotSender` (cancel); a disallowed
current status raises `InvalidStateTransition`.

## Service rules
Implemented in `app/domain/collab_request_service.py` against ports (`BusinessOwnership`, a clock, `CollabRequestRepository`). `owner_id` is the authenticated user id.

1. `create` checks, in this order: (a) sender equals receiver raises `InvalidRequest` (422 `REQUEST_VALIDATION_FAILED`) (assumption); (b) the user does not own the sender business raises `Forbidden` (403 `AUTH_FORBIDDEN`); (c) a pending request already exists between the two businesses in either direction raises `DuplicatePendingRequest` (409 `REQUEST_INVALID_STATE`) (assumption: both directions); (d) otherwise the request is created as `pending` and stored.
2. `accept` / `reject`: only an owner of the receiver business, otherwise `Forbidden`. An unknown id raises `NotFoundInRepository` (404 `NOT_FOUND`). An illegal transition raises `InvalidStateTransition` (409 `REQUEST_INVALID_STATE`). On success `responded_at` is the clock value.
3. `cancel`: only an owner of the sender business, from `pending` only. `responded_at` stays empty (assumption; the pure `cancel()` function still sets it, the service clears it).
4. The permission check runs before the state check (assumption), after the request is found. A `Forbidden` message is generic and never reveals request state.

Pure `cancel()` still sets `responded_at`; the service clears it afterwards (known inconsistency, not fixed here).

## Routes
Implemented in `app/api/collab_requests.py`. All require `Authorization: Bearer ...` (`current_owner`; failure is 401 `AUTH_REQUIRED`) and answer with `{"data": CollabRequest}`.

| Method and path | Service call | Success |
|---|---|---|
| `POST /v1/collab-requests` | `create` | 201 |
| `POST /v1/collab-requests/{id}/accept` | `accept` | 200 |
| `POST /v1/collab-requests/{id}/reject` | `reject` | 200 |
| `POST /v1/collab-requests/{id}/cancel` | `cancel` | 200 |

The create body is strict: integer ids (no strings), `source` / `collab_type` enums, unknown fields rejected (422). `{id}` must be an integer >= 1.

### Error mapping
One place: `app/api/domain_errors.py`. Messages are generic (no token, owner id or other users' data). Anything unmapped stays 500 `INTERNAL_ERROR`.

| Domain error | Code | HTTP |
|---|---|---|
| `Forbidden` | `AUTH_FORBIDDEN` | 403 |
| `DuplicatePendingRequest` | `REQUEST_INVALID_STATE` | 409 |
| `InvalidStateTransition` | `REQUEST_INVALID_STATE` | 409 |
| `InvalidRequest` | `REQUEST_VALIDATION_FAILED` | 422 |
| `NotFoundInRepository` | `NOT_FOUND` | 404 |

### Assumptions
- Unknown id gives 404 before the ownership check (403). Assumption: request ids are sequential integers and their existence is not secret.
- Default wiring denies every write: the repository is one process-wide in-memory instance, and ownership is `NotConfiguredBusinessOwnership` (`owns()` is always false), so real routes answer 403 until a database ownership adapter exists. The mock server stays the frontend's target. Repository, ownership and clock are replaceable through FastAPI dependency overrides (`get_collab_repository`, `get_business_ownership`, `get_clock`).
- Ids come from one process-wide counter (the service is built per request).

### Contract mismatches (contract not edited)
- `POST /v1/collab-requests` can answer 409 (duplicate pending); the contract does not document 409. It documents 404, which this route can never produce.
- `accept` and `reject` can answer 403 and 422 (path id < 1); the contract documents neither.
- `cancel` / `accept` / `reject` with id < 1 answer 422; only `create` documents 422.
- The create schema does not say `additionalProperties: false`; the implementation rejects unknown fields anyway.
- The `cancel` example shows a non-null `responded_at`; the service returns null (the schema allows it).

Limits: the duplicate check is not atomic (two concurrent creates can both pass it), and the database has no uniqueness on business pairs. Proposal P5 in `docs/db-change-proposals.md` would close this.

## Not decided - NOT modeled here
- Rate limits on sending requests
- Opt-out
- The moment contact information is revealed

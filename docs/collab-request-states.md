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

Error mapping: there is no domain-error-to-HTTP mapping in the code yet (`app/core/errors.py` only handles `AppError`), so none was added. Intended mapping for the future HTTP layer: `Forbidden` to `AUTH_FORBIDDEN` (403), `DuplicatePendingRequest` and `InvalidStateTransition` to `REQUEST_INVALID_STATE` (409), `InvalidRequest` to `REQUEST_VALIDATION_FAILED` (422), `NotFoundInRepository` to `NOT_FOUND` (404).

Limits: the duplicate check is not atomic (two concurrent creates can both pass it), and the database has no uniqueness on business pairs. Proposal P5 in `docs/db-change-proposals.md` would close this.

## Not decided - NOT modeled here
- Rate limits on sending requests
- Opt-out
- The moment contact information is revealed

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
| `id` | str | |
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

The domain never reads the clock; callers pass a timezone-aware `now`.

## States and transitions

```
            accept (receiver)
        +--------------------> ACCEPTED
        |  reject (receiver)
PENDING +--------------------> REJECTED
        |  cancel (sender)
        +--------------------> CANCELLED
```

| From | To | Triggered by |
|---|---|---|
| (new) | `PENDING` | Sender (`sender_business_id` must differ from `receiver_business_id`) |
| `PENDING` | `ACCEPTED` | Receiver only |
| `PENDING` | `REJECTED` | Receiver only |
| `PENDING` | `CANCELLED` | Sender only |
| `ACCEPTED` | - | Final |
| `REJECTED` | - | Final |
| `CANCELLED` | - | Final |

Wrong actor raises `NotRecipient` (accept/reject) or `NotSender` (cancel); a disallowed
current status raises `InvalidStateTransition`.

## Not decided - NOT modeled here
- Rate limits on sending requests
- Opt-out
- The moment contact information is revealed

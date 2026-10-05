# Collaboration request states

> **DRAFT - needs agreement with the UI/frontend teammate**

Implemented in `app/domain/collab_request.py` (pure logic, no web/DB code).

## Sources
All three entry paths create the same request object; only `source` differs.

| Source | Meaning |
|---|---|
| `RECOMMENDATION` | Started from a recommended business |
| `LOVE_CALL` | Started from a love call post (`post_id` set) |
| `PROFILE` | Started from a business profile |

## States and transitions

| From | To | Triggered by |
|---|---|---|
| (new) | `PENDING` | Sender (`sender_business_id` must differ from recipient) |
| `PENDING` | `ACCEPTED` | Recipient only |
| `PENDING` | `REJECTED` | Recipient only |
| `ACCEPTED` | - | Final |
| `REJECTED` | - | Final |

## Not decided - NOT modeled here
- Rate limits on sending requests
- Opt-out
- The moment contact information is revealed

INTERNAL DRAFT - not agreed with FE/UI/Data teammates yet.

| Feature | Method | Path | Actor | Purpose | Status |
|---|---|---|---|---|---|
| F1 | POST | /v1/businesses/{business_id}/verification | owner | Verify business registration number (registry lookup vs document upload undecided) | tbd |
| F1 | POST | /v1/businesses/{business_id}/intro-draft | owner | AI-generated one-line intro draft for the owner to edit | draft |
| F1 | POST | /v1/me/consents | owner | Record consents | draft |
| F2 | GET | /v1/recommendations | owner | AI-recommended collaboration candidates among registered shops | draft |
| F3 | POST | /v1/collab-requests | owner | Send collaboration request; one flow for all entry paths via source (ai_recommendation / collab_post / profile); rate limits, opt-out, notification channel undecided | tbd |
| F3 | GET | /v1/collab-requests?box=sent\|received | owner | List sent or received requests | draft |
| F3 | POST | /v1/collab-requests/{id}/accept | owner | Receiver accepts (when contact info is revealed undecided) | tbd |
| F3 | POST | /v1/collab-requests/{id}/reject | owner | Receiver rejects | draft |
| F3 | POST | /v1/collab-requests/{id}/cancel | owner | Sender cancels a pending request | draft |
| F3 | POST | /v1/posts/{id}/love-call | owner | Respond to a love call; creates a collab request with source=collab_post | draft |
| F5 | POST | /v1/me/marketing-links | owner | Link marketing data (e.g. Instagram); AI input only, never shown to other owners | tbd |
| F5 | DELETE | /v1/me/marketing-links/{id} | owner | Unlink marketing data | tbd |
| F6 | POST | /v1/collab-requests/{id}/ideas | owner | AI collaboration ideas and promotional content; output labeled AI-generated with "NOOK collaboration partner" disclosure | draft |
| F7 | POST | /v1/public/coupons/{code}/scan | guest | Record coupon/QR scan or redemption (scope undecided) | tbd |
| F7 | GET | /v1/me/measurements | owner | Coupon/QR effect results (scope undecided) | tbd |

Removed from the backend contract (2026-10-08)

(a) Handled directly by the app via Supabase (not served by this backend):
- GET /v1/me/business - read own shop profile
- PUT /v1/me/business - update own shop profile
- POST /v1/me/business/photos - shop photo upload
- GET /v1/posts - recruitment posts list
- POST /v1/posts - recruitment post create

(b) Removed as out of scope for the first release or no screen/storage:
- POST /v1/courses - F8 create course
- POST /v1/courses/{id}/confirm - F8 confirm course
- POST /v1/courses/{id}/publish - F8 publish course
- GET /v1/public/neighborhoods - F8 neighborhood list
- GET /v1/public/neighborhoods/{id}/courses - F8 neighborhood courses
- GET /v1/public/courses/{slug} - F8 course detail
- POST /v1/recommendations/preferences - recommendation preferences (no screen or storage)

Path renames (business-scoped, one account can own several businesses): POST /v1/me/business/verification is now POST /v1/businesses/{business_id}/verification; POST /v1/me/business/intro-draft is now POST /v1/businesses/{business_id}/intro-draft.

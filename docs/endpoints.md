INTERNAL DRAFT - not agreed with FE/UI/Data teammates yet.

| Feature | Method | Path | Actor | Purpose | Status |
|---|---|---|---|---|---|
| F1 | POST | /v1/businesses | owner | Register a business; server-side verification; clients cannot insert business rows | draft |
| F1 | POST | /v1/businesses/{business_id}/verification | owner | Verify business registration number (registry lookup vs document upload undecided) | tbd |
| F1 | POST | /v1/businesses/{business_id}/intro-draft | owner | AI-generated one-line intro draft for the owner to edit | draft |
| F1 | POST | /v1/me/consents | owner | Record consents | draft |
| F2 | GET | /v1/recommendations | owner | AI-recommended collaboration candidates among registered shops | draft |
| F3 | POST | /v1/collab-requests | owner | Send collaboration request; one flow for all entry paths via source (ai_recommendation / collab_post / profile); rate limits, opt-out, notification channel undecided | tbd |
| F3 | POST | /v1/collab-requests/{id}/accept | owner | Receiver accepts (when contact info is revealed undecided) | tbd |
| F3 | POST | /v1/collab-requests/{id}/reject | owner | Receiver rejects | draft |
| F3 | POST | /v1/collab-requests/{id}/cancel | owner | Sender cancels a pending request | draft |
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

(c) Removed from the backend contract (2026-10-16); each can be restored from git history using the old method and path:
- GET /v1/collab-requests?box=sent|received - list of collaboration requests. The app reads them directly through Supabase because the row-level security rules let participating owners read their own requests.
- POST /v1/posts/{id}/love-call - the love call is the create-request operation (POST /v1/collab-requests) with source=collab_post and a post_id.
- POST /v1/me/marketing-links - Instagram link. instagram_url is a column of the business profile, so the app writes it directly through Supabase.
- DELETE /v1/me/marketing-links/{id} - unlink Instagram; same reason (clear the instagram_url column).

## Business registration

POST /v1/businesses registers a business. The server does it because the database blocks client inserts into business_profiles and client writes to the verification fields (trigger nook_business_verification_guard, see docs/database.md).

Flow:
1. The app sends business_number, business_name, opening_date and category (the app completes the rest of the profile afterwards directly in Supabase).
2. The server calls the database function nook_consume_verification_attempt, which enforces the limit of 5 attempts per 10 minutes per user. Over the limit: 429 RATE_LIMITED.
3. The server looks the number up with the tax authority, inserts the row and returns 201 with id and verification_status.

Result mapping (assumption): valid number gives `verified`, invalid gives `rejected`, lookup unavailable gives `pending`.

Other points:
- The business number is digits only, 10 characters, no hyphens (assumption).
- The lookup uses the user's registered legal name (assumption). The external lookup request fields are unverified: verify them against the official API documentation before implementation.
- A business_number that is already registered gives 409 REQUEST_INVALID_STATE. Trade-off: a rejected row keeps its number reserved, because business_number is unique.
- Businesses in `pending` or `rejected` state retry through POST /v1/businesses/{business_id}/verification; retries count toward the same limit.

Error code RATE_LIMITED (HTTP 429) is new: too many verification attempts.

## Acting business

One account can own several businesses, so the client says which business it acts as, and the server verifies that the caller owns it:
- POST /v1/collab-requests: `sender_business_id` in the request body.
- GET /v1/recommendations and GET /v1/me/measurements: required `business_id` query parameter.
- Accept, reject, cancel and ideas: no business is passed; the acting business is derived from the request (receiver for accept/reject, sender for cancel).
- Verification and intro-draft: `business_id` path parameter.
- If the caller does not own the given business, the server answers 403 AUTH_FORBIDDEN.

## Path renames

Path renames (business-scoped, one account can own several businesses): POST /v1/me/business/verification is now POST /v1/businesses/{business_id}/verification; POST /v1/me/business/intro-draft is now POST /v1/businesses/{business_id}/intro-draft.

Verified database facts: see docs/database.md.

## Field renames (2026-10-16)

Business fields now use the `business_profiles` column names. These are provisional defaults for the frontend to review; see docs/catalog.md for the option values.

| Old name | New name |
|---|---|
| industry | category |
| neighborhood_id | district (string, the neighborhood display name, nullable, max 50) |
| main_customers | target_customers |
| quiet_hours | slow_times |
| name (business) | business_name |
| intro (business) | ai_intro |

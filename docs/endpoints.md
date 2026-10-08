INTERNAL DRAFT - not agreed with FE/UI/Data teammates yet.

| Feature | Method | Path | Actor | Purpose | Status |
|---|---|---|---|---|---|
| F1 | POST | /v1/me/business/verification | owner | Verify business registration number (registry lookup vs document upload undecided) | tbd |
| F1 | GET | /v1/me/business | owner | Read own shop profile | draft |
| F1 | PUT | /v1/me/business | owner | Save shop profile: industry, main customer group, quiet hours, mood tags, intro, optional Instagram link | draft |
| F1 | POST | /v1/me/business/photos | owner | Get presigned upload URL for shop photos (1-3) | draft |
| F1 | POST | /v1/me/business/intro-draft | owner | AI-generated one-line intro draft for the owner to edit | draft |
| F1 | POST | /v1/me/consents | owner | Record consents | draft |
| F2 | GET | /v1/recommendations | owner | AI-recommended collaboration candidates among registered shops | draft |
| F2 | POST | /v1/recommendations/preferences | owner | Answer the AI's first-time question: what kind of shop to collaborate with | draft |
| F3 | POST | /v1/collab-requests | owner | Send collaboration request; one flow for all entry paths via source (recommendation / love_call / profile); rate limits, opt-out, notification channel undecided | tbd |
| F3 | GET | /v1/collab-requests?box=sent\|received | owner | List sent or received requests | draft |
| F3 | POST | /v1/collab-requests/{id}/accept | owner | Recipient accepts (when contact info is revealed undecided) | tbd |
| F3 | POST | /v1/collab-requests/{id}/reject | owner | Recipient rejects | draft |
| F3 | POST | /v1/posts/{id}/love-call | owner | Respond to a love call; creates a collab request with source=love_call | draft |
| F4 | GET | /v1/posts | owner | List collaboration recruitment posts / love calls | draft |
| F4 | POST | /v1/posts | owner | Create a recruitment post / love call | draft |
| F5 | POST | /v1/me/marketing-links | owner | Link marketing data (e.g. Instagram); AI input only, never shown to other owners | tbd |
| F5 | DELETE | /v1/me/marketing-links/{id} | owner | Unlink marketing data | tbd |
| F6 | POST | /v1/collab-requests/{id}/ideas | owner | AI collaboration ideas and promotional content; output labeled AI-generated with "NOOK collaboration partner" disclosure | draft |
| F7 | POST | /v1/public/coupons/{code}/scan | guest | Record coupon/QR scan or redemption (scope undecided) | tbd |
| F7 | GET | /v1/me/measurements | owner | Coupon/QR effect results (scope undecided) | tbd |
| F8 | POST | /v1/courses | owner | Create collaboration course (AI draft + owner confirmation is only a proposal) | tbd |
| F8 | POST | /v1/courses/{id}/confirm | owner | Owner confirms course | tbd |
| F8 | POST | /v1/courses/{id}/publish | owner | Publish course to the public page | tbd |
| F8 | GET | /v1/public/neighborhoods | guest | Neighborhood list; customer picks manually, no GPS | draft |
| F8 | GET | /v1/public/neighborhoods/{id}/courses | guest | Neighborhood overview and its collaboration courses | draft |
| F8 | GET | /v1/public/courses/{slug} | guest | Course detail: ordered shops and collaboration benefits (via link/QR) | draft |

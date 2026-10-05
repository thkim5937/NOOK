# Error codes

**DRAFT - needs agreement with the frontend teammate**

Every error response has exactly this body:

```json
{"error": {"code": "<ErrorCode>", "message": "<text>", "details": []}}
```

The frontend should branch on `code`, not on `message`.

| Code | HTTP status | Meaning |
|---|---|---|
| AUTH_REQUIRED | 401 | Not logged in, or token missing/expired |
| AUTH_FORBIDDEN | 403 | Logged in but not allowed to do this |
| NOT_FOUND | 404 | Resource or path does not exist |
| REQUEST_INVALID_STATE | 409 | Action not allowed in the resource's current state |
| REQUEST_VALIDATION_FAILED | 422 | Request body/params invalid; field errors in `details` |
| INTERNAL_ERROR | 500 | Unexpected server error; no internal details exposed |
| HTTP_ERROR | original status | Any other framework HTTP error (e.g. 405 Method Not Allowed) |

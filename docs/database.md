# Database facts (verified 2026-10-16)

## How this was verified

Read-only metadata queries in the Supabase SQL Editor (information_schema.columns, pg_policies, pg_class, pg_constraint, information_schema.triggers, information_schema.table_privileges, pg_proc function definitions, information_schema.routine_privileges) plus a request to the public JWKS endpoint. No data rows were read or written. The environment (production or development) is unknown and is treated as production. This is a snapshot; the database can change, so re-verify before relying on it.

## Tables

All tables are in the public schema, all ids are bigint unless noted, and row-level security (RLS) is enabled on all 12 tables.

- business_profiles: id PK; owner_id uuid NOT NULL, FK auth.users ON DELETE CASCADE, NOT unique (one account can own several businesses); business_number varchar NOT NULL UNIQUE; business_name varchar NOT NULL; category varchar NOT NULL; target_customers, slow_times, mood_tags text[] default '{}'; ai_intro text; instagram_url text; district varchar; address text; verification_status varchar default 'pending' CHECK in (pending, verified, rejected); created_at, updated_at timestamptz default now(); opening_date date; nts_status_code varchar; verified_at timestamptz. There are no CHECK constraints on category or on the three array columns, so allowed values are not enforced by the database.
- business_photos: id; business_id FK business_profiles CASCADE; image_url text NOT NULL; ai_tags text[]; created_at.
- collab_posts: id; business_id FK CASCADE; title varchar NOT NULL; description; wanted_categories text[]; start_date, end_date date; status default 'open' CHECK in (open, closed, completed); created_at, updated_at.
- collab_matches: id; business_a_id and business_b_id FK business_profiles CASCADE, CHECK a <> b, no unique constraint and no ordering rule; match_score numeric; match_reason jsonb; model_version varchar; created_at.
- collab_requests: id; sender_business_id and receiver_business_id FK CASCADE, CHECK sender <> receiver; match_id FK collab_matches ON DELETE SET NULL; post_id FK collab_posts ON DELETE SET NULL; message text; source varchar NOT NULL CHECK in (ai_recommendation, collab_post, profile); status default 'pending' CHECK in (pending, accepted, rejected, cancelled); created_at; responded_at. There is no updated_at, no unique constraint on business pairs, and no collab_type or desired_timing column.
- collab_contents: id; collab_request_id FK CASCADE; idea_text; marketing_copy; content_type CHECK in (collab_idea, instagram, course, promotion, other); ai_metadata jsonb; created_at.
- coupons: id; collab_request_id FK CASCADE; coupon_code varchar NOT NULL UNIQUE; qr_url; title; start_date, end_date; status default 'active' CHECK in (active, expired, disabled); created_at.
- coupon_redemptions: id; coupon_id FK coupons CASCADE; redeemed_at default now().
- external_events: id; event_name NOT NULL; district; event_type; description; start_date, end_date; source_url; created_at.
- nook_verification_limits: user_id uuid PK, FK auth.users CASCADE; window_start timestamptz NOT NULL; attempts integer NOT NULL.
- staff_accounts: user_id uuid PK, FK auth.users CASCADE; created_at.
- user_profiles: id uuid PK, FK auth.users CASCADE; full_name text NOT NULL; created_at.

## Row-level security

Policies apply to the authenticated role unless stated. user_owns_business(id) means the caller owns that business.

- business_photos: SELECT everyone logged in; INSERT, UPDATE, DELETE only the owner.
- business_profiles: SELECT everyone logged in (true); INSERT allowed by policy for own rows but blocked by a trigger for clients; UPDATE own rows (two equivalent policies); DELETE own rows.
- collab_posts: SELECT everyone logged in; INSERT, UPDATE, DELETE only the owner.
- collab_matches: SELECT only owners of business_a or business_b; no write policy.
- collab_requests: SELECT participants (owner of sender or receiver); INSERT if the caller owns the sender business; UPDATE by either participant (USING and WITH CHECK both allow sender or receiver owner); DELETE by the sender owner.
- collab_contents, coupons, coupon_redemptions: SELECT participants of the request; no write policy.
- external_events: SELECT everyone logged in.
- staff_accounts: SELECT own row. user_profiles: SELECT own row (three equivalent policies, one targets role public but still requires auth.uid()).
- nook_verification_limits: RLS enabled, no policy (server-only).

## Triggers and functions

- Trigger nook_business_verification_guard (BEFORE INSERT, UPDATE on business_profiles, function nook_guard_business_verification): service_role, and postgres or supabase_admin with no JWT role, are allowed. Any other INSERT raises "Business registration requires trusted server verification". Any other UPDATE that changes owner_id, business_number, opening_date, verification_status, nts_status_code or verified_at raises an error.
- Trigger nook_user_profile_immutable (BEFORE UPDATE, DELETE on user_profiles, function nook_guard_user_profile): anon and authenticated cannot delete; id and full_name cannot be changed.
- nook_create_signup_profile(): SECURITY DEFINER; creates the user_profiles row from raw_user_meta_data.full_name (1 to 100 characters, otherwise sign-up fails). It is presumably attached to auth.users; that trigger was not inspected.
- nook_consume_verification_attempt(user_id uuid) returns boolean: SECURITY DEFINER; per user, a 10-minute window, at most 5 attempts. No EXECUTE grant to anon, authenticated or PUBLIC (server-only).
- user_owns_business(bigint) and user_in_collab_request(bigint): SECURITY DEFINER STABLE helpers used by RLS; EXECUTE granted to PUBLIC; they only answer about the caller (auth.uid()).
- rls_auto_enable(): event trigger that enables RLS on new tables in public.

## Privileges

anon has no SELECT, INSERT, UPDATE or DELETE on any public table (only TRIGGER, REFERENCES, TRUNCATE). authenticated has full CRUD on business_photos, business_profiles, collab_posts and collab_requests; SELECT only on collab_contents, collab_matches, coupons, coupon_redemptions, external_events, staff_accounts and user_profiles; no privilege on nook_verification_limits. Both roles also hold TRUNCATE, REFERENCES and TRIGGER on most tables (Supabase defaults; not reachable through the REST API as far as known).

## Authentication keys

The public JWKS endpoint (<project-url>/auth/v1/.well-known/jwks.json) returned one ES256 (curve P-256) public key. Access tokens are therefore verified locally against the JWKS, matching the token header kid, accepting only ES256. Not yet verified: that a real access token header carries this kid. Keys can rotate, so the JWKS must not be cached for long and an unknown kid must trigger a refresh.

## Findings

Closed: verification_status and the identity fields cannot be changed by clients (trigger); nook_consume_verification_attempt is not callable by clients.

Open (see docs/db-change-proposals.md):

- F-1 Either participant can UPDATE any column of a collab request, so the sender can accept their own request.
- F-2 Any logged-in user can read business_number and owner_id of every business.
- F-3 INSERT only checks that the caller owns the sender business, so a request can be created directly with status 'accepted' or a responded_at value, bypassing backend rules (same-industry rule, duplicate check, source consistency).
- F-4 The sender can DELETE a request; CASCADE removes collab_contents, coupons and coupon_redemptions, including those of accepted collaborations.
- F-5 (low) TRUNCATE is granted to anon and authenticated.

## What this means for the backend

- Server-only writes (service role): collab_matches, collab_contents, coupons, coupon_redemptions, nook_verification_limits, business registration and all verification fields.
- Until F-1, F-3 and F-4 are fixed in the database, the backend rules for collaboration requests are not enforced against clients that call Supabase directly.
- The database does not enforce allowed values for category, target_customers, slow_times or mood_tags; the backend must validate them.
- The backend must set responded_at on accept and reject, prevent duplicate pending requests between the same two businesses, and set updated_at on its own writes.
- collab_matches rows are visible to both businesses, so match_reason must contain only reason codes that are safe to show to both sides; never store hidden or one-sided signals.
- Pair order in collab_matches is not enforced. Provisional convention (assumption): business_a is the business the recommendation was made for, business_b is the recommended candidate.
- Call nook_consume_verification_attempt before every external business-verification lookup and refuse when it returns false.

## Not in the database

No tables or columns for push tokens, consents, coupon-scan measurement summaries, marketing links, courses, coordinates (latitude, longitude), collab_type or desired_timing.

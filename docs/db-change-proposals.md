# Database change proposals (not applied)

## Status

These are proposals written by the backend side. They are untested and have never been applied from this repository. The database owner decides whether and how to apply them. Test them on a copy or a staging project first, because the environment is treated as production. Evidence refers to the findings in docs/database.md.

## P1 collab_requests writes only through the backend (covers F-1, F-3, F-4)

### Evidence

- INSERT policy only checks that the caller owns the sender business (F-3).
- UPDATE policy allows either participant to change any column (F-1).
- DELETE policy lets the sender delete a request, and CASCADE removes collab_contents, coupons and coupon_redemptions (F-4).
- authenticated holds full CRUD on collab_requests.

### Risk

A client calling Supabase directly can create a request with status 'accepted', accept its own request, skip the same-industry and duplicate checks, or delete an accepted collaboration together with its coupons.

### Proposal

```sql
revoke insert, update, delete on public.collab_requests from authenticated;
drop policy "Owners can send collab requests" on public.collab_requests;
drop policy "Participants can update collab requests" on public.collab_requests;
drop policy "Senders can delete collab requests" on public.collab_requests;
```

A weaker alternative, if the app must keep direct writes: add guard triggers that force status 'pending' and null responded_at on INSERT, allow only the receiver to move pending to accepted or rejected, allow only the sender to move pending to cancelled, forbid changes to every other column, and forbid DELETE of non-pending requests. This still leaves the backend-only rules (same-industry rule, duplicate check) unenforced.

### Impact on the app

The app can no longer create, change or delete requests directly; it calls the backend (the service role bypasses RLS). SELECT for participants stays.

### How to verify afterwards (read-only queries)

```sql
select policyname, cmd from pg_policies where tablename = 'collab_requests';
```

Only the SELECT policy remains.

```sql
select privilege_type from information_schema.table_privileges where table_name = 'collab_requests' and grantee = 'authenticated';
```

No INSERT, UPDATE or DELETE.

### Rollback

```sql
grant insert, update, delete on public.collab_requests to authenticated;
create policy "Owners can send collab requests" on public.collab_requests for insert to authenticated with check (user_owns_business(sender_business_id));
create policy "Participants can update collab requests" on public.collab_requests for update to authenticated using (user_owns_business(sender_business_id) or user_owns_business(receiver_business_id)) with check (user_owns_business(sender_business_id) or user_owns_business(receiver_business_id));
create policy "Senders can delete collab requests" on public.collab_requests for delete to authenticated using (user_owns_business(sender_business_id));
```

## P2 hide business_number from other users (covers F-2)

### Evidence

business_profiles has a SELECT policy of true for every logged-in user, and authenticated has SELECT on all columns, including business_number and owner_id (F-2).

### Risk

Any logged-in user can read the business registration number and owner account id of every business.

### Proposal

```sql
revoke select on public.business_profiles from authenticated;
grant select (id, business_name, category, target_customers, slow_times, mood_tags, ai_intro, instagram_url, district, address, verification_status, created_at, updated_at) on public.business_profiles to authenticated;
```

Alternative: a view with only the public columns, and a SELECT policy on the base table limited to the owner.

### Impact on the app

- Queries using select=* will fail and must list columns.
- owner_id, business_number, opening_date, nts_status_code and verified_at become unreadable to the app, including for the owner. The backend must return the owner's own business number through an owner-only endpoint.
- UPDATE with returning data needs SELECT on the returned columns.
- Whether RLS expressions that reference owner_id need extra grants is untested, so test first.

### How to verify afterwards (read-only queries)

```sql
select column_name from information_schema.column_privileges where table_name = 'business_profiles' and grantee = 'authenticated' and privilege_type = 'SELECT';
```

business_number must not appear.

### Rollback

```sql
grant select on public.business_profiles to authenticated;
```

## P3 (optional, low) remove TRUNCATE (covers F-5)

### Evidence

anon and authenticated hold TRUNCATE on most public tables (Supabase defaults, F-5).

### Risk

Low: not reachable through the REST API as far as known, but it removes a privilege that is never needed.

### Proposal

```sql
revoke truncate on all tables in schema public from anon, authenticated;
```

### Impact on the app

None expected; the app does not truncate tables.

### How to verify afterwards (read-only queries)

```sql
select table_name, grantee from information_schema.table_privileges where table_schema = 'public' and privilege_type = 'TRUNCATE' and grantee in ('anon', 'authenticated');
```

No rows.

### Rollback

```sql
grant truncate on all tables in schema public to anon, authenticated;
```

## P4 collab_type and desired_timing columns (feature request)

### Evidence

The contract and the domain carry collab_type (values limited_product, popup, joint_event, sns_collab; the value list is provisional) and desired_timing. The table public.collab_requests has neither column (see docs/database.md).

### Risk

Without the columns the server cannot store these inputs; they would be dropped.

### Proposal

```sql
alter table public.collab_requests add column collab_type varchar, add column desired_timing varchar;
```

Both columns are nullable. There is no CHECK constraint yet because the collab_type values are provisional; add one once the values are final.

### Impact on the app

No effect on existing rows; the contract fields stay optional.

### How to verify afterwards (read-only queries)

```sql
select column_name, data_type from information_schema.columns where table_schema = 'public' and table_name = 'collab_requests' and column_name in ('collab_type', 'desired_timing');
```

Two rows.

### Rollback

```sql
alter table public.collab_requests drop column collab_type, drop column desired_timing;
```

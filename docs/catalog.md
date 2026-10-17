# Option catalog (canonical)

Source: database handoff v1, section 5. The code copy is `app/domain/catalog.py`.

**target_customers (9):** teens, 20s, 30s, 40s_plus, students, office_workers, couples, families, tourists

**slow_times (6):** weekday_morning, weekday_afternoon, weekday_evening, weekend_morning, weekend_afternoon, weekend_evening

**mood_tags (9):** quiet, warm, cozy, minimal, trendy, lively, premium, casual, artistic

## Rules

- The API and the database store the English canonical values above. Korean labels exist only in the UI.
- The database does **not** enforce these values (no CHECK constraints on the array columns), so the backend must validate them. `unknown_values(allowed, values)` returns the values that are not in the catalog.
- `category` has no catalog: the taxonomy is undecided. The sample and OpenAPI lists are PROVISIONAL (lowercase snake_case ASCII, at most 50 characters).
- Column limits: business_name varchar(100), category varchar(50), district varchar(50).

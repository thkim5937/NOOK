# Sample shop data (DRAFT)

`data/samples/businesses.sample.json` is a small dataset of **fictional** shops
(22 shops), validated by `data/samples/business.schema.json`
and `tests/test_sample_data.py`.

- **Purpose:** let backend work and tests (e.g. an LLM recommendation spike) start
  before the real schema and seed data exist.
- **IDs:** shop `id` is an integer >= 1 (matches the database `bigint` and the
  contract's `*_business_id` fields); ids are unique across the dataset.
- **Fictional:** every shop, name and district is made up. No real shops or brands.
- **Field names** follow the `business_profiles` columns (business_name, category, district,
  target_customers, slow_times, mood_tags, ai_intro).
- **Catalog:** target_customers, slow_times and mood_tags use only the canonical values in
  `docs/catalog.md`. `category` is PROVISIONAL (taxonomy undecided).
- **Not the production schema:** the database schema is owned by the data teammate.
  Do not copy this JSON Schema into models, migrations or API contracts.
- Contains deliberate same-category pairs per district for recommendation contrast.

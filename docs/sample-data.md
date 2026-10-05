# Sample shop data (DRAFT)

`data/samples/businesses.sample.json` is a small dataset of **fictional** shops
(2 neighborhoods, 22 shops), validated by `data/samples/business.schema.json`
and `tests/test_sample_data.py`.

- **Purpose:** let backend work and tests (e.g. an LLM recommendation spike) start
  before the real schema and seed data exist.
- **Fictional:** every shop, name and neighborhood is made up. No real shops or brands.
- **Provisional:** the option lists (industry, main_customers, quiet_hours, mood_tags)
  are NOT final. The UI/data teammates will decide the final lists and this file
  will be replaced or regenerated accordingly.
- **Not the production schema:** the database schema is owned by the data teammate.
  Do not copy this JSON Schema into models, migrations or API contracts.
- Contains deliberate same-industry pairs per neighborhood for recommendation contrast.

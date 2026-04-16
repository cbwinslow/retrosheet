# Utility Functions for Warehouse Maintenance

The **warehouse** schema contains a small set of reusable PostgreSQL functions that encapsulate common, repeatable operations required during data‑warehouse maintenance and health‑checking.

## Functions

### `features.refresh_all_materialized_views()`
Refreshes **all** materialised views in the `features` schema concurrently.  This is the preferred way to keep the advanced feature marts in sync after loading new historical data or after a schema change.

```sql
SELECT features.refresh_all_materialized_views();
```

### `core.season_range()`
Returns the minimum and maximum season currently present in `core.games`.

```sql
SELECT * FROM core.season_range();
```

### `core.count_rows(p_table regclass)`
Generic row‑count helper that works with any table name passed as a `regclass`.

```sql
SELECT core.count_rows('core.games'::regclass);
```

### `warehouse.health_check()`
Provides a quick health snapshot of the warehouse, returning the season range together with row counts for the three core tables used by the modelling pipeline.

```sql
SELECT * FROM warehouse.health_check();
```

## Permissions
All functions are granted `EXECUTE` to the `PUBLIC` role for ease of use in notebooks and CI pipelines.  Adjust the grants in `sql/200_utility_functions.sql` if a tighter security model is required.

---

These utilities are deliberately lightweight and have **no side‑effects** beyond refreshing materialised views.  They can be safely called from scripts, CI jobs, or interactive sessions.

# Issue 7 – Advanced Feature Development

**Goal**: Extend the feature set with high‑value advanced features for the win‑probability model.

## Target Features
1. **Batter‑Pitcher matchup history** – aggregate prior PA outcomes between specific batter/pitcher pairs.
2. **Park environment factors** – incorporate `features.park_prior_season_run_environment` metrics (run rates, temperature, etc.).
3. **Career‑prior rates** – add `features.batter_career_prior_pa_summary` and `features.pitcher_career_prior_pa_summary` to the model.
4. **Same‑game rolling state** – implement rolling 30‑game team form for the current season (already partially in `features.team_rolling_30_game_summary`).
5. **Live feature parity** – align live MLB data transformations with historical feature schema.

## Tasks
- [ ] Create materialized views for batter‑pitcher matchup (verify `features.batter_pitcher_prior_matchup_summary` integration).
- [ ] Add park‑environment columns to `GAME_ENRICHED_NUMERIC_FEATURES` in `scripts/train_models.py`.
- [ ] Extend `GAME_ENRICHED_NUMERIC_FEATURES` with career‑prior columns.
- [ ] Update `scripts/train_models.py` to join the new features.
- [ ] Write unit tests for the new feature extraction pipelines.
- [ ] Update documentation in `docs/FEATURE_AUDIT.md` and `docs/MLB_DATA_MODEL.md`.
- [ ] Add CI checks for the new features.

## Links & Context
- Related Issue: #06_model_training_pipeline (completed)
- Documentation: [FEATURE_AUDIT.md](../docs/FEATURE_AUDIT.md)
- SQL migrations: `sql/060_advanced_feature_marts.sql`, `sql/070_temporal_and_production_marts.sql`

---

**Status**: Not started – ready for implementation.

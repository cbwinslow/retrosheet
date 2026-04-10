# Project Objectives

## Mission

Build a reproducible baseball prediction engine that learns from Retrosheet historical play-by-play, bridges to live MLB game state, and serves calibrated probability estimates through scripts, SQL, APIs, and a web command center.

The engine should support Moneyball-style research: identify repeatable edges from historical data, quantify uncertainty, compare scenarios, and explain model outputs. Prediction-market comparison is research tooling only, not financial advice or automated trading.

## Core Principles

- PostgreSQL is the warehouse and system of record.
- Chadwick is the authoritative Retrosheet parser.
- Raw data is preserved before transformation.
- `core` tables are typed baseball facts.
- `features` tables/views are ML-ready examples and marts.
- `models.model_registry` records model artifacts, feature specs, and metrics.
- `predictions` stores targets, runs, outputs, simulations, and backtests.
- Live MLB data must be transformed into the same canonical shapes as historical Retrosheet data.
- Agents should orchestrate verified tools; they must not invent probabilities or schemas.

## Prediction Goals

### Goal 1: Game Outcome / Win Probability

Question examples:

- Who is likely to win this game?
- How did win probability change after this plate appearance?
- What is the home team win probability from a given game state?

Canonical target:

- `game_home_win`

Current assets:

- `features.game_outcome_examples`
- `features.game_outcome_advanced_examples`
- `features.game_outcome_temporal_examples`
- `scripts/train_models.py`
- `models.model_registry`

Next improvements:

- Rolling-origin backtests.
- Calibration reports.
- Live state bridge.
- WPA-style output.

### Goal 2: Binary Plate-Appearance Outcomes

Question examples:

- What is the probability this batter gets a hit?
- What is the probability of a strikeout?
- What is the probability the batter reaches base?

Canonical targets:

- `pa_batter_hit`
- `pa_batter_walk`
- `pa_batter_strikeout`
- `pa_batter_home_run`
- `pa_batter_reach_base`
- `pa_batter_extra_base_hit`

Current assets:

- `core.plate_appearances`
- `features.plate_appearance_examples`
- `features.plate_appearance_advanced_examples`
- `scripts/train_models.py`
- `scripts/predict_plate_appearance.py`
- `scripts/analyze_pa_models.py`
- `scripts/promote_best_models.py`

Next improvements:

- Better calibration.
- Same-game and rolling PA features.
- Live inference from MLB game state.
- Replace independent binary predictions with a coherent multiclass distribution when appropriate.

### Goal 3: Granular At-Bat / Plate-Appearance Outcome Distribution

Question examples:

- What is the full probability distribution over strikeout, walk, single, double, home run, ground out, fly out, etc.?
- What are derived probabilities for on-base, hit, extra-base hit, ball in play, and expected total bases?

Canonical target:

- `pa_outcome_distribution`

Current assets:

- `docs/ab_outcome.md`
- `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md`
- `sql/076_plate_appearance_outcome_model.sql`
- `features.plate_appearance_outcome_examples`
- `scripts/train_pa_outcome_distribution.py`

Next improvements:

- Full advanced-feature training run.
- Calibration and reliability reports per class.
- Prediction API returning coherent probabilities that sum to 1.
- Integration into Monte Carlo half-inning simulation.

### Goal 4: Half-Inning And Scenario Simulation

Question examples:

- What is the probability any run scores this half-inning?
- What is the probability all left-handed batters who appear in this inning get hits?
- What is the distribution of runs from this game state?

Canonical targets:

- `half_inning_any_run`
- `half_inning_lhb_any_hit`
- Future target definitions for two-plus runs, any hit, all eligible scheduled batters, team totals, and inning props.

Current assets:

- `features.half_inning_outcome_summary`
- `features.half_inning_examples` where available
- `predictions.simulation_runs`
- `predictions.recent_simulation_runs`
- `baseball-chatbot-ui/app/api/simulate/route.ts`
- `baseball-chatbot-ui/app/api/simulation-runs/route.ts`

Next improvements:

- Model-driven Monte Carlo using `pa_outcome_distribution`.
- Saved scenario detail and comparison UI.
- Explicit target definitions for ambiguous natural-language scenario requests.

### Goal 5: Live MLB Bridge

Question examples:

- Given the current live game state, what happens next?
- What is the live win probability?
- How does the model compare with market price right now?

Current assets:

- `raw_mlb.live_feed_snapshots`
- `bridge.*_xref`
- `core.live_games`
- `core.live_events`
- `scripts/transform_live_game.py` where available

Next improvements:

- Stable player/team/game ID reconciliation.
- Live feature parity with historical features.
- Polling/refresh strategy that respects free MLB endpoint usage.
- Live command-center panel.

### Goal 6: Market Comparison

Question examples:

- Is the model price meaningfully different from a public market price?
- Is the difference due to edge, stale data, fees, spread, or bad settlement mapping?

Current assets:

- `raw_markets.market_snapshots`
- `market_edges.market_prices`
- `market_edges.detected_edges`
- GitHub issue roadmap.

Next improvements:

- Market ingestion.
- Market-to-target mapping.
- Timestamp and liquidity-aware comparison.
- Research-only UI panels.

## Known Non-Goals For Now

- No automated betting/trading.
- No arbitrary browser shell.
- No LLM-generated SQL writes.
- No model binaries in git or Git LFS.
- No replacement of Retrosheet raw data with transformed-only tables.

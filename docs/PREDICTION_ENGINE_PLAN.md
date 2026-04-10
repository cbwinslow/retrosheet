# Prediction Engine Plan

## Objective

Build a flexible baseball probability engine that can train on historical Retrosheet play-by-play data, score live MLB game states, answer natural-language analytical questions, and compare model probabilities against market prices.

The system should support many prediction targets, not just game winners. Examples:

- Home team wins the game.
- Batter gets a hit in the next plate appearance.
- Pitcher records a strikeout in the next plate appearance.
- Half-inning has at least one run.
- Team scores two or more runs this inning.
- Any left-handed batter gets a hit this inning.
- All eligible left-handed batters in a precisely defined scenario get a hit.
- Game total ends over or under a line.

## Design Principles

- Preserve raw source data before transforming it.
- Keep historical and live data in the same canonical `core` shapes.
- Treat prediction targets as configurable products, not one-off scripts.
- Store every model input, model version, market price, and result needed for backtesting.
- Let AI agents plan, query, explain, and monitor; do not let them invent probabilities without calling deterministic tools or models.
- Prefer simple calibrated baselines before complex models.
- Separate research outputs from financial advice or automated trading.

## High-Level Architecture

```text
Retrosheet + Chadwick
    -> raw_retrosheet
    -> core historical game states
    -> features training tables
    -> ML models
    -> predictions

MLB live feed
    -> raw_mlb
    -> core live game states
    -> live feature rows
    -> ML models
    -> predictions

Market data
    -> raw_markets
    -> market_edges
    -> model-vs-market comparisons

Chat / agents
    -> semantic parser
    -> safe tools
    -> SQL/model/market calls
    -> explanations and alerts
```

## Warehouse Layers

### Raw Layer

Source-preserved tables. These should be append-friendly and traceable.

- `raw_retrosheet.chadwick_events`
- `raw_retrosheet.chadwick_games`
- `raw_retrosheet.chadwick_daily`
- `raw_retrosheet.chadwick_substitutions`
- `raw_retrosheet.chadwick_comments`
- `raw_mlb.live_feed_snapshots`
- `raw_markets.market_snapshots`

### Bridge Layer

Cross-source identifiers.

- `bridge.player_xref`: Retrosheet player ID, MLB player ID, Chadwick/Register ID, names, handedness metadata.
- `bridge.team_xref`: Retrosheet team ID, MLB team ID, league/division/franchise metadata.
- `bridge.park_xref`: Retrosheet park ID, MLB venue ID, park factors.
- `bridge.game_xref`: Retrosheet game ID, MLB gamePk, date, teams.
- `bridge.market_xref`: market venue, market ID, target ID, settlement rules.

### Core Layer

Typed baseball facts shared by historical and live data.

- `core.games`: one row per game.
- `core.teams`: canonical team records.
- `core.players`: canonical player records.
- `core.parks`: canonical park records.
- `core.events`: one row per Retrosheet/MLB play event.
- `core.plate_appearances`: one row per plate appearance.
- `core.substitutions`: defensive/offensive substitutions.
- `core.player_game_stats`: Chadwick daily player-game summaries.
- `core.game_states`: event-level state snapshots.
- `core.live_game_states`: current/live state snapshots transformed into the same shape as `core.game_states`.

### Feature Layer

ML-ready rows with labels for model training and inference.

- `features.game_outcome_examples`
- `features.plate_appearance_examples`
- `features.half_inning_examples`
- `features.player_prop_examples`
- `features.live_inference_queue`

### Modeling Layer

Model registry, training runs, metrics, and reproducibility.

- `models.model_registry`
- `models.training_runs`
- `models.model_artifacts`
- `models.validation_metrics`
- `models.calibration_reports`

### Prediction Layer

Predictions produced by models.

- `predictions.prediction_targets`
- `predictions.prediction_runs`
- `predictions.target_probabilities`
- `predictions.live_predictions`
- `predictions.outcomes`

### Market Layer

Market snapshots and detected edges.

- `market_edges.market_prices`
- `market_edges.detected_edges`
- `market_edges.edge_reviews`
- `market_edges.settlements`

### Chat / Agent Layer

Question-answering and workflow auditability.

- `chat.query_logs`
- `chat.tool_calls`
- `chat.saved_analyses`
- `chat.alerts`

## Prediction Target System

Every prediction should be represented as a target definition. This keeps the engine reusable.

Suggested `predictions.prediction_targets` columns:

- `target_id`
- `target_name`
- `target_family`
- `description`
- `question_template`
- `required_context`
- `training_label_sql`
- `live_resolution_rule`
- `default_model_family`
- `is_active`

Initial target families:

- `game_outcome`: full-game winner, moneyline-style predictions.
- `plate_appearance`: hit, walk, strikeout, reach base, extra-base hit.
- `half_inning`: at least one run, two or more runs, any hit, left-handed batter hit.
- `player_prop`: hit, total bases, strikeouts, RBI, runs.
- `team_prop`: team total, inning run, next score.
- `market_specific`: targets mapped to Kalshi/Polymarket-style settlement rules.

The target definition must be precise. For example, "all left-handed batters get a hit this inning" could mean several different things:

- All left-handed batters who actually appear in the half-inning record a hit.
- All currently scheduled left-handed batters due up this inning record a hit if they appear.
- At least one left-handed batter gets a hit in the half-inning.
- Every left-handed batter in the lineup records a hit before the inning ends.

The engine should reject ambiguous target definitions until a rule is selected.

## Model Families

Start simple, then grow.

### Baseline Models

- Historical lookup tables by inning, score differential, base/out state, and home/away.
- Logistic regression for game win probability.
- Empirical plate-appearance rates by batter/pitcher handedness.

### Intermediate Models

- Gradient-boosted trees for game state and plate-appearance outcomes.
- Calibrated classifiers for probability quality.
- Hierarchical smoothing for small player samples.
- Monte Carlo simulation for inning and game scenarios.

### Advanced Models

- Sequence models over play-by-play context.
- Bayesian player/pitcher latent talent estimates.
- Ensemble models combining historical state, player form, lineup, bullpen, and market priors.
- Counterfactual simulation tools for "what if" questions.

## AI Agent Responsibilities

AI agents should be orchestrators over trusted tools, not the probability source of truth.

### Query Agent

- Converts user questions into structured prediction or analytics requests.
- Resolves ambiguity by asking targeted clarification questions.
- Calls approved SQL/model tools.
- Produces explanations with references to model outputs and data slices.

### Data Agent

- Monitors Retrosheet, Chadwick, MLB, and market ingestion.
- Checks row counts, schema drift, missing IDs, and freshness.
- Opens issues or alerts when ingestion quality changes.

### Modeling Agent

- Runs training jobs.
- Compares metrics across seasons.
- Checks calibration, leakage, and feature importance.
- Registers accepted models.

### Market Agent

- Normalizes market prices and settlement rules.
- Compares model probability to implied probability.
- Accounts for fees, spread, liquidity, and timing.
- Flags research opportunities, not financial instructions.

### Explanation Agent

- Turns structured outputs into understandable summaries.
- Explains why the model moved.
- Shows historical analogs and uncertainty.

## Inference Flow

### Historical Backtest

```text
core.game_states
    -> features.*_examples
    -> model inference
    -> predictions.target_probabilities
    -> predictions.outcomes
    -> metrics and calibration
```

### Live Prediction

```text
MLB live feed snapshot
    -> raw_mlb.live_feed_snapshots
    -> core.live_game_states
    -> features.live_inference_queue
    -> model inference
    -> predictions.live_predictions
    -> optional market comparison
```

### Chat Question

```text
User question
    -> Query Agent parses intent
    -> target definition selected or created
    -> SQL/model tools retrieve evidence
    -> probability engine returns structured output
    -> Explanation Agent responds
```

## Market Edge Logic

The system should distinguish arbitrage from model edge.

- Arbitrage: a mathematically locked profit after fees, spread, liquidity, and settlement rules.
- Model edge: model probability differs from market implied probability.

Suggested edge calculation:

```text
edge = model_probability - market_implied_probability
expected_value = model_probability * payout_if_win - (1 - model_probability) * stake_if_loss - fees
```

Store all assumptions:

- Market venue.
- Market ID.
- Contract/side.
- Best bid/ask.
- Implied probability.
- Liquidity available.
- Fee model.
- Model version.
- Live game state timestamp.
- Eventual settlement.

## Milestones

### Milestone 1: Normalized Core

- Create `core.games`.
- Create `core.events`.
- Create `core.players`, `core.teams`, and `core.parks` starter tables.
- Validate counts against raw Chadwick tables.
- Add schema documentation.

### Milestone 2: Game-State Training Table

- Create `core.game_states`.
- Add base/out/inning/score state.
- Add final winner target.
- Create `features.game_outcome_examples`.
- Train a baseline win-probability model.

### Milestone 3: Plate-Appearance Models

- Create `core.plate_appearances`.
- Label hit, walk, strikeout, reach-base, extra-base-hit outcomes.
- Add batter/pitcher handedness once player metadata is bridged.
- Train baseline plate-appearance models.

### Milestone 4: Scenario Models

- Create `features.half_inning_examples`.
- Support scenario targets like inning runs, any hit, and left-handed batter hit.
- Add Monte Carlo simulation from plate-appearance probabilities.

### Milestone 5: Live MLB Bridge

- Ingest MLB schedule and live feed snapshots.
- Create `bridge.game_xref`, `bridge.player_xref`, and `bridge.team_xref`.
- Transform live feed plays into `core.live_game_states`.
- Run live inference using the same feature definitions as historical training.

### Milestone 6: Chat Interface

- Build safe analytics tools for SQL queries and model calls.
- Implement natural-language parsing into approved target definitions.
- Log all questions, tool calls, and outputs.
- Add explanations with uncertainty and historical analogs.

### Milestone 7: Market Intelligence

- Ingest market snapshots where legal and technically available.
- Map markets to prediction targets and settlement rules.
- Compare model probabilities to market prices.
- Backtest detected edges.
- Add alerting for high-confidence research opportunities.

## Immediate Next Steps

1. Create `sql/010_core_games_events.sql`.
2. Build typed `core.games` from `raw_retrosheet.chadwick_games`.
3. Build typed `core.events` from `raw_retrosheet.chadwick_events`.
4. Add validation queries for row counts, duplicate keys, dates, teams, scores, and missing IDs.
5. Document the initial `core` schema.
6. Create the first `predictions.prediction_targets` seed records for game outcome and plate-appearance targets.


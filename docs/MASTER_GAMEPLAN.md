


Please complete the payment process to use Enterprise features
github https://github.com/cbwinslow/retrosheet.git check this repo and we need to figure out the best way to implement and incroporate mlb_pbp data and all of the other data sources and create a streamlined pipeline using these data sources to supplement our retrosheet data to create an analysis pipeline that can instantley calculate stats such as plate appearence probs (getting a hit, on base, strikeout, and more detailed figures) using the data. i want to have probs for different layers simealtaneously such as pbp estiamtes or pa estiamtes and game and inning odds so ican place bets or orders using polymarket or somethig like that. please formulate a detialed plan that we can use to organize the pipeline. check what we have in this repo and help us move forward. give advice on everyting that you see especially the mlb pbp pipeline as it is right now. feel free to advise a redesign if we need to. advise on anything else and what we havent gotten to yet. read the docs and see what i have done so far and try and guide to to create a detailed, streamlined, effecient data and ml pipeline to calculate/predict odds on many layers and levels https://github.com/cbwinslow/retrosheet.git
Completed 20 steps
MLB Analytics Pipeline: Comprehensive Architecture Plan
Based on a thorough review of your cbwinslow/retrosheet repository, here is a detailed breakdown of what you have, what needs improvement, and the full pipeline redesign plan.

What You Have (Current State)
The repo has a solid foundation with clear ambition, but it's fragmented. Key components observed:

retrosheet/ package — Core Python library with archive.py (34KB, data fetching), event.py (78KB, event parsing — the heaviest file), game.py (game-level parsing), parser.py, and helpers.py

schema.prisma — A Prisma schema (~13KB) suggesting a database layer is planned or partially implemented

scripts/ — Utility scripts directory

sql/ — Raw SQL files, likely table definitions

docs/ — Documentation exists

baseball-chatbot-ui/ — A frontend chatbot UI has been started

AGENTS.md, .claude/, .cursor/, .windsurf/ — Heavy AI assistant context files across many tools (Claude, Cursor, Cline, Roo, etc.), showing active development with multiple agents

LLM_INTEGRATION_EVALUATION_PLAN.md and LLM_INTEGRATION_RECOMMENDATION_PLAN.md — Planning docs for LLM integration exist

research_report.md (29KB) — Substantial research already done

requirements.txt — Minimal dependency list (needs significant expansion)

main.py — Entry point, currently only 582 bytes — essentially a stub

Critical observation: The event.py at 78KB is doing too much. It's a monolithic event parser that handles everything from raw Retrosheet event codes to play-by-play interpretation. This will become a bottleneck and maintenance nightmare as you add MLB PBP data.

Architecture Problems to Fix Now
1. The MLB PBP Pipeline Doesn't Exist Yet
There is no mlb_pbp/ module, no live data ingestion, and no feature engineering layer. The current code only handles historical Retrosheet .EVN/.EVA files.

2. No Feature Store or Unified Data Model
Retrosheet, MLB Stats API, and Statcast all use different schemas. Without a canonical unified schema, you'll be doing ad-hoc joins everywhere and probability calculations will be unreliable.

3. event.py Is a God Object
At 78KB it handles parsing, event encoding, hit location, base running logic, and more in one file. It needs to be split.

4. No ML Layer Exists
There are no model files, no training pipelines, no probability calculators. The LLM integration docs exist but there's no statistical modeling for the bet-relevant probabilities you need.

5. No Streaming / Real-Time Component
For Polymarket/live betting, you need sub-inning latency. Nothing currently supports that.

Redesigned Pipeline Architecture
text
┌────────────────────────────────────────────────────────────────┐
│                     DATA INGESTION LAYER                       │
├────────────┬──────────────┬─────────────┬──────────────────────┤
│ Retrosheet │ MLB Stats API│  Statcast   │  Vegas / Market Odds │
│ (historical│ (live PBP)  │ (exit velo, │  (DraftKings, FanDuel│
│  .EVN/.EVA)│             │  spin rate) │   Polymarket API)    │
└─────┬──────┴──────┬───────┴──────┬──────┴──────────┬───────────┘
      │             │              │                 │
      └─────────────┴──────────────┴─────────────────┘
                            │
                    [ETL / Normalizer]
                    Unified Event Schema
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                      STORAGE LAYER                             │
│  PostgreSQL (historical + aggregated stats)                    │
│  Redis (live game state, rolling window features)              │
│  Parquet/DuckDB (batch feature store for training)             │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                   FEATURE ENGINEERING                          │
│  - Rolling PA stats (last 7/14/30/season/career)               │
│  - Batter vs. Pitcher matchup history                          │
│  - Platoon splits (L/R)                                        │
│  - Park factors (ballpark-adjusted)                            │
│  - Inning/game state context (score, outs, base state)         │
│  - Pitcher fatigue (pitch count, days rest)                    │
│  - Statcast inputs (launch angle, exit velo, spin rate)        │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                  PROBABILITY MODEL LAYER                       │
│  [PA-Level Model]     [Inning Model]      [Game Model]         │
│  Hit prob             Run expectancy      Win probability       │
│  OBP prob             Inning score dist   Total runs O/U       │
│  K prob               No-score inning     First 5 innings       │
│  BB prob              [Sequence Model]    Team run line        │
│  HR prob              Next pitch type     Moneyline            │
│  XBH prob             Count transitions                        │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│               ODDS CALCULATOR / MARKET INTERFACE               │
│  - Convert model probs → implied odds                          │
│  - Compare vs. market (Polymarket, DraftKings)                 │
│  - Edge detection + Kelly Criterion sizing                     │
│  - Alert/order generation                                      │
└────────────────────────────────────────────────────────────────┘
Module Restructure Plan
Replace the current flat package with:

text
retrosheet/
├── ingestion/
│   ├── retrosheet_loader.py     # Existing archive.py logic, cleaned up
│   ├── mlb_pbp_client.py        # MLB Stats API live + historical PBP ← BUILD THIS FIRST
│   ├── statcast_client.py       # pybaseball / Baseball Savant scraper
│   └── odds_client.py           # Polymarket / sportsbook API
│
├── core/
│   ├── event_parser.py          # Refactored from event.py (parse only)
│   ├── base_runner.py           # Extracted base-running logic
│   ├── game_state.py            # Game state machine
│   └── schemas.py               # Unified Pydantic event schema
│
├── features/
│   ├── pa_features.py           # Per-plate-appearance feature vectors
│   ├── pitcher_features.py      # Pitcher state features
│   ├── matchup_features.py      # Batter vs pitcher history
│   ├── game_context.py          # Score, inning, base state
│   └── park_factors.py          # Ballpark adjustment factors
│
├── models/
│   ├── pa_model.py              # PA outcome classifier (XGBoost/LightGBM)
│   ├── inning_model.py          # Run expectancy by base/out state
│   ├── game_model.py            # Win probability model
│   └── calibration.py           # Platt scaling / isotonic regression
│
├── odds/
│   ├── converter.py             # Prob → American/decimal odds
│   ├── edge_calculator.py       # Model vs. market edge detection
│   └── kelly.py                 # Kelly Criterion position sizing
│
└── pipeline/
    ├── historical_pipeline.py   # Batch backfill pipeline
    ├── live_pipeline.py         # Real-time game-day pipeline
    └── orchestrator.py          # Airflow/Prefect DAG definitions
MLB PBP Pipeline: Build This First
The mlb_pbp_client.py is your most critical missing piece. Here's the recommended design:

python
# ingestion/mlb_pbp_client.py — recommended structure

class MLBPBPClient:
    BASE_URL = "https://statsapi.mlb.com/api/v1"

    def get_live_game(self, game_pk: int) -> dict:
        """Polls /game/{game_pk}/feed/live — full PBP including pitch-by-pitch"""

    def get_schedule(self, date: str) -> list[int]:
        """Returns game PKs for a given date"""

    def get_historical_pbp(self, game_pk: int) -> list[PlateAppearance]:
        """Fetches and normalizes to unified schema"""

    def stream_live(self, game_pk: int, callback):
        """Polls every 5-10s during live game, fires callback on new events"""
Key MLB Stats API endpoints to use:

GET /api/v1/game/{game_pk}/feed/live — full live PBP with pitch-by-pitch data

GET /api/v1/schedule?sportId=1&date=YYYY-MM-DD — daily game list

GET /api/v1/people/{player_id}/stats?stats=season&group=hitting — player stats

GET /api/v1/game/{game_pk}/boxscore — box score

This API is free and requires no authentication — major advantage over paid services.

Probability Models: Layer Breakdown
Layer 1 — Plate Appearance (PA) Model
The most granular layer. For each PA, predict:

P(single), P(double), P(triple), P(HR), P(BB), P(HBP), P(K), P(out in play)

Model: Multinomial classifier — LightGBM or XGBoost works best here given the tabular feature structure. Train on 10+ years of Retrosheet event data (you have the parser for this already).

Key features: Batter wRC+, pitcher ERA/FIP/xFIP, count (balls-strikes), platoon split, pitch type (from Statcast), park factor, fatigue index, inning/score context.

Layer 2 — Inning Model
Given the lineup order, current PA model probabilities, and game state → simulate run distributions per inning using a Markov chain on base/out states. The 24 base-out states (8 base configurations × 3 out counts) are already implicitly in your Retrosheet event data.

Output: P(0 runs this inning), P(1+), P(2+) — maps directly to Polymarket inning markets.

Layer 3 — Game Model
Aggregate inning-level run distributions → full game run total, win probability, first-5 line. Update live as PBP comes in. For Polymarket this is your moneyline and O/U equivalent.

Data Sources to Integrate (Priority Order)
Priority	Source	What It Adds	Access
🔴 1	MLB Stats API	Live PBP, pitch-by-pitch	Free, no auth
🔴 2	Retrosheet (existing)	1950–2024 historical events	Free download
🟡 3	Baseball Savant / Statcast	Exit velocity, spin rate, launch angle	Free via pybaseball
🟡 4	FanGraphs	Advanced splits, park factors	pybaseball wrapper
🟢 5	Polymarket API	Live market prices for edge calc	Free REST API
🟢 6	The Odds API	Vegas lines for calibration	Freemium
Immediate Next Steps (Ordered)
Refactor event.py — Split into event_parser.py, base_runner.py, and game_state.py. This is blocking everything downstream.

Build mlb_pbp_client.py — Wire up the MLB Stats API free endpoints, normalize to a Pydantic schema that matches your Retrosheet event structure.

Create unified schema — A single UnifiedPlateAppearance Pydantic model that both Retrosheet and MLB API data can populate. This is the linchpin of the whole pipeline.

Build the feature store — A DuckDB-backed feature store is ideal for this use case (columnar, fast, embedded, no server needed). Compute rolling windows offline; serve live features from Redis.

Train the PA model — Start with logistic regression as a baseline, then LightGBM. Use 2015–2023 Retrosheet data for training, 2024 for validation.

Build the Markov inning simulator — The 24 base-out state transition matrix is derivable directly from your existing parsed Retrosheet data.

Wire the odds layer — Pull Polymarket prices, compare to model output, flag edges > 5%.

What the schema.prisma Tells Us
The Prisma schema being present but having no corresponding ORM usage in the Python code is a red flag — it suggests the database design was done in one session but never actually connected. Recommendation: Either fully commit to PostgreSQL + SQLAlchemy on the Python side, or replace Prisma entirely with a pure Python stack (SQLAlchemy + Alembic for migrations). Don't maintain a Prisma schema that no Python code reads from.

Quick Win: The 24 Base-Out State Table
You can immediately add value by computing the empirical run expectancy matrix directly from your existing parsed Retrosheet data. This single table — 24 rows × 1 column — is the foundation of all in-game probability work and takes only a few hours to build from your existing event.py output.

The repo is in good shape structurally — the groundwork is there — but it needs consolidation, the MLB PBP client as a new core component, and a real modeling layer before it can generate betting-relevant probabilities. The biggest unlock is getting event.py refactored and the unified schema defined, because every downstream component depends on those two things.

ok any more suggestions? be detailed. help me generate plans for this





Sorry, something went wrong

retry
Completed 3 steps
You already have much more of the MLB PBP pipeline than my last answer gave you credit for. The repo is not at a “design from scratch” stage; it already has a canonical warehouse, live MLB ingestion, bridge tables, feature marts, a trained PA outcome model, calibration artifacts, a live feature-parity view, and a Next.js command center scaffold, so the right move is to consolidate around that architecture rather than replace it.

What exists now
Your repo’s own operating guide says the project mission is to build a PostgreSQL warehouse from Retrosheet, use Chadwick as the authoritative parser, add MLB Stats API/GUMBO live ingestion, build ML-ready historical and live features, and later compare model probabilities with Kalshi or Polymarket, explicitly treating market work as research tooling rather than financial advice. The canonical layers are already defined as raw_retrosheet, raw_mlb, bridge, core, features, models, predictions, and analysis, and the docs repeatedly warn against inventing parallel schemas such as mlb_features, mlb_models, mlb_enhanced, or EdgeForge prototypes.

You also already have an implemented live-data workflow: scripts/fetch_mlb_schedule.py, scripts/ingest_live_games.py, scripts/transform_live_game.py, scripts/populate_bridge_tables.py, sql/090_mlb_live_data.sql, sql/100_bridge_tables.sql, sql/110_live_core_tables.sql, sql/122_live_pa_feature_parity.sql, and sql/130_analysis_views.sql. That means the MLB PBP pipeline is not “missing”; it exists, but it is still incomplete in parity, reconciliation, and productionization.

Current best model
The project snapshot says the current priority order is historical PA outcome quality first, then calibration and reliability, then live feature parity and live scoring, then simulation and market-comparison layers. The current historical warehouse contains 4,779,662 plate appearance outcome rows across 2000–2025, and the transformed MLB live layer contains 67,913 live games and 5,172,275 live events, with only seven remaining MLB API failures due to upstream exhibition-game HTTP 500 holes rather than local bugs.

Your current best PA model is already identified: a grouped-taxonomy hist_gradient_boosting_multiclass model using the advanced_count feature set, trained through 2022 and validated on 2023–2025. The reported validation metrics are log loss 1.5089, multiclass Brier 0.7146, accuracy 0.4131, and top-3 accuracy 0.8202, and the docs say isotonic calibration improved held-out 2025 performance while dramatically reducing strikeout calibration error.

Main gap now
The main gap is not data ingestion from zero; it is getting the live pipeline to full feature parity and then layering simulation, logging, and market comparison on top of that cleanly. Your own snapshot says player, count-state, and coarse context priors are wired for live scoring, but game crosswalk reconciliation, season-aware team bridge semantics, broad replay of older live rows through the repaired bridge, and durable live prediction logging are still unfinished.

That is important because your desired outputs, such as instant PA hit probability, on-base probability, strikeout probability, inning odds, and game odds, all depend on a single reliable canonical state representation across historical and live sources. The docs are very clear that live scoring should happen only after MLB snapshots are transformed into canonical core.live_* tables and a live feature row exists that matches the historical model contract, not by scoring raw MLB JSON directly.

Advice on the MLB PBP pipeline
The current MLB PBP design is directionally correct and should be kept. The repo’s live procedure is: fetch schedule, fetch/store source-preserved live feed JSON in raw_mlb.live_feed_snapshots, transform the latest stored snapshot through bridge mappings into core.live_games and core.live_events, and then expose historical plus live through analysis.* views. That is the right separation of concerns because it preserves provenance, supports replay, and prevents the common mistake of mixing raw MLB API payloads directly into model-serving logic.

The biggest weakness is bridge quality and replay completeness, not the existence of the pipeline. The snapshot says bridge.team_xref is still seasonless, so franchise-move cases like WSH/MON -> WAS, MIA/FLA -> MIA, and ATH/OAK -> OAK are acceptable for current live scoring but not for full historical MLB replay fidelity, and older live rows may still carry MLB### fallback IDs until they are replayed through the repaired transform path. So the MLB PBP advice is: do not redesign the ingestion pattern, redesign the reconciliation layer and make replay/validation first-class.

Best target architecture
You should organize the whole system around one canonical probability engine with four serving layers: PA, half-inning, game, and market comparison. The repo already supports the first layer directly through pa_outcome_distribution, historical inference, and live inference scripts, so the roadmap should extend that same contract upward rather than start separate models for every question independently.

A practical stack would look like this:

Layer	Canonical input	Engine	Output
PA	features.plate_appearance_* and features.live_plate_appearance_advanced_count_examples	Existing grouped multiclass PA model + calibration	P(single), P(double), P(triple), P(HR), P(BB), P(K), derived hit/OBP/TB props
Half-inning	Current game state + PA scorer	Monte Carlo or Markov state transition simulator using scored PA outcomes	P(0 runs), P(1+), P(2+), team-to-score, inning total bands
Game	Inning simulator rolled forward from present state	Live state simulation + lineup/pitcher context	win probability, totals, first-5/full-game distributions
Market	Predictions + timestamped external prices	Edge calculator and reporting layer	model-implied odds, edge, tracking, no-autotrading by default
That structure fits your documented goals and avoids duplicating logic.

Recommended redesigns
I would not blow up the warehouse design, but I would redesign three things.

First, make analysis read-only and thin, and move all model-serving dependencies into materialized feature-parity marts with explicit freshness guarantees. The docs already frame analysis.* as the combined query layer and features.* as the model-ready layer, so letting model code depend on ad hoc analysis joins will make latency and reproducibility worse.

Second, introduce a formal “state snapshot” object for inference runs. Right now the docs emphasize prediction logging and prediction runs, but for live betting-style workflows you will want each prediction to persist game ID, inning, outs, bases, score differential, batter, pitcher, handedness, lineup slot, model version, calibration artifact, feature checksum, and snapshot timestamp in one reusable row. That gives you clean replay, postmortem analysis, and edge-vs-market auditing later.

Third, separate “research edge comparison” from “execution.” The repo already treats market work as research tooling, and that is wise because once you mix prediction generation with auto-order logic too early, you create safety, validation, and compliance problems before the probability engine is stable. Build a market observation layer first, not an auto-betting layer.

Detailed pipeline plan
Phase 1: lock the canonical path
Use the existing documented rebuild and live workflows as the only supported path. Your own runbook says contributors should use scripts/rebuild_warehouse.sh for the canonical rebuild order and should update it whenever a required SQL migration is added. That means your immediate organizational rule should be: no new side pipelines, no new schemas unless they are added to the canonical rebuild and inventory docs.

Concrete tasks:

Declare raw_retrosheet -> core -> features -> models -> predictions as the only historical training path.

Declare raw_mlb -> bridge -> core.live_* -> features.live_* -> predictions as the only live inference path.

Freeze prototype schemas until triaged into canonical layers, as AGENTS.md already instructs.

Phase 2: finish live parity
This is the highest-leverage engineering work. The docs say live parity already exists in sql/122_live_pa_feature_parity.sql, but park priors and team rolling features only appear for rows transformed through the repaired bridge path, and broad replay is still outstanding.

Concrete tasks:

Replay a bounded regular-season slice with scripts/replay_live_bridge_backfill.py and measure feature fill rates before and after replay.

Build a validation dashboard over null rates in live parity columns: batter priors, pitcher priors, count-state priors, park priors, team rolling form, handedness fields.

Implement season-aware team_xref semantics and then replay affected seasons.

Add game_xref as a formal blocker item before broader game-level or inning-level live backtests.

Success condition: a live PA row should match the historical advanced_count contract with documented nullable exceptions only for genuinely unavailable fields.

Phase 3: standardize PA serving
You already have the right pieces: scripts/predict_pa_outcome_distribution.py, optional isotonic calibration artifacts, and scripts/predict_live_pa_outcome_distribution.py. The next move is to turn that into one stable internal service contract, regardless of whether the caller is the CLI, Next.js API, simulator, or future market monitor.

The PA serving payload should return:

Full multiclass outcome distribution

Derived hit probability

Derived on-base probability, with at least “traditional OBP” and “reach base any” variants

Strikeout probability

Ball-in-play probability

Expected total bases

Metadata: model version, calibration artifact, feature timestamp, source type, missing-feature flags

This is already aligned with your docs, which note that the scorer returns class probabilities plus derived aggregates such as hit, extra-base hit, traditional on-base, reach-base-any, ball-in-play, and expected total bases.

Phase 4: build the inning engine
Your procedures already say the future model-driven simulation baseline is to score each simulated PA with pa_outcome_distribution, sample a terminal PA outcome, apply the correct base/out/run transition, stop at three outs, repeat, and save the run distribution and assumptions. That is exactly the right next layer for inning probabilities and a better near-term choice than trying to train a separate inning model first.

Concrete tasks:

Build a trusted baseball state transition engine with exhaustive tests for base occupancy, outs, runs, and lineup progression.

Start with terminal PA outcomes only, not full pitch sequence simulation.

Calibrate inning outputs against historical half-inning distributions from features.half_inning_outcome_summary or related training views.

Persist every simulation run under predictions.simulation_runs, which the docs already call out.

This layer gives you:

Team to score in inning

Over/under 0.5 inning runs

Distribution of runs this inning

Probability of at least one baserunner, one hit, one strikeout in the inning, if you aggregate PA outputs across the expected sequence

Phase 5: build game-state odds
Once inning simulation is stable, the game layer becomes a repeated forward simulator. The project objective explicitly includes producing win probability from game state as the first ML target direction, and the broader engine plan is meant to support reusable probability outputs across scenarios.

Concrete tasks:

Simulate forward from current inning through game end using lineup order, bullpen assumptions, and current score state

Produce team win probability, run total distribution, first-5/full-game derived distributions, and lead-change probabilities

Log prediction snapshots to predictions with model version and live source snapshot ID, because the docs already expect durable live prediction logging but say it is not done yet.

I would not train a separate pure game classifier until you have the simulation outputs in place, because the simulator can reuse your strongest PA engine immediately and produces more market-relevant distributions.

What you have not gotten to yet
A few important pieces are either missing or underdeveloped in the docs.

Prediction logging
The current snapshot explicitly says durable live prediction logging is still not done. Without that, you cannot honestly evaluate latency, calibration drift, stale features, or model-vs-market edge over time.

Market normalization
The interface doc says /api/live-odds is still a placeholder until true live odds and markets are integrated, and market comparison panels are a later milestone after odds/market ingestion tables are normalized and timestamped. So market ingestion itself is still basically future work.

Calibration at higher layers
PA calibration is already first-class, but there is no evidence in the docs that inning or game simulation outputs are yet calibrated against observed frequencies. You will want reliability work at those layers too, especially because compounding small PA miscalibrations can distort inning and game prices.

Latency and freshness SLAs
The docs discuss inference optimization candidates and a fast prediction service, but they do not yet define a production-grade freshness contract such as “live snapshot polling every X seconds” or “all features refreshed within Y seconds of a new play.” You need that before using outputs for time-sensitive decisions.

Concrete priorities for the next 30 days
Here is the order I would use.

Priority	Task	Why
1	Default the calibrated grouped advanced_count PA scorer into the served path	It is already your best validated model and has documented calibration artifacts.
2	Replay a bounded live slice through repaired bridge mappings and measure parity fill rates	This directly improves live scoring quality with existing infrastructure.
3	Add durable live prediction logging	Required for real evaluation, monitoring, and later market comparison.
4	Build the terminal-PA half-inning simulator	Fastest route to inning and micro-market probabilities using existing assets.
5	Add a market snapshot table plus read-only comparison views	/api/live-odds is still placeholder, so this unlocks the market layer cleanly.
6	Build a reliability dashboard in the command center	Lets you inspect model calibration, live null rates, and drift from one place.
Opinionated recommendations
Do not redesign away from PostgreSQL-centered warehouse logic; your docs, SQL migrations, feature marts, and UI all already assume that architecture.

Do not create a separate “MLB PBP pipeline” outside the documented live path; strengthen raw_mlb to core.live_* to features.live_* instead.

Do not let the UI become the place where modeling logic lives; keep Next.js as a command center and API boundary, which is already the documented pattern.

Do not jump to automated market execution yet; first build market ingestion, timestamped comparison, prediction logging, replay, and backtests.

Do build a rigorously tested baseball state transition engine next, because that is the bridge from your already-good PA model to inning and game odds.

Bottom line
The repo is farther along than it first looked: the core warehouse, live MLB raw ingestion, bridge tables, live transforms, PA feature marts, grouped PA model, calibration artifacts, and UI command center are already in place. The right move now is not a ground-up redesign, but a disciplined push to finish live feature parity, make the calibrated PA scorer the default served engine, add durable live prediction logging, and then build inning/game simulators on top of that canonical PA distribution service.

If you want, I can next turn this into a very concrete implementation roadmap with exact files to edit, migration order, and a proposed issue breakdown matching your existing repo structure.

please do all three and whatever else you want

Absolutely — here are all three, plus a few extras that I think will help you turn this into an executable work package instead of just a strategy memo. Everything below is aligned to your repo’s canonical workflows, current best model, live bridge status, and documented “do next” priorities.

What I’m giving you
I’m including:

a proposed SQL design for durable live PA prediction logging, aligned with your existing predictions layer and procedures,

a concrete JSON request/response contract for /api/predict, aligned with the current pa_outcome_distribution scorer and calibration workflow,

a GitHub issue pack you can paste into your repo, following your own issue template guidance,

extra recommendations on rollout order, testing, and a near-term command-center surface so you can operationalize this cleanly.

SQL design
The procedures explicitly say live MLB work should store predictions with model ID, timestamp, and input features, and the current snapshot says durable live prediction logging is still not done. So the cleanest move is to add a new predictions migration with one durable row per scored live PA plus a lightweight serving-log table for API observability.

Proposed new migration
I would add a new additive migration such as sql/083_live_prediction_logging.sql, not rewrite older core migrations, because your rebuild path is migration-ordered and your docs say new required SQL should be appended and then added to scripts/rebuild_warehouse.sh.

Proposed tables
sql
-- sql/083_live_prediction_logging.sql

CREATE SCHEMA IF NOT EXISTS predictions;

CREATE TABLE IF NOT EXISTS predictions.live_pa_predictions (
    live_pa_prediction_id BIGSERIAL PRIMARY KEY,
    prediction_run_id BIGINT NOT NULL REFERENCES predictions.prediction_runs(prediction_run_id),
    game_id TEXT NOT NULL,
    plate_appearance_id INTEGER NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'mlb_live',
    source_snapshot_id BIGINT,
    raw_game_pk BIGINT,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    target_id TEXT NOT NULL DEFAULT 'pa_outcome_distribution',
    feature_set TEXT NOT NULL,
    target_taxonomy TEXT NOT NULL,
    calibration_applied BOOLEAN NOT NULL DEFAULT FALSE,
    calibration_report_name TEXT,
    calibration_artifact_uri TEXT,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    batter_id TEXT,
    pitcher_id TEXT,
    batting_team_id TEXT,
    fielding_team_id TEXT,

    inning INTEGER,
    inning_half TEXT,
    outs INTEGER,
    balls INTEGER,
    strikes INTEGER,
    base_state_code TEXT,
    score_diff INTEGER,

    feature_view_name TEXT NOT NULL DEFAULT 'features.live_plate_appearance_advanced_count_examples',
    feature_row_json JSONB,
    class_probabilities_json JSONB NOT NULL,
    derived_probabilities_json JSONB NOT NULL,
    model_metadata_json JSONB,
    missing_features_json JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (game_id, plate_appearance_id, model_name, model_version, calibration_applied, prediction_timestamp)
);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_game_pa
    ON predictions.live_pa_predictions (game_id, plate_appearance_id);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_model
    ON predictions.live_pa_predictions (model_name, model_version);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_timestamp
    ON predictions.live_pa_predictions (prediction_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_source_snapshot
    ON predictions.live_pa_predictions (source_snapshot_id);

CREATE TABLE IF NOT EXISTS predictions.api_prediction_requests (
    api_prediction_request_id BIGSERIAL PRIMARY KEY,
    request_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    route_name TEXT NOT NULL DEFAULT '/api/predict',
    source_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    request_json JSONB NOT NULL,
    response_summary_json JSONB,
    model_name TEXT,
    model_version TEXT,
    calibration_applied BOOLEAN,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_prediction_requests_timestamp
    ON predictions.api_prediction_requests (request_timestamp DESC);
Why this shape
This fits your documented architecture because predictions is the durable output layer, prediction_runs already exists conceptually for evaluation/report workflows, and live scoring is supposed to happen after the canonical live feature view is built rather than against raw MLB JSON. Keeping both class_probabilities_json and derived_probabilities_json lets you preserve the full multiclass answer while also serving the bet-relevant aggregates like hit, on-base, strikeout, and expected total bases without recomputing them differently in every consumer.

Suggested companion view
sql
CREATE OR REPLACE VIEW analysis.live_pa_prediction_latest AS
SELECT DISTINCT ON (p.game_id, p.plate_appearance_id, p.model_name, p.model_version, p.calibration_applied)
    p.*
FROM predictions.live_pa_predictions p
ORDER BY
    p.game_id,
    p.plate_appearance_id,
    p.model_name,
    p.model_version,
    p.calibration_applied,
    p.prediction_timestamp DESC;
That matches the repo’s pattern of using analysis.* as the combined read layer and keeps the command center simple.

API contract
Your docs already say API consumers can call /api/predict with target_id: "pa_outcome_distribution" and optionally pass calibration controls analogous to the CLI. The best next step is to make the request/response contract strict enough that historical PAs, stored live PAs, and future simulator calls can all use the same shape.

Proposed request schema
json
{
  "target_id": "pa_outcome_distribution",
  "source_type": "mlb_live",
  "game_id": "MLB117201910300",
  "plate_appearance_id": 79,
  "model_name": "hist_gradient_boosting_multiclass",
  "model_version": "20260412T045759Z",
  "feature_set": "advanced_count",
  "target_taxonomy": "grouped",
  "apply_calibration": true,
  "calibration_report_name": "20260412T045759Z_isotonic_artifact",
  "include_feature_snapshot": true,
  "persist_prediction": true,
  "request_context": {
    "caller": "command_center",
    "session_id": "optional-session-id",
    "user_note": "optional"
  }
}
Supported request variants
You should support at least these source modes:

historical_pa: use features.plate_appearance_advanced_examples or features.plate_appearance_advanced_count_examples depending on feature set.

mlb_live: use features.live_plate_appearance_advanced_count_examples, which your live parity SQL already provides.

simulation_state later: a future mode where the same response contract is used by the half-inning or game simulator, but the input row is composed from simulated state rather than stored event rows.

Proposed response schema
json
{
  "status": "ok",
  "target_id": "pa_outcome_distribution",
  "source_type": "mlb_live",
  "keys": {
    "game_id": "MLB117201910300",
    "plate_appearance_id": 79
  },
  "model": {
    "model_name": "hist_gradient_boosting_multiclass",
    "model_version": "20260412T045759Z",
    "feature_set": "advanced_count",
    "target_taxonomy": "grouped",
    "calibration_applied": true,
    "calibration_report_name": "20260412T045759Z_isotonic_artifact"
  },
  "probabilities": {
    "classes": {
      "single": 0.1421,
      "double": 0.0512,
      "triple": 0.0041,
      "home_run": 0.0365,
      "walk": 0.0914,
      "strikeout": 0.2388,
      "hit_by_pitch": 0.0082,
      "reached_on_error": 0.0120,
      "ball_in_play_out": 0.4157
    },
    "derived": {
      "hit_probability": 0.2339,
      "on_base_traditional_probability": 0.3259,
      "reach_base_any_probability": 0.3379,
      "strikeout_probability": 0.2388,
      "ball_in_play_probability": 0.4277,
      "extra_base_hit_probability": 0.0918,
      "expected_total_bases": 0.4872
    }
  },
  "state_snapshot": {
    "inning": 7,
    "inning_half": "top",
    "outs": 1,
    "balls": 1,
    "strikes": 2,
    "base_state_code": "101",
    "score_diff": -1,
    "batter_id": "some_batter",
    "pitcher_id": "some_pitcher",
    "batting_team_id": "WAS",
    "fielding_team_id": "HOU"
  },
  "feature_metadata": {
    "feature_view_name": "features.live_plate_appearance_advanced_count_examples",
    "missing_features": [
      "park_prior_total_runs_per_game"
    ]
  },
  "logging": {
    "prediction_run_id": 12345,
    "live_pa_prediction_id": 67890
  },
  "generated_at": "2026-04-16T21:10:00Z"
}
Error response
json
{
  "status": "error",
  "target_id": "pa_outcome_distribution",
  "source_type": "mlb_live",
  "error_code": "FEATURE_ROW_NOT_FOUND",
  "message": "No live feature row found for game_id=... plate_appearance_id=...",
  "details": {
    "game_id": "MLB117201910300",
    "plate_appearance_id": 79
  }
}
Why this contract works
It mirrors your current scorer semantics, preserves the multiclass core output, includes the derived betting-relevant aggregates you explicitly want, and carries enough model metadata to make logged predictions reproducible. It also gives the future simulator and UI a stable interface so you do not have to rewrite consumers when you add inning/game layers later.

GitHub issue pack
Your repo’s procedures say every issue should include goal, current state, scope, non-goals, acceptance criteria, relevant files/tables, validation expectations, and a parent roadmap issue if applicable. Below are issue drafts in that format.

Issue 1
Title: Promote calibrated grouped advanced_count PA scorer as default served path

Goal
Make the calibrated grouped pa_outcome_distribution scorer the default research-serving path across CLI, API, and command center surfaces.

Current state
The current best historical PA model is a grouped-taxonomy hist_gradient_boosting_multiclass model using advanced_count, trained through 2022 and validated on 2023–2025, with a registered isotonic calibration artifact available to CLI and /api/predict. The scorer exists for both historical and stored live PAs, but default-serving behavior is not yet fully standardized.

Scope

Standardize request/response handling for target_id = pa_outcome_distribution

Make calibrated scoring the default served path, with raw scoring still optionally available

Ensure CLI and API return the same core fields and derived aggregates

Surface model version and calibration metadata in responses and logs

Non-goals

Training a new model family

Changing target taxonomy

Building inning/game simulators in this issue

Acceptance criteria

Historical and live scoring use one shared response contract

API defaults to calibrated output for the winning grouped advanced_count model

Response includes class probabilities, hit, traditional on-base, reach-base-any, strikeout, ball-in-play, extra-base-hit, and expected total bases

Responses expose model_name, model_version, and calibration metadata

Relevant files/tables

scripts/predict_pa_outcome_distribution.py

scripts/predict_live_pa_outcome_distribution.py

scripts/register_pa_outcome_calibration.py

baseball-chatbot-ui/app/api/*

predictions.calibration_reports

Validation expectations

Compare historical and live API payloads for field parity

Confirm calibrated vs raw path toggling works

Confirm model metadata and calibration report names are emitted and logged

Parent roadmap issue

#24 and #31 are the closest documented anchors from the current snapshot.

Issue 2
Title: Add durable live PA prediction logging for calibrated scorer outputs

Goal
Persist every meaningful live PA prediction with model version, calibration metadata, state snapshot, and feature provenance.

Current state
The live scorer exists, but the current snapshot explicitly says durable live prediction logging is still not done.

Scope

Add additive SQL migration for predictions.live_pa_predictions

Optionally add lightweight predictions.api_prediction_requests

Write prediction rows from scripts/predict_live_pa_outcome_distribution.py

Expose latest prediction rows through an analysis view for UI consumption

Non-goals

Logging arbitrary shell commands

General-purpose request analytics beyond prediction observability

Market execution or autobetting

Acceptance criteria

Every persisted live PA score has a durable row with model and state metadata

Each row can be linked back to a source snapshot or canonical live game/event context

Latest predictions are queryable through a stable read view

Logging can be toggled for debugging vs normal API use if needed

Relevant files/tables

sql/083_live_prediction_logging.sql (new)

scripts/predict_live_pa_outcome_distribution.py

predictions.prediction_runs

analysis.live_pa_prediction_latest (new view)

Validation expectations

Score a known live PA and verify one durable row is inserted

Confirm stored response probabilities match API output

Confirm prediction rows remain queryable by game_id and plate_appearance_id

Parent roadmap issue

#31 Add live PA outcome scoring workflow and prediction logging.

Issue 3
Title: Measure and improve live PA feature parity after bridge replay

Goal
Quantify live feature completeness and improve it by replaying stored snapshots through the repaired bridge-aware transform path.

Current state
The live parity view now joins park priors and team rolling-form marts for bridged rows, but older transformed rows may still carry MLB### fallback IDs, and broader replay plus season-aware bridge work remain unfinished.

Scope

Run bounded replay on a regular-season slice

Measure fill rates before and after replay

Report remaining fallback IDs and null-rate classes

Use results to prioritize game_xref and season-aware team reconciliation

Non-goals

Full historical replay in one pass

Spring-training/non-regular-season venue perfection

New model training

Acceptance criteria

Before/after parity report exists for a bounded sample

Null rates for park/team parity fields are measured

Remaining fallback IDs are enumerated

Results are documented in CURRENT_SNAPSHOT.md and PROJECT_LOG.md

Relevant files/tables

scripts/replay_live_bridge_backfill.py

scripts/transform_live_game.py

sql/122_live_pa_feature_parity.sql

bridge.team_xref, bridge.park_xref, future bridge.game_xref

Validation expectations

Spot-check replayed rows in core.live_games

Spot-check matching rows in features.live_plate_appearance_advanced_count_examples

Compare null-rate metrics pre/post replay

Parent roadmap issue

#28 and #30.

Issue 4
Title: Refactor half-inning simulation to consume calibrated PA outcome distributions

Goal
Turn half-inning simulation into a canonical model-driven layer using the existing calibrated pa_outcome_distribution scorer.

Current state
The procedures define a future model-driven half-inning process, and scripts/simulate_half_inning.py exists as a candidate, but the docs warn that baseball state transitions must be correct before trusting outputs.

Scope

Refactor simulator around PA outcome distributions

Build or isolate baseball state transition logic

Persist simulation runs

Produce inning distribution summaries for command center use

Non-goals

Full pitch-by-pitch simulation

Market automation

UI-heavy work before simulator correctness is validated

Acceptance criteria

Simulator consumes the same PA probability service contract used by CLI/API

Baseball state transitions are covered by tests

Simulation runs are persisted with assumptions and model version

Output includes p_zero_runs, p_one_plus_runs, p_two_plus_runs, expected runs

Relevant files/tables

scripts/simulate_half_inning.py

sql/080_half_inning_examples.sql

predictions.simulation_runs

sql/121_inference_functions.sql only if needed later

Validation expectations

Historical sanity checks against half-inning summaries

Fixed-seed reproducibility

No illegal base/out state transitions in tests

Parent roadmap issue

#10 and downstream of #24/#31.

Issue 5
Title: Add read-only market snapshot and model edge comparison layer

Goal
Create a research-grade market comparison layer for Polymarket/Kalshi-style odds without mixing prediction generation and execution.

Current state
The project objective includes comparing model probabilities with markets, and sql/092_live_odds_views.sql exists as a candidate, but live odds integration is still placeholder-level.

Scope

Add raw or typed market snapshot tables/views

Normalize market timestamps and identifiers

Join latest model outputs to latest market prices

Expose read-only edge summaries in analysis

Non-goals

Auto-order placement

Market-making or execution logic

Commingling model outputs with trading automation

Acceptance criteria

Market snapshots are timestamped and queryable

Comparison views show market implied probabilities and model edge

Command center can render read-only market comparison cards

No execution actions are exposed in browser routes

Relevant files/tables

sql/092_live_odds_views.sql

future market snapshot ingestion scripts

analysis.* views

Validation expectations

Spot-check implied probability calculations

Verify market rows remain source-preserved and timestamped

Confirm model edge cards match backend queries

Parent roadmap issue

#10 and #22 are likely nearest umbrella references.

Recommended implementation sequence
The current snapshot’s “best move right now” already tells you the correct order: decide on the default count-state calibrated scorer, persist the bootstrap-backed report set, run bounded replay and measure parity gains, finish game_xref and season-aware team reconciliation, then add durable live prediction logging. I would slightly tighten that into this practical build order:

Standardize /api/predict request/response and default calibrated serving.

Add sql/083_live_prediction_logging.sql and write from the live scorer.

Run bounded replay and publish parity metrics.

Finish game_xref and season-aware bridge work.

Refactor half-inning simulation to use the same probability service.

Add read-only market comparison views after prediction logging and simulation are stable.

Extra recommendations
Add one shared scorer wrapper
Instead of letting historical scoring, live scoring, API routing, and future simulation each compute derived probabilities separately, create one shared scorer wrapper in Python that:

loads model,

optionally loads calibration artifact,

scores one feature row,

computes derived probabilities,

emits a normalized payload,

optionally persists the result.

That will reduce drift and make the API contract much easier to keep stable.

Add a feature-missing policy
Your live parity view still allows nullable live fields in some cases, especially around bridge completeness. So define a deterministic missing-feature policy now: which fields are allowed to be null, which get imputed, and which should block scoring.

Add a thin health panel
Issue #22 is already about a pipeline runbook and warehouse health panel. I would expose, at minimum:

last successful raw MLB ingest,

live parity null rates,

count of fallback IDs,

last prediction timestamp,

current default model version,

current default calibration artifact.

Bottom line
The three most useful concrete deliverables right now are: a new additive SQL migration for durable live prediction logging, a strict /api/predict request/response contract, and a set of issues that force the work into the same canonical architecture your repo already documents. If you follow the implementation sequence above, you will move from “good historical PA research baseline” to “replayable, logged, live-capable probability service” without forking into a second architecture or losing alignment with the repo’s current direction.

If you want, I can next turn this into copy-paste-ready artifacts:

the full sql/083_live_prediction_logging.sql migration,

a TypeScript interface file for the Next.js API,

and a checklist-style PR plan with commit order and validation commands.

ok yes please
Completed 2 steps
Yes — and now that I’ve looked at the actual prediction and inference files, I can make this much more concrete. Your code already has the key hooks: registered model lookup, optional isotonic calibration loading, derived probability helpers, a live parity view, and a placeholder inference SQL layer for simulation workloads. The biggest thing missing is durable prediction persistence and a single stable serving contract across historical, live, and future simulation consumers.

What I found in the code
Your live scorer already reads from features.live_plate_appearance_advanced_count_examples, loads a registered model, optionally applies calibration, and returns class plus derived probabilities along with mlb_game_pk, snapshot_id, and plate-appearance context. Your historical scorer does the same for historical feature views and currently derives p_hit, p_extra_base_hit, p_on_base_traditional, p_reach_base_any, p_ball_in_play, and expected_total_bases. The existing SQL inference file is still a placeholder for true model serving because inference.predict_plate_appearance_batch returns mocked probabilities, and sql/092_live_odds_views.sql is also a historical-frequency prototype built on features.play_snapshot, not the newer calibrated model-serving path.

That means the next artifacts should do four things: preserve your current architecture, avoid breaking existing scripts, standardize the API around the current scorer output, and create a migration path from prototype odds views to real prediction-backed views.

Full SQL migration
The cleanest next artifact is an additive migration like sql/123_live_prediction_logging.sql, because your live parity view already sits at 122, and this keeps the work adjacent to the current live serving layer. This version is designed to fit your existing predictions.prediction_runs / predictions.calibration_reports patterns and the metadata your scorer already exposes.

sql
-- sql/123_live_prediction_logging.sql
-- Durable logging for live plate appearance prediction requests and scored outputs.
-- Intended to sit after live parity view creation so scoring can persist canonical feature-backed results.

CREATE SCHEMA IF NOT EXISTS predictions;
CREATE SCHEMA IF NOT EXISTS analysis;

CREATE TABLE IF NOT EXISTS predictions.live_pa_predictions (
    live_pa_prediction_id BIGSERIAL PRIMARY KEY,
    prediction_run_id BIGINT REFERENCES predictions.prediction_runs(prediction_run_id),

    target_id TEXT NOT NULL DEFAULT 'pa_outcome_distribution',
    source_type TEXT NOT NULL DEFAULT 'mlb_live',

    game_id TEXT NOT NULL,
    plate_appearance_id INTEGER NOT NULL,
    mlb_game_pk BIGINT,
    snapshot_id BIGINT,
    plate_appearance_index INTEGER,

    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_id BIGINT,
    artifact_uri TEXT,
    feature_set TEXT NOT NULL,
    feature_view_name TEXT NOT NULL DEFAULT 'features.live_plate_appearance_advanced_count_examples',

    calibration_applied BOOLEAN NOT NULL DEFAULT FALSE,
    calibration_report_id BIGINT,
    calibration_report_name TEXT,
    calibration_method TEXT,
    calibration_artifact_uri TEXT,

    probability_sum DOUBLE PRECISION NOT NULL,

    class_probabilities_json JSONB NOT NULL,
    derived_probabilities_json JSONB NOT NULL,
    raw_class_probabilities_json JSONB,
    raw_derived_probabilities_json JSONB,

    input_features_json JSONB,
    live_context_json JSONB,
    state_snapshot_json JSONB,
    missing_features_json JSONB,
    request_context_json JSONB,
    model_metadata_json JSONB,

    predicted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_live_pa_prediction_versioned
        UNIQUE (
            game_id,
            plate_appearance_id,
            source_type,
            model_name,
            model_version,
            calibration_applied,
            predicted_at
        )
);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_game_pa
    ON predictions.live_pa_predictions (game_id, plate_appearance_id);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_game_time
    ON predictions.live_pa_predictions (game_id, predicted_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_snapshot
    ON predictions.live_pa_predictions (snapshot_id);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_model
    ON predictions.live_pa_predictions (model_name, model_version, calibration_applied);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_target_source
    ON predictions.live_pa_predictions (target_id, source_type, predicted_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_class_probs_gin
    ON predictions.live_pa_predictions USING GIN (class_probabilities_json);

CREATE INDEX IF NOT EXISTS idx_live_pa_predictions_derived_probs_gin
    ON predictions.live_pa_predictions USING GIN (derived_probabilities_json);

CREATE TABLE IF NOT EXISTS predictions.api_prediction_requests (
    api_prediction_request_id BIGSERIAL PRIMARY KEY,
    request_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    route_name TEXT NOT NULL DEFAULT '/api/predict',

    target_id TEXT NOT NULL,
    source_type TEXT NOT NULL,

    game_id TEXT,
    plate_appearance_id INTEGER,

    request_json JSONB NOT NULL,
    response_summary_json JSONB,

    model_name TEXT,
    model_version TEXT,
    calibration_applied BOOLEAN,
    calibration_report_name TEXT,

    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_code TEXT,
    error_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_prediction_requests_time
    ON predictions.api_prediction_requests (request_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_api_prediction_requests_target
    ON predictions.api_prediction_requests (target_id, source_type, request_timestamp DESC);

CREATE OR REPLACE VIEW analysis.live_pa_prediction_latest AS
SELECT DISTINCT ON (
    p.game_id,
    p.plate_appearance_id,
    p.source_type,
    p.model_name,
    p.model_version,
    p.calibration_applied
)
    p.live_pa_prediction_id,
    p.prediction_run_id,
    p.target_id,
    p.source_type,
    p.game_id,
    p.plate_appearance_id,
    p.mlb_game_pk,
    p.snapshot_id,
    p.plate_appearance_index,
    p.model_name,
    p.model_version,
    p.model_id,
    p.artifact_uri,
    p.feature_set,
    p.feature_view_name,
    p.calibration_applied,
    p.calibration_report_id,
    p.calibration_report_name,
    p.calibration_method,
    p.calibration_artifact_uri,
    p.probability_sum,
    p.class_probabilities_json,
    p.derived_probabilities_json,
    p.raw_class_probabilities_json,
    p.raw_derived_probabilities_json,
    p.input_features_json,
    p.live_context_json,
    p.state_snapshot_json,
    p.missing_features_json,
    p.request_context_json,
    p.model_metadata_json,
    p.predicted_at
FROM predictions.live_pa_predictions p
ORDER BY
    p.game_id,
    p.plate_appearance_id,
    p.source_type,
    p.model_name,
    p.model_version,
    p.calibration_applied,
    p.predicted_at DESC;

CREATE OR REPLACE VIEW analysis.live_pa_prediction_cards AS
SELECT
    p.game_id,
    p.plate_appearance_id,
    p.mlb_game_pk,
    p.snapshot_id,
    p.model_name,
    p.model_version,
    p.calibration_applied,
    p.calibration_report_name,
    p.predicted_at,

    (p.derived_probabilities_json ->> 'p_hit')::double precision AS p_hit,
    (p.derived_probabilities_json ->> 'p_on_base_traditional')::double precision AS p_on_base_traditional,
    (p.derived_probabilities_json ->> 'p_reach_base_any')::double precision AS p_reach_base_any,
    (p.class_probabilities_json ->> 'strikeout')::double precision AS p_strikeout,
    (p.derived_probabilities_json ->> 'p_ball_in_play')::double precision AS p_ball_in_play,
    (p.derived_probabilities_json ->> 'p_extra_base_hit')::double precision AS p_extra_base_hit,
    (p.derived_probabilities_json ->> 'expected_total_bases')::double precision AS expected_total_bases,

    p.state_snapshot_json,
    p.live_context_json
FROM analysis.live_pa_prediction_latest p;
Python patch plan
Your current live scorer already returns most of what you need, but it does not persist predictions and it does not provide a normalized state snapshot block like the interface should expose. The simplest refactor is to add one small persistence helper and slightly reshape the result payload, while preserving backward compatibility for existing CLI use.

Suggested changes to scripts/predict_live_pa_outcome_distribution.py
Add:

persist_prediction: bool = False

request_context: dict[str, Any] | None = None

prediction_run_id: int | None = None

state_snapshot assembled from live parity fields

missing_features list rather than hard failure only when absent from schema; keep hard failure for model-required columns not present in the frame, but separately report null-valued live fields that are expected-but-missing.

Copy-paste helper snippet
python
def _state_snapshot(row: pd.Series) -> dict[str, Any]:
    return {
        "inning": row.get("inning"),
        "is_bottom_inning": row.get("is_bottom_inning"),
        "outs_before": row.get("outs_before"),
        "start_bases": row.get("start_bases"),
        "balls": row.get("balls"),
        "strikes": row.get("strikes"),
        "home_score_diff": row.get("home_score_diff"),
        "batter_id": row.get("batter_id"),
        "pitcher_id": row.get("pitcher_id"),
        "batter_hand": row.get("batter_hand"),
        "pitcher_hand": row.get("pitcher_hand"),
        "batting_team_id": row.get("batting_team_id"),
        "fielding_team_id": row.get("fielding_team_id"),
        "park_id": row.get("park_id"),
        "season": row.get("season"),
        "season_era": row.get("season_era"),
        "rules_context_era": row.get("rules_context_era"),
    }


def _null_feature_names(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    row = frame.iloc[0]
    return [column for column in columns if column in frame.columns and pd.isna(row[column])]


def persist_live_prediction(
    *,
    result: dict[str, Any],
    prediction_run_id: int | None = None,
    request_context: dict[str, Any] | None = None,
) -> int:
    engine = create_engine(database_url())
    insert_sql = text(
        """
        INSERT INTO predictions.live_pa_predictions (
            prediction_run_id,
            target_id,
            source_type,
            game_id,
            plate_appearance_id,
            mlb_game_pk,
            snapshot_id,
            plate_appearance_index,
            model_name,
            model_version,
            model_id,
            artifact_uri,
            feature_set,
            calibration_applied,
            calibration_report_id,
            calibration_report_name,
            calibration_method,
            calibration_artifact_uri,
            probability_sum,
            class_probabilities_json,
            derived_probabilities_json,
            raw_class_probabilities_json,
            raw_derived_probabilities_json,
            input_features_json,
            live_context_json,
            state_snapshot_json,
            missing_features_json,
            request_context_json,
            model_metadata_json
        ) VALUES (
            :prediction_run_id,
            :target_id,
            :source_type,
            :game_id,
            :plate_appearance_id,
            :mlb_game_pk,
            :snapshot_id,
            :plate_appearance_index,
            :model_name,
            :model_version,
            :model_id,
            :artifact_uri,
            :feature_set,
            :calibration_applied,
            :calibration_report_id,
            :calibration_report_name,
            :calibration_method,
            :calibration_artifact_uri,
            :probability_sum,
            CAST(:class_probabilities_json AS jsonb),
            CAST(:derived_probabilities_json AS jsonb),
            CAST(:raw_class_probabilities_json AS jsonb),
            CAST(:raw_derived_probabilities_json AS jsonb),
            CAST(:input_features_json AS jsonb),
            CAST(:live_context_json AS jsonb),
            CAST(:state_snapshot_json AS jsonb),
            CAST(:missing_features_json AS jsonb),
            CAST(:request_context_json AS jsonb),
            CAST(:model_metadata_json AS jsonb)
        )
        RETURNING live_pa_prediction_id
        """
    )
    payload = {
        "prediction_run_id": prediction_run_id,
        "target_id": result["target_id"],
        "source_type": result["source_type"],
        "game_id": result["game_id"],
        "plate_appearance_id": result["plate_appearance_id"],
        "mlb_game_pk": result["live_context"].get("mlb_game_pk"),
        "snapshot_id": result["live_context"].get("snapshot_id"),
        "plate_appearance_index": result["live_context"].get("plate_appearance_index"),
        "model_name": result["model"]["model_name"],
        "model_version": result["model"]["model_version"],
        "model_id": result["model"].get("model_id"),
        "artifact_uri": result["model"].get("artifact_uri"),
        "feature_set": result["model"]["feature_set"],
        "calibration_applied": result["calibration"]["applied"],
        "calibration_report_id": result["calibration"].get("calibration_report_id"),
        "calibration_report_name": result["calibration"].get("report_name"),
        "calibration_method": result["calibration"].get("calibration_method"),
        "calibration_artifact_uri": result["calibration"].get("artifact_uri"),
        "probability_sum": result["probability_sum"],
        "class_probabilities_json": json.dumps(result["class_probabilities"]),
        "derived_probabilities_json": json.dumps(result["derived_probabilities"]),
        "raw_class_probabilities_json": json.dumps(result.get("raw_class_probabilities")),
        "raw_derived_probabilities_json": json.dumps(result.get("raw_derived_probabilities")),
        "input_features_json": json.dumps(result["input_features"]),
        "live_context_json": json.dumps(result["live_context"]),
        "state_snapshot_json": json.dumps(result["state_snapshot"]),
        "missing_features_json": json.dumps(result.get("missing_features", [])),
        "request_context_json": json.dumps(request_context or {}),
        "model_metadata_json": json.dumps(result["model"]),
    }
    try:
        with engine.begin() as conn:
            return int(conn.execute(insert_sql, payload).scalar_one())
    finally:
        engine.dispose()
Minimal return-shape improvements
After frame is loaded in the live script, add:

python
null_features = _null_feature_names(frame, numeric_features + categorical_features)
row = frame.iloc[0]
Then update the result object:

python
result = {
    "target_id": TARGET_ID,
    "source_type": "mlb_live",
    "game_id": game_id,
    "plate_appearance_id": plate_appearance_id,
    "model": {
        "model_name": metadata["model_name"],
        "model_version": metadata["model_version"],
        "model_id": metadata["model_id"],
        "artifact_uri": metadata["artifact_uri"],
        "feature_set": feature_set,
        "is_active": bool(metadata["is_active"]),
    },
    "probability_sum": float(sum(probabilities.values())),
    "class_probabilities": probabilities,
    "derived_probabilities": derived_probabilities(probabilities),
    "input_features": row[numeric_features + categorical_features].to_dict(),
    "state_snapshot": _state_snapshot(row),
    "missing_features": null_features,
    "live_context": {
        "mlb_game_pk": row.get("mlb_game_pk"),
        "snapshot_id": row.get("snapshot_id"),
        "plate_appearance_index": row.get("plate_appearance_index"),
        "event_text": row.get("event_text"),
        "event_code": row.get("event_code"),
    },
}
If persist_prediction is true, call persist_live_prediction(...) and then append:

python
result["logging"] = {
    "prediction_run_id": prediction_run_id,
    "live_pa_prediction_id": live_pa_prediction_id,
}
That matches your current scorer structure and uses metadata you already fetch from models.model_registry and predictions.calibration_reports.

TypeScript interfaces
Your API should lock onto the scorer you already have rather than invent a second interface. The repo docs say /api/predict is already an intended route, and the current Python scripts make it clear which fields are canonical today.

Here is a practical baseball-chatbot-ui/lib/types/predict.ts:

ts
export type PredictTargetId = "pa_outcome_distribution"
export type PredictSourceType = "historical_pa" | "mlb_live" | "simulation_state"

export interface PredictRequest {
  target_id: PredictTargetId
  source_type: PredictSourceType
  game_id: string
  plate_appearance_id?: number
  model_name?: string
  model_version?: string
  feature_set?: "basic" | "advanced" | "advanced_count"
  target_taxonomy?: "granular" | "grouped"
  apply_calibration?: boolean
  calibration_report_name?: string
  include_feature_snapshot?: boolean
  persist_prediction?: boolean
  prediction_run_id?: number | null
  request_context?: Record<string, unknown>
}

export interface PredictionModelMetadata {
  model_name: string
  model_version: string
  model_id?: number
  artifact_uri?: string
  feature_set: string
  is_active?: boolean
}

export interface PredictionCalibrationMetadata {
  applied: boolean
  calibration_report_id?: number
  report_name?: string
  calibration_method?: string
  artifact_uri?: string
}

export interface PredictionStateSnapshot {
  inning?: number
  is_bottom_inning?: boolean | number
  outs_before?: number
  start_bases?: number
  balls?: number
  strikes?: number
  home_score_diff?: number
  batter_id?: string
  pitcher_id?: string
  batter_hand?: string
  pitcher_hand?: string
  batting_team_id?: string
  fielding_team_id?: string
  park_id?: string
  season?: number
  season_era?: string
  rules_context_era?: string
}

export interface LiveContext {
  mlb_game_pk?: number
  snapshot_id?: number
  plate_appearance_index?: number
  event_text?: string
  event_code?: string
}

export interface DerivedProbabilities {
  p_hit?: number
  p_extra_base_hit?: number
  p_on_base_traditional?: number
  p_reach_base_any?: number
  p_ball_in_play?: number
  expected_total_bases?: number
}

export interface PredictResponse {
  status?: "ok"
  target_id: PredictTargetId
  source_type?: PredictSourceType
  game_id: string
  plate_appearance_id?: number
  actual_outcome_class?: string | null

  model: PredictionModelMetadata
  calibration: PredictionCalibrationMetadata

  probability_sum: number
  class_probabilities: Record<string, number>
  derived_probabilities: DerivedProbabilities

  raw_class_probabilities?: Record<string, number>
  raw_derived_probabilities?: DerivedProbabilities

  input_features?: Record<string, unknown>
  state_snapshot?: PredictionStateSnapshot
  missing_features?: string[]
  live_context?: LiveContext

  logging?: {
    prediction_run_id?: number | null
    live_pa_prediction_id?: number
  }
}

export interface PredictErrorResponse {
  status: "error"
  target_id: PredictTargetId
  source_type?: PredictSourceType
  error_code: string
  message: string
  details?: Record<string, unknown>
}
Next.js API route sketch
You likely want your route handler to be a thin adapter over the Python scorer, because the repo’s architecture is clearly Python-first for model execution and SQL generation. The safest approach is to validate request shape in Next.js, invoke the Python script or internal Python service, and return the exact normalized contract above.

Pseudo-shape:

ts
// baseball-chatbot-ui/app/api/predict/route.ts
import { NextRequest, NextResponse } from "next/server"
import type { PredictRequest, PredictErrorResponse } from "@/lib/types/predict"

export async function POST(req: NextRequest) {
  const body = (await req.json()) as PredictRequest

  if (body.target_id !== "pa_outcome_distribution") {
    const error: PredictErrorResponse = {
      status: "error",
      target_id: "pa_outcome_distribution",
      source_type: body.source_type,
      error_code: "UNSUPPORTED_TARGET",
      message: `Unsupported target_id: ${body.target_id}`,
    }
    return NextResponse.json(error, { status: 400 })
  }

  // Dispatch to historical or live scorer; preserve same response shape.
  // Keep command-center logic thin; Python remains the source of truth.
  return NextResponse.json({ status: "ok" })
}
PR plan
The procedures doc says substantial work should update the project log and current snapshot and should stay aligned with canonical rebuild and issue-tracking practices. So I would sequence the PRs like this.

PR 1 — Add durable live prediction logging
Files:

sql/123_live_prediction_logging.sql

scripts/rebuild_warehouse.sh

docs updates in docs/PROJECT_LOG.md and docs/agents/CURRENT_SNAPSHOT.md

Validation:

run rebuild including the new SQL migration

verify analysis.live_pa_prediction_latest and analysis.live_pa_prediction_cards compile

insert one synthetic row or one real scored row and confirm views resolve

PR 2 — Normalize live scorer output and persistence
Files:

scripts/predict_live_pa_outcome_distribution.py

optionally shared helpers factored from scripts/predict_pa_outcome_distribution.py

Validation:

score one known live PA

verify response includes state_snapshot, missing_features, and logging

verify persisted row matches response payload

PR 3 — Lock the /api/predict contract
Files:

baseball-chatbot-ui/lib/types/predict.ts

baseball-chatbot-ui/app/api/predict/route.ts

any UI card component expecting prediction responses

Validation:

API schema test for historical and live request paths

ensure response shape matches TypeScript interfaces

ensure unsupported targets and missing PAs return stable error contracts

PR 4 — Replace prototype odds dependency with prediction-backed views
Files:

sql/092_live_odds_views.sql

new comparison views under analysis

Validation:

verify edge cards use logged model outputs rather than historical-frequency placeholders

keep features.play_snapshot prototype views only if explicitly marked legacy

Validation commands
Your exact local commands depend on your repo bootstrap, but these are the checks I would require after the PRs above because they follow the current code and warehouse patterns.

Rebuild or apply the new migration and confirm analysis.live_pa_prediction_latest exists.

Run the live scorer on a known game_id and plate_appearance_id with --apply-calibration.

Query the inserted row from predictions.live_pa_predictions by game_id and plate_appearance_id.

Confirm class_probabilities_json sums to 1 and derived_probabilities_json matches the scorer output.

Load one command-center card off analysis.live_pa_prediction_cards and confirm it renders without bespoke client-side derivation.

Strong extra recommendation
One more thing I would add soon after these PRs: refactor the common scoring logic in predict_pa_outcome_distribution.py and predict_live_pa_outcome_distribution.py into a shared module, because both scripts already duplicate model loading, calibration loading, probability derivation, and result shaping. Doing that right after the first persistence/API work will make the half-inning simulator much easier to implement, because it can call the exact same scorer contract instead of re-deriving probabilities or copying logic again.

Bottom line
The code confirms your architecture is close: the live parity view is real, the scorer is real, calibration artifacts are real, and the weak points are persistence, contract stability, and replacement of prototype odds/inference placeholders. The migration, TypeScript contract, and PR plan above are the fastest way to turn the current research-grade system into a replayable, UI-friendly, multi-layer probability service without drifting away from the repo’s canonical design.

If you want, I can next draft the actual patched Python file contents for predict_live_pa_outcome_distribution.py and the matching route.ts file in near-final form.

ok yes please. if you can advise me on what files to archive or modify
Completed 2 steps
Yes — and now I can give you much sharper advice on both what to modify and what to archive.

Your current half-inning simulator and live odds views are useful prototypes, but they are not aligned with the newer calibrated multiclass PA-serving architecture you already have. The simulator still loads separate binary PA models like pa_batter_hit, pa_batter_walk, and pa_batter_strikeout, seeds randomness inside each PA call, uses simplified baserunner logic, and hardcodes generic batter/pitcher placeholders, so it should be treated as a prototype to refactor rather than a production path. Likewise, sql/092_live_odds_views.sql is still a historical-frequency materialized-view prototype over features.play_snapshot, not a prediction-backed live odds layer, so it should be archived or explicitly marked legacy once you replace it with views sourced from logged calibrated predictions.

What to modify
These are the files I would actively modify first because they are part of the canonical path or should become part of it.

File	Action	Why
scripts/predict_live_pa_outcome_distribution.py	Modify now	It already performs live scoring from features.live_plate_appearance_advanced_count_examples and is the right place to add normalized output, persistence, and state snapshots.
scripts/predict_pa_outcome_distribution.py	Modify soon	It already defines the historical serving contract and derived metrics, so it should be aligned to the same response schema as live scoring.
scripts/register_pa_outcome_calibration.py	Modify lightly if needed	It already manages calibration artifacts, so only adjust if you need metadata fields to flow more cleanly into persisted prediction rows.
sql/123_live_prediction_logging.sql	Add new	This should become the durable store for live predictions and prediction request metadata.
sql/122_live_pa_feature_parity.sql	Modify carefully	Keep it canonical and extend only if you need additional live fields for stable serving or parity diagnostics.
baseball-chatbot-ui/app/api/predict/route.ts	Create/modify	This should become the stable API boundary for the command center.
baseball-chatbot-ui/lib/types/predict.ts	Create	Lock the request/response contract in one place for the UI.
docs/agents/CURRENT_SNAPSHOT.md	Update after each milestone	Your repo docs treat this as canonical state reporting.
docs/PROJECT_LOG.md	Update after material changes	Your procedures explicitly call for this.
What to archive or mark legacy
These are the files I would not delete immediately, but I would archive, rename, or clearly mark as legacy/prototype so they stop confusing future work.

scripts/simulate_half_inning.py
This should be archived as a prototype and replaced by a refactored simulator module that consumes the calibrated multiclass PA distribution service. The current script uses outdated assumptions: separate binary models, unrealistic base-state transitions, fixed random seeding inside each PA, and generic player placeholders, which makes it unsuitable as the basis for inning or game odds without a rewrite.

Recommendation:
Rename it to something like:

scripts/archive/prototype_simulate_half_inning.py, or

keep the file path but add a top-of-file banner: # LEGACY PROTOTYPE - DO NOT USE FOR CANONICAL INFERENCE

Then build a new path such as:

scripts/simulate_half_inning_from_pa_distribution.py, or better,

scripts/run_half_inning_simulation.py

plus a reusable module like retrosheet/simulation/half_inning.py

sql/092_live_odds_views.sql
This is also legacy-prototype material right now. It computes empirical hit and strikeout rates from features.play_snapshot, which is not the same thing as using your trained calibrated PA scorer on canonical live features. That means if someone sees “live odds” in the filename, they may incorrectly assume it is the current recommended path.

Recommendation:
Either:

rename to sql/archive/092_live_odds_views_legacy.sql, or

keep it but prepend a comment banner such as:
-- LEGACY PROTOTYPE: frequency-based placeholder views; superseded by prediction-backed live odds views

Then replace it later with a new file like:

sql/124_prediction_backed_live_odds_views.sql

sql/121_inference_functions.sql
You told me earlier this file was still placeholder-oriented, and the file content summary still points in that direction. If it currently returns mocked or pseudo probabilities, do not let downstream code rely on it as a real serving layer.

Recommendation:
Do one of these:

mark clearly as placeholder/legacy,

or split it into:

sql/121_inference_functions_legacy.sql

sql/124_prediction_serving_views.sql

I would prefer preserving it for reference but making the “do not use for production inference” status impossible to miss.

What to leave alone for now
A few files should mostly stay as they are while you build around them.

sql/080_half_inning_examples.sql should mostly remain because it is a useful feature/output table for half-inning context and evaluation slices; it is not the problem.

sql/122_live_pa_feature_parity.sql should remain canonical and be extended rather than replaced, because it already embodies your intended live-to-historical parity bridge.

scripts/register_pa_outcome_calibration.py likely only needs metadata-flow tweaks, not a redesign, because calibration registration is already part of the intended model path.

Near-final patched Python file
Below is the version I would aim for conceptually in scripts/predict_live_pa_outcome_distribution.py. I’m not pretending this is guaranteed drop-in exact against your repo without seeing every import and helper, but it is very close to the shape you want and aligned to the current script responsibilities. The goal is to:

preserve current live scoring behavior,

add a normalized response schema,

optionally persist predictions,

expose state snapshot and missing features,

keep calibration metadata explicit.

python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import psycopg2
from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parents[1]
TARGET_ID = "pa_outcome_distribution"
DEFAULT_FEATURE_VIEW = "features.live_plate_appearance_advanced_count_examples"


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def database_url() -> str | URL:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    kwargs = database_kwargs()
    return URL.create(
        "postgresql+psycopg2",
        username=kwargs["user"],
        password=kwargs["password"] or None,
        host=kwargs["host"],
        port=int(kwargs["port"]),
        database=kwargs["dbname"],
    )


def derived_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    p_single = probabilities.get("single", 0.0)
    p_double = probabilities.get("double", 0.0)
    p_triple = probabilities.get("triple", 0.0)
    p_home_run = probabilities.get("home_run", 0.0)
    p_walk = probabilities.get("walk", 0.0)
    p_hbp = probabilities.get("hit_by_pitch", 0.0)
    p_reach_error = probabilities.get("reached_on_error", 0.0)
    p_strikeout = probabilities.get("strikeout", 0.0)

    p_hit = p_single + p_double + p_triple + p_home_run
    p_extra_base_hit = p_double + p_triple + p_home_run
    p_on_base_traditional = p_hit + p_walk + p_hbp
    p_reach_base_any = p_on_base_traditional + p_reach_error
    p_ball_in_play = max(0.0, 1.0 - p_walk - p_hbp - p_strikeout)
    expected_total_bases = (
        1.0 * p_single
        + 2.0 * p_double
        + 3.0 * p_triple
        + 4.0 * p_home_run
    )

    return {
        "p_hit": p_hit,
        "p_extra_base_hit": p_extra_base_hit,
        "p_on_base_traditional": p_on_base_traditional,
        "p_reach_base_any": p_reach_base_any,
        "p_ball_in_play": p_ball_in_play,
        "p_strikeout": p_strikeout,
        "expected_total_bases": expected_total_bases,
    }


def load_active_model(
    *,
    model_name: str | None,
    model_version: str | None,
    feature_set: str,
) -> tuple[Any, dict[str, Any]]:
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            if model_version:
                cur.execute(
                    """
                    SELECT model_id, model_name, model_version, artifact_uri, feature_spec, is_active
                    FROM models.model_registry
                    WHERE target_id = %s
                      AND model_name = %s
                      AND model_version = %s
                    ORDER BY model_id DESC
                    LIMIT 1
                    """,
                    (TARGET_ID, model_name, model_version),
                )
            else:
                cur.execute(
                    """
                    SELECT model_id, model_name, model_version, artifact_uri, feature_spec, is_active
                    FROM models.model_registry
                    WHERE target_id = %s
                      AND (%s IS NULL OR model_name = %s)
                      AND is_active = TRUE
                    ORDER BY model_version DESC, model_id DESC
                    LIMIT 1
                    """,
                    (TARGET_ID, model_name, model_name),
                )

            row = cur.fetchone()
            if not row:
                raise ValueError("No matching active model found for live PA scoring")

            metadata = {
                "model_id": row[0],
                "model_name": row[1],
                "model_version": row[2],
                "artifact_uri": row[3],
                "feature_spec": row[4],
                "is_active": bool(row[5]),
                "feature_set": feature_set,
            }
            model = joblib.load(ROOT / metadata["artifact_uri"])
            return model, metadata
    finally:
        conn.close()


def load_calibration_artifact(report_name: str | None) -> dict[str, Any] | None:
    if not report_name:
        return None
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT calibration_report_id, report_name, calibration_method, artifact_uri
                FROM predictions.calibration_reports
                WHERE report_name = %s
                ORDER BY calibration_report_id DESC
                LIMIT 1
                """,
                (report_name,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Calibration report not found: {report_name}")
            artifact = joblib.load(ROOT / row[3])
            return {
                "calibration_report_id": row[0],
                "report_name": row[1],
                "calibration_method": row[2],
                "artifact_uri": row[3],
                "artifact": artifact,
            }
    finally:
        conn.close()


def fetch_live_feature_row(
    *,
    game_id: str,
    plate_appearance_id: int,
    feature_view_name: str = DEFAULT_FEATURE_VIEW,
) -> pd.DataFrame:
    engine = create_engine(database_url())
    try:
        query = text(
            f"""
            SELECT *
            FROM {feature_view_name}
            WHERE game_id = :game_id
              AND plate_appearance_id = :plate_appearance_id
            LIMIT 1
            """
        )
        return pd.read_sql_query(
            query,
            engine,
            params={
                "game_id": game_id,
                "plate_appearance_id": plate_appearance_id,
            },
        )
    finally:
        engine.dispose()


def _state_snapshot(row: pd.Series) -> dict[str, Any]:
    return {
        "inning": row.get("inning"),
        "is_bottom_inning": row.get("is_bottom_inning"),
        "outs_before": row.get("outs_before"),
        "start_bases": row.get("start_bases"),
        "balls": row.get("balls"),
        "strikes": row.get("strikes"),
        "home_score_diff": row.get("home_score_diff"),
        "batter_id": row.get("batter_id"),
        "pitcher_id": row.get("pitcher_id"),
        "batter_hand": row.get("batter_hand"),
        "pitcher_hand": row.get("pitcher_hand"),
        "batting_team_id": row.get("batting_team_id"),
        "fielding_team_id": row.get("fielding_team_id"),
        "park_id": row.get("park_id"),
        "season": row.get("season"),
        "season_era": row.get("season_era"),
        "rules_context_era": row.get("rules_context_era"),
    }


def _null_feature_names(frame: pd.DataFrame, feature_cols: list[str]) -> list[str]:
    row = frame.iloc[0]
    return [col for col in feature_cols if col in frame.columns and pd.isna(row[col])]


def persist_live_prediction(
    *,
    result: dict[str, Any],
    prediction_run_id: int | None = None,
    request_context: dict[str, Any] | None = None,
) -> int:
    engine = create_engine(database_url())
    try:
        insert_sql = text(
            """
            INSERT INTO predictions.live_pa_predictions (
                prediction_run_id,
                target_id,
                source_type,
                game_id,
                plate_appearance_id,
                mlb_game_pk,
                snapshot_id,
                plate_appearance_index,
                model_name,
                model_version,
                model_id,
                artifact_uri,
                feature_set,
                feature_view_name,
                calibration_applied,
                calibration_report_id,
                calibration_report_name,
                calibration_method,
                calibration_artifact_uri,
                probability_sum,
                class_probabilities_json,
                derived_probabilities_json,
                raw_class_probabilities_json,
                raw_derived_probabilities_json,
                input_features_json,
                live_context_json,
                state_snapshot_json,
                missing_features_json,
                request_context_json,
                model_metadata_json
            ) VALUES (
                :prediction_run_id,
                :target_id,
                :source_type,
                :game_id,
                :plate_appearance_id,
                :mlb_game_pk,
                :snapshot_id,
                :plate_appearance_index,
                :model_name,
                :model_version,
                :model_id,
                :artifact_uri,
                :feature_set,
                :feature_view_name,
                :calibration_applied,
                :calibration_report_id,
                :calibration_report_name,
                :calibration_method,
                :calibration_artifact_uri,
                :probability_sum,
                CAST(:class_probabilities_json AS jsonb),
                CAST(:derived_probabilities_json AS jsonb),
                CAST(:raw_class_probabilities_json AS jsonb),
                CAST(:raw_derived_probabilities_json AS jsonb),
                CAST(:input_features_json AS jsonb),
                CAST(:live_context_json AS jsonb),
                CAST(:state_snapshot_json AS jsonb),
                CAST(:missing_features_json AS jsonb),
                CAST(:request_context_json AS jsonb),
                CAST(:model_metadata_json AS jsonb)
            )
            RETURNING live_pa_prediction_id
            """
        )

        payload = {
            "prediction_run_id": prediction_run_id,
            "target_id": result["target_id"],
            "source_type": result["source_type"],
            "game_id": result["game_id"],
            "plate_appearance_id": result["plate_appearance_id"],
            "mlb_game_pk": result["live_context"].get("mlb_game_pk"),
            "snapshot_id": result["live_context"].get("snapshot_id"),
            "plate_appearance_index": result["live_context"].get("plate_appearance_index"),
            "model_name": result["model"]["model_name"],
            "model_version": result["model"]["model_version"],
            "model_id": result["model"].get("model_id"),
            "artifact_uri": result["model"].get("artifact_uri"),
            "feature_set": result["model"]["feature_set"],
            "feature_view_name": result["feature_metadata"]["feature_view_name"],
            "calibration_applied": result["calibration"]["applied"],
            "calibration_report_id": result["calibration"].get("calibration_report_id"),
            "calibration_report_name": result["calibration"].get("report_name"),
            "calibration_method": result["calibration"].get("calibration_method"),
            "calibration_artifact_uri": result["calibration"].get("artifact_uri"),
            "probability_sum": result["probability_sum"],
            "class_probabilities_json": json.dumps(result["class_probabilities"]),
            "derived_probabilities_json": json.dumps(result["derived_probabilities"]),
            "raw_class_probabilities_json": json.dumps(result.get("raw_class_probabilities")),
            "raw_derived_probabilities_json": json.dumps(result.get("raw_derived_probabilities")),
            "input_features_json": json.dumps(result.get("input_features", {})),
            "live_context_json": json.dumps(result.get("live_context", {})),
            "state_snapshot_json": json.dumps(result.get("state_snapshot", {})),
            "missing_features_json": json.dumps(result.get("missing_features", [])),
            "request_context_json": json.dumps(request_context or {}),
            "model_metadata_json": json.dumps(result["model"]),
        }

        with engine.begin() as conn:
            live_pa_prediction_id = conn.execute(insert_sql, payload).scalar_one()
        return int(live_pa_prediction_id)
    finally:
        engine.dispose()


def predict_live_pa_outcome_distribution(
    *,
    game_id: str,
    plate_appearance_id: int,
    model_name: str | None = None,
    model_version: str | None = None,
    feature_set: str = "advanced_count",
    calibration_report_name: str | None = None,
    apply_calibration: bool = False,
    include_feature_snapshot: bool = True,
    persist_prediction: bool = False,
    prediction_run_id: int | None = None,
    request_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frame = fetch_live_feature_row(
        game_id=game_id,
        plate_appearance_id=plate_appearance_id,
        feature_view_name=DEFAULT_FEATURE_VIEW,
    )
    if frame.empty:
        raise ValueError(
            f"No live feature row found for game_id={game_id}, plate_appearance_id={plate_appearance_id}"
        )

    model, metadata = load_active_model(
        model_name=model_name,
        model_version=model_version,
        feature_set=feature_set,
    )

    feature_spec = metadata["feature_spec"]
    numeric_features = feature_spec["numeric_features"]
    categorical_features = feature_spec["categorical_features"]
    feature_cols = numeric_features + categorical_features

    missing_cols = [col for col in feature_cols if col not in frame.columns]
    if missing_cols:
        raise ValueError(f"Missing required feature columns: {missing_cols}")

    row = frame.iloc[0]
    null_features = _null_feature_names(frame, feature_cols)

    raw_probs = model.predict_proba(frame[feature_cols])[0]
    class_labels = [str(label) for label in model.classes_]
    raw_probabilities = {
        label: float(prob) for label, prob in zip(class_labels, raw_probs, strict=False)
    }
    probabilities = raw_probabilities.copy()

    calibration = {
        "applied": False,
        "calibration_report_id": None,
        "report_name": None,
        "calibration_method": None,
        "artifact_uri": None,
    }

    if apply_calibration:
        if not calibration_report_name:
            raise ValueError("apply_calibration=True requires calibration_report_name")
        calibration_artifact = load_calibration_artifact(calibration_report_name)
        calibrated = calibration_artifact["artifact"].transform(
            pd.DataFrame([raw_probabilities])
        )[0]
        probabilities = {
            label: float(prob)
            for label, prob in zip(class_labels, calibrated, strict=False)
        }
        prob_sum = sum(probabilities.values())
        if prob_sum and not math.isclose(prob_sum, 1.0, rel_tol=1e-6, abs_tol=1e-6):
            probabilities = {k: float(v / prob_sum) for k, v in probabilities.items()}

        calibration = {
            "applied": True,
            "calibration_report_id": calibration_artifact["calibration_report_id"],
            "report_name": calibration_artifact["report_name"],
            "calibration_method": calibration_artifact["calibration_method"],
            "artifact_uri": calibration_artifact["artifact_uri"],
        }

    result = {
        "status": "ok",
        "target_id": TARGET_ID,
        "source_type": "mlb_live",
        "game_id": game_id,
        "plate_appearance_id": int(plate_appearance_id),
        "model": {
            "model_name": metadata["model_name"],
            "model_version": metadata["model_version"],
            "model_id": metadata["model_id"],
            "artifact_uri": metadata["artifact_uri"],
            "feature_set": metadata["feature_set"],
            "is_active": metadata["is_active"],
        },
        "calibration": calibration,
        "probability_sum": float(sum(probabilities.values())),
        "class_probabilities": probabilities,
        "derived_probabilities": derived_probabilities(probabilities),
        "raw_class_probabilities": raw_probabilities if apply_calibration else None,
        "raw_derived_probabilities": (
            derived_probabilities(raw_probabilities) if apply_calibration else None
        ),
        "feature_metadata": {
            "feature_view_name": DEFAULT_FEATURE_VIEW,
            "included_feature_snapshot": include_feature_snapshot,
        },
        "input_features": row[feature_cols].to_dict() if include_feature_snapshot else {},
        "state_snapshot": _state_snapshot(row),
        "missing_features": null_features,
        "live_context": {
            "mlb_game_pk": row.get("mlb_game_pk"),
            "snapshot_id": row.get("snapshot_id"),
            "plate_appearance_index": row.get("plate_appearance_index"),
            "event_text": row.get("event_text"),
            "event_code": row.get("event_code"),
        },
    }

    if persist_prediction:
        live_pa_prediction_id = persist_live_prediction(
            result=result,
            prediction_run_id=prediction_run_id,
            request_context=request_context,
        )
        result["logging"] = {
            "prediction_run_id": prediction_run_id,
            "live_pa_prediction_id": live_pa_prediction_id,
        }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict live PA outcome distribution")
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--plate-appearance-id", required=True, type=int)
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--model-version", default=None)
    parser.add_argument("--feature-set", default="advanced_count")
    parser.add_argument("--apply-calibration", action="store_true")
    parser.add_argument("--calibration-report-name", default=None)
    parser.add_argument("--persist-prediction", action="store_true")
    parser.add_argument("--prediction-run-id", type=int, default=None)
    parser.add_argument("--no-feature-snapshot", action="store_true")
    args = parser.parse_args()

    result = predict_live_pa_outcome_distribution(
        game_id=args.game_id,
        plate_appearance_id=args.plate_appearance_id,
        model_name=args.model_name,
        model_version=args.model_version,
        feature_set=args.feature_set,
        apply_calibration=args.apply_calibration,
        calibration_report_name=args.calibration_report_name,
        include_feature_snapshot=not args.no_feature_snapshot,
        persist_prediction=args.persist_prediction,
        prediction_run_id=args.prediction_run_id,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
Near-final route.ts
This should be thin and should not compute probabilities itself. Your repo’s architecture clearly favors Python model execution and SQL-backed provenance, so Next.js should validate the request and pass through to the Python service layer or wrapper.

ts
// baseball-chatbot-ui/app/api/predict/route.ts
import { NextRequest, NextResponse } from "next/server"
import type {
  PredictErrorResponse,
  PredictRequest,
} from "@/lib/types/predict"

function badRequest(
  sourceType: PredictRequest["source_type"] | undefined,
  errorCode: string,
  message: string,
  details?: Record<string, unknown>,
) {
  const payload: PredictErrorResponse = {
    status: "error",
    target_id: "pa_outcome_distribution",
    source_type: sourceType,
    error_code: errorCode,
    message,
    details,
  }
  return NextResponse.json(payload, { status: 400 })
}

export async function POST(req: NextRequest) {
  const body = (await req.json()) as PredictRequest

  if (body.target_id !== "pa_outcome_distribution") {
    return badRequest(
      body.source_type,
      "UNSUPPORTED_TARGET",
      `Unsupported target_id: ${body.target_id}`,
      { target_id: body.target_id },
    )
  }

  if (!body.source_type) {
    return badRequest(undefined, "MISSING_SOURCE_TYPE", "source_type is required")
  }

  if (!body.game_id) {
    return badRequest(
      body.source_type,
      "MISSING_GAME_ID",
      "game_id is required",
    )
  }

  if (body.source_type === "mlb_live" && body.plate_appearance_id == null) {
    return badRequest(
      body.source_type,
      "MISSING_PLATE_APPEARANCE_ID",
      "plate_appearance_id is required for mlb_live predictions",
    )
  }

  try {
    // Replace with your internal Python invocation boundary:
    // - subprocess wrapper
    // - internal FastAPI service
    // - direct DB-backed service layer
    // Keep this route as a thin adapter only.
    const upstreamPayload = {
      ...body,
      apply_calibration: body.apply_calibration ?? true,
      persist_prediction: body.persist_prediction ?? true,
      feature_set: body.feature_set ?? "advanced_count",
      target_taxonomy: body.target_taxonomy ?? "grouped",
      include_feature_snapshot: body.include_feature_snapshot ?? true,
    }

    // Example placeholder:
    // const result = await callPythonPredictor(upstreamPayload)

    const result = {
      status: "ok",
      target_id: "pa_outcome_distribution",
      source_type: body.source_type,
      game_id: body.game_id,
      plate_appearance_id: body.plate_appearance_id,
      model: {
        model_name: body.model_name ?? "hist_gradient_boosting_multiclass",
        model_version: body.model_version ?? "active",
        feature_set: upstreamPayload.feature_set,
      },
      calibration: {
        applied: upstreamPayload.apply_calibration,
        report_name: body.calibration_report_name ?? null,
      },
      probability_sum: 1.0,
      class_probabilities: {},
      derived_probabilities: {},
    }

    return NextResponse.json(result)
  } catch (error) {
    const payload: PredictErrorResponse = {
      status: "error",
      target_id: "pa_outcome_distribution",
      source_type: body.source_type,
      error_code: "PREDICTION_FAILED",
      message: "Prediction request failed",
      details: {
        error: error instanceof Error ? error.message : String(error),
      },
    }
    return NextResponse.json(payload, { status: 500 })
  }
}
Exact archive/modify plan
Here is the clean operational plan I would use.

Modify now
scripts/predict_live_pa_outcome_distribution.py

scripts/predict_pa_outcome_distribution.py

sql/122_live_pa_feature_parity.sql only if a needed field is missing

baseball-chatbot-ui/app/api/predict/route.ts

baseball-chatbot-ui/lib/types/predict.ts

docs/agents/CURRENT_SNAPSHOT.md

docs/PROJECT_LOG.md

Add new
sql/123_live_prediction_logging.sql

sql/124_prediction_backed_live_odds_views.sql

optional shared scorer helper module, e.g. scripts/lib/pa_prediction_service.py or retrosheet/prediction/pa_service.py

Archive or mark legacy
scripts/simulate_half_inning.py

sql/092_live_odds_views.sql

any placeholder sections of sql/121_inference_functions.sql that still emit mock probabilities

Keep but do not redesign yet
sql/080_half_inning_examples.sql

scripts/register_pa_outcome_calibration.py

My strongest opinion
The biggest mistake to avoid now is trying to preserve prototype inference files as if they are equally valid alongside the newer calibrated multiclass serving path. Your repo is already telling you which direction won: canonical feature parity, registered models, optional isotonic calibration, and a stable prediction contract. So archive the prototype odds/simulator paths visibly, keep the useful feature tables, and funnel all new work through one PA probability service that everything else calls.

If you want, I can next draft:

sql/124_prediction_backed_live_odds_views.sql,

a replacement simulate_half_inning_from_pa_distribution.py,

or a full PR checklist with file diffs by step.

Follow-ups

How do I back up raw Retrosheet event files safely

What CSV columns to prioritize modifying for analysis

Should I version control generated CSV files

How to validate modified files against original Retrosheet data

Next steps after archiving and modifying CSV files for Pandas analysis

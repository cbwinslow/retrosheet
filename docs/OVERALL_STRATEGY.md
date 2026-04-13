# Real-Time Baseball Odds Strategy Supplement

## Purpose

This document is designed to supplement an existing baseball analytics and trading stack rather than replace it. It assumes there is already work in progress around Retrosheet, PostgreSQL, feature engineering, model development, MLB live data ingestion, and Polymarket market monitoring, and it focuses on how to make that stack more robust, modular, and production-oriented.[cite:1][cite:2][cite:6]

The core objective is to support a real-time odds calculator for plate appearances and downstream baseball outcomes, then compare fair probabilities against live market prices to detect actionable dislocations. Retrosheet provides historical event files and game logs for training data, while Polymarket provides developer APIs and market access patterns that can support live monitoring and execution workflows.[cite:11][cite:20]

## How To Use This

This strategy should be handed to an AI engineering agent with explicit instructions to preserve existing naming, schemas, services, and pipeline choices wherever they already work. The agent should treat the recommendations below as extension points, hardening steps, and architectural constraints rather than a greenfield rewrite.[cite:2][cite:6][cite:7]

The adaptation rule is simple: prefer reuse over replacement. If the current stack already has working views, materialized views, ingestion scripts, feature jobs, or model code, the agent should map the strategy onto those assets first, only introducing new components where there is a clear gap in latency, calibration, observability, or maintainability.[cite:2][cite:6]

## Existing Assumptions

The current project context already includes a Moneyball-style modeling goal, a plan to combine Retrosheet data with MLB live data and Polymarket outcomes, and a PostgreSQL-centered design with views and materialized views for easier analytics access.[cite:1][cite:2][cite:6]

The current environment also appears suitable for self-hosted experimentation and training, given the available Dell R720 server, 128 GB RAM, and GPU resources, which is enough for strong tabular modeling, simulation workloads, and modest real-time infrastructure if the design remains efficient.[cite:4]

## Strategic Principles

The stack should be designed around five principles: state fidelity, modularity, calibration, latency awareness, and risk discipline. Baseball prediction quality depends less on flashy model choice than on representing the exact game state correctly, calibrating probabilities honestly, and acting only when the executable edge exceeds the error bars introduced by latency and market frictions.[cite:2][cite:10][cite:12][cite:17]

The project should also separate modeling from trading logic. A good baseball model estimates probabilities; a good trading system decides whether those probabilities justify an action after slippage, fees, contract wording, and market depth are considered.[cite:17][cite:20]

## Recommended Architecture

The recommended architecture is a four-plane system: data plane, feature plane, model plane, and execution plane. This keeps historical warehousing, live state assembly, probabilistic scoring, and market decisioning decoupled enough to evolve independently while still sharing canonical identifiers and state definitions.[cite:2][cite:6][cite:10][cite:20]

A practical implementation should keep PostgreSQL as the canonical warehouse, add a hot-state cache for in-game state, and use event-driven workers for live updates. This preserves the value of the existing Postgres work while reducing the risk that heavy analytical SQL interferes with low-latency model serving.[cite:4][cite:6]

### Data plane

The data plane should continue to use Retrosheet as the historical event backbone, with raw preservation of downloaded files and deterministic parsing into structured tables. Retrosheet documents event files, game logs, and related research/database tooling, which makes it well-suited for reproducible historical backtesting and feature generation.[cite:11][cite:18]

The live portion of the data plane should ingest MLB game-state updates and Polymarket market data as append-only event streams. Raw payload retention matters because every model bug, edge claim, and trading decision should be replayable later against the exact data the system saw at that moment.[cite:2][cite:20]

### Feature plane

The feature plane should sit mostly inside PostgreSQL at first, especially if views and materialized views already exist. The first preference should be to extend current `stats` or similar schemas with feature views for count state, base-out state, lineup position, handedness, park factors, recent form, times-through-order, bullpen freshness, leverage proxies, and batter-pitcher matchup priors.[cite:2][cite:6]

For low-latency serving, the feature plane should expose a compact online feature object keyed by game, plate appearance, batter, pitcher, inning state, and market target. Only the subset needed to score the current event should be copied into Redis or another in-memory store; everything else can remain in Postgres.[cite:2][cite:6]

### Model plane

The model plane should use at least two linked model families. The first is a plate-appearance outcome model that estimates probabilities for outcomes such as strikeout, walk, hit-by-pitch, generic out, single, double, triple, home run, and optionally reach-on-error if the data pipeline supports it cleanly.[cite:7][cite:10][cite:12]

The second is a state-value layer that converts local outcome probabilities into market-relevant downstream probabilities. This is where run expectancy, win expectancy, Markov transitions, or Monte Carlo simulation should be used to move from "what happens this plate appearance" to "what is the fair price for this market right now."[cite:10][cite:16][cite:22]

### Execution plane

The execution plane should remain conservative. Polymarket developer documentation provides API and SDK access, and third-party documentation also shows real-time market and trade data access patterns, but tradable opportunity depends on executable prices and contract wording, not merely headline market odds.[cite:17][cite:20]

This layer should be responsible for probability-to-price conversion, edge calculation, liquidity checks, position sizing, stale-data detection, and audit logging. It should never contain hidden modeling assumptions; it should only consume model outputs and market inputs, then apply clear risk rules.[cite:17][cite:20]

## Canonical Stack Setup

The stack below is designed to align with an existing self-hosted build rather than force a managed-cloud rewrite.

| Layer | Preferred default | Adaptation rule |
|---|---|---|
| Historical warehouse | PostgreSQL | Reuse current schemas, tables, views, and materialized views first.[cite:6] |
| Raw ingest | Python scripts plus raw file retention | Preserve current import logic if deterministic and replayable.[cite:3][cite:6] |
| Live ingest | Async Python workers | Add consumers around existing code rather than replacing it wholesale.[cite:2] |
| Hot cache | Redis | Only introduce for truly latency-sensitive online features.[cite:2] |
| Messaging | Redis Streams, Redpanda, or Kafka | Start simple unless current throughput already justifies Kafka-class tooling.[cite:4] |
| Orchestration | Cron, systemd timers, Prefect, or Dagster | Match whatever is already stable in the environment.[cite:4] |
| Training | Python, scikit-learn, XGBoost/LightGBM/CatBoost | Keep current modeling code if outputs can be calibrated and versioned.[cite:12] |
| Bayesian/specialized modeling | PyMC or Stan-adjacent workflow | Add only where shrinkage clearly beats simpler pooled estimates.[cite:15] |
| Serving API | FastAPI | Wrap existing model code behind versioned inference endpoints if helpful.[cite:2] |
| Monitoring | Prometheus/Grafana style metrics | Integrate with current observability habits if already in use.[cite:4] |

## Schema Adaptation Guidance

The AI agent should not rename existing database objects unless there is a serious consistency issue. Instead, it should create an adaptation map showing how existing schemas and views correspond to the target layers described in this document, for example mapping current raw import tables to `raw`, normalized baseball entities to `core`, derived analytics to `stats`, and live-scoring artifacts to `serving`.[cite:6]

If such layers already exist informally, the agent should document them rather than migrate them immediately. The safest first step is a compatibility layer of views, helper SQL functions, and metadata tables that standardize access without breaking current queries or downstream notebooks.[cite:6][cite:7]

## Model Strategy

The recommended path is not to chase one perfect model. Instead, use a tiered modeling strategy with strong baselines, calibrated tabular models, and a state-transition layer that turns local predictions into market prices.[cite:10][cite:12][cite:16]

A robust plate-appearance stack should include the following sequence:

1. Build an interpretable baseline using historical frequencies conditioned on game state and broad player buckets.[cite:16]
2. Add a regularized multinomial or logistic baseline for PA outcomes.[cite:12]
3. Add a boosted-tree model for structured baseball features.[cite:12]
4. Calibrate all outputs by bucket and over time before any trading use.[cite:12]
5. Use Markov or Monte Carlo downstream valuation to price the market target.[cite:10][cite:16]

The baseline matters because it acts as a fault detector. If an advanced model starts producing implausible live probabilities, the system should fall back to a simpler calibrated model rather than continue with silent drift.[cite:10][cite:12]

## Feature Strategy

The AI agent should preserve any existing feature engineering work and classify it into three groups: static priors, rolling historical features, and live state features. That categorization makes it easier to identify what can be precomputed daily, what should refresh intra-day, and what must be assembled on every event tick.[cite:2][cite:6]

Priority feature groups should include batter skill, pitcher skill, matchup context, count and base-out state, game leverage, park and weather effects, lineup quality, bullpen freshness, and short-horizon form. Existing materialized views are especially valuable for rolling splits and historical priors, while live state should be injected just-in-time during inference.[cite:2][cite:6]

### Static priors

Static priors should include handedness, multi-year player talent estimates, park effects, and broad roster/role labels. These are slow-moving and should live in durable warehouse tables rather than being recomputed in real time.[cite:2][cite:6]

### Rolling historical features

Rolling features should include last 7, 14, and 30 day indicators where sample sizes are acceptable, as well as season-to-date and multi-season shrunk rates. Materialized views are a good fit here because they simplify consistent feature reuse across training, backtesting, and live scoring.[cite:2][cite:6]

### Live state features

Live features should include count, outs, base occupancy, inning, score differential, current pitcher pitch count, times through order, batter slot, bullpen usage, defensive replacements, and any immediately available live feed flags. These should be represented in a deterministic online feature object so the same state can be replayed offline.[cite:2][cite:7]

## Pricing Strategy

The system should explicitly separate probability modeling from fair-value pricing. The model estimates event probabilities, then a pricing module transforms those probabilities into implied odds for each supported market target.[cite:10][cite:20]

A minimal fair-price engine should compute at least three values for every target: model probability, market implied probability, and executable edge. Executable edge should account for spread, slippage, fees, stale-book risk, and a safety margin for model uncertainty.[cite:17][cite:20]

The decision rule should be conservative. If the edge is not larger than both a cost threshold and a calibration buffer, no action should be taken even if the raw model looks favorable.[cite:12][cite:17]

## Risk Strategy

The system should be designed under the assumption that false positives are more dangerous than missed opportunities. Thin liquidity, bad contract interpretation, live feed lag, and model overconfidence can all create the illusion of arbitrage where none exists.[cite:17][cite:20]

Required safeguards should include:

- Maximum position size by market type and by game.[cite:20]
- Maximum correlated exposure across related contracts.[cite:20]
- Automatic freeze when source data is stale beyond threshold.[cite:2]
- Automatic freeze when model output exits plausible bounds for a state.[cite:10][cite:12]
- Manual review mode for new market templates or changed contract wording.[cite:20]
- Full decision logs containing features, model version, market snapshot, and chosen action.[cite:2]

## Latency Strategy

Low latency matters, but determinism matters more. For this project, the better target is consistent low-latency processing with replayable audit trails rather than maximum theoretical speed.[cite:2][cite:17]

The serving path should therefore minimize heavyweight joins during a live event. Daily and pregame features should be precomputed, while the live worker only merges current game state with a compact set of preloaded priors before scoring and pricing.[cite:2][cite:6]

## AI Agent Instructions

The following rules should be given directly to any AI engineering agent working on this stack.

### Primary instruction

Adapt all recommendations in this strategy to the current project before introducing any new schema, service, or model. Reuse current PostgreSQL objects, materialized views, ingestion scripts, naming conventions, and local infrastructure unless a specific deficiency can be demonstrated in writing.[cite:2][cite:6]

### Required workflow

1. Inventory existing assets first: schemas, views, materialized views, raw ingestors, notebooks, model scripts, daemons, APIs, and market listeners.[cite:2][cite:6]
2. Produce an adaptation map from current assets to the target architecture in this document.[cite:6]
3. Preserve backward compatibility where possible by adding wrapper views, helper functions, or service adapters instead of rewrites.[cite:6]
4. Only propose replacement when the current component fails on one of these axes: correctness, latency, reproducibility, calibration, or maintainability.[cite:10][cite:12]
5. For every new component, specify why the existing stack cannot already satisfy the same need.[cite:2][cite:6]

### Deliverables expected from the agent

The AI agent should return:

- A current-state inventory.[cite:2][cite:6]
- A gap analysis against this strategy.[cite:2][cite:6]
- A phased implementation plan preserving existing work.[cite:2]
- Proposed schema additions only where necessary.[cite:6]
- Proposed feature additions categorized by static, rolling, and live classes.[cite:2]
- Model and calibration plan tied to supported markets.[cite:10][cite:12]
- Risk controls and observability plan.[cite:17][cite:20]

## Phased Implementation Plan

### Phase 1: Standardize without rewriting

The first phase should document the current system and normalize access patterns. The main goal is to make existing work easier to reason about, not to replace it.[cite:2][cite:6]

Tasks in this phase should include creating a data dictionary, standardizing IDs across baseball and market data, documenting feature provenance, and identifying the current inference path from raw event to model output. If necessary, add compatibility views and model metadata tables, but keep core production logic intact.[cite:2][cite:6]

### Phase 2: Harden the feature layer

The second phase should focus on reliability and reproducibility of the current feature store. Materialized views should be reviewed for freshness, recomputation cost, indexing, and training-serving consistency, while online features should be reduced to a compact serving contract.[cite:2][cite:6]

The key output of this phase is a canonical feature interface that both training jobs and live scoring code can consume with minimal divergence. That interface matters more than whether the feature values originate in SQL, Python, or mixed workflows.[cite:2]

### Phase 3: Improve model calibration

The third phase should compare current model outputs against simple baselines and bucketed calibration diagnostics. The system should not move toward automated execution until the plate-appearance probabilities behave sensibly across count states, handedness splits, leverage buckets, and roster quality tiers.[cite:10][cite:12]

This phase should also create a model registry table that stores training window, target definition, feature set hash, calibration method, and validation metrics. That is essential for debugging edge claims later.[cite:12]

### Phase 4: Add market coupling

The fourth phase should integrate model outputs with live Polymarket data through a dedicated pricing and decision layer. Contract definitions should be stored explicitly so the system knows exactly how each baseball state maps to each market resolution rule.[cite:20]

At this point, the stack should compute model probability, executable market probability, edge after costs, and risk-adjusted action recommendation. Human review mode should remain the default until live replay and paper-trading results are convincing.[cite:17][cite:20]

### Phase 5: Paper trade and audit

The fifth phase should paper trade against archived and live markets before any real execution. This is necessary because a model that predicts baseball well may still fail as a market strategy if the market prices already embed the same information faster.[cite:12][cite:17]

Every paper-trade decision should be replayable from raw state, feature snapshot, model version, and market snapshot. If that audit trail does not exist, the system is not yet production-ready.[cite:2][cite:20]

## Suggested Repository Organization

The repository should be organized to reflect current assets first and target capabilities second. The important thing is not the exact folder names but the separation of concerns.

```text
project/
  docs/
    strategy/
    data-dictionary/
  sql/
    raw/
    core/
    stats/
    serving/
  ingest/
    retrosheet/
    mlb_live/
    polymarket/
  features/
    offline/
    online/
  models/
    pa_outcomes/
    state_value/
    calibration/
  services/
    scorer/
    pricer/
    risk/
  notebooks/
  tests/
```

If the current repository already has a working structure, the AI agent should preserve it and only add missing directories where the current organization is creating confusion or duplication.[cite:2][cite:6]

## Concrete Supplement Rules

To ensure this document supplements existing work rather than conflicts with it, the following non-negotiable adaptation rules should apply:

- Do not replace current Postgres schemas merely for stylistic consistency.[cite:6]
- Do not rewrite working ingestion code unless determinism or replayability is broken.[cite:3][cite:6]
- Do not swap model families simply because a newer algorithm exists; require measured improvement.[cite:12]
- Do not add distributed systems complexity before current throughput and latency justify it.[cite:4]
- Do not automate trade execution before calibration, replay, and paper-trading evidence are strong.[cite:12][cite:17]
- Do not treat quoted market price as executable edge without depth and slippage analysis.[cite:17][cite:20]

## Immediate Next Actions

The highest-value next step is to have the AI agent produce a current-state inventory and adaptation map. That gives a clean bridge between the work already underway and the strategy in this document without forcing premature rewrites.[cite:2][cite:6]

After that, the next best move is to define one narrow production target such as a single plate-appearance market, then align warehouse objects, live features, model outputs, pricing rules, and logging around that target end to end. Narrow scope will expose integration gaps faster than broad architecture planning alone.[cite:7][cite:10]

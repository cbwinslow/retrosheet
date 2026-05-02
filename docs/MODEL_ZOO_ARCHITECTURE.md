# Model Zoo Architecture
## Comprehensive Prediction System for All Baseball Abstraction Layers

**Version:** 1.0  
**Date:** 2026-05-01  
**Purpose:** Train, register, and serve 50+ models across all layers of baseball data

---

## Architecture Philosophy

> "If there's data to predict it, we should have a model for it."

**Principles:**
1. **No Pigeon-Holing**: Models aren't limited to specific feature sets
2. **Brute Force First**: Train many models, evaluate later, keep the best
3. **Layer-Agnostic**: Predictions at ANY level where data exists
4. **Player-Specific When Feasible**: Use materialized views for efficiency
5. **Database-Native**: Models stored in MLflow-style registry

---

## The 8 Layers of Abstraction

Not 5 - we expand to capture ALL predictable contexts:

```
Layer 1: League/Season (Macro)
  → "Will HRs be up or down this season?"
  
Layer 2: Team/Organization (Meso)
  → "Will the Tigers win 90 games this year?"
  
Layer 3: Game/Match (Event)
  → "Who wins today's game? What's the final score?"
  
Layer 4: Inning/Frame (Context)
  → "How many runs this inning? Will they score?"
  
Layer 5: Plate Appearance (PA)
  → "K, BB, or hit? HR probability?"
  
Layer 6: At-Bat/Count (State)
  → "Next pitch type? Count progression?"
  
Layer 7: Pitch (Micro)
  → "Swing? Contact? Fair ball? Location?"
  
Layer 8: Player/Historical (Career)
  → "When's Harper's next milestone? Career trajectory?"
```

---

## Model Taxonomy (The Zoo)

### By Layer

| Layer | Model Count | Example Predictions |
|-------|-------------|---------------------|
| L1 League | 5 | Season HR rate, scoring environment, playoff odds |
| L2 Team | 10 | Win total, playoff probability, streak length |
| L3 Game | 15 | Winner, total runs, spread, momentum shifts |
| L4 Inning | 8 | Runs this inning, batting around, pitcher change |
| L5 PA | 20 | Outcome distribution, is_walk, is_hr, pitch count |
| L6 Count | 15 | Next pitch type, balls/strikes, count progression |
| L7 Pitch | 12 | Swing, contact, fair, exit velo, launch angle |
| L8 Player | 25 | Next milestone, career WAR, injury risk, aging |
| **Total** | **110+** | Every conceivable baseball prediction |

### By Prediction Target

#### **Pitch-Level Models (L7)**
- `pitch_swing_probability` - Will batter swing?
- `pitch_contact_probability` - If swing, contact?
- `pitch_fair_probability` - Contact → fair ball?
- `pitch_location_x` - Horizontal location prediction
- `pitch_location_z` - Vertical location prediction
- `pitch_velocity_prediction` - Pitch speed
- `pitch_spin_prediction` - Spin rate
- `pitch_type_classifier` - FF/SL/CU/CH/etc
- `pitch_outcome_full` - Complete outcome (swing/contact/fair/result)

#### **Count-Level Models (L6)**
- `count_next_state` - Markov transition (0-0 → 0-1, 1-0, etc)
- `count_final_outcome` - Given current count, PA outcome
- `count_pitches_remaining` - How many pitches until resolution?
- `count_walk_probability` - P(BB | current count)
- `count_strikeout_probability` - P(K | current count)

#### **PA-Level Models (L5)**
- `pa_outcome_distribution` - Full multinomial (K, BB, 1B, 2B, 3B, HR, Out)
- `pa_is_home_run` - Binary HR prediction
- `pa_is_strikeout` - Binary K prediction
- `pa_is_walk` - Binary BB prediction
- `pa_is_hit` - Binary hit prediction
- `pa_total_bases` - Expected total bases
- `pa_pitch_count` - How many pitches in this PA?
- `pa_runs_created` - Linear weights runs created
- `pa_milestone_hit` - Is this a career milestone? (500th HR, etc)

#### **Inning-Level Models (L4)**
- `inning_runs_scored` - How many runs this inning?
- `inning_batting_around` - Will they bat around?
- `inning_pitcher_change` - Pitcher change this inning?
- `inning_big_inning` - 3+ runs scored?
- `inning_lead_change` - Will lead change?

#### **Game-Level Models (L3)**
- `game_winner` - Home or away team wins
- `game_total_runs` - Combined score O/U
- `game_spread` - Margin of victory
- `game_first_inning_runs` - YRFI/NRFI
- `game_comeback` - Will trailing team come back?
- `game_shutout` - Will game be shutout?
- `game_extra_innings` - Goes to extras?
- `game_momentum_shift` - Next scoring play affects momentum?

#### **Team-Level Models (L2)**
- `team_season_wins` - Total wins this season
- `team_playoff_probability` - Make playoffs?
- `team_division_winner` - Win division?
- `team_world_series_probability` - Win WS?
- `team_streak_length` - How long will current streak last?
- `team_run_differential` - Season run diff
- `team_momentum_next_10` - Win % next 10 games

#### **League-Level Models (L1)**
- `league_scoring_environment` - Runs per game trend
- `league_hr_rate_trend` - HR environment
- `league_k_rate_trend` - Strikeout trend
- `league_playoff_picture` - Which teams make playoffs

#### **Player-Level Models (L8) - Player-Specific**

**Generic (all players):**
- `player_next_pa_outcome` - Generic player model
- `player_season_war_projection` - Season WAR
- `player_injury_risk` - Injury probability

**Star-Player Specific (materialized views):**
- `harper_next_pa_hr_probability`
- `harper_vs_rhp_slg_prediction`
- `harper_career_600_hr_probability`
- `ohtani_steal_probability`
- `judge_vs_fastball_exit_velo`
- [One model per star player per prediction type]

**Career Trajectory:**
- `career_milestone_probability` - Next milestone (3000 hits, 500 HR, etc)
- `career_hall_of_fame_probability` - HOF odds
- `career_peak_age_prediction` - When will they peak?
- `career_retirement_age_prediction` - Retirement year

---

## Model Implementation Matrix

### Architectures by Use Case

| Prediction Type | Architectures | Training Data | Latency Target |
|---------------|---------------|---------------|----------------|
| Pitch-level | XGBoost, LSTM, Neural Net | 5M pitches | <100ms |
| Count-level | Markov Chain, XGBoost | 2M PAs | <50ms |
| PA-level | XGBoost, Random Forest, Neural Net | 3M PAs | <200ms |
| Inning-level | Monte Carlo, XGBoost | 500K innings | <500ms |
| Game-level | Monte Carlo, Ensemble | 50K games | <1s |
| Team-level | Time Series (ARIMA, Prophet), XGBoost | 30 seasons | <2s |
| League-level | Time Series, Regression | 150 seasons | <2s |
| Player-level | Survival Analysis, XGBoost, Neural Net | Career data | <5s |

---

## Model Registry Schema

### Database Tables

```sql
-- Model Registry
CREATE TABLE models.registry (
    model_id UUID PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    
    -- Classification
    layer VARCHAR(20),  -- 'pitch', 'count', 'pa', 'game', 'team', 'league', 'player'
    prediction_target VARCHAR(50),  -- 'swing', 'outcome', 'winner', etc
    architecture VARCHAR(50),  -- 'xgboost', 'lstm', 'markov', etc
    
    -- Scope
    is_generic BOOLEAN,  -- True = works for any player/team
    player_id VARCHAR(20),  -- NULL if generic
    team_id VARCHAR(20),  -- NULL if generic
    
    -- Performance
    accuracy DECIMAL(5,4),
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    rmse DECIMAL(8,4),  -- For regression
    mae DECIMAL(8,4),   -- For regression
    log_loss DECIMAL(8,4),  -- For classification
    
    -- Training info
    training_data_start DATE,
    training_data_end DATE,
    training_samples INTEGER,
    training_duration_seconds INTEGER,
    
    -- Features
    feature_count INTEGER,
    feature_list TEXT[],  -- Array of feature names
    feature_importance JSONB,  -- {feature: importance_score}
    
    -- Model artifact
    model_binary BYTEA,  -- Serialized model
    model_framework VARCHAR(20),  -- 'sklearn', 'pytorch', 'xgboost', 'custom'
    model_size_bytes INTEGER,
    
    -- Status
    status VARCHAR(20),  -- 'training', 'active', 'deprecated', 'failed'
    is_production BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    trained_by VARCHAR(50),
    training_config JSONB,  -- Hyperparameters, etc
    
    -- Constraints
    UNIQUE(model_name, model_version)
);

-- Model Performance History
CREATE TABLE models.performance_history (
    history_id BIGSERIAL PRIMARY KEY,
    model_id UUID REFERENCES models.registry(model_id),
    evaluation_date DATE,
    
    -- Metrics on hold-out set
    accuracy DECIMAL(5,4),
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    rmse DECIMAL(8,4),
    mae DECIMAL(8,4),
    
    -- Test set info
    test_samples INTEGER,
    test_date_start DATE,
    test_date_end DATE,
    
    -- Overfitting check
    train_accuracy DECIMAL(5,4),
    test_accuracy DECIMAL(5,4),
    overfit_gap DECIMAL(5,4),  -- train - test
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Model Predictions Log (for tracking accuracy over time)
CREATE TABLE models.prediction_log (
    log_id BIGSERIAL PRIMARY KEY,
    model_id UUID REFERENCES models.registry(model_id),
    
    -- Input
    input_features JSONB,
    input_hash VARCHAR(64),  -- Hash for deduplication
    
    -- Prediction
    prediction JSONB,  -- Can be scalar, vector, or distribution
    prediction_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Actual outcome (populated later)
    actual_outcome JSONB,
    outcome_timestamp TIMESTAMP,
    
    -- Performance
    was_correct BOOLEAN,
    error DECIMAL(8,4),  -- For regression
    log_likelihood DECIMAL(8,4),  -- For classification
    
    -- Context
    game_pk INTEGER,
    pa_id VARCHAR,
    pitch_id BIGINT
);

-- Model Selection Rules
CREATE TABLE models.selection_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100),
    
    -- When to use this model
    query_pattern VARCHAR(200),  -- Regex pattern on query
    required_layer VARCHAR(20),
    required_target VARCHAR(50),
    
    -- Selection criteria
    min_accuracy DECIMAL(5,4),
    max_latency_ms INTEGER,
    prefer_generic BOOLEAN,  -- Generic vs player-specific
    
    -- Ranking
    priority INTEGER,  -- 1 = highest priority
    
    -- Model selection
    selected_model_id UUID REFERENCES models.registry(model_id),
    fallback_model_id UUID REFERENCES models.registry(model_id),
    
    -- Ensemble
    ensemble_model_ids UUID[],  -- Multiple models to ensemble
    ensemble_weights DECIMAL(5,4)[],  -- Weights for ensemble
    
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Training Pipeline Architecture

### Pipeline Stages

```
1. Data Preparation
   └── Extract features from all 8 layers
   └── Create materialized views for star players
   └── Time-based train/validation/test split
   
2. Feature Engineering
   └── Generate 500+ raw features
   └── Feature selection (keep top 200)
   └── Cross-validation folds
   
3. Model Training (Parallel)
   └── For each (layer, target) combination:
       └── Train 5 architectures:
           ├── XGBoost (baseline)
           ├── Random Forest
           ├── Neural Network
           ├── LSTM (for sequences)
           └── Markov Chain (for states)
       
4. Evaluation
   └── Hold-out test set evaluation
   └── Overfitting detection (train vs test gap)
   └── Backtesting on historical seasons
   
5. Registration
   └── Serialize to database
   └── Log performance metrics
   └── Set production flag (top performer only)
   
6. Materialized Views
   └── Refresh player-specific predictions
   └── Pre-compute common queries
```

### Training Configuration Example

```yaml
# training_config.yaml
layers:
  pitch:
    targets:
      - swing_probability
      - contact_probability
      - pitch_type
    architectures:
      - xgboost
      - lstm
      - neural_net
    sample_size: 5000000
    training_frequency: daily
    
  pa:
    targets:
      - outcome_distribution
      - is_home_run
      - is_strikeout
    architectures:
      - xgboost
      - random_forest
    sample_size: 3000000
    training_frequency: daily
    
  player:
    targets:
      - next_milestone
      - career_trajectory
    player_specific: true
    star_players_only: false  # Set true if performance issues
    architectures:
      - xgboost
      - survival_analysis
    training_frequency: weekly

overfitting_protection:
  max_train_test_gap: 0.05  # 5% accuracy gap max
  min_test_samples: 10000
  cross_validation_folds: 5
  
performance_thresholds:
  min_accuracy: 0.60
  min_f1: 0.50
  max_latency_ms: 5000
```

---

## Natural Language Query Routing

### Query → Model Mapping

```python
# Example routing logic
QUERY_PATTERNS = {
    # Pitch-level
    r"next pitch.*type|what.*pitch": {
        "layer": "count",
        "target": "pitch_type",
        "models": ["count_pitch_type_classifier"]
    },
    
    r"swing|will.*swing": {
        "layer": "pitch",
        "target": "swing",
        "models": ["pitch_swing_probability"]
    },
    
    # PA-level
    r"home run|HR|homer": {
        "layer": "pa",
        "target": "is_home_run",
        "models": ["pa_is_home_run", "pa_outcome_distribution"]
    },
    
    r"strikeout|K|whiff": {
        "layer": "pa",
        "target": "is_strikeout",
        "models": ["pa_is_strikeout", "pa_outcome_distribution"]
    },
    
    r"walk|BB|base on balls": {
        "layer": "pa",
        "target": "is_walk",
        "models": ["pa_is_walk"]
    },
    
    r"hit|single|double": {
        "layer": "pa",
        "target": "is_hit",
        "models": ["pa_is_hit", "pa_outcome_distribution"]
    },
    
    # Game-level
    r"win|who.*win|winner": {
        "layer": "game",
        "target": "winner",
        "models": ["game_winner", "game_monte_carlo"]
    },
    
    r"total|over under|runs": {
        "layer": "game",
        "target": "total_runs",
        "models": ["game_total_runs"]
    },
    
    # Historical/Pattern
    r"first time|since|last.*when": {
        "layer": "historical",
        "target": "pattern_match",
        "models": ["historical_pattern_database", "sql_query"]
    },
    
    # Career/Milestone
    r"milestone|500.*hr|3000.*hit|hall of fame|hof": {
        "layer": "player",
        "target": "milestone",
        "models": ["career_milestone_probability"]
    }
}
```

---

## Materialized Views for Efficiency

### Player-Specific Predictions

```sql
-- Materialized view: Star player next PA predictions
CREATE MATERIALIZED VIEW mv_star_player_predictions AS
SELECT 
    p.player_id,
    p.player_name,
    
    -- Current context
    t.team_name,
    opp.team_name as opponent,
    
    -- Model predictions
    m1.prediction as hr_probability,
    m2.prediction as k_probability,
    m3.prediction as hit_probability,
    m4.prediction as outcome_distribution,
    
    -- Historical context
    h.career_hr,
    h.career_hr / NULLIF(h.career_pa, 0) as career_hr_rate,
    
    -- Hot/cold
    r.last_30_pa,
    r.trend_direction

FROM players.star_players p
JOIN predictions.team_context_rolling t ON p.current_team_id = t.team_id
JOIN predictions.team_context_rolling opp ON p.next_opponent_id = opp.team_id

-- Model predictions (LATEST ONLY)
JOIN LATERAL (
    SELECT prediction 
    FROM models.get_prediction('pa_is_home_run', p.player_id)
    ORDER BY prediction_timestamp DESC LIMIT 1
) m1 ON true

JOIN LATERAL (
    SELECT prediction 
    FROM models.get_prediction('pa_is_strikeout', p.player_id)
    ORDER BY prediction_timestamp DESC LIMIT 1
) m2 ON true

JOIN LATERAL (
    SELECT prediction 
    FROM models.get_prediction('pa_is_hit', p.player_id)
    ORDER BY prediction_timestamp DESC LIMIT 1
) m3 ON true

JOIN LATERAL (
    SELECT prediction 
    FROM models.get_prediction('pa_outcome_distribution', p.player_id)
    ORDER BY prediction_timestamp DESC LIMIT 1
) m4 ON true

LEFT JOIN predictions.matchup_history h ON p.player_id = h.batter_id
LEFT JOIN predictions.batter_profiles_rolling r ON p.player_id = r.batter_id

WHERE p.is_star = true
  AND t.as_of_date = CURRENT_DATE - 1
  AND r.as_of_date = CURRENT_DATE - 1;

-- Refresh every hour during season
CREATE INDEX idx_mv_star_player ON mv_star_player_predictions(player_id);
```

---

## Usage Examples

### Example 1: Simple Prediction
```python
from baseball.models import ModelZoo

zoo = ModelZoo()

# Get all predictions for current PA
predictions = zoo.predict(
    layer="pa",
    context={
        "pitcher_id": "scherzer_max",
        "batter_id": "harper_bryce",
        "count": "2-2",
        "inning": 9,
        "outs": 2
    }
)

# Returns dict of all models
print(predictions['pa_is_home_run'])  # 0.085
print(predictions['pa_is_strikeout'])  # 0.320
print(predictions['pa_outcome_distribution'])  # {K: 0.32, BB: 0.08, 1B: 0.15, ...}
```

### Example 2: Natural Language
```python
from baseball.models import NLQueryEngine

engine = NLQueryEngine()

response = engine.query(
    "Bottom 9th, 2-2 count, Scherzer vs Harper - HR chance?"
)

# Response:
# {
#   "query_type": "pa_is_home_run",
#   "models_used": ["pa_is_home_run_xgboost", "pa_outcome_distribution"],
#   "prediction": 0.085,
#   "confidence": 0.72,
#   "factors": {
#     "league_hr_rate": 0.034,
#     "harper_vs_fastball_slg": 0.620,
#     "scherzer_2_2_fb_pct": 0.40,
#     "matchup_hr_rate": 0.095
#   },
#   "historical_context": "Harper has 2 HR in 21 career PAs vs Scherzer",
#   "similar_situations": 45,
#   "model_accuracy": 0.68
# }
```

### Example 3: Historical Pattern
```python
response = engine.query(
    "When's the last time a Tiger under 25 hit back-to-back doubles?"
)

# Response:
# {
#   "query_type": "historical_pattern",
#   "result": {
#     "found": true,
#     "player": "Spencer Torkelson",
#     "date": "2024-06-15",
#     "opponent": "CLE",
#     "inning": 3,
#     "previous_occurrence": "Justin Verlander (actually a pitcher!), 2019-08-22"
#   },
#   "sql_query": "SELECT ...",  # Generated SQL
#   "execution_time_ms": 1200
# }
```

---

## Overfitting Protection

### Checks in Training Pipeline

1. **Time-Based Splits**
   ```python
   train: 2015-2021
   validation: 2022-2023
   test: 2024
   ```

2. **Gap Monitoring**
   ```python
   train_accuracy = 0.85
   test_accuracy = 0.78
   gap = 0.07  # Alert if > 0.05
   ```

3. **Regularization**
   - XGBoost: `max_depth=6`, `reg_alpha=0.1`, `reg_lambda=1.0`
   - Neural Net: Dropout=0.3, L2 regularization
   - Random Forest: `max_depth=10`, `min_samples_leaf=50`

4. **Cross-Validation**
   - 5-fold time-series CV
   - No random shuffling (preserves temporal order)

5. **Backtesting**
   - Run models on 2020-2023 seasons
   - Compare to actual outcomes
   - Track ROI if used for betting

---

## Next Steps

1. **Create Model Registry Schema** (SQL tables above)
2. **Implement Training Pipeline** (Python scripts)
3. **Build First Batch of Models** (Pitch + PA layers first)
4. **Create NL Query Router**
5. **Set up Materialized Views** (Star player predictions)
6. **Test with Live Data**

---

**Related Documents:**
- `docs/HIERARCHICAL_PREDICTION_SYSTEM.md` - Original 5-layer architecture
- `docs/HPS_DATA_DICTIONARY.md` - 130+ available features
- `sql/60_models/6005_hierarchical_prediction_schema.sql` - Database schema
- `docs/STATCAST_MODELS_RESEARCH_REPORT.md` - Research-backed architectures

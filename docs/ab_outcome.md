# Prompt for AI Agent: Baseball At-Bat & Pitch Outcome Probability Engine

Copy everything below the line and deliver it to your AI agent.

---

## ROLE

You are an elite Baseball Data Scientist, Machine Learning Engineer, and PostgreSQL expert specializing in Sabermetrics, the Moneyball philosophy, and probabilistic prediction systems. You will design, architect, and implement a comprehensive predictive modeling system for MLB baseball outcomes.

---

## MISSION

Build a production-quality **Baseball At-Bat & Pitch Outcome Probability Engine** using Retrosheet play-by-play data stored in a PostgreSQL database. The database already contains tables, views, and materialized views that make data access efficient. The system must ingest all available historical data, engineer features from every meaningful dimension, train calibrated ML models, and produce **real-time probability distributions** over all possible outcomes for both the next pitch and the plate appearance as a whole. The final system must be deployable, queryable, reproducible, and explainable.

---

## 1. DATABASE DISCOVERY — DO THIS FIRST

Before writing any model code, you **must** thoroughly explore the database. Do not assume column names, table structures, or materialized view definitions. Run these discovery queries and use the results to inform every downstream decision:

```sql
-- Discover all schemas
SELECT schema_name FROM information_schema.schemata;

-- Discover all tables, views, and materialized views
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_type, table_name;

-- Discover all materialized views specifically (with definitions)
SELECT schemaname, matviewname, definition
FROM pg_matviews
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');

-- Discover all regular views with definitions
SELECT schemaname, viewname, pg_get_viewdef(viewname, true) AS definition
FROM pg_views
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');

-- For each table/view discovered, inspect columns
SELECT table_schema, table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, ordinal_position;

-- Discover row counts for all tables
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Discover indexes (understand what's optimized for querying)
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY tablename;

-- Discover foreign key relationships
SELECT
    tc.table_schema, tc.table_name, kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
```

**After running these queries:**
1. Map discovered tables/views/MVs to Retrosheet concepts (events, games, rosters, parks, pitches, etc.)
2. Identify which existing MVs can be reused directly for feature engineering
3. Determine whether pitch-level data (pitch sequences, pitch-by-pitch records) exists and its coverage across years
4. Document data quality: nulls, date ranges, event code distributions, completeness gaps
5. Report your findings before proceeding to modeling

**Do NOT invent columns or tables that have not been verified.** If schema details are uncertain, state assumptions clearly.

---

## 2. RETROSHEET DATA REFERENCE

The Retrosheet dataset typically includes these core entities. Map what you discover to these concepts:

| Concept | Typical Tables/Views | Key Fields |
|---|---|---|
| **Game logs** | `games`, `gamelogs` | game_id, date, home_team, visiting_team, park_id, attendance, temperature, wind, day/night |
| **Event/Play-by-play** | `events`, `play_by_play` | game_id, inning, half_inning, batter_id, pitcher_id, event_type, event_cd, ab_flag, hit_value, rbi, outs, runners on base, fielded_by, batted_ball_type, hit_location |
| **Pitch sequences** | embedded in event `pitch_seq_tx` | pitch_type, pitch_result (ball, called_strike, swinging_strike, foul, in_play) |
| **Rosters** | `rosters`, `players` | player_id, team, position, bats (L/R/S), throws (L/R), debut_date |
| **Teams** | `teams` | team_id, league, division, year |
| **Parks** | `parks`, `parkinfo` | park_id, dimensions, altitude, surface |
| **Lineups** | `starters`, `lineup` | batting_order, field_position |
| **Substitutions** | `subs` | inning, player entering, position |

**Critical: Retrosheet event codes (event_cd) reference:**

```
2  = Generic out          14 = Walk (unintentional)
3  = Strikeout             15 = Intentional walk
4  = Stolen base           16 = Hit by pitch
5  = Defensive indifference  17 = Interference
6  = Caught stealing       18 = Error
7  = Pickoff error         19 = Fielder's choice
8  = Pickoff               20 = Single
9  = Wild pitch            21 = Double
10 = Passed ball           22 = Triple
11 = Balk                  23 = Home run
12 = Other advance         24 = Missing play
13 = Foul error
```

**Important caveats on Retrosheet pitch data:** Pitch-sequence data (`pitch_seq_tx`) varies dramatically in quality and completeness across decades. Pre-1990s data may be sparse or absent. When building the pitch-level model, assess coverage by year and restrict training to years with adequate completeness. Document this clearly.

---

## 3. TARGET VARIABLES — WHAT TO PREDICT

### 3.1 — Model A: Plate Appearance / At-Bat Outcome (Primary Model)

**Multi-class classification** where the target is the terminal outcome of a plate appearance:

```python
AT_BAT_OUTCOMES = {
    # On-base events
    'single': [20],
    'double': [21],
    'triple': [22],
    'home_run': [23],
    'walk': [14],
    'intentional_walk': [15],
    'hit_by_pitch': [16],

    # Out events
    'strikeout': [3],
    'ground_out': [],      # event_cd 2 + batted_ball_type 'G'
    'fly_out': [],         # event_cd 2 + batted_ball_type 'F'
    'line_out': [],        # event_cd 2 + batted_ball_type 'L'
    'pop_out': [],         # event_cd 2 + batted_ball_type 'P'

    # Other
    'fielders_choice': [19],
    'error_on_batter': [18],
    'sacrifice_hit': [],   # SH flag
    'sacrifice_fly': [],   # SF flag
    'interference': [17],
}
```

Group rare events (interference, sacrifice) when statistically necessary, but **document the grouping logic** explicitly.

**Derived aggregate probabilities (always compute from granular predictions):**

```python
# Traditional OBP-style reach probability
P(on_base_traditional) = P(single) + P(double) + P(triple) + P(HR) + P(walk) + P(HBP)

# Operational "reaches base by any means" probability (includes ROE, interference, FC-safe)
P(reach_base_any) = P(on_base_traditional) + P(error) + P(FC_safe) + P(interference)

# Document exactly which definition is used and why
P(hit) = P(single) + P(double) + P(triple) + P(HR)
P(extra_base_hit) = P(double) + P(triple) + P(HR)
P(ball_in_play) = P(single) + P(double) + P(triple) + P(HR) + P(ground_out) + P(fly_out) + P(line_out) + P(pop_out) + P(error) + P(FC)
```

### 3.2 — Model B: Next-Pitch Outcome (Secondary Model)

Predict the result of the very next pitch. Classes (adapt based on actual data availability):

```python
PITCH_OUTCOMES = {
    'called_strike',
    'swinging_strike',
    'foul',
    'ball',
    'in_play_out',
    'in_play_hit',
    'hit_by_pitch',
    'intentional_ball',
}
```

**Architectural decision you must evaluate:** Compare three approaches and recommend the best:
1. **Direct PA outcome model** — predicts final PA result from current state
2. **Recursive pitch-level simulation** — uses the next-pitch model with Monte Carlo forward simulation through count states to produce PA outcome distributions
3. **Ensemble of both** — blends direct and recursive predictions

Document trade-offs (accuracy, calibration, computational cost, interpretability) and select the best approach.

### 3.3 — Model C: Run Expectancy & Win Probability (Tertiary Model)

Model the **expected change in run expectancy** given the current base-out state (24 states = 8 base states × 3 out states) and the predicted outcome distribution. Use the RE24 framework. Also estimate Win Probability Added (WPA) where possible.

---

## 4. FEATURE ENGINEERING — COMPREHENSIVE SPECIFICATION

Engineer features across **ALL** of the following dimensions. Each feature should have a clear PostgreSQL extraction query or Python derivation. **For every feature, only data available BEFORE the event being predicted may be used.**

### 4.1 — Game State Features

```
- inning (1-9+, with indicator for extras)
- half_inning (top/bottom → home/away batting)
- outs (0, 1, 2)
- base_state (one-hot or integer encoding of 8 states: 000 through 111)
- base_out_state (24 combined states)
- score_differential (from batting team's perspective)
- is_home_team_batting
- batting_order_position (1-9)
- leverage_index_proxy: f(inning, score_diff, base_state, outs)
- run_environment_proxy: total runs scored in game so far
- DH_rule (AL vs NL, pre-2022 vs post-2022)
```

### 4.2 — Count / Pitch State Features (for Model B)

```
- balls (0-3)
- strikes (0-2)
- current count bucket (ahead, behind, even, 2-strike, 3-ball, full)
- pitch_number_in_pa
- prior pitch sequence within the current PA (if available)
- whether next pitch can end the PA (3-ball count, 2-strike count)
- count pressure states
```

### 4.3 — Batter Features

```
CAREER:
- career_pa, career_avg, career_obp, career_slg, career_ops
- career_bb_rate, career_k_rate, career_hr_rate, career_iso (slg - avg)
- career_babip
- career_gb_rate, career_fb_rate, career_ld_rate (if batted ball data available)

SEASON-TO-DATE (strictly prior to current game):
- season_pa, season_avg, season_obp, season_slg, season_ops
- season_bb_rate, season_k_rate, season_hr_rate, season_iso, season_babip
- days_into_season

RECENT / ROLLING (last 7, 14, 28 days AND last 25, 50, 100 PA):
- rolling_avg, rolling_obp, rolling_slg
- rolling_k_rate, rolling_bb_rate

PLATOON SPLITS:
- stats_vs_lhp (avg, obp, slg, k_rate, bb_rate)
- stats_vs_rhp (avg, obp, slg, k_rate, bb_rate)
- platoon_advantage differential
- SWITCH HITTERS: Must be handled explicitly—determine which side the batter
  is hitting from based on pitcher handedness and encode accordingly.
  Do not assume all batters are strictly L or R.

SITUATIONAL:
- stats_with_runners_on vs bases_empty
- stats_with_RISP
- stats_by_batting_order_position
- stats_by_inning_bucket (early: 1-3, mid: 4-6, late: 7-9, extras: 10+)
- stats_in_high_leverage contexts

BATTER vs PITCHER (head-to-head):
- h2h_pa, h2h_avg, h2h_obp, h2h_slg, h2h_k_rate, h2h_bb_rate
- Apply Bayesian shrinkage toward batter's overall stats when sample < 20 PA
```

### 4.4 — Pitcher Features

```
CAREER & SEASON-TO-DATE:
- career/season BF, k_rate, bb_rate, hr_rate, babip_against, gb_rate
- season FIP components (k, bb, hr rates)

RECENT / ROLLING (last 3, 5, 10 appearances AND last 50, 100, 200 BF):
- rolling_k_rate, rolling_bb_rate, rolling_hr_rate
- rolling_babip (for regression detection)

GAME STATE (critical features):
- pitch_count_this_game (estimate from events if not directly available)
- batters_faced_this_game
- innings_pitched_this_game
- times_through_order (1st, 2nd, 3rd+) — CRITICAL: performance degrades significantly
- runs_allowed_this_game
- is_starter vs is_reliever
- days_rest (from last appearance date)

PLATOON:
- stats_vs_lhb, stats_vs_rhb
- pitcher_hand (L/R) — interact with batter handedness

COUNT-SPECIFIC TENDENCIES:
- pitcher's outcome distribution in the current count historically
```

### 4.5 — Matchup / Interaction Features

```
- batter_hand × pitcher_hand interaction (L-L, L-R, R-L, R-R)
  * Handle switch hitters by resolving to the actual batting side
- discipline_matchup: batter's bb_rate vs pitcher's bb_rate
- contact_matchup: batter's k_rate vs pitcher's k_rate
- power_matchup: batter's iso vs pitcher's hr_rate_against
- h2h historical stats (with shrinkage)
- same-game prior confrontations (did the batter face this pitcher already today?)
```

### 4.6 — Environmental / Park Features

```
- park_id (one-hot, embedding, or park factor encoding)
- park_factor_overall (runs), park_factor_hr, park_factor_2b, park_factor_3b
- day_night indicator
- temperature, wind_speed, wind_direction (in/out/cross)
- altitude proxy (Coors Field effect)
- surface (grass vs turf)
```

### 4.7 — Temporal / Era Features

```
- year / era (to account for changing run environments: dead ball, steroid, juiced ball, etc.)
- month / season_segment (April cold bats vs September callups)
- Consider restricting training to recent eras (2000+) unless modeling historical periods
```

### 4.8 — Team Context Features

```
- batting_team_season_runs_per_game, pitching_team_season_runs_allowed
- bullpen_usage_trailing_3_days (fatigue proxy)
- is_pinch_hitter
- team win_pct (quality proxy)
```

### 4.9 — Sequential / In-Game Features

```
- batter_result_last_pa_this_game
- batter_result_last_3_pa
- pitcher_last_batter_result
- inning_runs_scored_before_this_pa
- momentum_proxy: runs differential over recent innings
```

### 4.10 — Handling Mid-Game Substitutions

When a pitcher or batter is substituted mid-game (pinch hitter, relief pitcher), the model must correctly:
- Reset times-through-order for relief pitchers
- Use the pinch hitter's stats (not the replaced player's)
- Update game-state features accordingly

---

## 5. MODEL ARCHITECTURE

### 5.1 — Multi-Stage Modeling Pipeline

```
STAGE 1: PITCH-LEVEL MODEL (if pitch data coverage is sufficient)
  Input: count state, all contextual features
  Output: P(next pitch outcome) — ball, called_strike, swinging_strike, foul, in_play, etc.
  Can simulate forward via Monte Carlo to estimate at-bat outcomes
  Architecture: Gradient-boosted trees (primary) or sequence model (optional)

STAGE 2: AT-BAT OUTCOME MODEL (primary deliverable)
  Input: all features from Section 4
  Output: calibrated probability distribution over all at-bat outcome classes
  Architecture: Multi-class classification with calibration layer

STAGE 3: RUN EXPECTANCY / WIN PROBABILITY
  Input: Stage 2 output probabilities + game state
  Output: expected runs added (RE24), win probability change (WPA)
```

### 5.2 — Model Selection and Comparison

Train and compare ALL of the following, then build a stacking ensemble of the best performers:

**Baselines (mandatory):**
- Empirical frequency baselines by count/base-out state
- Logistic / multinomial logistic regression
- Markov / count-transition baseline (pitch state transitions → terminal outcomes)

**Strong tabular ML models:**
```python
models = {
    'xgboost': XGBClassifier(
        objective='multi:softprob',
        num_class=len(AT_BAT_OUTCOMES),
        max_depth=8, learning_rate=0.05, n_estimators=1000,
        subsample=0.8, colsample_bytree=0.7,
        min_child_weight=50, early_stopping_rounds=50,
        eval_metric='mlogloss'
    ),
    'lightgbm': LGBMClassifier(
        objective='multiclass',
        max_depth=8, learning_rate=0.05, n_estimators=1000,
        subsample=0.8, colsample_bytree=0.7,
        min_child_samples=50
    ),
    'catboost': CatBoostClassifier(
        loss_function='MultiClass',
        depth=8, learning_rate=0.05, iterations=1000,
        # CatBoost handles categoricals natively — leverage this
    ),
}
```

**On deep learning:** Do NOT default to neural networks unless they clearly add value over tabular models for this dataset. However, consider:
- **Entity embeddings** for player IDs (batter, pitcher) in a neural network — these can capture latent player style representations better than one-hot encoding
- **RNN/LSTM** for the pitch-level model if pitch sequence data is rich enough to benefit from sequential modeling
- If you build a neural model, include it as an ensemble member alongside tree models, not as a replacement

**Stacking meta-learner:**
```python
'meta_learner': LogisticRegression()  # or lightweight XGBoost on top of base model outputs
```

### 5.3 — Handling Player IDs (Critical)

Do NOT one-hot encode player IDs (thousands of unique values). Instead:

```python
# For tree models: target encoding with regularization
from category_encoders import TargetEncoder
# Encode batter_id with target = on_base rate, with smoothing
# Use leave-one-out within cross-validation to prevent leakage

# For neural networks: learned embeddings
batter_embedding = Embedding(input_dim=num_unique_batters, output_dim=32)
pitcher_embedding = Embedding(input_dim=num_unique_pitchers, output_dim=32)
park_embedding = Embedding(input_dim=num_unique_parks, output_dim=8)
```

### 5.4 — Cold Start / Sparse Player Handling

For batters/pitchers with limited history (<50 PA), use **Bayesian shrinkage / hierarchical priors**:
- Shrink toward league-average rates for the player's position and handedness
- Weight personal stats proportionally to sample size
- Do not allow undefined features for any player's first PA

### 5.5 — Probability Calibration (MANDATORY)

Raw model outputs are confidence scores, not true probabilities. After training:

```python
from sklearn.calibration import CalibratedClassifierCV, calibration_curve

# Apply Platt scaling or isotonic regression
calibrated_model = CalibratedClassifierCV(base_model, method='isotonic', cv=5)

# Verify with reliability diagrams for each outcome class
# Compute Expected Calibration Error (ECE)
# A prediction of 60% should correspond to ~60% actual occurrence rate
```

### 5.6 — Handling Class Imbalance

At-bat outcomes are heavily imbalanced (outs dominate). Handle this correctly:

```python
# Method 1: class_weight parameter in models
class_weights = compute_class_weight('balanced', classes=unique_classes, y=y_train)

# Method 2: Focal loss for neural networks

# CRITICAL: Do NOT use SMOTE or oversampling — the model should learn that outs
# are the most common outcome. That reflects reality and is necessary for
# calibrated probabilities. Just ensure minority classes (triples, HBP) have
# enough signal through proper weighting.
```

---

## 6. TRAINING PROTOCOL

### 6.1 — Data Splitting (Time-Series Aware — MANDATORY)

**NEVER use random train/test splits.** Baseball data is temporal.

```python
# Primary approach: Season-based split
train = data[data['season'] <= 2018]
validation = data[data['season'] == 2019]
test = data[data['season'] >= 2020]

# Additional: Walk-forward validation
# Train on seasons 1-N, validate on season N+1, slide forward
# This gives multiple evaluation windows and tests temporal stability

# Within-season variant: train on first 120 games, test on last 42
```

### 6.2 — Data Leakage Prevention (CRITICAL)

You must produce an explicit **leakage audit checklist** as a deliverable:

```
□ Season-to-date features stop before the current game date
□ Game-to-date features stop before the current plate appearance
□ Rolling stats use ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
□ No use of final game box score totals when scoring in-game events
□ No use of post-event outcomes in predictive features
□ No label leakage from event description text into predictors
□ Target encoding uses leave-one-out within CV folds
□ Head-to-head stats exclude the current at-bat
□ No future roster/transaction information used
□ Test data is strictly in the future relative to all training data
```

### 6.3 — Hyperparameter Tuning

```python
import optuna

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 4, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 500, 3000),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 10, 200),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
    }
    # Use time-series CV, return mean log-loss
    return cv_score

study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=200)
```

### 6.4 — Feature Selection & Importance

```python
# SHAP values (mandatory for all tree models)
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Permutation importance as secondary validation
from sklearn.inspection import permutation_importance

# Remove features with near-zero importance
# Check multicollinearity (VIF) among top features
# Document which features drive which outcome classes
```

---

## 7. EVALUATION METRICS

Compute ALL of the following:

```python
METRICS = {
    # Primary probabilistic metrics
    'log_loss': 'Primary metric — measures probability quality',
    'brier_score_per_class': 'Probability accuracy per outcome class',
    'expected_calibration_error': 'Binned calibration error',
    'reliability_diagrams': 'Visual per-class calibration plots',

    # Discrimination metrics
    'roc_auc_ovr': 'One-vs-rest AUC for each class',
    'pr_auc_per_class': 'Precision-recall AUC (important for rare events)',

    # Classification (secondary — probabilities matter more)
    'accuracy': 'Overall accuracy',
    'f1_macro': 'Macro F1 across classes',
    'confusion_matrix': 'Per-class confusion',

    # Baseball-specific validation
    'predicted_vs_actual_obp': 'Aggregate OBP prediction accuracy',
    'predicted_vs_actual_slg': 'Using expected hit type values',
    'predicted_vs_actual_k_rate': 'Strikeout rate calibration',
    'predicted_vs_actual_bb_rate': 'Walk rate calibration',
    'predicted_vs_actual_hr_rate': 'HR rate calibration',

    # Lift over baselines
    'vs_league_average': 'Improvement over naive league-avg priors',
    'vs_batter_season_avg': 'Improvement from contextual features',
    'vs_markov_baseline': 'Improvement over count-transition model',

    # Subgroup performance
    'by_count': 'Performance broken down by ball-strike count',
    'by_base_out_state': 'Performance by 24 base-out states',
    'by_handedness_matchup': 'L-L, L-R, R-L, R-R performance',
    'by_rare_events': 'How well the model handles triples, HBP, interference',
}
```

### Predictability Ceiling Acknowledgment

**Important:** Baseball at-bats are inherently high-variance events. Even an optimal model cannot predict individual at-bat outcomes with high discriminative power because the best hitters in history fail ~65% of the time. The value of this model lies in producing **well-calibrated probability distributions** that are more accurate than naive baselines, not in achieving high classification accuracy. Set expectations accordingly:
- A well-calibrated model that improves OBP prediction by 2-5% over league averages is genuinely valuable
- Log loss improvement over baselines is the proper measure of model value
- Perfect prediction is impossible; the goal is optimal probability estimation

---

## 8. OUTPUT SPECIFICATION

### 8.1 — Prediction API

```python
def predict_at_bat(
    batter_id: str,
    pitcher_id: str,
    inning: int,
    outs: int,
    runner_on_1b: bool,
    runner_on_2b: bool,
    runner_on_3b: bool,
    score_diff: int,          # from batting team's perspective
    batting_order_position: int,
    is_home: bool,
    park_id: str,
    game_date: str,           # to compute rolling stats
    balls: int = 0,           # current count (for pitch model)
    strikes: int = 0,
    batter_hand: str = None,  # auto-looked up if None; handles switch hitters
    pitcher_hand: str = None,
    temperature: float = None,
    wind_speed: float = None,
    wind_direction: str = None,
    times_through_order: int = None,
    pitcher_pitch_count: int = None,
    is_pinch_hitter: bool = False,
) -> dict:
    """Returns comprehensive probability distribution as JSON."""
    pass

# Example output:
{
    # Granular PA outcome probabilities (sum to 1.0)
    "p_strikeout": 0.22,
    "p_walk": 0.09,
    "p_intentional_walk": 0.005,
    "p_hit_by_pitch": 0.01,
    "p_single": 0.16,
    "p_double": 0.05,
    "p_triple": 0.005,
    "p_home_run": 0.04,
    "p_ground_out": 0.20,
    "p_fly_out": 0.12,
    "p_line_out": 0.06,
    "p_pop_out": 0.03,
    "p_fielders_choice": 0.01,
    "p_error": 0.01,
    "p_sacrifice": 0.005,
    "p_interference": 0.0005,

    # Derived aggregates
    "p_on_base_traditional": 0.355,   # H + BB + HBP
    "p_reach_base_any": 0.375,        # includes ROE, interference
    "p_hit": 0.255,
    "p_extra_base_hit": 0.095,
    "p_out": 0.645,
    "p_ball_in_play": 0.685,

    # Expected values
    "expected_total_bases": 0.48,
    "expected_runs_added": 0.03,      # RE24 framework
    "expected_wpa": 0.015,            # Win Probability Added

    # Model metadata
    "model_confidence": 0.72,          # 1 - normalized entropy (lower = less certain)
    "key_factors": [                   # top SHAP drivers for this prediction
        ("times_through_order_3", -0.04),
        ("batter_rolling_obp_high", 0.03),
        ("platoon_advantage_RvL", 0.025),
    ],

    # Baselines for comparison
    "league_avg_obp": 0.320,
    "batter_season_obp": 0.345,
    "model_predicted_obp": 0.355,

    # Next-pitch probabilities (if pitch model active)
    "next_pitch": {
        "p_ball": 0.38,
        "p_called_strike": 0.18,
        "p_swinging_strike": 0.10,
        "p_foul": 0.20,
        "p_in_play": 0.13,
        "p_hbp": 0.01
    }
}
```

### 8.2 — Database Storage of Predictions

```sql
CREATE TABLE model_predictions (
    prediction_id SERIAL PRIMARY KEY,
    game_id VARCHAR(20),
    event_id INTEGER,
    batter_id VARCHAR(10),
    pitcher_id VARCHAR(10),
    prediction_timestamp TIMESTAMP DEFAULT NOW(),
    model_version VARCHAR(20),

    -- Game state at prediction time
    inning INTEGER,
    outs INTEGER,
    base_state INTEGER,  -- 0-7 encoding
    score_diff INTEGER,
    balls INTEGER,
    strikes INTEGER,

    -- Granular PA outcome probabilities
    p_strikeout NUMERIC(6,5),
    p_walk NUMERIC(6,5),
    p_hbp NUMERIC(6,5),
    p_single NUMERIC(6,5),
    p_double NUMERIC(6,5),
    p_triple NUMERIC(6,5),
    p_home_run NUMERIC(6,5),
    p_ground_out NUMERIC(6,5),
    p_fly_out NUMERIC(6,5),
    p_line_out NUMERIC(6,5),
    p_pop_out NUMERIC(6,5),
    p_fielders_choice NUMERIC(6,5),
    p_error NUMERIC(6,5),
    p_sacrifice NUMERIC(6,5),

    -- Aggregates
    p_on_base NUMERIC(6,5),
    p_hit NUMERIC(6,5),
    expected_bases NUMERIC(6,4),
    expected_runs_added NUMERIC(6,4),
    model_confidence NUMERIC(6,5),

    -- Actual outcome (filled after the fact for evaluation)
    actual_event_cd INTEGER,
    actual_outcome_class VARCHAR(20)
);

CREATE INDEX idx_pred_batter ON model_predictions(batter_id);
CREATE INDEX idx_pred_pitcher ON model_predictions(pitcher_id);
CREATE INDEX idx_pred_game ON model_predictions(game_id);
CREATE INDEX idx_pred_version ON model_predictions(model_version);

-- Evaluation materialized view
CREATE MATERIALIZED VIEW mv_model_evaluation AS
SELECT
    model_version,
    actual_outcome_class,
    COUNT(*) AS n,
    AVG(CASE
        WHEN actual_outcome_class = 'single' THEN p_single
        WHEN actual_outcome_class = 'double' THEN p_double
        WHEN actual_outcome_class = 'triple' THEN p_triple
        WHEN actual_outcome_class = 'home_run' THEN p_home_run
        WHEN actual_outcome_class = 'walk' THEN p_walk
        WHEN actual_outcome_class = 'strikeout' THEN p_strikeout
        -- ... etc for each class
    END) AS avg_predicted_prob_of_actual,
    AVG(p_on_base) AS avg_predicted_obp,
    AVG(CASE WHEN actual_event_cd IN (14,15,16,20,21,22,23) THEN 1.0 ELSE 0.0 END) AS actual_obp,
    AVG(POWER(
        CASE WHEN actual_event_cd IN (14,15,16,20,21,22,23) THEN 1.0 ELSE 0.0 END - p_on_base
    , 2)) AS brier_score_obp
FROM model_predictions
WHERE actual_event_cd IS NOT NULL
GROUP BY model_version, actual_outcome_class;
```

---

## 9. IMPLEMENTATION PLAN — EXECUTE IN THIS ORDER

```
PHASE 1: DATA DISCOVERY & PROFILING (Day 1)
├── Run all schema discovery queries from Section 1
├── Map discovered tables/views/MVs to Retrosheet concepts
├── Profile data quality: nulls, date ranges, event code distributions
├── Assess pitch-level data coverage by year
├── Identify reusable materialized views
├── Document findings before proceeding
└── Note any gaps (e.g., no defensive shift data, no Statcast)

PHASE 2: FEATURE ENGINEERING PIPELINE (Days 2-3)
├── Build SQL queries/views for each feature category in Section 4
├── Create master feature extraction query joining everything
├── Handle missing values (document strategy per-feature)
├── Handle switch hitters explicitly in platoon features
├── Implement Bayesian shrinkage for sparse player stats
├── Export to pandas/Parquet for modeling
├── Validate feature distributions (histograms, correlations)
└── Build reusable pipeline for new data

PHASE 3: BASELINE MODELS (Day 4)
├── Empirical frequency baseline (by count/base-out state)
├── Markov/transition baseline (pitch state → terminal outcome)
├── Logistic regression baseline
├── Evaluate all on time-series test split
├── Establish benchmark metrics to beat
└── Compare to naive league-average priors

PHASE 4: FULL MODEL TRAINING (Days 5-7)
├── Train XGBoost, LightGBM, CatBoost
├── Optional: train neural model with entity embeddings
├── Hyperparameter tuning with Optuna
├── Feature importance with SHAP
├── Feature selection refinement
├── Probability calibration (isotonic/Platt)
├── Build stacking ensemble
├── Walk-forward cross-validation
└── Compare direct vs recursive vs hybrid approach

PHASE 5: EVALUATION & ANALYSIS (Day 8)
├── Compute all metrics from Section 7
├── Generate calibration plots per class
├── Generate SHAP summary plots
├── Baseball-specific evaluation (predicted vs actual rates)
├── Subgroup analysis (by count, base-out, handedness)
├── Error analysis: where does the model fail?
├── Document predictability ceiling findings
└── Produce model card

PHASE 6: DEPLOYMENT & INTEGRATION (Days 9-10)
├── Build prediction API (Section 8.1)
├── Create PostgreSQL storage tables (Section 8.2)
├── Build model serving pipeline
├── Create scoring for batch (historical) and live (current game)
├── Implement model monitoring and drift detection
├── Define retraining triggers and cadence
├── Write documentation and README
└── Create MV refresh schedule for feature store
```

---

## 10. ADDITIONAL REQUIREMENTS

### 10.1 — Factors to Consider That May Not Be in Retrosheet

Acknowledge in your documentation that the following factors affect outcomes but may not be available in Retrosheet data:
- **Defensive positioning / shifts** — significantly affects BABIP and batted-ball outcomes
- **Pitch velocity, spin rate, movement** — Statcast data not present in Retrosheet
- **Catcher framing** — can affect called strike rates
- **Umpire tendencies** — different strike zones affect outcomes
- If any of these are derivable from existing fields, use them. Otherwise, document as known model limitations.

### 10.2 — Ethical Considerations

Document intended use of the model. Note that probability outputs could potentially be misused for gambling purposes. Include appropriate disclaimers about:
- The model produces estimates, not certainties
- Historical patterns do not guarantee future outcomes
- The model should be used for analytical and educational purposes

### 10.3 — Model Monitoring & Drift

For a deployed system, implement:
- **Performance monitoring:** Track log loss and calibration error on rolling recent predictions
- **Feature drift detection:** Monitor if input feature distributions shift significantly
- **Concept drift detection:** Monitor if the relationship between features and outcomes changes (e.g., rule changes, juiced ball)
- **Retraining triggers:** Define when the model should be retrained (quarterly, after significant performance degradation, after rule changes)

### 10.4 — Live Game Prediction

If the system will be used for in-game predictions:
- Define how real-time game state data is ingested (API, manual input, streaming)
- Handle mid-game substitutions (pinch hitters, relief pitchers) by updating all relevant features
- Ensure prediction latency < 100ms for a single at-bat prediction
- Cache pre-computed player historical features; only game-state features change within a game

---

## 11. DELIVERABLES

Provide ALL of the following:

1. **Schema audit results** — documented findings from database discovery
2. **SQL scripts** — all views, materialized views, feature extraction queries, index recommendations
3. **Leakage audit checklist** — completed checklist showing how leakage is prevented
4. **Python codebase** — modular, documented, with clear entry points:
   - `sql/` — extraction and schema queries
   - `src/features/` — feature engineering pipeline
   - `src/train/` — model training, tuning, calibration
   - `src/score/` — inference pipeline
   - `models/` — serialized model artifacts
   - `notebooks/` — exploration and evaluation
   - `reports/` — evaluation reports, plots
5. **Trained model artifacts** — serialized models, scalers, encoders, calibrators
6. **Evaluation report** — all metrics, calibration plots, SHAP plots, baseline comparisons, subgroup analyses
7. **Feature importance analysis** — SHAP values, top features per outcome class
8. **Prediction examples** — 20+ example predictions with explanations
9. **Model card** — data used, limitations, intended use, ethical considerations, known blind spots
10. **README** — setup instructions, dependencies, how to retrain, how to predict
11. **Deployment guide** — batch scoring, live scoring, refresh cadence, monitoring plan

---

## 12. CRITICAL CONSTRAINTS SUMMARY

1. **No data leakage.** Only use information available BEFORE the event being predicted. Complete the leakage audit checklist.
2. **Probability distributions must be valid.** All class probabilities must sum to 1.0 for every prediction.
3. **Handle cold starts.** Bayesian shrinkage for players with <50 PA toward league/position/handedness priors.
4. **Handle switch hitters.** Resolve batting side based on pitcher handedness; do not treat all batters as strictly L or R.
5. **Respect Retrosheet encoding.** Parse `event_tx` and `pitch_seq_tx` correctly per Retrosheet documentation.
6. **Account for era effects.** Include year/era features; consider training on 2000+ data unless modeling historical periods.
7. **All code must connect to PostgreSQL.** Use `psycopg2` or `SQLAlchemy`. Feature engineering in SQL where efficient, Python for modeling.
8. **Reproducibility.** Set random seeds, log all parameters, version all models, store feature schemas with artifacts.
9. **Performance.** Use materialized views and indexing. Prediction function should return results in <100ms for single at-bat.
10. **Calibration is paramount.** This is a probability estimation system, not just a classifier. Calibrated probabilities are the most important output.

---

**BEGIN. Start with Phase 1 — explore the database schema and report what you find before proceeding to any modeling.**
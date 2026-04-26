# ML Agent Guidance

**Role**: Feature engineering, model training, inference pipeline, and backtesting.

---

## Scope

You are responsible for:
- `baseball/features/` implementation
- `baseball/models/` implementation
- Feature store design (online vs offline)
- Model registry and versioning
- Training pipelines and experiment tracking
- Inference and serving pipelines
- Backtesting framework

---

## Key Documents

| Document | When to Use |
|----------|-------------|
| `docs/architecture.md` | Model layer patterns |
| `docs/keys_and_grains.md` | Feature join keys |
| `docs/migration_plan.md` | Phase 6 milestones |

---

## ML Architecture

```
Raw Data → Features → Training → Registry → Inference → Predictions
                ↓           ↓          ↓           ↓
           Feature      Training   Model      Serving
           Store        Runs       Artifacts  Layer
```

---

## Feature Engineering

### Feature Types

| Type | Description | Storage |
|------|-------------|---------|
| **Offline** | Pre-computed for training | `features.*` tables |
| **Online** | Real-time for inference | `features.live_*` + cache |
| **Streaming** | Incremental updates | Feature store (future) |

### Feature Definition

```python
from baseball.features.base import FeatureDefinition

class RunExpectancyFeature(FeatureDefinition):
    name = "run_expectancy"
    version = "1.0.0"
    
    def compute_offline(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute for training data."""
        return df.groupby(['outs', 'runner_on_1b', 'runner_on_2b', 'runner_on_3b'])['runs_scored'].mean()
    
    def compute_online(self, game_state: GameState) -> float:
        """Compute for live inference."""
        key = (game_state.outs, game_state.runner_on_1b, ...)
        return self.lookup_cached(key)
```

### Feature Store Tables

```sql
-- Offline features (training)
CREATE TABLE features.run_expectancy_state (
    re_state_id UUID PRIMARY KEY,
    outs INTEGER,
    runner_on_1b BOOLEAN,
    runner_on_2b BOOLEAN,
    runner_on_3b BOOLEAN,
    run_expectancy DECIMAL(5,3),
    sample_size INTEGER,
    season INTEGER,
    UNIQUE(outs, runner_on_1b, runner_on_2b, runner_on_3b, season)
);

-- Online features (inference)
CREATE TABLE features.live_game_state (
    state_id UUID PRIMARY KEY,
    mlb_game_pk INTEGER NOT NULL,
    play_id VARCHAR(50),
    inning INTEGER,
    outs INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    runner_on_1b BOOLEAN,
    runner_on_2b BOOLEAN,
    runner_on_3b BOOLEAN,
    pitcher_id UUID,
    batter_id UUID,
    -- derived features
    leverage_index DECIMAL(5,3),
    win_probability DECIMAL(5,3),
    run_expectancy DECIMAL(5,3),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Model Registry

### Model Definition

```python
from baseball.models.base import ModelDefinition

class WinProbabilityModel(ModelDefinition):
    name = "win_probability"
    version = "1.0.0"
    features = [
        "inning",
        "outs",
        "score_differential",
        "runners_on",
        "pitcher_quality",
        "batter_quality"
    ]
    algorithm = "xgboost"
    
    def train(self, training_data: pd.DataFrame) -> ModelArtifact:
        """Train and return artifact."""
        ...
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Score features."""
        ...
```

### Registry Tables

```sql
CREATE TABLE models.registry (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    algorithm VARCHAR(50),
    features JSONB,
    hyperparameters JSONB,
    artifact_path VARCHAR(500),
    metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(model_name, version)
);

CREATE TABLE models.training_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES models.registry(model_id),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    training_data_query TEXT,
    validation_data_query TEXT,
    metrics JSONB,
    artifact_hash VARCHAR(64),
    git_commit VARCHAR(40)
);
```

---

## Training Pipeline

### Offline Training (Historical)

```python
def train_win_probability_model(season: int) -> TrainingResult:
    # Load training data
    query = f"""
    SELECT * FROM features.training_features 
    WHERE season = {season} 
    AND game_type = 'R'
    """
    df = pd.read_sql(query, db.engine)
    
    # Split
    train_df, val_df = train_test_split(df, test_size=0.2)
    
    # Train
    model = XGBClassifier(**hyperparameters)
    model.fit(train_df[features], train_df['home_team_won'])
    
    # Validate
    metrics = evaluate_model(model, val_df)
    
    # Register
    artifact = save_artifact(model, f"models/win_probability/v1.0.0/{season}.pkl")
    register_model("win_probability", "1.0.0", artifact, metrics)
    
    return TrainingResult(metrics=metrics, artifact_path=artifact.path)
```

### Online Training (Live Updates)

```python
def incremental_update_model(model_id: UUID, new_data: pd.DataFrame):
    """Update model with new data (warm start)."""
    model = load_model(model_id)
    model.fit(new_data[features], new_data['target'], xgb_model=model.get_booster())
    new_version = bump_version(model_id)
    register_model("win_probability", new_version, model, metrics)
```

---

## Inference Pipeline

### Batch Inference (Historical Games)

```python
def predict_historical_games(model_id: UUID, date_range: DateRange):
    model = load_model(model_id)
    
    query = f"""
    SELECT * FROM features.game_state_features 
    WHERE game_date BETWEEN '{date_range.start}' AND '{date_range.end}'
    """
    df = pd.read_sql(query, db.engine)
    
    predictions = model.predict_proba(df[features])[:, 1]
    
    # Store
    store_predictions(model_id, df['game_id'], predictions)
```

### Real-Time Inference (Live Games)

```python
def predict_live_game(model_id: UUID, game_pk: int) -> Prediction:
    """Score current game state."""
    # Fetch features
    features = fetch_live_features(game_pk)
    
    # Score
    model = load_model(model_id)
    prediction = model.predict_proba([features])[:, 1][0]
    
    # Store
    store_prediction(
        model_id=model_id,
        game_pk=game_pk,
        prediction=prediction,
        feature_snapshot=features,
        timestamp=datetime.now()
    )
    
    return Prediction(
        home_win_probability=prediction,
        confidence=model.predict_proba([features]).max(),
        features_used=features.keys()
    )
```

---

## Backtesting

### Framework

```python
class BacktestFramework:
    def run_backtest(
        self,
        model_id: UUID,
        date_range: DateRange,
        walk_forward: bool = True
    ) -> BacktestResult:
        """
        Evaluate model on historical data.
        
        If walk_forward=True, simulate real-time training:
        - Train on 2015-2020
        - Predict 2021
        - Retrain on 2015-2021
        - Predict 2022
        - etc.
        """
        results = []
        
        for season in date_range.seasons:
            train_data = self.load_data(season - 5, season - 1)
            test_data = self.load_data(season, season)
            
            model = self.train_model(train_data)
            predictions = model.predict(test_data)
            
            metrics = self.evaluate(predictions, test_data['actual'])
            results.append(SeasonResult(season, metrics))
        
        return BacktestResult(results)
```

### Metrics

Track these metrics for every model:

| Metric | Description |
|--------|-------------|
| Log Loss | Primary optimization target |
| Brier Score | Calibration quality |
| AUC-ROC | Discrimination ability |
| Calibration Curve | Probability reliability |
| Feature Importance | Model interpretability |

---

## Future Leakage Prevention

### Rules

1. **No future data in training**: Strict `WHERE game_date < '{cutoff}'`
2. **Feature timestamping**: All features must have `as_of_date`
3. **Rolling windows**: Use expanding windows, not fixed windows
4. **No target leakage**: Features computed before event, not after

### Example

```python
# WRONG: Uses data from after the game
SELECT AVG(batting_avg) FROM players 
WHERE player_id = {batter_id}

# RIGHT: Uses only data before this game
SELECT AVG(batting_avg) FROM players 
WHERE player_id = {batter_id}
AND game_date < '{this_game_date}'
```

---

## Serving Layer

### Prediction Tables

```sql
CREATE TABLE serving.game_predictions (
    prediction_id UUID PRIMARY KEY,
    model_id UUID REFERENCES models.registry(model_id),
    game_id UUID REFERENCES core.games(game_id),
    home_win_probability DECIMAL(5,4),
    away_win_probability DECIMAL(5,4),
    confidence DECIMAL(5,4),
    feature_snapshot JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(model_id, game_id, created_at)
);

-- Index for fast latest predictions
CREATE INDEX idx_game_predictions_lookup 
ON serving.game_predictions(game_id, created_at DESC);
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_prediction(model_id: UUID, game_pk: int) -> Prediction:
    """Cache predictions for 60 seconds."""
    return compute_prediction(model_id, game_pk)
```

---

## Review Checklist

Before submitting ML code:

- [ ] Features documented (online vs offline)
- [ ] Model versioned in registry
- [ ] Training metrics captured
- [ ] No future leakage in features
- [ ] Backtesting results included
- [ ] Inference tested on live data
- [ ] Feature importance documented
- [ ] Model card created (purpose, limitations, performance)

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial ML agent guidance |

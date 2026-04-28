# Phase 4: ML Model Layer - Training, Inference & Win Probability

## Prerequisites
- Phase 3 features complete
- All calculators working
- CLI foundation solid

## Goal
Build complete model training pipeline and implement Win Probability model.

---

## Task 4.1: Complete Model Infrastructure

### Current State
- `baseball/models/base.py` has `BaseModel` abstract class
- `baseball/models/pa_outcome_model.py` has working examples
- `baseball/models/registry.py` exists (check completeness)
- SQL tables in `sql/60_models/` (check completeness)

### Requirements

#### 4.1.1 Verify/Complete Model Registry SQL

Read and verify `sql/60_models/` files exist:
- `600_models_registry.sql`
- `601_models_training_runs.sql`
- `602_models_artifacts.sql`
- `603_models_evaluation.sql`

If missing, create them with proper schema.

#### 4.1.2 Complete `baseball/models/training.py`

```python
class ModelTrainer:
    """Handles model training orchestration."""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
    
    def train_model(
        self,
        model: BaseModel,
        config: TrainingConfig,
    ) -> TrainingResult:
        """Train a model with full tracking.
        
        Steps:
        1. Log training run start
        2. Fetch training data
        3. Split train/validation/test
        4. Train model
        5. Evaluate on validation
        6. Log metrics
        7. Save artifact
        8. Log training run complete
        """
        pass
    
    def cross_validate(
        self,
        model: BaseModel,
        config: TrainingConfig,
        folds: int = 5,
    ) -> list[TrainingResult]:
        """Run k-fold cross-validation."""
        pass
```

#### 4.1.3 Complete `baseball/models/inference.py`

```python
class ModelInference:
    """Handles model inference/scoring."""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self._cache: dict[str, BaseModel] = {}  # Loaded models
    
    def load_model(self, model_name: str, version: str | None = None) -> BaseModel:
        """Load model into memory."""
        # Check cache first
        # If not cached, load from registry
        # Return model instance
        pass
    
    def predict_single(
        self,
        model_name: str,
        features: dict[str, Any],
    ) -> PredictionResult:
        """Make single prediction."""
        # Load model
        # Assemble feature vector
        # Run inference
        # Return prediction with metadata
        pass
    
    def predict_batch(
        self,
        model_name: str,
        features_list: list[dict[str, Any]],
    ) -> list[PredictionResult]:
        """Make batch predictions."""
        pass
    
    def predict_game(
        self,
        model_name: str,
        game_pk: int,
    ) -> GamePrediction:
        """Predict entire game state."""
        # Fetch game state
        # Compute features
        # Run prediction for each at-bat/pitch
        # Return full game prediction
        pass
```

---

## Task 4.2: Implement Win Probability Model

### Background
Win Probability (WP) is the most valuable model for live predictions. It answers: "Given current game state, what's the probability home team wins?"

### Features Needed

From feature calculators:
- Current inning, score differential, base state, outs
- Win Expectancy (from WE calculator)
- Leverage Index (from LI calculator)
- Batter/pitcher matchup features (from MatchupCalculator)
- Bullpen stress (from BullpenStressCalculator)
- Home field advantage
- Historical team strength (ELO or similar)

### Requirements

#### 4.2.1 Create `baseball/models/win_probability.py`

```python
class WinProbabilityModel(BaseModel):
    """Win Probability model for live game predictions.
    
    Predicts probability home team wins given current game state.
    """
    
    model_type = ModelType.WIN_PROBABILITY
    
    def __init__(self, db_connection=None):
        super().__init__(db_connection)
        self.model = None  # sklearn/xgboost model
        self.feature_importance = {}
    
    @property
    def model_type(self) -> ModelType:
        return ModelType.WIN_PROBABILITY
    
    def get_feature_names(self) -> list[str]:
        """Return list of feature names this model uses."""
        return [
            'inning',
            'is_top_inning',
            'score_diff',
            'home_score',
            'away_score',
            'base_state',
            'outs',
            'win_expectancy',
            'leverage_index',
            'matchup_historical_wp',
            'home_bullpen_stress',
            'away_bullpen_stress',
            'home_team_elo',
            'away_team_elo',
            'home_pitcher_fatigue',
            'away_pitcher_fatigue',
        ]
    
    def fetch_training_data(
        self,
        seasons: list[int],
    ) -> pd.DataFrame:
        """Fetch historical game states and outcomes.
        
        Query should join:
        - core.games (final scores, winner)
        - core.events (game states at each play)
        - features.win_expectancy_matrix (pre-computed WE)
        - features.matchup_features (batter/pitcher history)
        - features.bullpen_stress (reliever fatigue)
        """
        pass
    
    def prepare_features(
        self,
        df: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Convert raw data to X, y arrays.
        
        Args:
            df: DataFrame from fetch_training_data
        
        Returns:
            X: Feature matrix (n_samples, n_features)
            y: Target vector (1 if home team won, 0 otherwise)
        """
        pass
    
    def train(self, config: TrainingConfig) -> TrainingResult:
        """Train Win Probability model.
        
        Recommended approach:
        1. Use XGBoost or Logistic Regression
        2. Class weights for balance (home wins ~54% of games)
        3. Cross-validation for robustness
        4. Feature importance analysis
        """
        # Fetch data
        df = self.fetch_training_data(config.seasons)
        X, y = self.prepare_features(df)
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'log_loss': log_loss(y_test, y_prob),
            'roc_auc': roc_auc_score(y_test, y_prob),
            'calibration': self._check_calibration(y_test, y_prob),
        }
        
        # Feature importance
        self.feature_importance = dict(
            zip(self.get_feature_names(), self.model.feature_importances_)
        )
        
        return TrainingResult(
            success=True,
            metrics=metrics,
            feature_importance=self.feature_importance,
        )
    
    def predict(self, features: dict[str, Any]) -> PredictionResult:
        """Predict win probability for current game state."""
        # Assemble feature vector
        X = self._assemble_features(features)
        
        # Predict
        prob = self.model.predict_proba([X])[0][1]
        
        return PredictionResult(
            prediction=prob,
            confidence=self._calculate_confidence(features),
            feature_values=features,
        )
    
    def _assemble_features(self, game_state: dict) -> list[float]:
        """Convert game state dict to feature vector."""
        # Map game_state to ordered feature list
        pass
```

#### 4.2.2 Create SQL Tables for Model

Create `sql/60_models/604_win_probability_model.sql`:

```sql
/*
File: sql/60_models/604_win_probability_model.sql
Purpose: Win Probability model storage
Author: Agent [codex]
Date: 2026-04-28
*/

-- Model predictions storage
CREATE TABLE IF NOT EXISTS serving.win_prob_predictions (
    id BIGSERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    at_bat_index INTEGER,  -- NULL = game-level prediction
    pitch_index INTEGER,   -- NULL = at-bat-level prediction
    
    -- Prediction
    home_win_probability NUMERIC(5,4) NOT NULL CHECK (home_win_probability BETWEEN 0 AND 1),
    confidence NUMERIC(4,3),  -- Model confidence in this prediction
    
    -- Game state at prediction time
    inning SMALLINT,
    is_top_inning BOOLEAN,
    score_diff SMALLINT,
    base_state SMALLINT,
    outs SMALLINT,
    batter_id INTEGER,
    pitcher_id INTEGER,
    
    -- Model metadata
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(game_pk, at_bat_index, pitch_index, model_version)
);

COMMENT ON TABLE serving.win_prob_predictions IS 
    'Win probability predictions for games, at-bats, and pitches';

CREATE INDEX IF NOT EXISTS idx_wp_predictions_game 
    ON serving.win_prob_predictions(game_pk, created_at DESC);

-- Feature values used for predictions (for debugging/auditing)
CREATE TABLE IF NOT EXISTS serving.win_prob_features (
    id BIGSERIAL PRIMARY KEY,
    prediction_id BIGINT REFERENCES serving.win_prob_predictions(id),
    feature_name VARCHAR(100),
    feature_value NUMERIC(10,4),
    
    UNIQUE(prediction_id, feature_name)
);

COMMENT ON TABLE serving.win_prob_features IS 
    'Feature values used for each win probability prediction';
```

---

## Task 4.3: Complete Model CLI Commands

### Current State
Stub commands exist in `baseball/cli.py`:
- `models list` - shows table but queries nothing
- `models info` - stub
- `models train` - partial, dry-run only
- `models predict` - may be missing

### Requirements

#### 4.3.1 Complete `models list`

```python
@models_app.command(name='list')
def models_list():
    """List all registered models."""
    registry = ModelRegistry()
    models = registry.list_models()
    
    table = Table(show_header=True, header_style='bold magenta')
    table.add_column('Model')
    table.add_column('Type')
    table.add_column('Last Trained')
    table.add_column('Status')
    table.add_column('Best Metric')
    
    for model in models:
        table.add_row(
            model['name'],
            model['type'],
            model['last_trained'] or 'Never',
            model['status'],
            f"{model['best_metric']:.3f}" if model['best_metric'] else 'N/A',
        )
    
    console.print(table)
```

#### 4.3.2 Complete `models info`

```python
@models_app.command(name='info')
def models_info(
    model_name: str = typer.Option(..., '--model', '-m', ...),
):
    """Show detailed model info."""
    registry = ModelRegistry()
    model_info = registry.get_model_info(model_name)
    
    console.print(f'\n[bold]{model_name}[/bold]')
    console.print(f'Type: {model_info["type"]}')
    console.print(f'Status: {model_info["status"]}')
    
    # Show feature importance
    if model_info.get('feature_importance'):
        console.print('\n[bold]Feature Importance:[/bold]')
        for feature, importance in sorted(
            model_info['feature_importance'].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]:
            console.print(f'  {feature}: {importance:.3f}')
```

#### 4.3.3 Complete `models train`

```python
@models_app.command(name='train')
def models_train(
    model_type: str = typer.Option(..., '--model', '-m', ...),
    seasons: str = typer.Option('2020-2024', '--seasons', '-s', ...),
    dry_run: bool = typer.Option(False, '--dry-run', ...),
):
    """Train a model."""
    # Parse seasons
    season_list = parse_seasons(seasons)  # "2020-2024" -> [2020, 2021, 2022, 2023, 2024]
    
    console.print(f'\n[bold]Training {model_type} model[/bold]')
    console.print(f'Seasons: {season_list}')
    
    if dry_run:
        console.print('[dim]Dry run - would train here[/dim]')
        return
    
    # Get model class
    model_class = get_model_class(model_type)
    model = model_class()
    
    # Train
    config = TrainingConfig(seasons=season_list)
    result = model.train(config)
    
    if result.success:
        console.print('[green]✅ Training complete[/green]')
        console.print(f'Accuracy: {result.metrics["accuracy"]:.3f}')
        console.print(f'Log Loss: {result.metrics["log_loss"]:.3f}')
    else:
        console.print(f'[red]❌ Training failed: {result.error}[/red]')
```

#### 4.3.4 Add `models predict` (if missing)

```python
@models_app.command(name='predict')
def models_predict(
    model_name: str = typer.Option(..., '--model', '-m', ...),
    game_pk: int = typer.Option(..., '--game', '-g', ...),
):
    """Run prediction for a game."""
    inference = ModelInference()
    
    prediction = inference.predict_game(model_name, game_pk)
    
    console.print(f'\n[bold]Prediction for Game {game_pk}[/bold]')
    console.print(f'Home Win Probability: {prediction.home_win_prob:.1%}')
    console.print(f'Away Win Probability: {prediction.away_win_prob:.1%}')
```

---

## Task 4.4: Integration Testing

### Test Plan

Create comprehensive tests:

```python
# tests/unit/test_win_probability_model.py
class TestWinProbabilityModel:
    def test_model_initialization(self):
        model = WinProbabilityModel()
        assert model.model_type == ModelType.WIN_PROBABILITY
    
    def test_fetch_training_data(self, db_conn):
        model = WinProbabilityModel(db_conn)
        df = model.fetch_training_data([2023])
        assert len(df) > 0
        assert 'home_won' in df.columns
    
    def test_train_and_predict(self, db_conn):
        model = WinProbabilityModel(db_conn)
        
        # Train
        config = TrainingConfig(seasons=[2023])
        result = model.train(config)
        assert result.success
        assert 'accuracy' in result.metrics
        
        # Predict
        features = {
            'inning': 5,
            'is_top_inning': True,
            'score_diff': 2,
            'base_state': 1,
            'outs': 1,
            # ... other features
        }
        pred = model.predict(features)
        assert 0 <= pred.prediction <= 1
```

---

## Documentation Updates

1. **AGENTS.md**:
   - Mark Win Probability model as complete
   - Update model status table

2. **PROJECT_LOG.md**:
   - Entry: "Phase 4: Win Probability model implemented"
   - Document training metrics achieved

3. **FILE_INVENTORY.md**:
   - Add new model files
   - Add new SQL files

---

## Validation Steps

```bash
# 1. Import test
python -c "from baseball.models import WinProbabilityModel; print('OK')"

# 2. List models
baseball models list
# Should show: win_probability (and others)

# 3. Train dry-run
baseball models train --model win_probability --seasons 2023 --dry-run

# 4. Real training (small data)
baseball models train --model win_probability --seasons 2023

# 5. Make prediction
baseball models predict --model win_probability --game 123456

# 6. Pipeline integration
baseball pipeline run --pipeline daily --date 2024-04-28 --dry-run

# 7. Tests
python -m pytest tests/unit/test_win_probability_model.py -v

# 8. Demo
python scripts/demo_full_system.py --mode quick
```

---

## Success Criteria

- [ ] `WinProbabilityModel` implemented
- [ ] Model training works end-to-end
- [ ] Model inference works
- [ ] Predictions stored in `serving.win_prob_predictions`
- [ ] CLI commands fully functional
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Can make live predictions for games

---

## Time Estimate

6-7 hours for complete model layer implementation.

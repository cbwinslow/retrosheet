## Progress Update (2026-04-23)

### Completed:
Built modular prediction framework with Strategy pattern:

**Files created in `scripts/prediction_framework/`:**
- `base.py` - Predictor base class, PredictionTarget, ModelMetadata, PredictorRegistry
- `pa_predictor.py` - PAOutcomeDistributionPredictor implementation
- `__init__.py` - PredictionEngine unified interface
- `db.py` - Database config

**Database additions:**
- `models.register_model()` - register new models
- `models.register_calibration()` - register calibration artifacts  
- `models.promote_model()` - set active model
- `models.get_active_model()` - get active model for target
- `models.calibration_artifacts` table
- `models.v_active_models` view

**Active models registered:**
- `pa_outcome_distribution`: hist_gradient_boosting_multiclass (v20260412T045759Z)
- `game_home_win`: hist_gradient_boosting (v20260416T085327Z)
- `half_inning_any_run`: hist_gradient_boosting (v20260410T090317Z)
- `half_inning_lhb_any_hit`: hist_gradient_boosting (v20260410T090325Z)

### Usage:
```python
from prediction_framework import PredictionEngine

engine = PredictionEngine()
predictor = engine.get_predictor('pa_outcome_distribution')
result = predictor.predict(features_df)
```

### Next:
1. Add run expectancy matrix (#64)
2. Add Markov chain model
3. Add handedness matchup features
4. Research GIS pitch mapping
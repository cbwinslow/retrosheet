## Issue #3: 🎯 Model Orchestration Layer for Real-time Predictions

### Description
Create a unified orchestration layer that can coordinate between all 18 ML models, handle real-time odds calculation, and manage complex multi-model predictions for baseball outcomes.

### Technical Requirements
- **Model Coordination**: Orchestrate calls to 18 different ML models
- **Real-time Odds**: Convert probabilities to betting odds format
- **Batch Processing**: Handle multiple predictions efficiently
- **Model Selection**: Choose best model per target automatically
- **Caching**: Cache predictions with appropriate TTL

### Implementation Details
```python
class BaseballModelOrchestrator:
    def __init__(self):
        self.prediction_service = PredictionService()
        self.model_selector = ModelSelector()
        self.odds_calculator = OddsCalculator()

    def predict_outcomes(self, game_state: Dict, targets: List[str]) -> Dict[str, float]:
        \"\"\"Predict multiple baseball outcomes for a game state.\"\"\"
        predictions = {}

        for target in targets:
            # Select best model for this target
            model = self.model_selector.select_model(target)

            # Get prediction
            prob = self.prediction_service.predict_single(target, game_state)

            # Convert to odds if needed
            predictions[target] = {
                'probability': prob,
                'odds': self.odds_calculator.prob_to_odds(prob),
                'model_used': model.name
            }

        return predictions

    def get_live_odds(self, game_id: str) -> Dict[str, Any]:
        \"\"\"Get live odds for all outcomes in an active game.\"\"\"
        # Get current game state from live data
        game_state = self._get_live_game_state(game_id)

        # Predict all outcomes
        return self.predict_outcomes(game_state, ALL_TARGETS)
```

### Key Features
- **18 Model Management**: Coordinate hist_gradient_boosting and logistic_regression models for each target
- **Odds Calculation**: Convert ML probabilities to American/Moneyline odds
- **Live Data Integration**: Pull real-time game state from MLB API
- **Caching Strategy**: Cache predictions for 30-60 seconds during live games
- **Fallback Handling**: Graceful degradation when models unavailable

### Real-time Odds Calculation
```python
class OddsCalculator:
    def prob_to_american_odds(self, probability: float) -> str:
        \"\"\"Convert probability to American odds format.\"\"\"
        if probability > 0.5:
            # Favorite
            odds = -100 / ((probability - 1) / probability)
            return f"{int(odds)}"
        else:
            # Underdog
            odds = 100 / probability - 100
            return f"+{int(odds)}"

    def prob_to_moneyline(self, probability: float) -> float:
        \"\"\"Convert to moneyline odds.\"\"\"
        if probability > 0.5:
            return -100 / ((probability - 1) / probability)
        else:
            return 100 / probability - 100
```

### Acceptance Criteria
- [ ] Can orchestrate predictions across all 18 models
- [ ] Provides real-time odds for live games
- [ ] Handles model failures gracefully
- [ ] Caches predictions appropriately
- [ ] Converts probabilities to multiple odds formats
- [ ] Supports batch prediction requests

### Dependencies
- #2 (Tool Execution Engine) - for model access
- Existing PredictionService infrastructure

### Estimated Effort
- **Orchestrator Core**: 2-3 days (model coordination, caching)
- **Odds Engine**: 1-2 days (probability conversion, multiple formats)
- **Live Integration**: 1-2 days (real-time data pipeline)
- **Testing**: 1-2 days (accuracy validation, edge cases)

### Files to Create/Modify
- `scripts/model_orchestrator.py` - Main orchestration logic
- `scripts/odds_calculator.py` - Probability to odds conversion
- `scripts/live_data_manager.py` - Real-time game state management
- `scripts/model_selector.py` - Best model selection logic
- `tests/test_orchestrator.py` - Integration tests

### Related Issues
 - #2 (Tool Execution Engine)
 - #5 (Real-time Data Pipeline)
 - #7 (API Design)

## Links & Context
- **Next Steps Doc**: [Next Steps](../docs/agents/next_steps.md)
- **SQL Migration**: [MLB Data Completeness](../sql/150_mlb_data_completeness.sql)
- **Related Issue**: #05_documentation_and_issue_linking

**Labels**: enhancement, ml, real-time, orchestration, priority:high
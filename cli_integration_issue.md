## 🎯 Objective
Integrate CLI commands and test end-to-end workflow for the pitch-level modeling pipeline to provide a unified interface for training, evaluation, and serving.

## 📋 Task Breakdown
- [ ] Fix CLI import issues in baseball package
- [ ] Complete pitch-models CLI command integration
- [ ] Test end-to-end workflow from data to predictions
- [ ] Implement CLI commands for model training
- [ ] Add CLI commands for model calibration
- [ ] Create CLI commands for feature population
- [ ] Test CLI integration with database
- [ ] Validate CLI help documentation
- [ ] Implement CLI error handling and logging
- [ ] Create CLI usage examples and documentation

## 🔧 Technical Requirements
- Use Typer framework for CLI interface
- Integrate with baseball namespace structure
- Support all pitch-level modeling operations
- Provide comprehensive help and documentation
- Handle database connection management
- Implement proper error handling and logging
- Support configuration file options
- Enable dry-run modes for testing

## 🎯 Success Criteria
- All pitch-models CLI commands working
- End-to-end workflow tested successfully
- CLI help documentation complete
- Error handling robust and user-friendly
- Database integration seamless
- Configuration management functional
- Performance monitoring available

## 🔗 Dependencies
- Base features population completed (✓ issue #172)
- Engineered features completed (⏳ issue #173)
- Model training completed (⏳ issue #175)
- ML dependencies installed (⏳ issue #176)
- CLI commands implemented (⏳ partial)

## 📅 Timeline
Target completion: Within 3 days

## 🚀 Implementation Strategy
1. Fix CLI import issues in baseball package
2. Complete pitch-models CLI integration
3. Test CLI commands with real data
4. Implement end-to-end workflow testing
5. Add comprehensive help documentation
6. Create usage examples and tutorials
7. Validate error handling and logging
8. Performance test CLI operations

## 📊 CLI Commands to Implement

### Model Training Commands
```bash
# Train tier-1 model
baseball pitch-models train --target tier1 --seasons 2015-2023

# Train tier-2 model
baseball pitch-models train --target tier2 --sample-rate 0.5
```

### Feature Population Commands
```bash
# Populate base features
baseball pitch-models populate-features --type base --all

# Populate engineered features
baseball pitch-models populate-features --type engineered --batch-size 10000
```

### Model Evaluation Commands
```bash
# Calibrate model
baseball pitch-models calibrate --model-path model.joblib --method temperature

# Evaluate model
baseball pitch-models evaluate --model-path model.joblib --test-data test.csv
```

### Status and Monitoring Commands
```bash
# Show pipeline status
baseball pitch-models status

# Show model performance
baseball pitch-models performance --model-path model.joblib
```

## 🔍 Technical Implementation

### CLI Structure
```python
# baseball/cli/commands/pitch_models.py
import typer
from baseball.models.pitch.train_tier1_xgboost import PitchTier1XGBoostModel
from baseball.models.pitch.calibration import PitchModelCalibrator

pitch_app = typer.Typer(help='Pitch-level model commands')

@pitch_app.command()
def train(target: str, seasons: list[int], sample_rate: float):
    """Train pitch-level XGBoost model."""
    model = PitchTier1XGBoostModel(target_tier=target)
    # Training logic here
```

### Main CLI Integration
```python
# baseball/cli/main.py
from baseball.cli.commands.pitch_models import pitch_app
app.add_typer(pitch_app, name='pitch-models', help='Pitch-level model commands')
```

## 🚨 Known Issues to Fix
- Import errors in baseball.cli.commands.live.py
- Missing BookRegion, Sport, MarketStatus enums
- Syntax errors with await outside async functions
- Database connection issues in CLI context

## 🔧 Required Fixes

### Fix Import Errors
```python
# Add missing enums to baseball.betting.schemas.py
class BookRegion(StrEnum):
    US = 'us'
    EU = 'eu'
    UK = 'uk'
    AU = 'au'

class Sport(StrEnum):
    BASEBALL = 'baseball'
    MLB = 'mlb'
    FOOTBALL = 'football'
    NBA = 'nba'
    # ... other sports

class MarketStatus(StrEnum):
    OPEN = 'open'
    CLOSED = 'closed'
    SUSPENDED = 'suspended'
    CANCELLED = 'cancelled'
```

### Fix Async/Await Issues
```python
# Fix live.py syntax errors
if component == 'unified':
    asyncio.run(_test_unified_scheduler(test_type))
elif component == 'service':
    asyncio.run(_test_live_service(test_type))
elif component == 'processor':
    asyncio.run(_test_data_processor(test_type))
```

## 📋 Testing Strategy
1. Unit tests for each CLI command
2. Integration tests with database
3. End-to-end workflow testing
4. Error handling validation
5. Performance testing
6. Documentation validation

## 🔗 Related Issues
- #172: Complete Base Features Population (data source)
- #173: Complete Engineered Features (data source)
- #175: Train Two-Tier XGBoost Model (uses CLI)
- #176: Install ML Dependencies (required for training)
- #177: Build Player Context Features (enhanced features)

## 🎯 Integration Points
- Database connection management
- Model serving integration
- Feature engineering pipeline
- Performance monitoring
- Configuration management

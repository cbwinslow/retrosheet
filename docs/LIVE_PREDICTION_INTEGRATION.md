# Live Prediction System Integration

Complete real-time MLB prediction system integrated into the baseball CLI namespace.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    baseball CLI (Typer)                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   predict    │  │     live     │  │       ingest         │ │
│  │   (app)      │  │    (app)     │  │       (app)          │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
└─────────┼─────────────────┼─────────────────────┼─────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   baseball.predictions                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LivePredictionEngine                                       │  │
│  │ ├── MarkovPitchPredictor (next-pitch)                     │  │
│  │ ├── SwingDecisionPredictor (future)                       │  │
│  │ └── ContactOutcomePredictor (future)                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LiveGameContext                                          │  │
│  │ └── Captures: count, bases, score, pitch_count_pa, etc.  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│              baseball.ingestion (Live Feed)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LiveDataIngestionService                                 │  │
│  │ ├── WebSocket connections                                │  │
│  │ ├── Auto-reconnect with backoff                         │  │
│  │ └── Event hooks for prediction triggers                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SmartScheduler                                           │  │
│  │ ├── Adaptive polling (in-game vs off-hours)             │  │
│  │ └── Idempotent ingestion with checksums                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## CLI Command Reference

### Main Entry Points

All commands accessible via:
```bash
# Module execution
python -m baseball [command]

# Direct CLI (after pip install)
baseball [command]

# Via uv
uv run python -m baseball [command]
```

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `baseball --help` | Show all commands | `baseball --help` |
| `baseball predict --help` | Prediction commands | - |
| `baseball live --help` | Live game tracking | - |
| `baseball live games` | List live games | `baseball live games` |
| `baseball live watch <game>` | Watch game updates | `baseball live watch 717341` |
| `baseball live poll <game>` | Poll game N times | `baseball live poll 717341 --count 10` |
| `baseball live next-pitch <game>` | Predict next pitch | `baseball live next-pitch --game 717341` |
| `baseball live server` | Start prediction server | `baseball live server --port 8000` |

## Python API

### Import from baseball namespace

```python
# Core predictions
from baseball import (
    LivePredictionEngine,
    MarkovPitchPredictor,
    Prediction,
    LiveGameContext,
    get_prediction_engine,
)

# Full module access
from baseball.predictions import PredictionType, display_prediction
```

### Example Usage

```python
from baseball import get_prediction_engine, LiveGameContext

# Get singleton engine
engine = get_prediction_engine()

# Predict next pitch for live game
game_pk = 717341
prediction = engine.predict_next_pitch(game_pk)

if prediction:
    print(f"Predicted: {prediction.prediction}")
    print(f"Confidence: {prediction.confidence:.1%}")
    print(f"Top 3 alternatives:")
    for pitch, prob in sorted(
        prediction.probabilities.items(),
        key=lambda x: -x[1]
    )[:3]:
        print(f"  {pitch}: {prob:.1%}")
```

## Model Training

### Train Markov Pitch Predictor

```bash
# View training statistics
python scripts/train_markov_model.py --stats-only

# Train and persist model
python scripts/train_markov_model.py --seasons 2020 2021 2022 2023 2024 --persist

# Train on all available data
python scripts/train_markov_model.py --persist
```

### Model Storage

- Trained models saved to: `models/markov_pitch_predictor.pkl`
- Uses pickle serialization of transition matrix
- Loaded automatically by `LivePredictionEngine`

## Live Feed System

### Daemon Mode (Continuous Ingestion)

```bash
# Adaptive polling daemon
python scripts/live_feed_runner.py --daemon

# Custom intervals
python scripts/live_feed_runner.py --daemon \
    --in-game-interval 10 \
    --off-hours-interval 3600 \
    --pre-game-minutes 60
```

### Single Run

```bash
# All active games
python scripts/live_feed_runner.py --once --active

# Specific game
python scripts/live_feed_runner.py --once --game-pk 717341
```

### CLI Live Commands

```bash
# List all live games
baseball live games

# Watch a specific game (continuous updates)
baseball live watch 717341

# Poll 10 times then exit
baseball live poll 717341 --count 10

# Predict next pitch
baseball live next-pitch --game 717341
```

## Database Schema

### Core Tables

| Schema | Table | Purpose |
|--------|-------|---------|
| `core` | `live_games` | Current game state |
| `core` | `live_events` | Play-by-play events |
| `raw_mlb` | `live_feed_snapshots` | Raw API responses |
| `predictions` | `prediction_log` | All predictions made |
| `predictions` | `accuracy_summary` | Model performance |

### Prediction Tracking

```sql
-- View recent predictions
SELECT 
    prediction_type,
    predicted_value,
    confidence,
    actual_outcome,
    is_correct
FROM predictions.prediction_log
WHERE game_pk = 717341
ORDER BY created_at DESC
LIMIT 10;

-- View accuracy by model
SELECT 
    prediction_type,
    total_predictions,
    correct_predictions,
    accuracy_rate,
    avg_confidence
FROM predictions.accuracy_summary
ORDER BY accuracy_rate DESC;
```

## Data Flow

### Real-Time Prediction Pipeline

```
1. MLB API (Live Feed)
   ↓
2. LiveDataIngestionService (WebSocket/polling)
   ↓
3. raw_mlb.live_feed_snapshots (persist raw)
   ↓
4. transform_live_game() (transform to canonical)
   ↓
5. core.live_games + core.live_events (update state)
   ↓
6. LivePredictionEngine (generate prediction)
   ↓
7. predictions.prediction_log (record prediction)
   ↓
8. CLI / WebSocket / API (serve to users)
```

### Prediction Lifecycle

```
Event: New pitch recorded
  ↓
Action: Update live_games state
  ↓
Trigger: Generate prediction for NEXT pitch
  ↓
Query: Markov transition matrix P(next | count, prev)
  ↓
Store: Log prediction with confidence
  ↓
Display: Show via CLI or broadcast via WebSocket
  ↓
Event: Actual pitch occurs
  ↓
Action: Record actual_outcome in prediction_log
  ↓
Update: Calculate is_correct, update accuracy_summary
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MLB_DATABASE_URL` | - | PostgreSQL connection string |
| `MLB_LIVE_POLL_INTERVAL` | 10 | In-game poll interval (seconds) |
| `MLB_OFF_HOURS_INTERVAL` | 3600 | Off-hours poll interval (seconds) |
| `MLB_WEBSOCKET_ENABLED` | false | Enable WebSocket ingestion |
| `MLB_MODEL_PATH` | models/ | Path to trained models |

### Polling Schedule

| Game State | Interval | Trigger |
|------------|----------|---------|
| Pre-game (< 60 min) | 60s | Game about to start |
| Live | 10s | In progress |
| Between innings | 30s | Transition |
| Post-game | 300s | Recently ended |
| Off-hours | 3600s | No games today |

## Testing

### Integration Tests

```bash
# Run CLI integration tests
python scripts/test_cli_integration.py

# Run with verbose output
python scripts/test_cli_integration.py --verbose
```

### Manual Verification

```bash
# 1. Verify imports work
python -c "from baseball import LivePredictionEngine; print('✓ Imports work')"

# 2. Verify CLI structure
baseball --help
baseball live --help
baseball predict --help

# 3. Test predictions (requires live game)
baseball live games
baseball live next-pitch --game <game_pk>
```

## Future Extensions

### Planned Predictions

| Prediction Type | Status | Model |
|-------------------|--------|-------|
| Next pitch type | ✅ Complete | Markov Chain |
| Swing/Take decision | 🚧 Planned | Logistic Regression |
| Contact/Out outcome | 🚧 Planned | XGBoost |
| PA result | 🚧 Planned | LSTM |
| Game state transition | 🚧 Planned | Markov Chain |

### Advanced Models

| Model | Purpose |
|-------|---------|
| LSTM Sequential | Pitch sequence patterns |
| XGBoost Hierarchical | Ball/Strike/Play + outcome |
| Multi-Task NN | Pitch type + location jointly |
| Transformer | Context-aware predictions |

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: baseball` | Run from repo root or install package |
| No live games found | Check MLB schedule, may be off-season |
| Predictions not accurate | Run `train_markov_model.py --persist` |
| WebSocket disconnects | Check network, auto-reconnect enabled |

### Debug Commands

```bash
# Check database connection
python -c "from baseball.core.db import get_db_connection; print(get_db_connection())"

# Verify live data exists
psql -d mlb -c "SELECT COUNT(*) FROM core.live_games;"

# Check training data
psql -d mlb -c "SELECT COUNT(*) FROM pitch_sequence.training_rows;"
```

## Performance

### Benchmarks

| Operation | Target | Notes |
|-----------|--------|-------|
| Prediction latency | < 10ms | From context → prediction |
| Ingestion throughput | > 100 games/min | Parallel processing |
| Database writes | < 50ms | Indexed tables |
| WebSocket broadcast | < 5ms | Async handlers |

### Scaling

| Component | Strategy |
|-----------|----------|
| Ingestion | Horizontal (per-game workers) |
| Predictions | Caching (per-pitcher models) |
| Database | Read replicas for queries |
| WebSockets | Connection pooling |

---

**System Status**: ✅ Complete and Integrated
- All CLI commands registered
- Namespace exports configured
- Models trainable and loadable
- Real-time pipeline operational

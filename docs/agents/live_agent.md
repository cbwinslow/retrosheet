# Live Data Agent Guidance

**Role**: Real-time data ingestion, streaming, WebSocket handling, and live prediction loops.

---

## Scope

You are responsible for:
- MLB live feed ingestion (`baseball/sources/mlb.py`)
- Real-time polling and streaming architecture
- Event processing and deduplication
- Live game state management
- Low-latency feature computation
- WebSocket infrastructure (future)
- Live prediction loops

---

## Key Documents

| Document | When to Use |
|----------|-------------|
| `docs/architecture.md` | Live data flow patterns |
| `docs/keys_and_grains.md` | Live entity keys |
| `docs/migration_plan.md` | Phase 3 milestones |

---

## Live Data Architecture

```
MLB API → Raw Snapshots → Event Processor → Core Live → Features Live → Predictions
    ↑           ↓              ↓               ↓            ↓            ↓
    └─────── Polling      Deduplication    State Mgmt    Incremental   Serving
        (every 10s)       (checksum)        (mutable)     Compute       (cache)
```

---

## Data Sources

### MLB Stats API (Primary)

- **Schedule**: Daily game list
- **Live Feed**: Per-game play-by-play (`/game/{game_pk}/feed/live`)
- **Rate Limit**: ~100 req/min (be conservative)
- **Format**: JSON (GUMBO schema)

### ESPN (Secondary/Fallback)

- **Scoreboard**: Daily scores
- **Gamecast**: Per-game details
- **Rate Limit**: ~60 req/min
- **Format**: JSON

---

## Polling Strategy

### Active Game Detection

```python
def get_active_games(date: str) -> List[int]:
    """Get list of game_pks for active games."""
    schedule = mlb_api.get_schedule(date)
    active = [
        game['gamePk'] 
        for game in schedule['dates'][0]['games']
        if game['status']['abstractGameState'] in ['Live', 'Preview']
    ]
    return active
```

### Smart Polling Intervals

```python
POLL_INTERVALS = {
    'Preview': 300,      # 5 min before game
    'Warmup': 60,       # 1 min during warmup
    'Live': 10,         # 10 sec during live play
    'Delayed': 60,      # 1 min during delays
    'End': 300,         # 5 min after game
}

def get_poll_interval(game_status: str) -> int:
    return POLL_INTERVALS.get(game_status, 60)
```

---

## Raw Persistence

### Snapshot Storage

```sql
CREATE TABLE raw_mlb.live_feed_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_pk INTEGER NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL,
    payload_checksum VARCHAR(64) NOT NULL,
    mlb_timestamp TIMESTAMP,  -- From API response
    ingest_latency_ms INTEGER,  -- Time from MLB to our DB
    UNIQUE(game_pk, payload_checksum)
);

-- Index for deduplication lookup
CREATE INDEX idx_snapshots_lookup 
ON raw_mlb.live_feed_snapshots(game_pk, payload_checksum);

-- Index for recent snapshots
CREATE INDEX idx_snapshots_recent 
ON raw_mlb.live_feed_snapshots(game_pk, snapshot_timestamp DESC);
```

### Deduplication

```python
import hashlib
import json

def compute_checksum(payload: dict) -> str:
    """Compute MD5 checksum of canonical JSON."""
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(canonical.encode()).hexdigest()

def is_duplicate(game_pk: int, checksum: str) -> bool:
    """Check if we've already stored this payload."""
    query = """
    SELECT 1 FROM raw_mlb.live_feed_snapshots 
    WHERE game_pk = %s AND payload_checksum = %s
    """
    return db.execute(query, (game_pk, checksum)).fetchone() is not None
```

---

## Event Processing

### Change Detection

Only process events that have changed:

```python
def get_new_events(game_pk: int, current_payload: dict) -> List[dict]:
    """Extract only new events since last processed."""
    last_checkpoint = load_checkpoint(f"mlb_live_{game_pk}")
    
    all_plays = current_payload['liveData']['plays']['allPlays']
    
    if last_checkpoint:
        last_play_id = last_checkpoint['last_play_id']
        new_plays = [p for p in all_plays if p['playId'] > last_play_id]
    else:
        new_plays = all_plays
    
    return new_plays
```

### Event Transformation

```python
def transform_play(play: dict, game_pk: int) -> LiveEvent:
    """Transform MLB play to canonical event."""
    return LiveEvent(
        mlb_game_pk=game_pk,
        play_id=play['playId'],
        inning=play['about']['inning'],
        half_inning=play['about']['halfInning'],
        outs=play['count']['outs'],
        balls=play['count']['balls'],
        strikes=play['count']['strikes'],
        batter_id=play['matchup']['batter']['id'],
        pitcher_id=play['matchup']['pitcher']['id'],
        event_type=play['result']['eventType'],
        description=play['result']['description'],
        rbi=play['result']['rbi'],
        away_score=play['result']['awayScore'],
        home_score=play['result']['homeScore'],
        is_scoring_play=play['result']['isScoringPlay'],
        wall_clock_time=play['about']['endTime'],
    )
```

---

## Live State Management

### Mutable Live Tables

Unlike historical tables, live tables are updated in real-time:

```sql
CREATE TABLE core.live_games (
    live_game_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mlb_game_pk INTEGER UNIQUE NOT NULL,
    game_date DATE NOT NULL,
    status VARCHAR(20),
    inning INTEGER,
    top_bottom VARCHAR(10),
    outs INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    runner_on_1b BOOLEAN,
    runner_on_2b BOOLEAN,
    runner_on_3b BOOLEAN,
    current_batter_id UUID,
    current_pitcher_id UUID,
    last_event_id VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trigger to auto-update timestamp
CREATE OR REPLACE FUNCTION update_live_game_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_live_games_updated
    BEFORE UPDATE ON core.live_games
    FOR EACH ROW
    EXECUTE FUNCTION update_live_game_timestamp();
```

### State Updates

```python
def update_live_game_state(game_pk: int, payload: dict):
    """Update mutable game state from live feed."""
    live_data = payload['liveData']
    linescore = live_data['linescore']
    
    query = """
    INSERT INTO core.live_games (
        mlb_game_pk, game_date, status, inning, top_bottom, outs,
        home_score, away_score, runner_on_1b, runner_on_2b, runner_on_3b
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (mlb_game_pk) DO UPDATE SET
        status = EXCLUDED.status,
        inning = EXCLUDED.inning,
        top_bottom = EXCLUDED.top_bottom,
        outs = EXCLUDED.outs,
        home_score = EXCLUDED.home_score,
        away_score = EXCLUDED.away_score,
        runner_on_1b = EXCLUDED.runner_on_1b,
        runner_on_2b = EXCLUDED.runner_on_2b,
        runner_on_3b = EXCLUDED.runner_on_3b,
        updated_at = NOW()
    """
    
    db.execute(query, (
        game_pk,
        payload['gameData']['datetime']['officialDate'],
        linescore[' inningState'],
        linescore['currentInning'],
        linescore['inningHalf'],
        linescore['outs'],
        linescore['teams']['home']['runs'],
        linescore['teams']['away']['runs'],
        linescore['offense']['first'] is not None,
        linescore['offense']['second'] is not None,
        linescore['offense']['third'] is not None,
    ))
```

---

## Feature Computation

### Incremental Updates

Only recompute features affected by new events:

```python
def update_live_features(game_pk: int, new_events: List[LiveEvent]):
    """Incrementally update features for affected plays."""
    for event in new_events:
        # Recompute state-based features
        features = compute_state_features(event)
        
        # Store
        store_live_features(game_pk, event.play_id, features)
        
        # Trigger prediction
        trigger_prediction(game_pk, event.play_id)
```

### Fast Lookups

```sql
-- Pre-computed lookup tables for fast feature access
CREATE TABLE features.run_expectancy_lookup (
    outs INTEGER,
    runner_1b BOOLEAN,
    runner_2b BOOLEAN,
    runner_3b BOOLEAN,
    run_expectancy DECIMAL(5,3),
    PRIMARY KEY (outs, runner_1b, runner_2b, runner_3b)
);

-- Materialized view for player form
CREATE MATERIALIZED VIEW features.current_player_form AS
SELECT 
    player_id,
    AVG(batting_avg) OVER (ORDER BY game_date ROWS BETWEEN 30 PRECEDING AND CURRENT ROW) as rolling_avg_30d,
    AVG(batting_avg) OVER (ORDER BY game_date ROWS BETWEEN 7 PRECEDING AND CURRENT ROW) as rolling_avg_7d
FROM player_stats
WHERE game_date >= CURRENT_DATE - INTERVAL '30 days';
```

---

## Prediction Loop

### Real-Time Scoring

```python
async def prediction_loop(game_pk: int, model_id: UUID):
    """Continuously score live game."""
    while True:
        # Get current state
        state = get_live_game_state(game_pk)
        
        # Compute features
        features = compute_live_features(state)
        
        # Score
        model = load_model(model_id)
        prediction = model.predict_proba([features])[0][1]
        
        # Store
        store_prediction(model_id, game_pk, prediction, features)
        
        # Check if game ended
        if state.status == 'Final':
            break
        
        # Wait for next poll
        await asyncio.sleep(get_poll_interval(state.status))
```

---

## Error Handling

### Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((HTTPError, Timeout))
)
def fetch_live_feed(game_pk: int) -> dict:
    """Fetch with exponential backoff."""
    return mlb_api.get_live_feed(game_pk)
```

### Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerOpen()
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
```

---

## Monitoring

### Key Metrics

Track these for live pipeline:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Ingest latency | < 30s | > 60s |
| Event processing lag | < 5s | > 15s |
| API error rate | < 1% | > 5% |
| Prediction latency | < 100ms | > 500ms |
| Deduplication ratio | > 80% | < 50% |

### Health Checks

```python
def health_check() -> HealthStatus:
    """Return system health for monitoring."""
    return HealthStatus(
        last_snapshot_age=time.time() - get_last_snapshot_time(),
        active_games_count=get_active_games_count(),
        pending_events_count=get_pending_events_count(),
        api_error_rate=get_error_rate(minutes=5),
        db_connection_healthy=check_db_connection(),
    )
```

---

## WebSocket (Future)

### Architecture

```
MLB WebSocket → Message Queue → Processors → Database → WebSocket Server → Clients
```

### Message Types

```python
class LiveMessage:
    game_pk: int
    message_type: str  # 'play', 'status', 'score'
    timestamp: datetime
    payload: dict
```

---

## Review Checklist

Before submitting live data changes:

- [ ] Polling intervals appropriate for game state
- [ ] Deduplication working correctly
- [ ] Only changed events processed
- [ ] Error handling with retry logic
- [ ] Circuit breaker for API failures
- [ ] Latency metrics tracked
- [ ] State updates are atomic
- [ ] Fallback to secondary source implemented
- [ ] No blocking operations in main loop

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial live data agent guidance |

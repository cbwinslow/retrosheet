# Phase 3: Feature Calculators - Run Expectancy & Bullpen Stress

## Prerequisites
- Phase 2 foundation complete
- CLI commands working
- Database connectivity verified

## Goal
Implement missing feature calculators and wire them to CLI/pipelines.

---

## Task 3.1: Implement Run Expectancy Calculator

### Background
Run Expectancy (RE) is the expected number of runs scored given:
- Base state (bases empty, runner on 1st, etc.) = 8 possibilities
- Outs (0, 1, 2) = 3 possibilities
- Total: 24 base-out states

It's a foundational sabermetric feature used in Win Expectancy and Leverage Index.

### Current State
- Mentioned in `baseball/features/__init__.py` docstring
- No `run_expectancy.py` file exists
- No SQL table exists

### Requirements

#### 3.1.1 Create `baseball/features/run_expectancy.py`

```python
class RunExpectancyCalculator(FeatureStore):
    """Calculator for Run Expectancy (RE) features.
    
    Run Expectancy is the expected number of runs scored
    in the remainder of the inning given the current base-out state.
    """
    
    def __init__(self):
        super().__init__('run_expectancy')
        self.matrix: dict[tuple[int, int], float] = {}  # (base_state, outs) -> runs
    
    @property
    def feature_name(self) -> str:
        return 'run_expectancy'
    
    @property
    def table_name(self) -> str:
        return 'features.run_expectancy_matrix'
    
    def build(self, config: FeatureConfig, conn: Any) -> FeatureResult:
        """Build RE matrix from historical data."""
        # Query historical games for all base-out transitions
        # Calculate average runs scored from each state
        # Store in features.run_expectancy_matrix
        pass
    
    def get_re(self, base_state: int, outs: int) -> float:
        """Get run expectancy for a base-out state.
        
        Args:
            base_state: 0-7 representing bases (0=empty, 1=1st, 2=2nd, 3=3rd, 
                       4=1st+2nd, 5=1st+3rd, 6=2nd+3rd, 7=loaded)
            outs: 0, 1, or 2
        
        Returns:
            Expected runs for remainder of inning
        """
        pass
    
    def get_re24(self, inning: int, base_state: int, outs: int, 
                 score_diff: int) -> float:
        """Get RE24-style value (run value of play).
        
        RE24 = (RE_start - RE_end - runs_scored_on_play)
        """
        pass
```

#### 3.1.2 Create SQL Table

Create `sql/50_features/501_features_run_expectancy.sql`:

```sql
/*
File: sql/50_features/501_features_run_expectancy.sql
Purpose: Run Expectancy matrix storage
Author: Agent [codex]
Date: 2026-04-28
Depends On: None
Called By: baseball/features/run_expectancy.py

Tables Created:
- features.run_expectancy_matrix (24 base-out states)
- features.run_expectancy_by_inning (optional - inning-specific)
*/

CREATE TABLE IF NOT EXISTS features.run_expectancy_matrix (
    id SERIAL PRIMARY KEY,
    base_state SMALLINT NOT NULL CHECK (base_state BETWEEN 0 AND 7),
    outs SMALLINT NOT NULL CHECK (outs BETWEEN 0 AND 2),
    expected_runs NUMERIC(5,3) NOT NULL,
    avg_runs_scored NUMERIC(5,3),  -- From historical data
    occurrences INTEGER,  -- Number of times this state occurred
    season SMALLINT,  -- Season this matrix was computed from (NULL = all time)
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(base_state, outs, season)
);

COMMENT ON TABLE features.run_expectancy_matrix IS 
    'Run expectancy matrix: expected runs from each base-out state';

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_re_matrix_lookup 
    ON features.run_expectancy_matrix(base_state, outs, season);

-- Insert standard values (can be overwritten by computed values)
-- These are approximate MLB averages, should be computed from actual data
INSERT INTO features.run_expectancy_matrix (base_state, outs, expected_runs, season)
VALUES 
    (0, 0, 0.461, NULL),  -- Bases empty, 0 outs
    (0, 1, 0.243, NULL),  -- Bases empty, 1 out
    (0, 2, 0.095, NULL),  -- Bases empty, 2 outs
    (1, 0, 0.831, NULL),  -- Runner on 1st, 0 outs
    (1, 1, 0.489, NULL),  -- Runner on 1st, 1 out
    (1, 2, 0.214, NULL),  -- Runner on 1st, 2 outs
    (2, 0, 1.068, NULL),  -- Runner on 2nd, 0 outs
    (2, 1, 0.644, NULL),  -- Runner on 2nd, 1 out
    (2, 2, 0.305, NULL),  -- Runner on 2nd, 2 outs
    (3, 0, 1.426, NULL),  -- Runner on 3rd, 0 outs
    (3, 1, 0.864, NULL),  -- Runner on 3rd, 1 out
    (3, 2, 0.413, NULL),  -- Runner on 3rd, 2 outs
    (4, 0, 1.313, NULL),  -- 1st & 2nd, 0 outs
    (4, 1, 0.814, NULL),  -- 1st & 2nd, 1 out
    (4, 2, 0.400, NULL),  -- 1st & 2nd, 2 outs
    (5, 0, 1.741, NULL),  -- 1st & 3rd, 0 outs
    (5, 1, 1.118, NULL),  -- 1st & 3rd, 1 out
    (5, 2, 0.510, NULL),  -- 1st & 3rd, 2 outs
    (6, 0, 1.844, NULL),  -- 2nd & 3rd, 0 outs
    (6, 1, 1.152, NULL),  -- 2nd & 3rd, 1 out
    (6, 2, 0.494, NULL),  -- 2nd & 3rd, 2 outs
    (7, 0, 2.292, NULL),  -- Bases loaded, 0 outs
    (7, 1, 1.542, NULL),  -- Bases loaded, 1 out
    (7, 2, 0.747, NULL)   -- Bases loaded, 2 outs
ON CONFLICT (base_state, outs, season) DO NOTHING;
```

#### 3.1.3 Implement Build Logic

The calculator should:
1. Query `core.events` for all plate appearances
2. For each base-out state, track runs scored in remainder of inning
3. Average across all occurrences
4. Store in matrix table

```python
def build(self, config: FeatureConfig, conn: Any) -> FeatureResult:
    """Compute RE matrix from historical data."""
    result = FeatureResult(feature_name=self.feature_name)
    
    try:
        with conn.cursor() as cur:
            # Query all base-out transitions with runs scored
            cur.execute("""
                WITH base_out_states AS (
                    SELECT 
                        game_id,
                        event_id,
                        inning,
                        base_state,
                        outs,
                        runs_on_play,
                        leadoff_flag
                    FROM core.events
                    WHERE season = %s
                ),
                runs_by_state AS (
                    SELECT 
                        base_state,
                        outs,
                        AVG(runs_scored_after) as expected_runs,
                        COUNT(*) as occurrences
                    FROM (
                        SELECT 
                            bos.*,
                            SUM(subsequent.runs_on_play) as runs_scored_after
                        FROM base_out_states bos
                        JOIN base_out_states subsequent
                            ON bos.game_id = subsequent.game_id
                            AND bos.inning = subsequent.inning
                            AND bos.event_id <= subsequent.event_id
                        GROUP BY bos.game_id, bos.event_id, bos.base_state, bos.outs
                    )
                    GROUP BY base_state, outs
                )
                SELECT base_state, outs, expected_runs, occurrences
                FROM runs_by_state
                ORDER BY base_state, outs
            """, (config.season,))
            
            # Insert results into matrix table
            for row in cur.fetchall():
                self.save_re_state(conn, row[0], row[1], row[2], row[3], config.season)
        
        result.success = True
        result.rows_processed = 24  # All states
        
    except Exception as e:
        result.success = False
        result.error = str(e)
    
    return result
```

#### 3.1.4 Wire to CLI

Update `baseball/cli.py`:
```python
@features_app.command(name='compute')
def features_compute(
    calculator: str = typer.Option(..., '--calculator', '-c', ...),
    season: int = typer.Option(..., '--season', '-s', ...),
):
    """Compute features for a season."""
    calculators = {
        'win_expectancy': WinExpectancyCalculator,
        'leverage_index': LeverageIndexCalculator,
        'run_expectancy': RunExpectancyCalculator,  # ADD THIS
        # ... others
    }
    # ... existing logic
```

#### 3.1.5 Update `__init__.py`

```python
from .run_expectancy import RunExpectancyCalculator

__all__ = [
    # ... existing
    'RunExpectancyCalculator',  # ADD THIS
]
```

#### 3.1.6 Add Tests

Create `tests/unit/test_run_expectancy.py`:

```python
import pytest
from baseball.features.run_expectancy import RunExpectancyCalculator

class TestRunExpectancyCalculator:
    def test_init(self):
        calc = RunExpectancyCalculator()
        assert calc.feature_name == 'run_expectancy'
    
    def test_get_re_empty_bases(self, db_conn):
        calc = RunExpectancyCalculator()
        calc.load_matrix(db_conn)
        
        # Bases empty, 0 outs should be ~0.5 runs
        re = calc.get_re(base_state=0, outs=0)
        assert 0.4 < re < 0.6
    
    def test_get_re_bases_loaded(self, db_conn):
        calc = RunExpectancyCalculator()
        calc.load_matrix(db_conn)
        
        # Bases loaded, 0 outs should be ~2.3 runs
        re = calc.get_re(base_state=7, outs=0)
        assert 2.0 < re < 2.5
    
    def test_re_decreases_with_outs(self, db_conn):
        calc = RunExpectancyCalculator()
        calc.load_matrix(db_conn)
        
        # Same base state, more outs = lower RE
        re_0_outs = calc.get_re(base_state=1, outs=0)
        re_2_outs = calc.get_re(base_state=1, outs=2)
        assert re_0_outs > re_2_outs
```

---

## Task 3.2: Implement/Verify Bullpen Stress Calculator

### Background
Bullpen stress measures reliever fatigue and availability. Critical for late-game predictions.

### Current State
`bullpen.py` has `BullpenCalculator` with:
- `RelieverFatigue` dataclass
- `TeamBullpenStatus` dataclass
- `get_team_bullpen()`, `get_reliever_fatigue()` methods
- Fatigue scoring logic

### Analysis
Read `baseball/features/bullpen.py` completely and determine:
1. Is this sufficient for "bullpen stress" feature?
2. Or do we need a separate `BullpenStressCalculator`?
3. What's missing?

### Requirements (if needed)

If `BullpenCalculator` is sufficient, just wire it properly. If gaps exist:

#### 3.2.1 Extend BullpenCalculator or Create BullpenStressCalculator

```python
class BullpenStressCalculator(FeatureStore):
    """Calculator for bullpen stress/fatigue features.
    
    Measures reliever fatigue, availability, and effectiveness
    for late-game situations.
    """
    
    def calculate_stress_index(self, team_id: int, game_date: date) -> float:
        """Calculate bullpen stress index (0-1, higher = more stressed)."""
        # Factors:
        # - Total pitches thrown in last 3 days
        # - Number of relievers used yesterday
        # - Days of rest available
        # - Average leverage faced
        # - Key reliever availability
        pass
    
    def get_late_game_confidence(self, team_id: int, 
                                  inning: int, game_date: date) -> float:
        """Confidence in bullpen for late-game situation (9th inning, etc.)."""
        # Higher stress = lower confidence
        pass
```

#### 3.2.2 Create SQL Table

Create `sql/50_features/502_features_bullpen_stress.sql`:

```sql
/*
File: sql/50_features/502_features_bullpen_stress.sql
Purpose: Bullpen stress metrics
Author: Agent [codex]
Date: 2026-04-28
*/

CREATE TABLE IF NOT EXISTS features.bullpen_stress (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL,
    game_date DATE NOT NULL,
    season SMALLINT NOT NULL,
    
    -- Stress metrics
    stress_index NUMERIC(4,3),  -- 0-1 composite score
    total_pitches_3d INTEGER,  -- Pitches thrown last 3 days
    relievers_used_yesterday INTEGER,
    avg_leverage_faced_3d NUMERIC(4,3),
    
    -- Availability
    available_pitchers INTEGER,
    key_relievers_available INTEGER,
    
    -- Effectiveness (recent performance)
    bullpen_era_7d NUMERIC(5,2),
    bullpen_whip_7d NUMERIC(4,2),
    
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(team_id, game_date)
);

COMMENT ON TABLE features.bullpen_stress IS 
    'Bullpen fatigue and stress metrics by team and date';

CREATE INDEX IF NOT EXISTS idx_bullpen_stress_lookup 
    ON features.bullpen_stress(team_id, game_date);
```

#### 3.2.3 Wire to CLI

Add to `features compute` command.

---

## Task 3.3: Update Pipeline Config

### Current State
`config/pipelines.yml` has `feature_building` pipeline with steps:
- run_expectancy
- win_expectancy
- leverage_index
- matchup_features
- rolling_form

### Requirements

1. Verify all feature calculators referenced exist
2. Fix any references to non-existent calculators
3. Ensure pipeline can call `build()` on each calculator

```yaml
feature_building:
  description: "Build all ML features from ingested data"
  steps:
    - run_expectancy      # Now exists
    - win_expectancy      # Exists
    - leverage_index      # Exists
    - matchup_features    # Exists (via MatchupCalculator)
    - rolling_form        # Exists
    - bullpen_stress      # ADD or verify
```

---

## Task 3.4: Integration Testing

### Test Plan

1. **Unit Tests**: Each calculator in isolation
2. **Integration Tests**: Calculator + database
3. **E2E Test**: Full feature pipeline

```python
# tests/e2e/test_features_pipeline.py
def test_feature_building_pipeline():
    """Test that feature building pipeline works end-to-end."""
    # Run pipeline for a small test season
    # Verify all feature tables populated
    # Check row counts match expected
```

---

## Documentation Updates

1. **AGENTS.md**:
   - Mark Run Expectancy as complete
   - Mark Bullpen Stress as complete

2. **PROJECT_LOG.md**:
   - Entry: "Phase 3: Feature calculators implemented"
   - List new calculators

3. **FILE_INVENTORY.md**:
   - Add new SQL files
   - Add new Python files
   - Add new test files

---

## Validation Steps

```bash
# 1. Import test
python -c "from baseball.features import RunExpectancyCalculator; print('OK')"

# 2. SQL test
psql -c "\dt features.*" | grep run_expectancy

# 3. CLI test
baseball features compute --calculator run_expectancy --season 2024 --dry-run

# 4. Pipeline test
baseball pipeline run --pipeline feature_building --year 2024 --dry-run

# 5. Demo script
python scripts/demo_full_system.py --mode quick
# Should show: Feature Calculators: 6/6 ✅

# 6. Tests
python -m pytest tests/unit/test_run_expectancy.py tests/unit/test_bullpen.py -v
```

---

## Success Criteria

- [ ] `RunExpectancyCalculator` implemented and tested
- [ ] `sql/50_features/501_features_run_expectancy.sql` created
- [ ] RE matrix table populated with values
- [ ] Bullpen stress calculator working
- [ ] Both calculators wired to CLI
- [ ] Pipeline config updated
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Demo shows 6/6 calculators

---

## Time Estimate

5-6 hours for complete implementation, SQL, tests, and integration.

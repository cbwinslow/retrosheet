# Phase 5: Serving Layer & Performance Optimization

## Prerequisites
- Phase 4 models complete
- Win Probability model working
- Feature calculators all functional

## Goal
Build low-latency serving layer for real-time predictions.

---

## Task 5.1: Create Serving Materialized Views

### Background
Live predictions need <100ms latency. Materialized views pre-compute commonly accessed data.

### Current State
Only 1 file in `sql/70_serving/`. Need more for fast lookups.

### Requirements

#### 5.1.1 Current Standings View

Create `sql/70_serving/701_mv_current_standings.sql`:

```sql
/*
File: sql/70_serving/701_mv_current_standings.sql
Purpose: Pre-computed team standings for fast lookup
Author: Agent [codex]
Date: 2026-04-28
*/

CREATE MATERIALIZED VIEW IF NOT EXISTS serving.mv_current_standings AS
WITH team_records AS (
    SELECT 
        g.home_team_id as team_id,
        COUNT(*) FILTER (WHERE g.home_score > g.away_score) as wins_home,
        COUNT(*) FILTER (WHERE g.home_score < g.away_score) as losses_home,
        SUM(g.home_score) as runs_scored_home,
        SUM(g.away_score) as runs_allowed_home
    FROM core.games g
    WHERE g.season = (SELECT MAX(season) FROM core.games)
      AND g.game_type = 'R'  -- Regular season
    GROUP BY g.home_team_id
    
    UNION ALL
    
    SELECT 
        g.away_team_id as team_id,
        COUNT(*) FILTER (WHERE g.away_score > g.home_score) as wins_away,
        COUNT(*) FILTER (WHERE g.away_score < g.home_score) as losses_away,
        SUM(g.away_score) as runs_scored_away,
        SUM(g.home_score) as runs_allowed_away
    FROM core.games g
    WHERE g.season = (SELECT MAX(season) FROM core.games)
      AND g.game_type = 'R'
    GROUP BY g.away_team_id
)
SELECT 
    t.team_id,
    t.team_name,
    t.division,
    SUM(COALESCE(tr.wins_home, 0) + COALESCE(tr.wins_away, 0)) as wins,
    SUM(COALESCE(tr.losses_home, 0) + COALESCE(tr.losses_away, 0)) as losses,
    ROUND(
        SUM(COALESCE(tr.wins_home, 0) + COALESCE(tr.wins_away, 0))::numeric /
        NULLIF(SUM(COALESCE(tr.wins_home, 0) + COALESCE(tr.wins_away, 0) + 
                   COALESCE(tr.losses_home, 0) + COALESCE(tr.losses_away, 0)), 0),
        3
    ) as win_pct,
    SUM(COALESCE(tr.runs_scored_home, 0) + COALESCE(tr.runs_scored_away, 0)) as runs_scored,
    SUM(COALESCE(tr.runs_allowed_home, 0) + COALESCE(tr.runs_allowed_away, 0)) as runs_allowed,
    SUM(COALESCE(tr.runs_scored_home, 0) + COALESCE(tr.runs_scored_away, 0)) - 
    SUM(COALESCE(tr.runs_allowed_home, 0) + COALESCE(tr.runs_allowed_away, 0)) as run_diff,
    games_behind(t.division, t.team_id) as gb  -- Function to calculate games behind
FROM core.teams t
LEFT JOIN team_records tr ON t.team_id = tr.team_id
WHERE t.active = true
GROUP BY t.team_id, t.team_name, t.division
ORDER BY t.division, win_pct DESC, run_diff DESC;

-- Index for fast lookup
CREATE UNIQUE INDEX idx_mv_standings_team 
    ON serving.mv_current_standings(team_id);
CREATE INDEX idx_mv_standings_division 
    ON serving.mv_current_standings(division);

COMMENT ON MATERIALIZED VIEW serving.mv_current_standings IS 
    'Pre-computed team standings for <50ms lookup';
```

#### 5.1.2 Player Form View

Create `sql/70_serving/702_mv_player_form_30d.sql`:

```sql
/*
File: sql/70_serving/702_mv_player_form_30d.sql
Purpose: 30-day rolling player performance
Author: Agent [codex]
Date: 2026-04-28
*/

CREATE MATERIALIZED VIEW IF NOT EXISTS serving.mv_player_form_30d AS
WITH recent_plate_appearances AS (
    SELECT 
        pa.batter_id as player_id,
        'batter' as role,
        pa.game_date,
        pa.at_bat_result,
        pa.exit_velocity,
        pa.launch_angle,
        CASE 
            WHEN pa.at_bat_result IN ('single', 'double', 'triple', 'home_run') THEN 1 
            ELSE 0 
        END as hit,
        CASE 
            WHEN pa.at_bat_result = 'home_run' THEN 1 
            ELSE 0 
        END as hr,
        CASE 
            WHEN pa.at_bat_result = 'strikeout' THEN 1 
            ELSE 0 
        END as so
    FROM core.plate_appearances pa
    WHERE pa.game_date >= CURRENT_DATE - INTERVAL '30 days'
      AND pa.at_bat_result IS NOT NULL
    
    UNION ALL
    
    SELECT 
        pa.pitcher_id as player_id,
        'pitcher' as role,
        pa.game_date,
        pa.at_bat_result,
        NULL as exit_velocity,
        NULL as launch_angle,
        CASE 
            WHEN pa.at_bat_result IN ('single', 'double', 'triple', 'home_run') THEN 1 
            ELSE 0 
        END as hit_allowed,
        CASE 
            WHEN pa.at_bat_result = 'home_run' THEN 1 
            ELSE 0 
        END as hr_allowed,
        CASE 
            WHEN pa.at_bat_result = 'strikeout' THEN 1 
            ELSE 0 
        END as so_made
    FROM core.plate_appearances pa
    WHERE pa.game_date >= CURRENT_DATE - INTERVAL '30 days'
      AND pa.pitcher_id IS NOT NULL
)
SELECT 
    player_id,
    role,
    COUNT(*) as pa_last_30d,
    AVG(hit::float) as avg_last_30d,
    AVG(hr::float) as hr_rate_last_30d,
    AVG(so::float) as k_rate_last_30d,
    AVG(exit_velocity) as avg_ev_last_30d,
    AVG(launch_angle) as avg_la_last_30d,
    CASE 
        WHEN AVG(hit::float) > 0.300 THEN 'hot'
        WHEN AVG(hit::float) < 0.200 THEN 'cold'
        ELSE 'average'
    END as form_trend,
    MAX(game_date) as last_game
FROM recent_plate_appearances
GROUP BY player_id, role;

CREATE UNIQUE INDEX idx_mv_player_form_lookup 
    ON serving.mv_player_form_30d(player_id, role);

COMMENT ON MATERIALIZED VIEW serving.mv_player_form_30d IS 
    '30-day rolling player stats for live form lookups';
```

#### 5.1.3 WE/LI Lookup Views

Create `sql/70_serving/703_mv_we_li_lookup.sql`:

```sql
/*
File: sql/70_serving/703_mv_we_li_lookup.sql
Purpose: Fast WE/LI matrix lookups
Author: Agent [codex]
Date: 2026-04-28
*/

-- Win Expectancy lookup (already exists, verify)
CREATE MATERIALIZED VIEW IF NOT EXISTS serving.mv_we_lookup AS
SELECT 
    inning,
    CASE WHEN is_top_inning THEN 1 ELSE 0 END as is_top,
    home_score - away_score as score_diff,
    base_state,
    outs,
    win_probability as wp_home,
    1 - win_probability as wp_away
FROM features.win_expectancy_matrix;

-- Leverage Index lookup
CREATE MATERIALIZED VIEW IF NOT EXISTS serving.mv_li_lookup AS
SELECT 
    inning,
    CASE WHEN is_top_inning THEN 1 ELSE 0 END as is_top,
    score_diff,
    base_state,
    outs,
    leverage_index as li,
    leverage_rating
FROM features.leverage_index_matrix;

CREATE INDEX idx_mv_we_lookup ON serving.mv_we_lookup(
    inning, is_top, score_diff, base_state, outs
);
CREATE INDEX idx_mv_li_lookup ON serving.mv_li_lookup(
    inning, is_top, score_diff, base_state, outs
);
```

#### 5.1.4 Pitcher Arsenal View

Create `sql/70_serving/704_mv_pitcher_arsenal.sql`:

```sql
/*
File: sql/70_serving/704_mv_pitcher_arsenal.sql
Purpose: Pitcher pitch-type breakdowns
Author: Agent [codex]
Date: 2026-04-28
*/

CREATE MATERIALIZED VIEW IF NOT EXISTS serving.mv_pitcher_arsenal AS
SELECT 
    pitcher_id,
    pitch_type,
    COUNT(*) as total_pitches,
    ROUND(AVG(release_speed), 1) as avg_velocity,
    ROUND(AVG(spin_rate), 0) as avg_spin,
    ROUND(AVG(pfx_x), 2) as avg_horizontal_break,
    ROUND(AVG(pfx_z), 2) as avg_vertical_break,
    ROUND(AVG(release_pos_x), 2) as avg_release_x,
    ROUND(AVG(release_pos_z), 2) as avg_release_z,
    COUNT(*) FILTER (WHERE description ILIKE '%swinging%')::float / 
        NULLIF(COUNT(*), 0) as whiff_rate,
    MAX(game_date) as last_seen
FROM raw_mlb.statcast  -- Or appropriate table
WHERE game_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY pitcher_id, pitch_type;

CREATE INDEX idx_mv_arsenal_pitcher 
    ON serving.mv_pitcher_arsenal(pitcher_id);

COMMENT ON MATERIALIZED VIEW serving.mv_pitcher_arsenal IS 
    'Pitcher pitch-type arsenal for matchup analysis';
```

---

## Task 5.2: Refresh Strategy

### Requirements

Materialized views need periodic refresh. Create strategy:

#### 5.2.1 Create Refresh Function

Create `sql/70_serving/799_refresh_serving_views.sql`:

```sql
/*
File: sql/70_serving/799_refresh_serving_views.sql
Purpose: Serving view refresh orchestration
Author: Agent [codex]
Date: 2026-04-28
*/

-- Function to refresh all serving views
CREATE OR REPLACE FUNCTION serving.refresh_all_views()
RETURNS TABLE(view_name TEXT, refreshed_at TIMESTAMP WITH TIME ZONE) AS $$
BEGIN
    RETURN QUERY
    WITH refreshes AS (
        SELECT 
            'serving.mv_current_standings'::text as name,
            clock_timestamp() as ts
        FROM refresh_materialized_view('serving.mv_current_standings')
        
        UNION ALL
        
        SELECT 
            'serving.mv_player_form_30d'::text,
            clock_timestamp()
        FROM refresh_materialized_view('serving.mv_player_form_30d')
        
        UNION ALL
        
        SELECT 
            'serving.mv_we_lookup'::text,
            clock_timestamp()
        FROM refresh_materialized_view('serving.mv_we_lookup')
        
        UNION ALL
        
        SELECT 
            'serving.mv_li_lookup'::text,
            clock_timestamp()
        FROM refresh_materialized_view('serving.mv_li_lookup')
        
        UNION ALL
        
        SELECT 
            'serving.mv_pitcher_arsenal'::text,
            clock_timestamp()
        FROM refresh_materialized_view('serving.mv_pitcher_arsenal')
    )
    SELECT name, ts FROM refreshes;
END;
$$ LANGUAGE plpgsql;

-- Create cron job or trigger for periodic refresh
-- Or call from Python service
```

#### 5.2.2 Python Refresh Service

Create `baseball/services/serving.py`:

```python
class ServingLayer:
    """Manages serving layer materialized views."""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def refresh_view(self, view_name: str) -> bool:
        """Refresh a single materialized view."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(f'REFRESH MATERIALIZED VIEW {view_name}')
            return True
        except Exception as e:
            logger.error(f'Failed to refresh {view_name}: {e}')
            return False
    
    def refresh_all(self) -> dict[str, bool]:
        """Refresh all serving views."""
        views = [
            'serving.mv_current_standings',
            'serving.mv_player_form_30d',
            'serving.mv_we_lookup',
            'serving.mv_li_lookup',
            'serving.mv_pitcher_arsenal',
        ]
        
        results = {}
        for view in views:
            results[view] = self.refresh_view(view)
        
        return results
    
    def get_view_stats(self) -> dict[str, Any]:
        """Get statistics on serving views."""
        # Query pg_matviews for last refresh time, row counts
        pass
```

---

## Task 5.3: Performance Monitoring

### Requirements

#### 5.3.1 Query Performance Logging

Create `baseball/core/performance.py`:

```python
class QueryProfiler:
    """Profile query performance."""
    
    def __init__(self):
        self.slow_query_threshold = 0.1  # 100ms
    
    def profile_query(self, sql: str, params: tuple = None) -> QueryStats:
        """Execute query and capture timing."""
        start = time.time()
        # Execute
        elapsed = time.time() - start
        
        if elapsed > self.slow_query_threshold:
            logger.warning(f'Slow query ({elapsed:.3f}s): {sql[:100]}...')
        
        return QueryStats(
            sql=sql,
            elapsed_seconds=elapsed,
            is_slow=elapsed > self.slow_query_threshold,
        )
```

#### 5.3.2 Index Usage Monitoring

Create SQL to check index usage:

```sql
-- Create view for index usage monitoring
CREATE OR REPLACE VIEW serving.index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as times_used,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname IN ('serving', 'features', 'core')
ORDER BY idx_scan DESC;
```

---

## Task 5.4: CLI Integration

### Add to `baseball status` Command

Show serving layer status:

```python
# In status command
console.print('\n[bold]📊 Serving Layer[/bold]')
for view in ['mv_current_standings', 'mv_player_form_30d', ...]:
    last_refresh = get_last_refresh_time(view)
    row_count = get_row_count(view)
    console.print(f'  {view}: {row_count} rows (refreshed {last_refresh})')
```

### Add Refresh Command

```python
@serving_app.command(name='refresh')
def serving_refresh(
    view: str = typer.Option('all', '--view', '-v', ...),
):
    """Refresh serving materialized views."""
    service = ServingLayer()
    
    if view == 'all':
        results = service.refresh_all()
    else:
        results = {view: service.refresh_view(f'serving.{view}')}
    
    for view_name, success in results.items():
        status = '✅' if success else '❌'
        console.print(f'{status} {view_name}')
```

---

## Validation Steps

```bash
# 1. Create all SQL
psql -f sql/70_serving/701_mv_current_standings.sql
psql -f sql/70_serving/702_mv_player_form_30d.sql
psql -f sql/70_serving/703_mv_we_li_lookup.sql
psql -f sql/70_serving/704_mv_pitcher_arsenal.sql

# 2. Verify views exist
psql -c "\dm serving.*"

# 3. Test query performance
psql -c "EXPLAIN ANALYZE SELECT * FROM serving.mv_current_standings"
# Should show <50ms

# 4. Test refresh
python -c "from baseball.services.serving import ServingLayer; s = ServingLayer(); print(s.refresh_all())"

# 5. CLI test
baseball serving refresh --view all

# 6. Status shows serving layer
baseball status
# Should show serving views and refresh times
```

---

## Success Criteria

- [ ] 5+ materialized views created
- [ ] All views queryable in <100ms
- [ ] Refresh mechanism working
- [ ] `baseball status` shows serving layer
- [ ] Index usage monitoring in place
- [ ] Documentation updated

---

## Time Estimate

4-5 hours for complete serving layer implementation.

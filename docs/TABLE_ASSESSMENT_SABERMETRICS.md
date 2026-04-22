# Table Assessment for Sabermetrics and Baseball Modeling

**Date:** 2026-04-22
**Purpose:** Assess current table structure to support sabermetrics and baseball modeling requirements

## Current Data Sources Available

### ✅ Primary Data Sources (Available)

**Retrosheet (Historical Play-by-Play)**
- Schema: `raw_retrosheet`
- Coverage: 1871-present
- Tables: Chadwick extracts, reference tables
- Status: ✓ Fully integrated into core

**MLB Stats API (Live and Historical)**
- Schema: `raw_mlb`
- Coverage: 2015-present (live), historical backfill
- Tables: schedule_snapshots, live_feed_snapshots, reference_snapshots, statcast
- Status: ✓ Partially integrated

**Statcast (Pitch-Level Tracking)**
- Schema: `raw_mlb.statcast`
- Coverage: 2015-present
- Fields: pitcher, batter, pitch_type, release_speed, spin_rate, launch_angle, launch_speed, hit_distance, events, zone, pfx_x, pfx_z, plate_x, plate_z, etc.
- Status: ✓ Raw data available, transformation needed

**ESPN API (Real-Time Scores)**
- Schema: `raw_espn`
- Coverage: Recent games
- Tables: game_snapshots, schedule_snapshots, player_stats_snapshots, team_stats_snapshots
- Status: ✓ Raw data available, bridge not tested

**Lahman Database**
- Schema: External (not yet integrated)
- Coverage: Historical comprehensive database
- Status: ✗ Not integrated

**Baseball Reference**
- Schema: External (not yet integrated)
- Coverage: Historical statistics and biographical data
- Status: ✗ Not integrated

**FanGraphs**
- Schema: External (not yet integrated)
- Coverage: Advanced sabermetrics and splits
- Status: ✗ Not integrated

## Bridge Table Assessment

### ✅ Existing Bridge Tables

**bridge.player_xref**
- Current fields: retrosheet_player_id, mlb_player_id, chadwick_register_id, first_name, last_name, bats, throws
- Schema enhancement created: bbref_id, fangraphs_id, mlb_played_first, birth_year (NOT APPLIED)
- Status: ⚠️ Missing bbref_id and fangraphs_id columns (schema enhancement created but not applied)
- Data sources supported: Retrosheet, MLB, Chadwick Register
- Missing: FanGraphs, Baseball Reference (schema ready, not applied)

**bridge.team_xref**
- Current fields: retrosheet_team_id, mlb_team_id, team_name, league, division
- Season-aware procedure exists: populate_season_aware_team_xref() (valid_from_season, valid_to_season)
- Status: ✓ Season-aware mappings implemented, handles franchise moves (MON→WAS, FLO→MIA)
- Data sources supported: Retrosheet, MLB

**bridge.park_xref**
- Current fields: retrosheet_park_id, mlb_venue_id, park_name
- Status: ✓ 45 venues mapped
- Data sources supported: Retrosheet, MLB

**bridge.game_xref**
- Current fields: retrosheet_game_id, mlb_game_pk, game_date, retrosheet_home_team_id, retrosheet_away_team_id, mlb_home_team_id, mlb_away_team_id
- Status: ✓ Matching by date + teams + game number
- Data sources supported: Retrosheet, MLB

**bridge.coach_xref**
- Current fields: retrosheet_coach_id, mlb_coach_id, first_name, last_name
- Status: ✓ Biofile_legacy name resolution
- Data sources supported: Retrosheet, MLB

**bridge.umpire_xref**
- Current fields: retrosheet_umpire_id, mlb_umpire_id, first_name, last_name
- Status: ✓ Biofile_legacy name resolution
- Data sources supported: Retrosheet, MLB

**bridge.external_player_xref**
- Current fields: external_source, external_player_id, retrosheet_player_id
- Status: ✓ For Statcast, Baseball Reference, Lahman IDs
- Data sources supported: Statcast, Baseball Reference, Lahman

**bridge.external_team_xref**
- Current fields: external_source, external_team_id, retrosheet_team_id
- Status: ✓ For external team IDs
- Data sources supported: External sources

## Pitching Data Assessment

### ✅ Available Pitching Data

**Statcast Pitch-Level Metrics (raw_mlb.statcast)**
- Pitcher identification: pitcher (MLB ID), player_name, p_throws
- Pitch characteristics: pitch_type, pitch_name, release_speed, release_spin_rate, release_extension
- Pitch movement: pfx_x, pfx_z, break_angle_deprecated, break_length_deprecated, spin_axis
- Pitch location: plate_x, plate_z, zone, release_pos_x, release_pos_y, release_pos_z
- Batted ball: launch_speed, launch_angle, launch_speed_angle, hit_distance_sc, bb_type
- Advanced: bat_speed, swing_length, attack_angle, attack_direction, arm_angle
- Context: balls, strikes, inning, outs_when_up, game_type
- Performance: events, description, woba_value, estimated_woba_using_speedangle
- Fatigue: pitcher_days_since_prev_game, pitcher_days_until_next_game, n_thruorder_pitcher

**Core Plate Appearances (core.plate_appearances)**
- Pitcher identification: pitcher_id, pitcher_hand
- Context: count, game_state
- Outcome: event_type, result
- Status: ✓ Fully integrated

**MLB Win Probability Features (mlb_features.player_season_stats)**
- Pitching stats: games_started, innings_pitched, earned_runs, pitcher_hits_allowed, pitcher_walks, pitcher_strikeouts, pitcher_home_runs, era, whip, k_per_9
- Status: ✓ Season-level stats available

**Batter-Pitcher Matchups (mlb_features.batter_pitcher_matchups)**
- Matchup history: batter_id, pitcher_id, season
- Stats: avg, pa_count, hits, hr, k, bb
- Statcast vs pitcher: exit_velocity_avg, launch_angle_avg, barrel_pct
- Status: ✓ Matchup data available

### ❌ Missing Pitching Features

**Pitcher Fatigue Metrics**
- ✗ Pitch count per game
- ✗ Cumulative pitch count (season)
- ✗ Rest days between starts
- ✗ Workload metrics (high-stress innings)

**Pitch Sequencing Patterns**
- ✗ Pitch sequence analysis (fastball-curveball patterns)
- ✗ Pitcher tendencies by count
- ✗ Pitcher batter-specific strategies
- ✗ Pitcher deception metrics

**Pitcher Platoon Splits**
- ✗ L/R splits for all metrics
- ✗ Home/road splits
- ✗ Month/season splits
- ✗ High-leverage splits

**Pitcher Park Factors**
- ✗ Park-adjusted pitching metrics
- ✗ Stadium-specific performance
- ✗ Environmental adjustments

**Pitcher Clutch Performance**
- ✗ High-leverage performance
- ✗ Late/close performance
- ✗ RISP performance
- ✗ Win probability added

## Sabermetrics Coverage Assessment

### ✅ Available Sabermetrics

**Hitting Metrics**
- OBP, OPS, SLG: ✓ Available in feature marts
- wOBA: ✓ Available in Statcast (woba_value, estimated_woba_using_speedangle)
- wRC+: ✗ Not calculated (need park adjustment)
- BABIP: ✓ Available (babip_value in Statcast)
- ISO: ✓ Available (iso_value in Statcast)

**Pitching Metrics**
- ERA: ✓ Available (era in player_season_stats)
- FIP: ✗ Not calculated (need HR, BB, HBP, K)
- xFIP: ✗ Not calculated
- WHIP: ✓ Available (whip in player_season_stats)
- K/9: ✓ Available (k_per_9 in player_season_stats)
- BB/9: ✗ Not calculated
- WAR: ✗ Not calculated
- WPA: ✗ Not calculated

**Advanced Statcast Metrics**
- Exit Velocity: ✓ Available (launch_speed, bat_speed)
- Launch Angle: ✓ Available (launch_angle, attack_angle)
- Barrel Rate: ✗ Not calculated (have barrel data but not rate)
- Spin Rate: ✓ Available (release_spin_rate, spin_axis)
- Pitch Movement: ✓ Available (pfx_x, pfx_z, break_angle)
- Zone Contact: ✗ Not calculated (have zone data but not contact rate)
- Chase Rate: ✗ Not calculated
- Swing Rate: ✗ Not calculated

### ❌ Missing Sabermetrics

**Advanced Pitching Metrics**
- FIP, xFIP, SIERA
- K%, BB%, HR/9
- Pitch type linear weights
- Pitch quality metrics

**Context-Dependent Metrics**
- Leverage-index-adjusted stats
- Clutch score
- WPA (Win Probability Added)
- RE24 (Run Expectancy)

**Splits**
- Platoon splits (L/R)
- Home/road splits
- Monthly splits
- High-leverage splits

**Predictive Metrics**
- xERA (Expected ERA)
- xFIP (Expected FIP)
- xWOBA (Expected wOBA)
- xSLG (Expected SLG)

## Data Source Integration Gaps

### Critical Gaps

**FanGraphs Integration**
- ⚠️ Schema enhancement created (fangraphs_id in player_xref) but NOT APPLIED
- ⚠️ No FanGraphs data ingestion
- ⚠️ No FanGraphs advanced metrics (WAR, FIP, xFIP, etc.)

**Baseball Reference Integration**
- ⚠️ Schema enhancement created (bbref_id in player_xref) but NOT APPLIED
- ⚠️ No Baseball Reference data ingestion
- ⚠️ No Baseball Reference biographical data

**Lahman Database Integration**
- ⚠️ No Lahman data ingestion
- ⚠️ No Lahman salary data
- ⚠️ No Lahman historical statistics

**Salary Data**
- ❌ No salary data source
- ❌ No payroll information
- ❌ No cap impact modeling

**Injury Data**
- ❌ No injury tracking (DL, IL status)
- ❌ No injury history
- ❌ No injury prediction features

**Weather Data**
- ❌ No weather data source
- ❌ No temperature, wind, humidity
- ❌ No environmental adjustments

**Umpire Data**
- ⚠️ Umpire bridge exists but no umpire-specific metrics
- ❌ No umpire strike zone tendencies
- ❌ No umpire performance data

## Recommendations

### Immediate Actions (This Week)

1. **Apply player_xref schema enhancement**
   - Execute `sql/bridge/980_player_xref_schema_enhancement.sql`
   - Add bbref_id and fangraphs_id columns
   - Update population script to include these fields

2. **Test Statcast integration**
   - Verify raw_mlb.statcast data is complete
   - Create transformation to core pitching metrics
   - Calculate FIP, xFIP, K%, BB%

3. **Implement missing sabermetrics calculations**
   - Add FIP calculation procedure
   - Add xFIP calculation procedure
   - Add WAR calculation (if feasible)
   - Add WPA calculation

### Short-Term Actions (Next 2 Weeks)

1. **Integrate FanGraphs data**
   - Create FanGraphs API ingestion script
   - Store in raw_fangraphs schema
   - Create bridge table for FanGraphs IDs
   - Transform to advanced metrics

2. **Integrate Baseball Reference data**
   - Create Baseball Reference API ingestion script
   - Store in raw_bref schema
   - Create bridge table for Baseball Reference IDs
   - Transform to biographical and historical data

3. **Add pitching fatigue features**
   - Calculate pitch counts from Statcast
   - Calculate rest days from schedule
   - Add workload metrics
   - Add fatigue features to feature marts

### Medium-Term Actions (Next Month)

1. **Integrate salary data**
   - Identify salary data source (MLB salary database, Spotrac)
   - Create salary data ingestion
   - Add salary bridge table
   - Add payroll features

2. **Integrate injury data**
   - Identify injury data source (MLB injury reports, Rotowire)
   - Create injury data ingestion
   - Add injury bridge table
   - Add injury status features

3. **Integrate weather data**
   - Integrate OpenWeatherMap API
   - Store weather data by game and venue
   - Add weather features to game context

4. **Integrate umpire data**
   - Add umpire-specific metrics from Statcast
   - Calculate umpire strike zone tendencies
   - Add umpire features to prediction models

## Data Integrity Rules

**NEVER MODIFY:**
- raw_retrosheet.* (source-preserved Retrosheet data)
- raw_mlb.* (source-preserved MLB API data)
- raw_espn.* (source-preserved ESPN API data)
- raw_statcast.* (source-preserved Statcast data)
- raw_external.* (source-preserved external data)

**SAFE TO MODIFY:**
- bridge.* (ID cross-reference tables)
- core.* (canonical entities and transformations)
- features.* (ML-ready feature marts)
- models.* (model registry and metadata)
- predictions.* (stored outputs and reports)
- analysis.* (combined historical + live views)

## Conclusion

The retrosheet warehouse has excellent foundation for sabermetrics and baseball modeling:
- ✓ Historical Retrosheet data fully integrated
- ✓ Statcast pitch-level data available
- ✓ Bridge tables for ID reconciliation
- ✓ Core feature marts for ML

**Critical Gaps:**
- ⚠️ player_xref schema enhancement not applied (bbref_id, fangraphs_id)
- ❌ FanGraphs, Baseball Reference, Lahman not integrated
- ❌ Salary, injury, weather data missing
- ❌ Advanced pitching metrics not calculated (FIP, xFIP, WAR, WPA)
- ❌ Pitching fatigue features not implemented

**Next Steps:**
1. Apply player_xref schema enhancement
2. Implement missing sabermetrics calculations
3. Integrate FanGraphs and Baseball Reference data
4. Add pitching fatigue and sequencing features

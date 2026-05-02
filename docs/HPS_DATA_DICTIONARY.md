# Hierarchical Prediction System - Comprehensive Data Dictionary

**Document:** Data Dictionary for All Abstraction Layers  
**Version:** 1.0  
**Date:** 2026-05-01  
**Purpose:** Complete reference of all data factors available for modeling at each layer

---

## Overview

This document catalogs **all data factors** available for the Hierarchical Prediction System (HPS) across 5 layers of abstraction. Use this to understand what data can be included/excluded when building models without changing queries.

**Design Principle:** All factors are carried forward in the data warehouse so models can flexibly select features without query modifications.

---

## Layer 1: League/Season Environment (Macro Trends)

### Purpose
Capture league-wide trends and season-level effects that influence all predictions.

### Data Sources
- `core.games` (aggregated)
- `core.events` (aggregated)
- `features_pitch.locations_clean` (aggregated)

### Available Factors

| Factor | Data Type | Description | Example |
|--------|-----------|-------------|---------|
| `season` | INTEGER | Year | 2024 |
| `league_id` | VARCHAR(10) | League ('AL', 'NL', 'MLB') | 'MLB' |
| `runs_per_game` | DECIMAL(5,3) | League scoring rate | 4.620 |
| `runs_per_pa` | DECIMAL(5,3) | Runs per plate appearance | 0.112 |
| `hr_rate` | DECIMAL(5,4) | Home runs per PA | 0.0342 |
| `k_rate` | DECIMAL(5,4) | Strikeouts per PA | 0.2281 |
| `bb_rate` | DECIMAL(5,4) | Walks per PA | 0.0885 |
| `league_avg` | DECIMAL(4,3) | League batting average | .247 |
| `league_obp` | DECIMAL(4,3) | League on-base percentage | .321 |
| `league_slg` | DECIMAL(4,3) | League slugging | .414 |
| `league_ops` | DECIMAL(4,3) | League OPS | .735 |
| `league_woba` | DECIMAL(4,3) | League wOBA | .318 |
| `avg_pitch_velocity` | DECIMAL(5,2) | Average pitch speed | 93.4 |
| `avg_pitch_spin` | DECIMAL(7,2) | Average spin rate | 2300.5 |
| `fastball_pct` | DECIMAL(4,3) | Percentage of fastballs | 0.52 |
| `breaking_pct` | DECIMAL(4,3) | Breaking ball percentage | 0.28 |
| `offspeed_pct` | DECIMAL(4,3) | Offspeed percentage | 0.20 |
| `home_field_advantage` | DECIMAL(4,3) | Home team win rate | 0.542 |
| `day_game_factor` | DECIMAL(4,3) | Day vs night game effect | 1.02 |
| `month_trends` | JSONB | Monthly breakdowns | `{"04": {"hr_rate": 0.032}}` |
| `ball_carry_index` | DECIMAL(4,3) | Ball carry vs neutral | 1.05 |

### Usage in Models
- **Time-series models:** ARIMA, Prophet for trend forecasting
- **Feature engineering:** Adjust player stats for league environment
- **Context:** "Is this a high-offense or low-offense season?"

### Sample Query
```sql
SELECT season, hr_rate, k_rate, league_ops
FROM predictions.league_environment
WHERE season BETWEEN 2015 AND 2024
ORDER BY season;
```

---

## Layer 2: Team Context (Form, Streak, Environment)

### Purpose
Capture team-level factors: form, home/away, bullpen status, weather effects.

### Data Sources
- `core.games` (team aggregates)
- `core.events` (recent performance)
- External: Weather APIs

### Available Factors

#### Form Metrics (Rolling 10 games)
| Factor | Data Type | Description | Update Frequency |
|--------|-----------|-------------|------------------|
| `team_id` | VARCHAR(20) | Team identifier | Static |
| `as_of_date` | DATE | Snapshot date | Daily |
| `last_10_wins` | INTEGER | Wins in last 10 | Daily |
| `last_10_losses` | INTEGER | Losses in last 10 | Daily |
| `last_10_win_pct` | DECIMAL(4,3) | Win percentage | Daily |
| `streak_type` | VARCHAR(10) | 'winning'/'losing'/'neutral' | Daily |
| `streak_length` | INTEGER | Current streak | Daily |

#### Home/Away Splits
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `home_win_pct` | DECIMAL(4,3) | Home winning % |
| `away_win_pct` | DECIMAL(4,3) | Away winning % |
| `home_advantage` | DECIMAL(4,3) | Home - Away spread |
| `park_factor` | DECIMAL(4,2) | ESPN park factor (100=neutral) |

#### Offense (30-day rolling)
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `team_ops` | DECIMAL(4,3) | Team OPS |
| `team_woba` | DECIMAL(4,3) | Team wOBA |
| `runs_per_game` | DECIMAL(4,2) | Runs per game |
| `hr_per_game` | DECIMAL(4,2) | HRs per game |

#### Pitching (30-day rolling)
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `team_era` | DECIMAL(4,2) | Team ERA |
| `team_whip` | DECIMAL(4,2) | Team WHIP |
| `k_per_nine` | DECIMAL(5,2) | K/9 rate |
| `bb_per_nine` | DECIMAL(5,2) | BB/9 rate |

#### Bullpen Status
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `bullpen_era` | DECIMAL(4,2) | Bullpen ERA |
| `bullpen_fatigue_score` | INTEGER | 0-100 fatigue index |
| `days_since_last_game` | INTEGER | Rest days |

#### Platoon Splits
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `vs_lhp_ops` | DECIMAL(4,3) | OPS vs left pitchers |
| `vs_rhp_ops` | DECIMAL(4,3) | OPS vs right pitchers |

### Usage in Models
- **Team win probability:** XGBoost with form features
- **Context adjustment:** "Is this team on a hot streak?"
- **Park adjustments:** "Coors Field boosts offense by 15%"

### Sample Query
```sql
SELECT 
    team_id,
    last_10_win_pct,
    streak_type || ' ' || streak_length as streak,
    team_ops,
    bullpen_era
FROM predictions.team_context_rolling
WHERE as_of_date = CURRENT_DATE - 1
ORDER BY last_10_win_pct DESC;
```

---

## Layer 3: Player Profiles (Batter/Pitcher Tendencies)

### Purpose
Rolling player statistics capturing individual tendencies and performance trends.

### Data Sources
- `core.plate_appearances`
- `features_pitch.locations_clean`
- `features.player_profiles`

### Batter Profile Factors

#### Overall Performance (30/100/Season)
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `batter_id` | VARCHAR(20) | Player identifier |
| `as_of_date` | DATE | Snapshot date |
| `last_30_pa` | INTEGER | PA sample size |
| `batting_avg` | DECIMAL(4,3) | Batting average |
| `obp` | DECIMAL(4,3) | On-base % |
| `slg` | DECIMAL(4,3) | Slugging |
| `ops` | DECIMAL(4,3) | OPS |
| `woba` | DECIMAL(4,3) | Weighted OBA |
| `wrc_plus` | INTEGER | wRC+ (100=avg) |

#### Discipline Metrics
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `k_rate` | DECIMAL(4,3) | Strikeout % |
| `bb_rate` | DECIMAL(4,3) | Walk % |
| `zone_swing_rate` | DECIMAL(4,3) | Swing % in zone |
| `o_swing_rate` | DECIMAL(4,3) | Chase % (out of zone) |
| `zone_contact_rate` | DECIMAL(4,3) | Contact % in zone |
| `o_contact_rate` | DECIMAL(4,3) | Contact % out of zone |
| `swinging_strike_rate` | DECIMAL(4,3) | Whiff % |

#### Power Metrics
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `iso` | DECIMAL(4,3) | Isolated power |
| `hr_flyball_rate` | DECIMAL(4,3) | HR per fly ball |
| `avg_exit_velocity` | DECIMAL(5,2) | Avg exit velo |
| `hard_hit_rate` | DECIMAL(4,3) | 95+ mph exit velo % |

#### Pitch Type Performance
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `vs_fastball_avg` | DECIMAL(4,3) | Avg vs fastball |
| `vs_fastball_slg` | DECIMAL(4,3) | SLG vs fastball |
| `vs_breaking_avg` | DECIMAL(4,3) | Avg vs breaking |
| `vs_breaking_slg` | DECIMAL(4,3) | SLG vs breaking |
| `vs_offspeed_avg` | DECIMAL(4,3) | Avg vs offspeed |
| `vs_offspeed_slg` | DECIMAL(4,3) | SLG vs offspeed |

#### Count Performance (JSONB)
| Factor | Data Type | Example |
|--------|-----------|---------|
| `count_performance` | JSONB | `{"0-0": {"avg": .280, "ops": .750}, "2-2": {"avg": .180, "ops": .520}}` |

#### Situational
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `risp_avg` | DECIMAL(4,3) | RISP batting avg |
| `risp_ops` | DECIMAL(4,3) | RISP OPS |
| `two_outs_ops` | DECIMAL(4,3) | 2 outs OPS |
| `late_close_ops` | DECIMAL(4,3) | Late/close OPS |

#### Trend Analysis
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `trend_direction` | VARCHAR(10) | 'improving'/'declining'/'stable' |
| `trend_confidence` | DECIMAL(4,3) | Confidence in trend |

### Pitcher Profile Factors

#### Overall Performance
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `pitcher_id` | VARCHAR(20) | Player identifier |
| `last_5_games_pitches` | INTEGER | Recent workload |
| `season_pitches` | INTEGER | Season total |
| `season_ip` | DECIMAL(5,1) | Innings pitched |
| `era` | DECIMAL(4,2) | Earned run avg |
| `fip` | DECIMAL(4,2) | Fielding-independent |
| `whip` | DECIMAL(4,2) | WHIP |
| `k_per_nine` | DECIMAL(5,2) | Strikeouts per 9 |
| `bb_per_nine` | DECIMAL(5,2) | Walks per 9 |
| `k_bb_ratio` | DECIMAL(4,2) | K/BB ratio |

#### Stuff Metrics
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `avg_velocity` | DECIMAL(5,2) | Avg pitch velo |
| `max_velocity` | DECIMAL(5,2) | Max pitch velo |
| `avg_spin_rate` | DECIMAL(7,2) | Avg spin |
| `stuff_plus` | INTEGER | Stuff+ metric (100=avg) |

#### Pitch Mix (JSONB)
| Factor | Data Type | Example |
|--------|-----------|---------|
| `pitch_mix` | JSONB | `{"FF": 0.45, "SL": 0.25, "CU": 0.20, "CH": 0.10}` |
| `primary_pitch` | VARCHAR(5) | Most used pitch type |
| `secondary_pitch` | VARCHAR(5) | Second most used |
| `pitch_mix_by_count` | JSONB | Nested by count: `{"0-0": {"FF": 0.60}, "2-2": {"FF": 0.40}}` |

#### Count-Specific Tendencies
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `first_pitch_strike_rate` | DECIMAL(4,3) | First pitch strike % |
| `first_pitch_fastball_pct` | DECIMAL(4,3) | FB % on 0-0 |
| `two_strike_k_rate` | DECIMAL(4,3) | K% with 2 strikes |
| `two_strike_out_of_zone_pct` | DECIMAL(4,3) | Chase pitch % |
| `three_ball_walk_rate` | DECIMAL(4,3) | BB% at 3 balls |
| `ahead_in_count_pct` | DECIMAL(4,3) | % of time ahead |
| `behind_in_count_pct` | DECIMAL(4,3) | % of time behind |

#### Outcome Rates
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `zone_rate` | DECIMAL(4,3) | % pitches in zone |
| `o_swing_rate` | DECIMAL(4,3) | Batter chase % |
| `whiff_rate` | DECIMAL(4,3) | Swinging strike % |
| `groundball_rate` | DECIMAL(4,3) | GB % |
| `flyball_rate` | DECIMAL(4,3) | FB % |
| `weak_contact_rate` | DECIMAL(4,3) | Weak contact % |

#### Situational
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `risp_era` | DECIMAL(4,2) | ERA with RISP |
| `high_leverage_era` | DECIMAL(4,2) | High leverage ERA |
| `times_thru_order_penalty` | DECIMAL(4,3) | OPS jump 2nd/3rd time |

### Usage in Models
- **Player comparisons:** "Harper's wOBA vs fastballs"
- **Trend detection:** "Is pitcher velocity declining?"
- **Personalization:** Models include player_id as feature

### Sample Query
```sql
-- Harper's performance vs fastballs in 2-2 count
SELECT 
    b.batter_id,
    b.woba as overall_woba,
    b.vs_fastball_woba,
    b.count_performance->'2-2'->>'woba' as woba_2_2,
    b.trend_direction
FROM predictions.batter_profiles_rolling b
WHERE b.batter_id = 'harper_bryce'
  AND b.as_of_date = CURRENT_DATE - 1;
```

---

## Layer 4: Matchup History (H2H Dynamics)

### Purpose
Historical pitcher-batter interaction data for matchup-specific adjustments.

### Data Sources
- `core.plate_appearances` (H2H aggregation)
- `features_pitch.locations_clean` (pitch-level H2H)

### Available Factors

| Factor | Data Type | Description |
|--------|-----------|-------------|
| `matchup_pair_id` | VARCHAR | pitcher_batter composite key |
| `pitcher_id` | VARCHAR(20) | Pitcher identifier |
| `batter_id` | VARCHAR(20) | Batter identifier |
| `career_pas` | INTEGER | Total PAs in matchup |
| `career_avg` | DECIMAL(4,3) | Career avg in matchup |
| `career_obp` | DECIMAL(4,3) | Career OBP |
| `career_slg` | DECIMAL(4,3) | Career SLG |
| `career_hr` | INTEGER | Career HRs vs pitcher |
| `career_so` | INTEGER | Career Ks vs pitcher |
| `career_bb` | INTEGER | Career BBs vs pitcher |
| `pitch_mix_faced` | JSONB | Pitches seen: `{"FF": 45, "SL": 23}` |
| `outcomes_distribution` | JSONB | Results: `{"single": 5, "hr": 2, "so": 8}` |
| `last_2_seasons_pas` | INTEGER | Recent sample size |
| `last_2_seasons_woba` | DECIMAL(4,3) | Recent performance |
| `times_faced_this_season` | INTEGER | Current season PAs |
| `most_recent_date` | DATE | Last matchup date |
| `trend_direction` | VARCHAR(10) | 'improving'/'declining'/'stable' |

### Usage in Models
- **Small sample Bayes:** Adjust for limited H2H history
- **Pattern detection:** "Scherzer throws 60% sliders to Harper"
- **Psychological factors:** Batter comfort vs specific pitcher

### Sample Query
```sql
-- Harper vs Scherzer career matchup
SELECT 
    career_pas,
    career_avg,
    career_hr,
    career_so,
    ROUND(career_hr::numeric / career_pas, 4) as hr_rate,
    pitch_mix_faced,
    trend_direction
FROM predictions.matchup_history
WHERE matchup_pair_id = 'scherzer_max_harper_bryce';
```

---

## Layer 5: Situational/Real-Time State

### Purpose
Immediate game state including count, base runners, score, pitch sequence.

### Data Sources
- `core.plate_appearances` (live)
- `pitch_sequence.training_rows` (pitch-level)
- `raw_mlb.statcast` (live feed)

### Game State Factors

#### Count State
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `balls` | INTEGER | Current balls (0-3) |
| `strikes` | INTEGER | Current strikes (0-2) |
| `count_label` | VARCHAR(5) | "2-2", "3-1", etc. |
| `count_category` | VARCHAR(20) | "ahead", "behind", "even", "two_strikes", "three_balls" |
| `strikes_remaining` | INTEGER | Strikes to K |
| `balls_remaining` | INTEGER | Balls to BB |

#### Base State
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `on_1b` | BOOLEAN | Runner on 1st |
| `on_2b` | BOOLEAN | Runner on 2nd |
| `on_3b` | BOOLEAN | Runner on 3rd |
| `base_state` | INTEGER | 0-7 encoding (binary) |
| `base_state_label` | VARCHAR(20) | "bases_empty", "runners_1_2", etc. |
| `risp` | BOOLEAN | Runner in scoring position |
| `runners_on` | INTEGER | Count of runners |

#### Game Context
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `outs` | INTEGER | Outs (0-2) |
| `inning` | INTEGER | Inning number |
| `inning_half` | VARCHAR(10) | "top" or "bottom" |
| `home_score` | INTEGER | Home team runs |
| `away_score` | INTEGER | Away team runs |
| `score_diff` | INTEGER | Score differential |
| `batting_team_leading` | BOOLEAN | True if batting team ahead |
| `game_leverage_index` | DECIMAL(4,2) | LI (1.0 = avg) |
| `win_exp_home` | DECIMAL(4,3) | Home team win probability |

#### Pitch Sequence
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `pitch_number` | INTEGER | Pitch # in PA |
| `previous_pitch_type` | VARCHAR(5) | Last pitch thrown |
| `previous_pitch_result` | VARCHAR(20) | Ball, strike, foul, etc. |
| `previous_location_x` | DECIMAL(5,2) | Plate X of last pitch |
| `previous_location_z` | DECIMAL(5,2) | Plate Z of last pitch |
| `pitch_sequence` | VARCHAR | Sequence string: "BCSF" |
| `sequence_pattern` | VARCHAR(20) | "setup_setup_payoff", etc. |
| `setup_pitch_type` | VARCHAR(5) | Pitch before payoff |

#### Pitcher State
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `pitcher_pitches_thrown` | INTEGER | Pitches this game |
| `pitcher_batters_faced` | INTEGER | Batters faced |
| `pitcher_innings` | DECIMAL(4,1) | Innings completed |
| `pitcher_days_rest` | INTEGER | Days since last start |
| `times_thru_order` | INTEGER | 1st/2nd/3rd time thru lineup |

#### Platoon
| Factor | Data Type | Description |
|--------|-----------|-------------|
| `batter_hand` | VARCHAR(1) | 'L' or 'R' |
| `pitcher_hand` | VARCHAR(1) | 'L' or 'R' |
| `platoon_advantage` | BOOLEAN | Same hand = advantage to pitcher |

### Real-Time Prediction Outputs

| Factor | Data Type | Description |
|--------|-----------|-------------|
| `pred_next_pitch_type` | JSONB | `{"FF": 0.45, "SL": 0.35}` |
| `pred_swing_probability` | DECIMAL(4,3) | Will batter swing? |
| `pred_contact_probability` | DECIMAL(4,3) | If swing, contact? |
| `pred_fair_probability` | DECIMAL(4,3) | Contact → fair ball? |
| `pred_pa_outcome` | JSONB | Full PA outcome distribution |
| `pred_home_run_prob` | DECIMAL(4,3) | HR probability this PA |
| `timestamp` | TIMESTAMP | Prediction timestamp |

### Usage in Models
- **Markov chains:** Count transition probabilities
- **LSTM sequences:** Pitch-by-pitch prediction
- **Real-time inference:** Sub-second predictions

### Sample Query
```sql
-- Current PA state with predictions
SELECT 
    count_label,
    base_state_label,
    outs,
    inning || ' ' || inning_half as situation,
    pred_next_pitch_type,
    pred_pa_outcome
FROM predictions.live_game_state
WHERE game_pk = 716190
ORDER BY pitch_number DESC
LIMIT 1;
```

---

## Cross-Layer Factor Combinations

### Panel Structure (All Layers in One Row)

The `predictions.panel_structure` table carries factors from ALL layers:

```sql
CREATE TABLE predictions.panel_structure (
    -- Observation ID
    observation_id BIGINT PRIMARY KEY,
    
    -- LAYER 1: League/Season
    season INTEGER,
    league_environment_id VARCHAR,
    league_hr_rate DECIMAL(5,4),
    
    -- LAYER 2: Team
    home_team_id VARCHAR,
    away_team_id VARCHAR,
    home_team_win_pct DECIMAL(4,3),
    away_team_streak VARCHAR,
    
    -- LAYER 3: Players
    pitcher_id VARCHAR,
    batter_id VARCHAR,
    pitcher_woba_allowed DECIMAL(4,3),
    batter_woba DECIMAL(4,3),
    
    -- LAYER 4: Matchup
    matchup_pair_id VARCHAR,
    matchup_career_pas INTEGER,
    matchup_career_woba DECIMAL(4,3),
    
    -- LAYER 5: State
    game_state_id VARCHAR,
    pa_state_id VARCHAR,
    count_label VARCHAR(5),
    base_state INTEGER,
    outs INTEGER,
    leverage_index DECIMAL(4,2),
    
    -- Target
    outcome VARCHAR,
    outcome_probability DECIMAL(5,4)
);
```

This enables models to SELECT any combination:
```sql
-- Model using L1, L3, L5 only
SELECT league_hr_rate, batter_woba, count_label, outcome
FROM predictions.panel_structure;

-- Model using L2, L4 only
SELECT home_team_win_pct, matchup_career_woba, outcome
FROM predictions.panel_structure;
```

---

## Factor Selection Guide

### By Prediction Target

| Target | Recommended Layers | Key Factors |
|--------|-------------------|-------------|
| **Next pitch type** | L3, L5 | `pitcher_id`, `count_label`, `previous_pitch_type`, `pitch_mix_by_count` |
| **PA outcome (K/BB/Hit)** | L1, L3, L5 | `k_rate`, `bb_rate`, `count_label`, `base_state` |
| **HR probability** | L1, L3, L4, L5 | `hr_rate`, `vs_fastball_slg`, `matchup_hr_rate`, `count_label` |
| **Game winner** | L1, L2, L3 | `runs_per_game`, `team_win_pct`, `starter_quality` |
| **Run total O/U** | L1, L2, L3 | `ball_carry_index`, `park_factor`, `bullpen_era` |

### By Model Type

| Model Type | Layer Focus | Example Features |
|------------|-------------|------------------|
| **Markov Chain** | L5 primary | `count_label`, `transition_probabilities` |
| **XGBoost** | All layers | 50+ features from L1-L5 |
| **LSTM/GRU** | L5 sequences | `pitch_sequence`, `count_sequence` |
| **Time-Series** | L1 primary | `season`, `month`, `hr_rate_trend` |
| **Bayesian Hierarchical** | L3, L4 | `player_id` random effects, `matchup_history` |

---

## Research KB Integration

### Relevant Knowledge Base Entries

1. **Pitch Sequence Modeling**
   - Memory: Pitch sequence Markov chains
   - Source: BaseballDataScience.com research
   - Factors: `count_label`, `raw_symbol`, `next_pitch_symbol`

2. **Statcast Model Architectures**
   - Document: `STATCAST_MODELS_RESEARCH_REPORT.md`
   - Models: XGBoost hierarchical, LSTM multi-task
   - Factors: All L3-L5 factors

3. **Player Attribution**
   - Document: `PITCH_PLAYER_ANALYSIS_ARCHITECTURE.md`
   - Focus: L3 player profiles, L4 matchups
   - Factors: `pitcher_id`, `batter_id`, bridge tables

4. **Panel Data Methodology**
   - Concept: Hierarchical/random effects models
   - Application: Multi-layer prediction
   - Factors: All layers with `random_effect` flags

---

## Data Refresh Schedule

| Layer | Table | Refresh Frequency | Trigger |
|-------|-------|------------------|---------|
| L1 | `league_environment` | Annual/Monthly | New season data |
| L2 | `team_context_rolling` | Daily | Game completion |
| L3 | `batter_profiles_rolling` | Daily | New games |
| L3 | `pitcher_profiles_rolling` | Daily | New games |
| L4 | `matchup_history` | Weekly | Cumulative H2H |
| L5 | `live_game_state` | Real-time | Each pitch |

---

## Usage Examples

### Example 1: Select Features for HR Prediction Model
```sql
-- All factors potentially predictive of HRs
SELECT 
    -- L1: Environment
    l.league_hr_rate,
    l.ball_carry_index,
    
    -- L3: Batter
    b.vs_fastball_slg,
    b.hr_flyball_rate,
    b.hard_hit_rate,
    
    -- L3: Pitcher
    p.fb_pct,
    p.flyball_rate,
    
    -- L4: Matchup
    m.career_hr::float / NULLIF(m.career_pas, 0) as matchup_hr_rate,
    
    -- L5: State
    s.count_label,
    s.base_state,
    s.inning_leverage_index,
    
    -- Target
    CASE WHEN outcome = 'home_run' THEN 1 ELSE 0 END as is_hr
FROM predictions.panel_structure p
JOIN predictions.league_environment l USING (season)
JOIN predictions.batter_profiles_rolling b ON p.batter_id = b.batter_id
JOIN predictions.pitcher_profiles_rolling p ON p.pitcher_id = p.pitcher_id
LEFT JOIN predictions.matchup_history m ON p.matchup_pair_id = m.matchup_pair_id
JOIN predictions.live_game_state s ON p.observation_id = s.pitch_id;
```

### Example 2: Exclude Specific Factors (Feature Ablation)
```sql
-- Same query but exclude L4 (matchup) factors
-- Just don't join matchup_history table
SELECT 
    l.league_hr_rate,
    b.vs_fastball_slg,
    p.fb_pct,
    s.count_label,
    outcome
FROM predictions.panel_structure p
JOIN predictions.league_environment l USING (season)
JOIN predictions.batter_profiles_rolling b ON p.batter_id = b.batter_id
JOIN predictions.pitcher_profiles_rolling p ON p.pitcher_id = p.pitcher_id
-- NO matchup join
JOIN predictions.live_game_state s ON p.observation_id = s.pitch_id;
```

---

## Summary

This data dictionary provides **100+ factors** across 5 layers of abstraction:

- **Layer 1 (League):** 20+ season/environment factors
- **Layer 2 (Team):** 25+ form/context factors
- **Layer 3 (Players):** 40+ batter/pitcher profile factors
- **Layer 4 (Matchup):** 15+ H2H factors
- **Layer 5 (State):** 30+ real-time situational factors

**Total: 130+ unique predictive factors** available for model training.

All factors are stored in the panel data structure, enabling flexible feature selection without query modification.

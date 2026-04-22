# Feature Engineering Plan - Advanced Predictive Features

**Date:** 2026-04-22  
**Goal:** Generate new predictive features across 8 key areas: pitch data, weather, momentum, umpires, coaches, postseason effects, stadium effects, and crowd/attendance.

---

## 1. Executive Summary

### Current State
- **Base Model:** PA outcome distribution (11 classes), log_loss=1.51, accuracy=41.3%
- **Feature Count:** 89 features (advanced_count set)
- **Data Available:** 4.78M historical PAs, 7.8M Statcast pitches (2015-2025)
- **Coverage:** All games 2000-2025 have attendance, temperature, wind data

### Target Improvement
- **Goal:** Reduce log_loss from 1.51 to <1.45 (4%+ improvement)
- **Approach:** Add 40-60 new engineered features across 8 categories
- **Priority Order:** Pitch data → Weather/Stadium → Momentum → Umpires → Coaches → Postseason

---

## 2. Feature Categories & Implementation Plan

### CATEGORY 1: Pitch Data (Statcast) - HIGHEST PRIORITY
**Data Source:** `raw_mlb.statcast` (7.8M pitches, 2015-2025)
**Lead:** You  
**Timeline:** 3-4 days

#### 1.1 Pitcher Arsenal & Usage Patterns
```sql
-- Pitch type distribution per pitcher
-- Pitch velocity trends (fastball velo decline = fatigue)
-- Pitch sequencing patterns (FB-CB vs CB-FB)
-- Pitch location tendencies (pitcher-specific zones)
```

**Features to Build:**
- [ ] `pitcher_fastball_pct` - % of fastballs thrown
- [ ] `pitcher_breaking_pct` - % of breaking balls (SL/CU)
- [ ] `pitcher_offspeed_pct` - % of offspeed (CH/FS)
- [ ] `pitcher_fb_velocity_90th` - Top-end velocity (fatigue indicator)
- [ ] `pitcher_velocity_decline` - 1st inning vs 6th inning velo drop
- [ ] `pitcher_spin_rate_avg` - Average spin rate
- [ ] `pitcher_spin_efficiency` - Active spin vs total spin
- [ ] `pitcher_release_extension` - Release point distance

#### 1.2 Batter-Pitcher Matchup Deep Dive
```sql
-- Historical matchup outcomes from Statcast
-- Swing decisions (chase rate, zone contact)
-- Batted ball quality against specific pitcher types
```

**Features to Build:**
- [ ] `matchup_chase_rate` - Batter's chase rate vs this pitcher
- [ ] `matchup_zone_contact_rate` - Contact rate in zone
- [ ] `matchup_whiff_rate` - Swing-and-miss rate
- [ ] `matchup_barrel_rate` - Barrel rate vs this pitcher
- [ ] `matchup_hard_hit_rate` - 95+ mph exit velocity rate

#### 1.3 In-Game Fatigue & Timing
- [ ] `pitcher_pitches_this_game` - Current pitch count
- [ ] `pitcher_times_through_order` - 1st/2nd/3rd time facing lineup
- [ ] `pitcher_days_rest` - Days since last appearance
- [ ] `batter_pa_today` - Batter's PAs in current game

#### 1.4 Pitch Quality Metrics
- [ ] `pitch_location_distance_from_heart` - Distance from center of zone
- [ ] `pitch_horizontal_break` - pfx_x movement
- [ ] `pitch_vertical_break` - pfx_z movement
- [ ] `pitch_approach_angle` - arm_angle from Statcast

---

### CATEGORY 2: Weather & Environmental Effects
**Data Source:** `core.games` (attendance, temp, wind) + NOAA API
**Lead:** You  
**Timeline:** 2-3 days

#### 2.1 Weather Conditions
**Already Have:** temperature_f, wind_speed_mph, wind_direction
**Need to Build:**

- [ ] `temp_extreme_flag` - >90°F or <50°F (affects grip/ball carry)
- [ ] `wind_in_direction` - Wind blowing toward LF/CF/RF (home run effect)
- [ ] `wind_out_speed` - Speed of wind blowing out
- [ ] `wind_effect_score` - Combined direction + speed score
- [ ] `humidity_proxy` - Based on month + temperature (if no direct data)

#### 2.2 Stadium Environmental Effects
- [ ] `park_day_game_factor` - Day vs night performance split
- [ ] `park_sun_angle_effect` - Fly ball difficulty by time of day
- [ ] `park_shadows_effect` - Late afternoon shadow games
- [ ] `altitude_factor` - Elevation effect on ball carry

#### 2.3 Ball Behavior Predictions
- [ ] `estimated_flight_distance` - Based on temp + wind + altitude
- [ ] `home_run_likelihood_boost` - Environmental HR factor (0.8-1.2)

---

### CATEGORY 3: Momentum & Streaks
**Data Source:** `core.games` + derived window functions
**Lead:** You  
**Timeline:** 2-3 days

#### 3.1 Team Momentum
- [ ] `team_last_5_win_rate` - Last 5 games (hot/cold)
- [ ] `team_last_10_win_rate` - Last 10 games
- [ ] `team_last_3_runs_scored_avg` - Recent offensive momentum
- [ ] `team_last_3_runs_allowed_avg` - Recent pitching momentum
- [ ] `team_momentum_delta` - Change from 30-day to 5-day performance

#### 3.2 Batter Momentum
- [ ] `batter_last_7_pa_count` - Recent playing time
- [ ] `batter_last_7_avg` - Last 7 days batting average
- [ ] `batter_last_7_obp` - Last 7 days on-base
- [ ] `batter_last_7_slg` - Last 7 days slugging
- [ ] `batter_streak_length` - Consecutive games with hit

#### 3.3 Pitcher Momentum
- [ ] `pitcher_last_3_era` - Last 3 starts ERA
- [ ] `pitcher_last_3_innings_avg` - Last 3 starts length
- [ ] `pitcher_last_3_strikeout_rate` - Recent K-rate
- [ ] `pitcher_last_3_walk_rate` - Recent BB-rate
- [ ] `pitcher_quality_starts_last_5` - Quality starts in last 5

---

### CATEGORY 4: Umpire Effects
**Data Source:** `core.umpires` + `raw_mlb.statcast` (umpire column)
**Lead:** You  
**Timeline:** 2-3 days

#### 4.1 Umpire Strike Zone
- [ ] `umpire_strike_zone_size` - Runs small/large zone
- [ ] `umpire_strike_zone_top` - Personalized top of zone
- [ ] `umpire_strike_zone_bottom` - Personalized bottom of zone
- [ ] `umpire_strike_calls_pct` - % called strikes (vs league avg)
- [ ] `umpire_ball_calls_pct` - % called balls

#### 4.2 Umpire Game Impact
- [ ] `umpire_k_friendly` - Higher strikeout games correlation
- [ ] `umpire_walk_friendly` - Higher walk games correlation
- [ ] `umpire_hitter_favored` - Runs small zone (favors hitters)
- [ ] `umpire_pitcher_favored` - Runs large zone (favors pitchers)

#### 4.3 Umpire Consistency
- [ ] `umpire_consistency_score` - Variance in zone calls
- [ ] `umpire_experience_years` - Tenure (experience = consistency?)

---

### CATEGORY 5: Coaching Effects
**Data Source:** `core.coach_assignments` + historical records
**Lead:** You  
**Timeline:** 3-4 days (need external data)

#### 5.1 Manager/Coach Experience
- [ ] `manager_experience_years` - Years as manager
- [ ] `manager_career_win_pct` - All-time winning percentage
- [ ] `manager_playoff_experience` - Playoff games managed
- [ ] `hitting_coach_tenure_months` - Time with current team
- [ ] `pitching_coach_tenure_months` - Time with current team

#### 5.2 Coaching Performance
- [ ] `team_improvement_under_coach` - Performance change since hire
- [ ] `coach_specialty_rating` - Reputation score (need external source)

---

### CATEGORY 6: Postseason & Clutch Effects
**Data Source:** `core.games` + historical records
**Lead:** You  
**Timeline:** 2-3 days

#### 6.1 Player Clutch History
- [ ] `batter_postseason_career_avg` - Career postseason average
- [ ] `batter_postseason_career_ops` - Career postseason OPS
- [ ] `batter_clutch_rating` - (RISP - overall) performance diff
- [ ] `batter_high_leverage_rating` - Late & close performance

#### 6.2 Current Game Context
- [ ] `is_postseason` - Flag for playoff games
- [ ] `is_elimination_game` - Win or go home
- [ ] `is_rivalry_game` - Historical rivalry flag (NYY-BOS, etc.)
- [ ] `games_back_in_standings` - Pressure/motivation factor

#### 6.3 Alex Rodriguez Effect (Choke Artists)
- [ ] `batter_october_decline` - Regular season vs postseason diff
- [ ] `batter_pressure_performance` - High-leverage vs normal split
- [ ] `batter_clutch_factor` - Custom clutch metric

---

### CATEGORY 7: Stadium Effects (Beyond Park Factors)
**Data Source:** `core.parks` + derived metrics
**Lead:** You  
**Timeline:** 2 days

#### 7.1 Stadium Physics
- [ ] `park_elevation_feet` - Altitude (Coors effect)
- [ ] `park_left_field_distance` - 315-335 ft range
- [ ] `park_center_field_distance` - 390-420 ft range
- [ ] `park_right_field_distance` - 315-335 ft range
- [ ] `park_left_field_height` - Wall height in LF
- [ ] `park_right_field_height` - Wall height in RF
- [ ] `park_foul_ground` - Amount of foul territory

#### 7.2 Stadium Characteristics
- [ ] `park_grass_turf` - Grass vs artificial turf
- [ ] `park_retractable_roof` - Roof status (closed = no wind/sun)
- [ ] `park_dome` - Indoor/outdoor effect
- [ ] `park_visibility_rating` - Sight lines affecting fielders

---

### CATEGORY 8: Crowd & Attendance Effects
**Data Source:** `core.games.attendance` + derived metrics
**Lead:** You  
**Timeline:** 2 days

#### 8.1 Attendance Level
- [ ] `attendance_vs_capacity_pct` - Crowd fullness
- [ ] `attendance_vs_team_avg` - Above/below normal for team
- [ ] `attendance_vs_league_avg` - Above/below league average
- [ ] `attendance_change_pct` - Change from last game

#### 8.2 Crowd Effect
- [ ] `home_field_advantage_score` - Combined attendance + team performance
- [ ] `is_sellout` - 95%+ capacity
- [ ] `crowd_noise_proxy` - Day game + attendance interaction
- [ ] `rivalry_crowd_boost` - Higher attendance for rival games

---

## 3. Implementation Priority

### Phase 1: Quick Wins (Days 1-5) - Pitch Data + Attendance
1. **Statcast pitcher features** (arsenal, velocity, spin)
2. **Attendance-based crowd effects**
3. **Basic weather effects** (temp extremes, wind)

### Phase 2: Context Features (Days 6-10)
4. **Momentum/streak features** (team + player)
5. **Umpire strike zone tendencies**
6. **Postseason clutch flags**

### Phase 3: Advanced Features (Days 11-15)
7. **Batter-pitcher matchup deep dive** (Statcast-level)
8. **Stadium physics** (elevation, dimensions)
9. **Coaching effects** (need external data)
10. **Clutch performance metrics** (A-Rod effect detection)

---

## 4. Technical Implementation Notes

### SQL Pattern for New Feature Marts
```sql
-- Create materialized view for each feature category
CREATE MATERIALIZED VIEW features.pitcher_arsenal_features AS
SELECT 
    pitcher_id,
    season,
    feature_season,
    -- Arsenal metrics
    fastball_pct,
    breaking_pct,
    offspeed_pct,
    avg_velocity,
    spin_rate_avg,
    -- Fatigue indicators
    velocity_decline_late_game,
    times_through_order_penalty
FROM ...
WITH DATA;

-- Join in main feature view
CREATE VIEW features.plate_appearance_enhanced_examples AS
SELECT 
    pa.*,
    arsenal.fastball_pct,
    arsenal.velocity_decline_late_game,
    momentum.team_last_5_win_rate,
    weather.wind_effect_score,
    umpire.strike_zone_size,
    attendance.attendance_vs_capacity_pct
FROM features.plate_appearance_advanced_examples pa
LEFT JOIN features.pitcher_arsenal_features arsenal ...
LEFT JOIN features.team_momentum_features momentum ...
...
```

### Model Training Update
```bash
# After adding features, train new model
uv run python scripts/model_training/train_pa_outcome_distribution.py \
    --feature-set enhanced \
    --target-taxonomy grouped \
    --train-through 2022 \
    --sample-rate 0.1
```

---

## 5. Expected Impact

| Feature Category | Expected Log Loss Improvement | Confidence |
|-----------------|------------------------------|------------|
| Pitch Data (Statcast) | -0.03 to -0.05 | High |
| Weather/Environment | -0.01 to -0.02 | Medium |
| Momentum/Streaks | -0.01 to -0.03 | Medium |
| Umpire Effects | -0.01 to -0.02 | Medium-High |
| Stadium Physics | -0.01 to -0.02 | Medium |
| Attendance/Crowd | -0.005 to -0.01 | Low-Medium |
| Postseason/Clutch | -0.005 to -0.01 | Low |
| Coaching | -0.005 to -0.01 | Low |
| **TOTAL POTENTIAL** | **-0.07 to -0.15** | **Medium** |

**Target:** Log Loss 1.51 → 1.40 (7% improvement)

---

## 6. Questions for You

### Before I Start Building:

1. **Priority Check:** Does the Phase 1-3 ordering make sense to you? Any categories you want to reorder?

2. **External Data:** For coaching effects, should I:
   - A) Scrape Baseball-Reference for manager career stats?
   - B) Use Lahman database (has manager tables)?
   - C) Skip coaching for now and focus on on-field features?

3. **Statcast Integration:** Should I:
   - A) Create pitcher-level aggregations from Statcast (easier)?
   - B) Create pitch-level features joined to each PA (more granular)?
   - C) Both?

4. **Clutch Metrics:** For the "A-Rod effect" (choking), what defines clutch?
   - A) Postseason vs Regular season split?
   - B) High-leverage (late/close) vs Low-leverage?
   - C) RISP (runners in scoring position) vs bases empty?
   - D) All of the above combined?

5. **Weather Data:** Should I backfill historical weather using NOAA API, or just use what we have in core.games?

6. **Feature Selection:** After building all these, should we run feature importance analysis to prune low-value features?

---

## 7. Next Steps

1. **Your Approval:** Review this plan and answer the 6 questions above
2. **Phase 1 Kickoff:** I'll start with Statcast pitcher arsenal features
3. **Daily Updates:** I'll update you on progress and any decisions needed
4. **Validation:** After each phase, we'll test model improvement

**Ready to start when you give the go-ahead!**

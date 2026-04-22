# Live Betting Pipeline Status Report

**Date:** 2026-04-22
**Purpose:** Comprehensive status assessment for live betting and prediction infrastructure

## Executive Summary

The retrosheet warehouse has excellent historical modeling infrastructure but is **not yet ready for live betting**. The pipeline lacks real-time data ingestion, comprehensive feature engineering for live prediction, and integration with betting markets. Significant infrastructure work is required before live betting can be operational.

**Current Readiness Level:** 30% (Historical modeling strong, live infrastructure weak)

---

## Current State Assessment

### ✅ What We Have (Strong Foundation)

**Historical Data & Modeling:**
- Historical Retrosheet data: 2000-2025 (4.7M plate appearances)
- Best PA outcome model: HistGradientBoosting, advanced_count features
- Calibration infrastructure: Isotonic calibration, ECE tracking
- Bootstrap evaluation: Season-stratified uncertainty estimation
- Model registry: Version tracking, artifact persistence
- Feature marts: Prior-season stats, rolling averages, matchup features

**Bridge Tables (Partially Complete):**
- `bridge.player_xref`: Retrosheet ↔ MLB player IDs (via Chadwick Register)
- `bridge.team_xref`: Retrosheet ↔ MLB team IDs (30 teams mapped)
- `bridge.park_xref`: Retrosheet ↔ MLB venue IDs (45 venues mapped)
- `bridge.game_xref`: Game cross-reference (date + team + game number matching)
- `bridge.coach_xref`: Coach cross-reference (biofile_legacy name resolution)
- `bridge.umpire_xref`: Umpire cross-reference (biofile_legacy name resolution)
- `bridge.external_player_xref`: External IDs (Statcast, Baseball Reference, Lahman)
- Confidence scoring framework: 0.0-1.0 scores with source tracking

**SQL Procedures (Recently Added):**
- `bridge.populate_all_bridge_tables()`: Master orchestrator
- `bridge.populate_season_aware_team_xref()`: Season-aware team mappings
- `bridge.populate_game_xref()`: Game matching by date/teams
- `bridge.populate_player_xref_full()`: SQL-based player ID population
- Validation functions: Boolean checks for data quality

**Live Data Infrastructure (Partial):**
- `raw_mlb.schedule_snapshots`: 9,286 MLB schedule snapshots
- `raw_mlb.live_feed_snapshots`: 72,199 live feed snapshots
- `core.live_games`: 67,913 transformed games
- `core.live_events`: 5.1M transformed events
- `raw_espn.game_snapshots`: ESPN API data (issue #59 completed)
- Live feature parity view: `features.live_plate_appearance_advanced_count_examples`

---

### ❌ What We're Missing (Critical Gaps)

**Real-Time Data Ingestion:**
- ❌ No automated live game discovery and ingestion pipeline
- ❌ No real-time play-by-play streaming from MLB/ESPN
- ❌ No materialized view refresh automation
- ❌ No pg_cron scheduling infrastructure
- ❌ No dependency-aware refresh strategy
- ❌ No data quality monitoring for live data

**Comprehensive Features for Live Prediction:**
- ❌ Player salaries: No salary data or cap impact modeling
- ❌ Injuries: No injury status, DL, IL tracking
- ❌ Fatigue: No rest days, travel distance, workload tracking
- ❌ Streaks: No hot/cold streak features
- ❌ Weather: No weather data for outdoor games
- ❌ Umpire effects: No umpire strike zone tendencies
- ❌ Coach effects: No manager decision tendencies
- ❌ Lineup changes: No projected vs actual lineup tracking

**Master Model Architecture:**
- ❌ No multi-outcome prediction framework (game, player, season, feats)
- ❌ No ensemble model infrastructure
- ❌ No feature selection for different prediction types
- ❌ No model versioning for different prediction horizons
- ❌ No A/B testing framework for model variants

**Betting Integration:**
- ❌ No Polymarket API integration
- ❌ No market data ingestion (odds, spreads, prices)
- ❌ No bet placement infrastructure
- ❌ No position sizing/risk management
- ❌ No P&L tracking and performance monitoring
- ❌ No market efficiency analysis

**Real-Time Pipeline:**
- ❌ No maintenance schema for automated procedures
- ❌ No refresh procedures for materialized views
- ❌ No live prediction logging
- ❌ No prediction-to-bet decision logic
- ❌ No latency monitoring
- ❌ No alerting for prediction drift

**Bridge Table Gaps:**
- ⚠️ Season-aware team mappings implemented but not fully tested
- ⚠️ Player_xref missing bbref_id and fangraphs_id columns (schema enhancement created, not applied)
- ⚠️ ESPN bridge tables created but population not tested
- ⚠️ No salary data bridge (MLB salary data not integrated)
- ⚠️ No injury data bridge (MLB injury reports not integrated)

---

## Detailed Gap Analysis

### 1. Real-Time Data Ingestion Pipeline

**Current State:**
- Manual ingestion via Python scripts
- No automation
- No scheduling
- Manual materialized view refresh

**Required for Live Betting:**
- Automated schedule discovery (every 5 minutes during game hours)
- Real-time play-by-play streaming (MLB Stats API or ESPN)
- Automatic transformation and feature update
- Sub-5 second latency from play to prediction
- Retry logic and error handling
- Monitoring and alerting

**Implementation Path:**
1. Install pg_cron extension
2. Create maintenance schema with refresh procedures
3. Implement scheduled live game discovery
4. Implement real-time play-by-play ingestion
5. Implement automated feature mart refresh
6. Add monitoring and alerting

**Estimated Effort:** 2-3 weeks

---

### 2. Comprehensive Feature Engineering

**Current State:**
- Prior-season stats (PA-level, pitcher-level, team-level)
- Rolling averages (30-game, 100-game windows)
- Matchup features (batter vs pitcher history)
- Park factors
- Count-state features
- Context features (inning, runners, outs)

**Missing Critical Features:**

**Player-Level:**
- Salary and cap impact
- Injury status (day-to-day, IL, DL)
- Fatigue metrics (rest days, consecutive games played)
- Streak metrics (hot/cold, last 10 games)
- Age and decline curves
- Position versatility

**Team-Level:**
- Travel distance and fatigue
- Rest days between games
- Rotation status (starter vs bullpen)
- Bullpen usage patterns
- Manager tendencies (aggressive vs conservative)
- Team chemistry/cohesion metrics

**Game-Level:**
- Weather (temperature, wind, humidity, precipitation)
- Umpire strike zone tendencies
- Home field advantage (adjusted for travel)
- Lineup changes (projected vs actual)
- Pitcher rest days
- Motivation factors (playoff race, elimination)

**Season-Level:**
- Team payroll and spending efficiency
- Front office quality metrics
- Draft and development quality
- Long-term injury trends

**Implementation Path:**
1. Add salary data source (MLB salary database)
2. Add injury data source (MLB injury reports, Rotowire)
3. Add weather data source (OpenWeatherMap)
4. Add umpire data source (MLB umpire database)
5. Engineer fatigue features from schedule data
6. Engineer streak features from recent performance
7. Engineer travel features from schedule data
8. Engineer lineup change features from projected vs actual

**Estimated Effort:** 3-4 weeks

---

### 3. Master Model Architecture

**Current State:**
- Single-target PA outcome model (multiclass)
- Game-level binary models (home win)
- Half-inning models (run probability)
- Individual model training scripts
- Manual model selection

**Required for Live Betting:**
- Multi-target prediction framework (game, player, season, feats)
- Ensemble model infrastructure (stacking, blending)
- Feature selection per prediction type
- Model versioning for different horizons
- A/B testing framework
- Prediction confidence intervals
- Model drift detection

**Prediction Types Needed:**
- Game outcomes (moneyline, spread, total)
- Player props (hits, HR, RBI, strikeouts)
- Season props (wins, HR, ERA)
- Feat props (first inning score, longest hit)
- Live props (next at-bat outcome, next inning runs)

**Implementation Path:**
1. Design multi-target prediction framework
2. Implement ensemble infrastructure
3. Create feature selection per prediction type
4. Implement model versioning system
5. Create A/B testing framework
6. Add prediction confidence intervals
7. Add model drift detection

**Estimated Effort:** 4-6 weeks

---

### 4. Betting Integration

**Current State:**
- None

**Required for Live Betting:**
- Polymarket API integration
- Market data ingestion (odds, spreads, prices)
- Bet placement infrastructure
- Position sizing/risk management
- P&L tracking and performance monitoring
- Market efficiency analysis
- Arbitrage detection

**Implementation Path:**
1. Integrate Polymarket API
2. Ingest market data (odds, spreads, prices)
3. Implement bet placement logic
4. Implement position sizing (Kelly criterion, risk parity)
5. Implement P&L tracking
6. Implement performance monitoring
7. Implement market efficiency analysis

**Estimated Effort:** 3-4 weeks

---

### 5. Bridge Table Completeness

**Current State:**
- Player, team, park, game, coach, umpire bridges exist
- Season-aware team mappings implemented
- Confidence scoring framework in place
- Validation functions created

**Missing:**
- bbref_id and fangraphs_id not in player_xref (schema enhancement created, not applied)
- ESPN bridge population not tested
- No salary data bridge
- No injury data bridge
- No weather data bridge
- Season-aware team mappings not fully tested

**Implementation Path:**
1. Apply player_xref schema enhancement (bbref_id, fangraphs_id)
2. Test ESPN bridge population
3. Add salary data bridge
4. Add injury data bridge
5. Add weather data bridge
6. Test season-aware team mappings thoroughly

**Estimated Effort:** 1-2 weeks

---

## Recommended Implementation Order

### Phase 1: Foundation (Week 1-2)
1. Apply player_xref schema enhancement
2. Test all bridge table populations
3. Implement maintenance schema and refresh procedures
4. Install pg_cron extension
5. Implement automated materialized view refresh

### Phase 2: Real-Time Ingestion (Week 3-4)
1. Implement automated live game discovery
2. Implement real-time play-by-play ingestion
3. Implement automated feature mart refresh
4. Add monitoring and alerting
5. Test end-to-end latency

### Phase 3: Feature Engineering (Week 5-8)
1. Add salary data and bridge
2. Add injury data and bridge
3. Add weather data and bridge
4. Engineer fatigue features
5. Engineer streak features
6. Engineer travel features
7. Engineer lineup change features

### Phase 4: Model Architecture (Week 9-14)
1. Design multi-target prediction framework
2. Implement ensemble infrastructure
3. Create feature selection per prediction type
4. Implement model versioning system
5. Create A/B testing framework
6. Add prediction confidence intervals
7. Add model drift detection

### Phase 5: Betting Integration (Week 15-18)
1. Integrate Polymarket API
2. Ingest market data
3. Implement bet placement logic
4. Implement position sizing
5. Implement P&L tracking
6. Implement performance monitoring
7. Implement market efficiency analysis

---

## Critical Path to Live Betting

**Minimum Viable Product (MVP) for Live Betting:**
1. Real-time play-by-play ingestion (MLB Stats API)
2. Automated feature mart refresh (pg_cron)
3. Multi-target prediction framework
4. Polymarket API integration
5. Bet placement infrastructure
6. Position sizing logic

**Estimated Time to MVP:** 8-10 weeks

**Full Production System:** 18-20 weeks

---

## Immediate Next Steps (This Week)

1. Apply player_xref schema enhancement (bbref_id, fangraphs_id)
2. Test all bridge table populations with validation functions
3. Implement maintenance schema and refresh procedures
4. Install pg_cron extension
5. Create GitHub issue for real-time ingestion pipeline

---

## Risks and Mitigations

**Risk 1: Real-time Latency**
- Mitigation: Use MLB Stats API (faster than ESPN), optimize SQL queries, use materialized views

**Risk 2: Data Quality Issues**
- Mitigation: Validation functions, confidence scoring, monitoring alerts

**Risk 3: Model Drift**
- Mitigation: Regular retraining, drift detection, A/B testing

**Risk 4: Market Integration Complexity**
- Mitigation: Start with paper trading, small position sizes, gradual ramp-up

**Risk 5: Regulatory Issues**
- Mitigation: Consult legal counsel, comply with jurisdiction requirements

---

## Conclusion

The retrosheet warehouse has excellent historical modeling infrastructure but requires significant work for live betting. The foundation is solid (bridge tables, feature engineering, model training), but the real-time infrastructure is missing entirely.

**Key Takeaway:** Focus on real-time ingestion and feature engineering first. Historical models are already strong; the bottleneck is getting live data into the prediction pipeline fast enough for betting decisions.

# Knowledge Base vs. Implementation Comparison Report

**Date:** 2026-04-23  
**Purpose:** Compare pitch-level modeling approaches from research literature vs. our current implementation

---

## Executive Summary

Our implementation **aligns well** with research best practices but has **gaps in execution** that need addressing. We have the data infrastructure correct but haven't fully populated all the player profile tables.

---

## 1. WHAT THE RESEARCH SAYS

### A. Key Research Findings on Pitch-Level Modeling

| Study | Approach | Features Used | Target | Accuracy |
|-------|----------|---------------|--------|----------|
| **SMU Gopal et al.** | Feedforward Neural Net (2×128) | Pitch physics, count, batter metrics | Ball/Foul/Strike/InPlay | **58%** (F1=0.81 for balls) |
| **CMU Neural Sabermetrics** | Llama-3.2 3B (LLM) | 7M pitch sequences | Pitch type, swing decision | **63.7%** pitch type, **76.6%** swing IZ |
| **Towards Data Science** | LightGBM | Location, speed, break, count, prev pitch | Swing/Take binary | **80.5%** (Joey Votto) |
| **Penn State** | ML + Sabermetrics | PITCHf/x, HITf/x, Statcast | Game winners | **~60%** |

### B. Research-Validated Features for Pitch-Level Models

From the KB, these features have proven predictive value:

**Pitch Physics (Always Included)**
- ✓ Release point (x, y, z)
- ✓ Velocity (start_speed, effective_speed)
- ✓ Spin rate and spin axis
- ✓ Movement (pfx_x, pfx_z)
- ✓ Plate location (plate_x, plate_z)
- ✓ Zone classification

**Context Features (Always Included)**
- ✓ Count (balls, strikes)
- ✓ Base state (on_1b, on_2b, on_3b)
- ✓ Inning, outs
- ✓ Score differential
- ✓ Previous pitch type

**Player-Specific Features (Research-Validated)**
- ✓ Pitcher arsenal composition (% fastball, breaking, offspeed)
- ✓ Batter zone discipline (swing % by zone)
- ✓ Pitcher-batter matchup history
- ✓ Times through order
- ✓ Pitch count (fatigue)

### C. Research Best Practices

1. **Source Preservation:** Never modify raw data ✓ (We do this)
2. **Bridge Tables for ID Linkage:** ✓ (We have this)
3. **Feature Engineering:** Combine sabermetrics with advanced metrics ✓ (In progress)
4. **Context Weighting:** Weight by game importance (not implemented yet)
5. **Markov Framework:** Use for PA simulation (not implemented yet)
6. **Run Expectancy:** RE288 for state values (not implemented yet)

---

## 2. WHAT WE HAVE BUILT

### A. Data Infrastructure (EXCELLENT - Research-Aligned)

| Component | Status | Alignment |
|-----------|--------|-----------|
| Source-preserved Statcast | ✅ 7.66M pitches | ✓ Research best practice |
| Quality flags for outliers | ✅ Implemented | ✓ Data integrity |
| Player attribution (batter_id, pitcher_id) | ✅ 100% coverage | ✓ Essential for player profiles |
| Bridge linkage (player_xref, game_xref) | ✅ 100% players linked | ✓ Enables cross-source analysis |
| PostGIS geometry for spatial analysis | ✅ Implemented | ✓ Enables zone analysis |

### B. Player Profile Tables (PARTIAL - Need Completion)

| Table | Research Need | Status | Gap |
|-------|-----------------|--------|-----|
| **pitcher_arsenals** | Required for arsenal %, velocity | ✅ Populated (2025 only) | Need all seasons |
| **batter_pitch_type_performance** | Required for batter-pitcher matchups | ✅ Populated (2025 only) | Need all seasons |
| **batter_zone_profiles** | Required for zone discipline | ⚠️ Empty | Not populated |
| **matchup_history** | Required for head-to-head | ⚠️ Empty | Not populated |
| **count_performance** | Required for count-specific performance | ⚠️ Empty | Not populated |

### C. Modeling Pipeline (NOT YET BUILT)

| Component | Research Need | Status |
|-----------|---------------|--------|
| Pitch outcome classifier (Ball/Foul/Strike/InPlay) | SMU paper: 58% accuracy | ❌ Not built |
| Swing probability model | Towards Data Science: 80.5% | ❌ Not built |
| Pitch type predictor | CMU: 63.7% accuracy | ❌ Not built |
| PA outcome model using pitch features | Baseline: log_loss=1.51 | ❌ Not integrated |

---

## 3. COMPARISON: KB Recommendations vs. Our Implementation

### ✅ ALIGNED (We're Doing This Right)

| KB Recommendation | Our Implementation |
|-------------------|-------------------|
| Source-preserved raw data | `raw_mlb.statcast` - source preserved ✓ |
| Player attribution on every pitch | `pitcher_id`, `batter_id` on all 7.66M pitches ✓ |
| Bridge tables for ID linkage | `bridge.player_xref`, `bridge.game_xref` ✓ |
| Arsenal composition features | `pitcher_arsenals` table structure ✓ |
| Zone discipline metrics | `batter_zone_profiles` designed ✓ |
| Matchup history tracking | `matchup_history` designed ✓ |
| Outlier quality flags | `quality_flag` column implemented ✓ |

### ⚠️ PARTIAL (Built But Incomplete)

| KB Recommendation | Our Implementation | Gap |
|---------------------|-------------------|-----|
| Complete pitcher profiles all seasons | 2025 only (2,595 rows) | Need 2015-2024 |
| Complete batter profiles all seasons | 2025 only (4,048 rows) | Need 2015-2024 |
| Matchup database | Empty | Needs population |
| Count performance | Empty | Needs population |

### ❌ MISSING (Not Yet Implemented)

| KB Recommendation | Why It Matters | Priority |
|-------------------|----------------|----------|
| **Pitch outcome classifier** | SMU achieved 58% on 4-class (ball/foul/strike/in_play) | HIGH |
| **Swing probability model** | 80.5% accuracy for swing/take decisions | HIGH |
| **Pitch type prediction** | CMU: 63.7% for next pitch type | MEDIUM |
| **Markov PA simulation** | SMU: RE288-based simulation framework | MEDIUM |
| **Run Expectancy (RE288)** | Base-out-count state values | HIGH |
| **Times-through-order penalty** | Research: pitchers worse 2nd/3rd time | MEDIUM |
| **Fatigue indicators** | Velocity decline, spin rate decline | MEDIUM |
| **Context weighting** | High-leverage games weighted more | LOW |

---

## 4. WHAT THE RESEARCH SAYS ABOUT OUR APPROACH

### Our Architecture is Research-Aligned

The KB notes several papers using similar architectures:
- **SMU (Gopal et al.)**: Uses Statcast pitch physics + count + batter metrics → We have this data
- **CMU Neural Sabermetrics**: Uses 7M pitch sequences with player attribution → We have 7.66M pitches with IDs
- **Towards Data Science**: Uses pitch location, speed, break, count, prev pitch → We have all these fields

### Our Missing Pieces (Per Research)

The KB "Missing Features" section explicitly lists:
1. ⚠️ Pitcher fatigue metrics (pitch counts, rest days) - We have data, not computed
2. ⚠️ Pitch sequencing patterns - We have data, not analyzed
3. ⚠️ Pitcher-batter matchup history - Table exists, empty
4. ⚠️ Pitcher platoon splits - Can compute, not done
5. ⚠️ Statcast pitch movement data - We have pfx_x/z, not aggregated
6. ⚠️ Exit velocity and launch angle distributions - We have data, not profiled
7. ⚠️ Zone contact and chase rates - Can compute, not done
8. ⚠️ Barrel rates and hard-hit rates - We have data, not aggregated

**ALL of these are data we have but haven't processed into player profiles.**

---

## 5. RECOMMENDATIONS

### Immediate (Next 1-2 Days)

1. **Populate all seasons** into player profile tables (not just 2025)
   ```sql
   -- Run for each season 2015-2024
   INSERT INTO features_pitch.pitcher_arsenals ... WHERE game_year = 2024;
   ```

2. **Build batter_zone_profiles** with swing/contact rates by zone
   ```sql
   -- Zone discipline metrics (research-validated)
   swing_rate_by_zone, contact_rate_by_zone, chase_rate
   ```

3. **Build matchup_history** for pitcher-batter pairs
   ```sql
   -- Historical head-to-head outcomes
   times_faced, outcomes, avg_launch_speed
   ```

### Short-term (Next Week)

4. **Build pitch outcome classifier** (Ball/Foul/Strike/InPlay)
   - Target: 58% accuracy (SMU benchmark)
   - Features: Physics + count + location
   - Model: Neural net or XGBoost

5. **Build swing probability model**
   - Target: 80%+ accuracy (Towards Data Science benchmark)
   - Features: Location, pitch type, count, batter zone profile
   - Model: LightGBM

6. **Build RE288 table** (Run Expectancy by 24 base-out states)
   - Required for Markov PA simulation
   - Historical averages from Retrosheet data

### Medium-term (Next 2-4 Weeks)

7. **Build pitch type predictor** (What pitch comes next?)
   - Target: 63.7% accuracy (CMU benchmark)
   - Features: Previous pitches, count, pitcher arsenal
   - Model: Neural net or LSTM

8. **Build PA simulation using Markov chains**
   - Use pitch outcome probabilities
   - Simulate PA outcomes pitch-by-pitch
   - Aggregate to PA-level predictions

---

## 6. SUMMARY

### What We're Doing Right
✅ Data infrastructure is research-aligned  
✅ Player attribution is complete  
✅ Bridge linkage enables cross-source analysis  
✅ Quality flags ensure data integrity  

### What We Need to Complete
⚠️ Populate player profiles for ALL seasons (not just 2025)  
⚠️ Build zone discipline metrics (swing/contact/chase rates)  
⚠️ Build matchup history table  
⚠️ Build count performance table  

### What We Haven't Started
❌ Pitch outcome classifier (58% target)  
❌ Swing probability model (80.5% target)  
❌ RE288 run expectancy table  
❌ Markov PA simulation framework  

**Bottom Line:** We have the data foundation that research papers wish they had. Now we need to build the models on top of it.

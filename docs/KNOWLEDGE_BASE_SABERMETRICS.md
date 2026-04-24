# Sabermetrics and Baseball Modeling Knowledge Base

**Date:** 2026-04-23
**Purpose:** Research findings on sabermetrics, baseball modeling, and prediction approaches
**Last Updated:** 2026-04-23 (major expansion with ingested papers)

---

## Table of Contents
1. [Research Sources](#research-sources)
2. [Key Sabermetrics and Metrics](#key-sabermetrics-and-metrics)
3. [Data Sources](#data-sources)
4. [Modeling Approaches](#modeling-approaches)
5. [Advanced Research Findings](#advanced-research-findings)
6. [Best Practices](#best-practices)
7. [Missing Features](#missing-features-in-current-pipeline)
8. [Steroid Era Research](#steroid-era-research)
9. [Retrosheet Bibliography](#retrosheet-bibliography-pavitt)
10. [Next Research Areas](#next-research-areas)

---

## Research Sources

### Machine Learning in Baseball Analytics: Sabermetrics and Beyond (MDPI)
- **URL:** https://www.mdpi.com/2078-2489/16/5/361
- **Key Findings:**
  - Four studies focused on predicting batter and pitcher performance using low-level data (PITCHf/x, HITf/x, Statcast)
  - Goal: Introduce more accurate sabermetrics or new ways to estimate existing metrics
  - Machine learning models can characterize performance metrics for pitchers and batters
  - Form embeddings combined with traditional sabermetrics can predict game winners with over 59% accuracy

### Penn State Research on Machine Learning in Baseball
- **URL:** https://www.nutanix.com/theforecastbynutanix/industry/how-machine-learning-and-ai-can-predict-player-outcomes
- **Key Findings:**
  - Tested on MLB games 2015-2019
  - AI in sabermetrics approach predicted game winners with almost 60% accuracy
  - Uses machine learning to show player's real impact on games

### Swing Probability Modeling (Towards Data Science)
- **URL:** https://towardsdatascience.com/modeling-swing-probability-b02b5ab7fbb5/
- **Key Findings:**
  - LightGBM gradient boosting model for binary swing/take classification
  - Features: pitch location, speed, vertical/horizontal break, count, previous pitch type
  - Achieved 80.5% accuracy for Joey Votto swing predictions
  - Model generates swing probability heatmaps by pitch location
  - Applications: hitter scouting reports, at-bat simulations

### Sabermetrics for MLB Performance and Casino Data Analysis
- **URL:** https://baseballegg.com/2025/11/05/sabermetrics-for-mlb-performance-and-casino-data-analysis
- **Key Findings:**
  - Machine learning processes millions of rows daily
  - Combines in-game tracking data with betting history
  - Systems process FanGraphs baseball splits to optimize predictions
  - Baseball and casino industries converging on similar best practices

### Application of Machine Learning for Baseball Outcome Prediction (MDPI)
- **URL:** https://www.mdpi.com/2076-3417/15/13/7081
- **Key Findings:**
  - Combining interpretable machine learning with sabermetrics provides valuable insights
  - Performance weighting based on game context is important
  - Coaches and analysts benefit from interpretable models

### Use of ML and Deep Learning for MLB Match Prediction (MDPI)
- **URL:** https://www.mdpi.com/2076-3417/11/10/4499
- **Key Findings:**
  - Popular data sources: Baseball-Reference, FanGraphs, Sean Lahman's database, Retrosheet
  - Retrosheet competition files used with feature selection
  - Key sabermetrics: OBP, OPS, ERA
  - Feature selection critical for model performance

### Machine Learning Outperforms Regression for Injury Prediction
- **URL:** https://journals.sagepub.com/doi/full/10.1177/2325967120963046
- **Key Findings:**
  - 13,982 player-years analyzed (2000-2017)
  - Input data: Age, performance data, injury history, DL data
  - Hitting sabermetrics: walks, strikeouts, HR, slugging, total bases, hits per base, RBI
  - Pitching sabermetrics: walks, strikeouts, innings pitched, pitches per type, intentional walks
  - Overall metrics: WAR, WPA, leverage index, clutch score
  - Machine learning outperformed regression for injury prediction

### Predicting Run Production and Run Prevention in Baseball (IJBHT)
- **URL:** https://ijbht.thebrpi.org/journals/Vol_2_No_4_June_2012/7.pdf
- **Authors:** Beneventano, Berger, Weinberg (Bentley University)
- **Key Findings:**
  - Stepwise multiple regression on 300 team-seasons (2001-2010)
  - **Runs Scored Model (R² = 95.3%):** Y = -903 + 2226(wOBA) - 184(K%) + 1116(SLG) + 1501(OBP)
  - **ERA Model (R² = 98.8%):** Y = -12.483 + 2.889(WHIP) - 9.564(LOB%) + 1.006(HR/9) - 19.022(FLD%) - 0.001(DP)
  - wOBA alone explains 89.6% of run scoring variance
  - WHIP alone explains 94.0% of ERA variance
  - Sabermetric variables enter first in stepwise but traditional variables also contribute significantly
  - UZR excluded from final model possibly due to park-adjustment inconsistencies and evolution over time

### Baseball Decision-Making: Optimizing At-bat Simulations (SMU)
- **URL:** https://scholar.smu.edu/datasciencereview/vol8/iss1/9
- **Authors:** Gopal, Kondakindi, Lohia, Williams (SMU)
- **Key Findings:**
  - Feedforward neural network (2 hidden layers, 128 neurons each) for pitch outcome prediction
  - Data: 700,000+ pitches per season from Statcast (2017-2019)
  - Features: pitch physics (release point, velocity, spin, movement), batter performance metrics, count
  - Target: 4-class classification (ball, foul, strike, into play)
  - **Accuracy: 58%** across all seasons; balls classified best (F1=0.81-0.82)
  - Markov Decision Process framework for at-bat simulation
  - Rewards based on RE288 (run expectancy by base-out-count state)
  - Terminal state rewards: batter's xWOBA for strikeout/foul, negative xWOBA for hit/walk

### Neural Sabermetrics with World Model (CMU)
- **URL:** https://arxiv.org/pdf/2602.07030.pdf
- **Authors:** Ahn, Du, Zhang, Kang (Carnegie Mellon)
- **Key Findings:**
  - LLM-based world model for baseball play-by-play prediction
  - Trained on 10+ years MLB data: 7M pitch sequences, ~3B tokens
  - Backbone: Llama-3.2 3B with continuous pretraining
  - **Pitch Type Prediction:** 63.7% accuracy, F1=0.722 (fastball vs non-fastball)
  - **Batter Swing Decision:** 76.6% in-zone accuracy, 79.2% out-of-zone accuracy
  - **Overall:** 84% of next pitches correct within PA, 78% of swing decisions correct
  - Evaluated on postseason data (out-of-distribution) showing robust generalization
  - Model bias toward predicting four-seam fastball (frequency-driven prior)
  - Performance degrades for pitchers with larger arsenals (5+ pitch types)

### Current State of Data and Analytics Research in Baseball (PMC)
- **URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9276858/
- **Key Findings:**
  - Systematic review of big data applications in baseball
  - Injury prediction models combining ML and traditional stats
  - ML vs logistic regression comparison studies
  - Emphasis on real-time tracking data integration

### Sabermetrics: The Past, the Present, and the Future (Jim Albert)
- **URL:** https://ww2.amstat.org/mam/2010/essays/AlbertSabermetrics.pdf
- **Key Findings:**
  - OPS explains 89% of variation in runs scored (vs 46% for batting average)
  - ERA has weak year-to-year correlation (only 9% of variance explained by prior year ERA)
  - Strikeout rate (SO/9) has strong year-to-year correlation (69% variance explained)
  - DICE (Defense-Independent Component ERA): DICE = 3.00 + (13×HR + 3(BB+HBP) - 2×SO) / IP
  - DICE better predictor of next year's ERA than current year's ERA
  - Fielding percentage ignores range; RF/9 (Range Factor per 9 innings) = 9 × (PO+A) / IP
  - PITCHf/x data enables measurement of pitcher fastball quality via batter "sweet spot"

### Two New Detailed Sabermetrics Books (Phil Birnbaum)
- **URL:** http://www.philbirnbaum.com/btn2006-02.pdf
- **Key Findings:**
  - Reviews of "Baseball Between the Numbers" and "The Book: Playing the Percentages"
  - Leverage index quantifies importance of game situations (8th inning tie = 2.54 leverage)
  - Optimal closer usage: before 9th, use if leverage > 2.32; in 9th, use if leverage > 1.66
  - Sacrifice bunt analysis: attempt more valuable than successful sac (reaching base possibility)
  - Players perform worse as pinch hitters (OBP drops .337 → .313)
  - No evidence batters "own" specific pitchers beyond general skill differentials
  - Pitchers: better 1st time through order, average 2nd, worse 3rd
  - Clutch hitting: slight evidence of very small skill (SD ≈ .008 OBP points)
  - Extra win worth $4.4M for playoff-contending teams vs $750K for non-contenders

---

## Key Sabermetrics and Metrics

### Hitting Metrics
- **OBP (On-Base Percentage):** (H + BB + HBP) / (AB + BB + HBP + SF)
- **SLG (Slugging Percentage):** (1B + 2×2B + 3×3B + 4×HR) / AB
- **OPS (On-Base Plus Slugging):** OBP + SLG
- **wOBA (Weighted On-Base Average):** Linear weights for each outcome, scaled to OBP
- **wRC+ (Weighted Runs Created Plus):** Park-adjusted wOBA, 100 = league average
- **BABIP (Batting Average on Balls In Play):** Hits on balls in play / balls in play
- **ISO (Isolated Power):** SLG - AVG

### Pitching Metrics
- **ERA (Earned Run Average):** Earned runs / innings pitched × 9
- **FIP (Fielding Independent Pitching):** (13×HR + 3×(BB+HBP) - 2×K) / IP + constant
- **xFIP (Expected FIP):** FIP with league-average HR rate
- **WHIP (Walks + Hits per Inning Pitched):** (BB + H) / IP
- **K/9 (Strikeouts per 9 Innings):** K / IP × 9
- **BB/9 (Walks per 9 Innings):** BB / IP × 9
- **DICE:** 3.00 + (13×HR + 3×(BB+HBP) - 2×SO) / IP
- **WAR (Wins Above Replacement):** Total player value
- **WPA (Win Probability Added):** Impact on win probability

### Fielding Metrics
- **UZR (Ultimate Zone Rating):** Estimated defensive contribution in runs above/below average
- **FRAA (Fielding Runs Above Average):** Adjusts for park, balls in play, GB/FB tendencies
- **DRS (Defensive Runs Saved):** Film/computer analysis of plays made vs league average
- **RF/9 (Range Factor per 9 innings):** 9 × (PO + A) / IP

### Advanced Metrics (Statcast)
- **Exit Velocity:** Speed of ball off bat
- **Launch Angle:** Vertical angle of batted ball
- **Barrel Rate:** Optimal exit velocity + launch angle combinations
- **Spin Rate:** RPM of pitch
- **Pitch Movement:** Horizontal/vertical break
- **Zone Contact:** Contact rate in strike zone
- **Chase Rate:** Swing rate outside strike zone
- **xWOBA:** Expected weighted on-base average based on exit velocity and launch angle
- **xBA:** Expected batting average
- **xSLG:** Expected slugging percentage

---

## Data Sources

### Primary Sources
- **Retrosheet:** Historical play-by-play data (1871-present)
- **MLB Stats API:** Official MLB data (live and historical)
- **Statcast:** Pitch-tracking and batted ball data (2015-present)
- **FanGraphs:** Advanced sabermetrics and splits
- **Baseball-Reference:** Historical statistics and biographical data
- **Sean Lahman Database:** Comprehensive historical database
- **ESPN:** Real-time scores and statistics

### Pitching Data Sources
- **PITCHf/x:** Pitch tracking system (2007-2015)
- **HITf/x:** Batted ball tracking (2015-2019)
- **Statcast:** Unified tracking system (2015-present)
- **Pitcher Info:** Pitcher characteristics and tendencies

---

## Modeling Approaches

### Game Outcome Prediction
- **Accuracy:** 59-60% with ML + sabermetrics
- **Features:** Team stats, player stats, context, historical performance
- **Models:** Gradient boosting, random forest, neural networks
- **Key:** Feature selection and context weighting

### Player Performance Prediction
- **Batter Performance:** Zone contact, hard-hit rate, swing decisions
- **Pitcher Performance:** Strikeout rate, walk rate, pitch sequencing
- **Injury Prediction:** Age, performance trends, injury history, workload
- **ML Outperforms:** Traditional regression for complex relationships

### Swing Probability
- **Context:** Pitcher-batter matchups, count, game situation
- **Features:** Pitch type, location, batter tendencies, pitcher patterns
- **Value:** Understanding decision-making in at-bats
- **Best Model:** LightGBM gradient boosting with 80.5% accuracy

### Pitch Outcome Prediction
- **Architecture:** Feedforward neural network (2×128 hidden layers)
- **Features:** Pitch physics, count, batter performance metrics
- **Target:** Ball / Foul / Strike / Into Play
- **Accuracy:** ~58% overall, balls classified best (F1 ~0.81)
- **Framework:** Markov Decision Process for at-bat simulation

### LLM World Models
- **Architecture:** Llama-3.2 3B continuously pretrained on baseball sequences
- **Data:** 7M pitch sequences, 3B tokens, 10+ years of MLB
- **Tasks:** Pitch type prediction (63.7%), swing decision (76.6% IZ, 79.2% OZ)
- **Advantage:** Unified model for multiple prediction tasks
- **Limitation:** Context window requires sliding windows, breaking long-range dependencies

---

## Advanced Research Findings

### Regression Analysis for Run Production
From Beneventano et al. (2012):
- wOBA is the single best predictor of runs scored (R² = 89.6%)
- Final runs-scored model achieves R² = 95.3% with wOBA, K%, SLG, OBP
- WHIP is the single best predictor of ERA (R² = 94.0%)
- Final ERA model achieves R² = 98.8% with WHIP, LOB%, HR/9, FLD%, DP
- Traditional statistics (batting average, HR, stolen bases) excluded from optimal offensive model

### Leverage and Reliever Usage
From Birnbaum (2006) and Woolner:
- Average maximum leverage per game: 1.66
- 8th inning tie game leverage: 2.54
- 9th inning up 3 runs leverage: 0.41
- Optimal strategy: save closer for leverage > 2.32 before 9th, > 1.66 in 9th
- Proper reliever usage can add ~1.6 wins per season

### Steroid Era Impact
From Tobin (2008) - Physics analysis:
- 10% muscle mass increase → ~5% bat speed increase → ~4% batted ball speed increase
- 4% batted ball speed increase → 50-100% increase in home run production
- HR per ball in play: pre-1980 elite ~10%, steroid era ~15%
- 50+ HR seasons: 17 times in first 70 years (1920-1989), 29 times in next 30 years (1990-2019)

### Plate Discipline Effects
From Vock & Vock (2018):
- Causal inference framework using G-computation algorithm
- Can estimate hypothetical performance under different plate discipline scenarios
- Plate discipline independent of inherent hitting ability

### Pitcher-Batter Matchups
From multiple sources:
- No evidence that batters "own" specific pitchers beyond general skill differentials
- Pitchers: better 1st time through order, average 2nd, worse 3rd
- Batting pitcher 8th instead of 9th adds "a couple" of runs per year

### Clutch Hitting
From Tango, Lichtman & Dolphin:
- Very slight evidence of very small clutch hitting skill
- Standard deviation of clutch OBP: ~0.008 points
- Not enough data to reliably identify best clutch hitters

---

## Best Practices

### Data Integration
1. **Source Preservation:** Never modify raw source data
2. **Bridge Tables:** Use for ID reconciliation between sources
3. **Feature Engineering:** Combine traditional sabermetrics with advanced metrics
4. **Context Weighting:** Weight performance by game importance and situation

### Modeling
1. **Interpretability:** Combine ML with interpretable sabermetrics
2. **Feature Selection:** Critical for performance, avoid overfitting
3. **Ensemble Methods:** Combine multiple models for robustness
4. **Validation:** Use hold-out sets and bootstrap for uncertainty
5. **Calibration:** Isotonic or Platt calibration for probability outputs

### Real-Time Applications
1. **Latency:** Sub-5 second latency for live betting
2. **Feature Updates:** Automated refresh of feature marts
3. **Monitoring:** Track model drift and performance degradation
4. **Fallback:** Have backup systems for data failures

---

## Missing Features in Current Pipeline

### Pitching-Specific Features
- Pitcher fatigue metrics (pitch counts, rest days)
- Pitch sequencing patterns
- Pitcher-batter matchup history
- Pitcher platoon splits
- Pitcher park factors
- Pitcher clutch performance

### Context Features
- Weather conditions (temperature, wind, humidity)
- Umpire strike zone tendencies
- Manager decision tendencies
- Lineup construction patterns
- Travel distance and fatigue
- Motivation factors (playoff race, elimination)

### Advanced Metrics
- Statcast pitch movement data
- Exit velocity and launch angle distributions
- Spin rate and movement profiles
- Zone contact and chase rates
- Barrel rates and hard-hit rates

---

## Steroid Era Research

### Key Papers and Findings

#### 1. "The Effect of the Steroid Era on Major League Baseball Hitters"
- **URL:** https://www.hilarispublisher.com/open-access/the-effect-of-the-steroid-era-on-major-league-baseball-hitters-2161-0673-1000161.pdf
- **Key Findings:**
  - Steroid era defined as 1993-2002
  - Average HR/season during steroid era: 4,782 +/- 767
  - Post-steroid era (2003-2012): 4,549 +/- 296
  - Pre-steroid era (1983-1992): 3,443 +/- 425
  - Players hitting 40+ HR significantly increased (p<0.002)
  - No significant change in overall batting average

#### 2. "The Possible Effect of Steroids on Home-Run Production" (Roger Tobin, Physics)
- **URL:** https://sabr.org/journal/article/the-possible-effect-of-steroids-on-home-run-production
- **URL:** https://baseball.physics.illinois.edu/Tobin_AJP_Jan08.pdf
- **Key Findings:**
  - HRBiP (home runs per balls in play) increased 50% in steroid era
  - Pre-steroid elite HR hitters: ~0.10 HRBiP
  - Steroid era hitters (Bonds, Sosa, McGwire): ~0.15 HRBiP
  - 10% muscle mass increase -> 50% increase in HRBiP
  - 4% increase in ball speed -> 50-100% increase in HR production

#### 3. "Did Performance-Enhancing Drugs Prolong Careers?" (SABR)
- **URL:** https://sabr.org/journal/article/stats-and-studies-did-performance-enhancing-drugs-prolong-careers/
- **Key Findings:**
  - 50 HR threshold: 17 times in first 70 years (1920-1989)
  - 50 HR threshold: 29 times in 30 years (1990-2019)
  - Barry Bonds production spike in late 30s due to PEDs
  - Performance declined in 40s similar to non-PED players

### Steroid Era Timeline
- **1988-1992:** Pre-steroid baseline
- **1993-2002:** Height of steroid era (no testing)
- **2003:** MLB begins testing (first survey testing)
- **2005:** HGH testing added
- **2006+:** Stricter penalties

### Implementation Recommendations
1. **Add era indicator:** Create `is_steroid_era` feature (1993-2002)
2. **Exclusion list:** Create table of known/suspected users to exclude or flag
3. **Adjust HR rates:** Consider 10-20% reduction for steroid-era HR predictions
4. **Separate models:** Train steroid-era data separately from modern data

### Known Suspected Players (Partial List)
- Barry Bonds, Mark McGwire, Sammy Sosa, Alex Rodriguez, Manny Ramirez
- See Mitchell Report (2007) for complete list

---

## Retrosheet Bibliography (Pavitt)

### Overview
- **Source:** Charlie Pavitt's Statistical Baseball Research Bibliography
- **URL:** https://www.retrosheet.org/resources/BBREF.xls
- **Size:** 4,153 entries as of October 2025 update
- **Format:** Excel spreadsheet with macrocode/microcode taxonomy

### Taxonomy Structure
The bibliography uses a two-level hierarchical code system:

**Macrocodes (General Subject Areas):**
- Base Running
- Batting Evaluation
- Batting Issues
- Batting Strategy
- Fielding Evaluation
- Fielding Strategy
- Game
- General
- Inning
- Injury
- Managing
- Overall Player Evaluation
- Pitching Evaluation
- Pitching Issues
- Pitching Strategy
- Situational
- Team Issues
- Team Performance
- Umpire

**Top Macrocode Categories by Count:**
| Category | Count |
|----------|-------|
| Wins Above Replacement | 88 |
| Run Differentials | 73 |
| Postseasons | 67 |
| Home Advantage | 67 |
| Starting Pitchers | 61 |
| Pitcher Workload | 59 |
| Hitting Streaks | 59 |
| Predictions, Batters | 58 |
| Competitive Balance | 57 |
| Predictors of Team Performance | 57 |
| Relief Pitchers | 51 |
| Player Development | 49 |
| Clutch Hitting | 48 |
| Managers, Evaluations | 47 |
| Statistical Analysis, Batting | 47 |

### Entry Format
Each entry contains:
- Column A: Last name of first author
- Column B: First name/middle initial of first author
- Column C: Macrocode (general subject area)
- Column D: Microcode (specific content area)
- Column E: Title (may be shortened)
- Column F: Journal/Publisher
- Column G: Volume/Issue
- Column H: Date of publication
- Column I: Pages
- Column J: Comments (coauthors, series citations)

### Key Journals Represented
- Baseball Analyst
- Baseball Research Journal
- By the Numbers
- Journal of Quantitative Analysis in Sports
- Journal of Sports Economics
- Journal of Sports Analytics
- Operations Research
- The American Statistician

### Notable Research Topics Covered
- Age/experience effects on performance
- Ballpark adjustments and park factors
- Clutch performance existence and measurement
- Draft position and future performance
- Home field advantage
- Lineup optimization
- Pythagorean theorem derivations
- Run expectancy tables
- Sacrifice bunt strategy
- Stolen base strategy
- Win probability models

---

## Next Research Areas

1. **Pitching Data Integration:** How to best integrate Statcast pitch-level data
2. **Feature Engineering:** Which advanced metrics provide most predictive value
3. **Model Architecture:** Ensemble approaches for multi-target prediction
4. **Real-Time Latency:** Optimizing for sub-5 second prediction latency
5. **Market Integration:** How to integrate with betting markets (Polymarket)
6. **LLM World Models:** Explore LLM-based approaches for unified baseball prediction
7. **RE288 Integration:** Incorporate count-specific run expectancy into feature engineering
8. **Causal Inference:** Apply G-computation and propensity score methods for strategy evaluation

---

## Source Documents

### Downloaded and Extracted
| Document | Pages | Size | Status |
|----------|-------|------|--------|
| Albert - Sabermetrics Past Present Future | 12 | 120KB | Extracted |
| Pavitt - Bibliography Explanation | 7 | 354KB | Extracted |
| Tobin - Steroids Physics | 20 | 560KB | Extracted |
| Beneventano - Run Production Regression | 9 | 215KB | Extracted |
| Neural Sabermetrics with World Model | 8 | 1.8MB | Extracted |
| Birnbaum - Book Review | 30 | 614KB | Extracted |
| Gopal - Baseball Decision-Making MDP | 20 | 591KB | Extracted |
| Pavitt - BBREF Bibliography | 4,153 entries | 1.6MB | Loaded |

### Web Resources Fetched
| Resource | Lines | Status |
|----------|-------|--------|
| Swing Probability (Towards Data Science) | 113 | Extracted |
| Retrosheet Fall 2025 Updates | 98 | Extracted |
| Retrosheet DB Tutorial | 22 | Extracted |
| CareerKarma Sabermetrics | 471 | Extracted |
| Syracuse Grad Program | 113 | Extracted |

---

## Related Documentation
- [docs/KNOWLEDGE_BASE_MODELS_REPOS.md](docs/KNOWLEDGE_BASE_MODELS_REPOS.md) — Models and repositories
- [docs/KNOWLEDGE_BASE_FRAMEWORK.md](docs/KNOWLEDGE_BASE_FRAMEWORK.md) — Prediction framework
- [docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md](docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md) — Markov chain research
- [docs/KNOWLEDGE_BASE_GIS_PITCH.md](docs/KNOWLEDGE_BASE_GIS_PITCH.md) — Pitch-level GIS data
- [docs/agents/MODELING_WORKFLOWS.md](docs/agents/MODELING_WORKFLOWS.md) — Current workflows
- [docs/SABERMETRICS_LINK_INVENTORY.md](docs/SABERMETRICS_LINK_INVENTORY.md) — Full link inventory

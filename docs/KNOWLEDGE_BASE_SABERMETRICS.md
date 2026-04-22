# Sabermetrics and Baseball Modeling Knowledge Base

**Date:** 2026-04-22
**Purpose:** Research findings on sabermetrics, baseball modeling, and prediction approaches

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
  - Batter uses knowledge of pitcher to predict pitch type (fastball vs breaking ball)
  - Pitcher uses information about batter to formulate pitch sequences
  - Mind games and prediction are central to sabermetrics
  - Statistical analysis of these interactions is valuable

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

## Key Sabermetrics and Metrics

### Hitting Metrics
- **OBP (On-Base Percentage):** Times reached base / plate appearances
- **OPS (On-Base Plus Slugging):** OBP + SLG
- **SLG (Slugging Percentage):** Total bases / at-bats
- **wOBA (Weighted On-Base Average):** Linear weights for each outcome
- **wRC+ (Weighted Runs Created Plus):** Park-adjusted wOBA
- **BABIP (Batting Average on Balls in Play):** Hits on balls in play / balls in play
- **ISO (Isolated Power):** SLG - AVG

### Pitching Metrics
- **ERA (Earned Run Average):** Earned runs / innings pitched * 9
- **FIP (Fielding Independent Pitching):** HR, BB, HBP, K normalized to innings
- **xFIP (Expected FIP):** FIP with league-average HR rate
- **WHIP (Walks + Hits per Inning Pitched):** (BB + H) / IP
- **K/9 (Strikeouts per 9 Innings):** K / IP * 9
- **BB/9 (Walks per 9 Innings):** BB / IP * 9
- **WAR (Wins Above Replacement):** Total player value
- **WPA (Win Probability Added):** Impact on win probability

### Advanced Metrics (Statcast)
- **Exit Velocity:** Speed of ball off bat
- **Launch Angle:** Vertical angle of batted ball
- **Barrel Rate:** Optimal exit velocity + launch angle combinations
- **Spin Rate:** RPM of pitch
- **Pitch Movement:** Horizontal/vertical break
- **Zone Contact:** Contact rate in strike zone
- **Chase Rate:** Swing rate outside strike zone

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

### Real-Time Applications
1. **Latency:** Sub-5 second latency for live betting
2. **Feature Updates:** Automated refresh of feature marts
3. **Monitoring:** Track model drift and performance degradation
4. **Fallback:** Have backup systems for data failures

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

## Next Research Areas

1. **Pitching Data Integration:** How to best integrate Statcast pitch-level data
2. **Feature Engineering:** Which advanced metrics provide most predictive value
3. **Model Architecture:** Ensemble approaches for multi-target prediction
4. **Real-Time Latency:** Optimizing for sub-5 second prediction latency
5. **Market Integration:** How to integrate with betting markets (Polymarket)

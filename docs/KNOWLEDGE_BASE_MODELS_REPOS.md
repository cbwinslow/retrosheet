# Baseball Models and Repositories Knowledge Base

**Date:** 2026-04-22
**Purpose:** Research-backed recommendations for useful baseball models and GitHub repositories

## Research Findings

### GitHub Topics: Sabermetrics
**Source:** https://github.com/topics/sabermetrics
- **Key Repositories:**
  - MLBDailyProjections: Machine learning for daily MLB player projections
  - baseball-analytics: Predicting MLB player salaries and team wins
  - baseball: Sabermetric analysis and machine learning
  - Baseball-Analytics: Machine learning models for baseball predictions
  - Predicting-Baseball-Statistics: Classification and regression using scikit-learn and TensorFlow

### Recommended Repositories

**1. MLBDailyProjections (brendanahart/MLBDailyProjections)**
- **URL:** https://github.com/brendanahart/MLBDailyProjections
- **Purpose:** Daily projections for MLB players
- **Techniques:** Machine Learning, Regression Analysis, Sabermetrics
- **Use Case for Our Pipeline:** Daily player performance projections, comparison with our models
- **Research Backing:** Active repository, uses similar techniques (ML + sabermetrics)

**2. baseball-analytics (eric8395/baseball-analytics)**
- **URL:** https://github.com/eric8395/baseball-analytics
- **Purpose:** Predict MLB player salaries and team wins
- **Techniques:** Machine learning regression models
- **Use Case for Our Pipeline:** Salary prediction models (we need this), team win prediction
- **Research Backing:** Regression models are well-established for these tasks

**3. baseball (jcusick13/baseball)**
- **URL:** https://github.com/jcusick13/baseball
- **Purpose:** Sabermetric analysis and machine learning
- **Use Case for Our Pipeline:** Feature engineering ideas, sabermetric calculations
- **Research Backing:** Comprehensive sabermetric analysis

**4. Baseball-Analytics (rh2835/Baseball-Analytics)**
- **URL:** https://github.com/rh2835/Baseball-Analytics
- **Purpose:** Machine learning models for baseball predictions
- **Use Case for Our Pipeline:** Prediction model architectures, feature selection
- **Research Backing:** Multiple ML approaches tested

**5. Predicting-Baseball-Statistics (tweichle/Predicting-Baseball-Statistics)**
- **URL:** https://github.com/tweichle/Predicting-Baseball-Statistics
- **Purpose:** Classification and regression for baseball statistics
- **Techniques:** scikit-learn, TensorFlow-Keras
- **Use Case for Our Pipeline:** Home run prediction, extra-base hit prediction
- **Research Backing:** Deep learning approaches for baseball

## Existing Project Models

### Current Model Infrastructure
- **Location:** `scripts/train_pa_outcome_distribution.py`
- **Model:** HistGradientBoosting (multiclass)
- **Target:** PA outcome distribution
- **Features:** Advanced count features
- **Validation:** Bootstrap evaluation, calibration

### Model Registry
- **Location:** `models` schema
- **Tracking:** Model versioning, artifact storage
- **Status:** Implemented but could be expanded

## Recommended Model Additions

### 1. Salary Prediction Model
- **Purpose:** Predict player salaries based on performance
- **Features:** WAR, age, position, team, recent performance
- **Algorithm:** Ridge Regression (from baseball-analytics repo)
- **Use Case:** Salary data integration, contract value prediction
- **Research Backing:** Regression models well-established for salary prediction

### 2. Team Win Prediction Model
- **Purpose:** Predict team wins for season
- **Features:** Team stats, player WAR, payroll, schedule strength
- **Algorithm:** Gradient Boosting or Random Forest
- **Use Case:** Season-long predictions, team strength assessment
- **Research Backing:** Multiple repositories use this approach

### 3. Injury Prediction Model
- **Purpose:** Predict player injury risk
- **Features:** Age, workload, position, injury history, performance decline
- **Algorithm:** Random Forest or Gradient Boosting
- **Use Case:** Injury data integration, roster management
- **Research Backing:** MDPI research shows ML outperforms regression for injury prediction

### 4. Pitch Sequencing Model
- **Purpose:** Predict next pitch type
- **Features:** Pitcher tendencies, batter tendencies, count, game situation
- **Algorithm:** LSTM or Transformer
- **Use Case:** Pitch sequence analysis, batter-pitcher matchup
- **Research Backing:** Deep learning approaches for sequence prediction

### 5. Game Outcome Model
- **Purpose:** Predict game winner
- **Features:** Team stats, starting pitchers, home field, weather, umpire
- **Algorithm:** Ensemble (Gradient Boosting + Logistic Regression)
- **Use Case:** Live betting, game outcome prediction
- **Research Backing:** 59-60% accuracy achievable with ML + sabermetrics

## Data Sources for Models

### Existing Data Sources
- **Retrosheet:** Historical play-by-play (1871-present)
- **MLB Stats API:** Live and historical data
- **Statcast:** Pitch-level tracking (2015-present)
- **ESPN:** Real-time scores and stats

### Additional Data Sources Needed
- **Salary Data:** MLB salary database, Spotrac
- **Injury Data:** MLB injury reports, Rotowire
- **Weather Data:** OpenWeatherMap
- **Umpire Data:** MLB umpire database

## Integration Strategy

### Phase 1: Clone and Study Repositories
1. Clone MLBDailyProjections
2. Clone baseball-analytics
3. Clone Predicting-Baseball-Statistics
4. Study model architectures and feature engineering
5. Adapt useful techniques to our pipeline

### Phase 2: Implement Salary Model
1. Integrate salary data source
2. Implement Ridge Regression for salary prediction
3. Validate against actual salaries
4. Add to model registry

### Phase 3: Implement Team Win Model
1. Aggregate team-level features
2. Implement Gradient Boosting for win prediction
3. Validate against actual wins
4. Add to model registry

### Phase 4: Implement Injury Model
1. Integrate injury data source
2. Implement Random Forest for injury prediction
3. Validate against actual injuries
4. Add to model registry

### Phase 5: Implement Game Outcome Model
1. Aggregate game-level features
2. Implement Ensemble model for game prediction
3. Validate against actual outcomes
4. Add to model registry

## Validation Strategy

### Model Validation
- **Cross-validation:** Season-stratified k-fold
- **Bootstrap:** Season-stratified game-cluster resampling
- **Hold-out:** Most recent season for final validation
- **Calibration:** Isotonic calibration for probability outputs
- **Uncertainty:** Bootstrap confidence intervals

### Feature Validation
- **Feature importance:** SHAP values, permutation importance
- **Feature selection:** Recursive feature elimination
- **Feature stability:** Feature importance across seasons
- **Feature correlation:** Remove highly correlated features

## Risk Assessment

### Repository Integration Risks
- **Risk:** Code quality varies across repositories
- **Mitigation:** Review code thoroughly, adapt to our standards
- **Validation:** Test in development environment first

### Model Performance Risks
- **Risk:** Models may not generalize to our data
- **Mitigation:** Validate on our data, use ensemble approaches
- **Validation:** Cross-validation, bootstrap evaluation

### Data Integration Risks
- **Risk:** External data sources may have quality issues
- **Mitigation:** Data validation, confidence scoring
- **Validation:** Monitor data quality over time

## Next Steps

1. **Clone repositories** (this week)
2. **Study model architectures** (this week)
3. **Implement salary model** (next week)
4. **Implement team win model** (next week)
5. **Implement injury model** (following week)
6. **Implement game outcome model** (following week)

## Conclusion

Multiple high-quality GitHub repositories exist for baseball analytics and machine learning. Key recommendations:
- MLBDailyProjections for daily player projections
- baseball-analytics for salary and team win prediction
- Predicting-Baseball-Statistics for deep learning approaches

All recommendations are research-backed and should be validated before production deployment.

## 🎯 Objective
Build comprehensive player context features including rolling averages, zone discipline, and matchup history to enhance pitch-level model predictions with temporal and opponent-specific context.

## 📋 Task Breakdown
- [ ] Design player context feature schema
- [ ] Implement rolling average calculations (last 30 days, season-to-date)
- [ ] Create zone discipline metrics (hot/cold zones, chase rates)
- [ ] Build matchup history features (batter vs pitcher performance)
- [ ] Develop sequence context features (previous pitch patterns)
- [ ] Create game situation context (leverage, inning, score)
- [ ] Implement feature caching and materialized views
- [ ] Validate feature quality and predictive power
- [ ] Document feature engineering methodology

## 🔧 Technical Requirements
- Target table: features_pitch.player_context
- Rolling windows: 7-day, 30-day, season-to-date
- Zone analysis: 9-zone grid with hot/cold identification
- Matchup history: Batter vs pitcher historical performance
- Sequence patterns: Previous 3-5 pitches context
- Performance metrics: OPS, wOBA, swing rates, contact rates
- Update frequency: Daily incremental updates

## 🎯 Success Criteria
- Player context table populated with all active players
- Rolling averages calculated for key performance metrics
- Zone discipline metrics identified for each player
- Matchup history features computed for all pairings
- Feature quality score > 90%
- Query performance < 100ms for context lookups
- Materialized views optimized for real-time access

## 🔗 Dependencies
- Base features table populated (✓ issue #172)
- Engineered features completed (⏳ issue #173)
- Database performance optimization needed
- Materialized view architecture ready

## 📅 Timeline
Target completion: Within 5 days

## 🚀 Implementation Strategy
1. Design player context schema with proper indexing
2. Implement rolling average calculations with window functions
3. Create zone discipline analysis algorithms
4. Build matchup history aggregation logic
5. Develop sequence context feature extraction
6. Optimize query performance with materialized views
7. Validate feature quality and predictive power
8. Document feature engineering methodology

## 📊 Feature Categories

### Rolling Averages
- **Batting**: AVG, OBP, SLG, wOBA (last 30 days)
- **Pitching**: ERA, WHIP, K/BB, FIP (last 30 days)
- **Plate Discipline**: Swing rate, contact rate, chase rate
- **Batted Ball**: Hard hit rate, GB/FB ratio, pull rate

### Zone Discipline
- **Hot Zones**: Areas where player performs >20% above average
- **Cold Zones**: Areas where player performs >20% below average
- **Chase Tendency**: Propensity to swing outside zone
- **Contact Ability**: Success rate in different zone regions

### Matchup History
- **Batter vs Pitcher**: Historical performance metrics
- **Handedness Splits**: Performance vs RHP/LHP
- **Recent Performance**: Last 10 at-bats trends
- **Situational Performance**: Clutch vs non-clutch situations

### Sequence Context
- **Previous Pitch**: Type, location, outcome
- **Pattern Recognition**: Tendency analysis
- **Count Adjustment**: Performance in different counts
- **Fatigue Factors**: Pitch count and game situation impact

## 🔍 Technical Implementation

### Window Functions
```sql
-- 30-day rolling average example
SELECT 
    batter_id,
    game_date,
    AVG(woba) OVER (
        PARTITION BY batter_id 
        ORDER BY game_date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as woba_30day
FROM game_events
```

### Zone Analysis
```sql
-- Hot zone identification
SELECT 
    batter_id,
    zone_x,
    zone_y,
    AVG(woba_contribution) as zone_performance,
    COUNT(*) as sample_size
FROM pitch_results
GROUP BY batter_id, zone_x, zone_y
HAVING COUNT(*) >= 10
```

## 📈 Performance Requirements
- Query response time: < 100ms
- Update frequency: Daily incremental
- Storage optimization: Compress historical data
- Caching strategy: Redis for hot player data
- Materialized views: For complex aggregations

## 🔗 Related Issues
- #172: Complete Base Features Population (upstream)
- #173: Complete Engineered Features (upstream)
- #175: Train Two-Tier XGBoost Model (uses these features)
- #176: Install ML Dependencies (for model training)

## 🎯 Integration Points
- Feature engineering pipeline integration
- Real-time prediction serving
- Model training data preparation
- Performance monitoring and analytics

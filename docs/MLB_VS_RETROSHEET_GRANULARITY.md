# MLB vs Retrosheet Data Granularity Comparison

## Executive Summary

**MLB API provides MORE detailed pitch-by-pitch data than Retrosheet**, but with different structure and focus. MLB offers physics-based pitch tracking while Retrosheet offers symbolic pitch classification. The data can be harmonized but requires different modeling approaches.

## Detailed Comparison

### 📊 **Pitch-Level Granularity**

#### **Retrosheet Pitch Sequences**
```
Example: "CBBX" (Called strike, Ball, Ball, Ball in play)
Symbols: C=Called strike, B=Ball, X=Ball in play
Granularity: Pitch result classification only
Coverage: ~85% of plate appearances have pitch sequences
```

#### **MLB API Pitch Data**
```
Example: Individual pitch with full physics
- Type: "FF" (Four-Seam Fastball) with confidence score
- Coordinates: x=54.37, y=171.75 (plate location)
- Physics: spinRate=2246, startSpeed=89.8, endSpeed=82.0
- Movement: pfxX=-1.89, pfxZ=-7.67 (horizontal/vertical break)
- Result: "F" (Foul) with zone=11
Granularity: Full pitch trajectory + physics + result
Coverage: 100% of pitches (when Statcast available)
```

### 🎯 **Data Structure Differences**

#### **Retrosheet Approach**
- **Symbolic**: C, B, S, F, X, etc.
- **Discrete**: Each pitch is a single character
- **Outcome-focused**: Classifies pitch result
- **Human-readable**: Strings like "CBBSFX"
- **Historical**: Available since 1988

#### **MLB API Approach**
- **Physical**: Coordinates, velocities, spin rates
- **Continuous**: Numeric measurements
- **Process-focused**: Describes pitch characteristics
- **Machine-readable**: JSON with nested objects
- **Modern**: Available since 2015 (expanded over time)

### 📈 **Detail Level Comparison**

| Data Type | Retrosheet | MLB API | Winner |
|-----------|------------|---------|--------|
| **Pitch Type** | Basic (FB, CB, CH, etc.) | Precise (FF, FT, FC, SL, etc.) | MLB |
| **Pitch Location** | Strike zone grid (1-9) | Exact coordinates (x,y) | MLB |
| **Pitch Speed** | Start speed only | Start + end speed + extension | MLB |
| **Pitch Movement** | Qualitative | Quantitative (pfxX, pfxZ, spin) | MLB |
| **Ball Trajectory** | Batted ball type + location | Launch angle, exit velocity, hit distance | MLB |
| **Pitch Sequence** | Complete symbolic sequence | Individual pitch events | Similar |
| **Temporal Data** | Event timing | Pitch timestamps, reaction time | MLB |
| **Player Tracking** | Basic position data | Full body/position tracking | MLB |

### 🔄 **Harmonization Strategies**

#### **Option 1: MLB → Retrosheet Format**
Convert MLB physics data to symbolic classifications:
```
MLB: type="FF", coordinates.x=54.37, result="F"
→ Retrosheet: "F" (Foul on Four-Seam Fastball)
```

#### **Option 2: Unified Feature Engineering**
Create new features that leverage both data sources:
```
- Physics-based features from MLB
- Symbolic patterns from Retrosheet
- Temporal features from MLB timestamps
- Trajectory features from MLB Statcast
```

#### **Option 3: Hybrid Models**
```
- Use MLB data for pitch prediction (physics-based)
- Use Retrosheet data for outcome prediction (historical patterns)
- Combine predictions for final outcome
```

### 🎯 **Impact on Analysis/Models**

#### **Enhanced Capabilities with MLB Data**
1. **Pitch Quality Analysis**: Spin rate, movement, velocity changes
2. **Pitch Location Precision**: Exact plate coordinates vs strike zone grid
3. **Pitch Arsenal Classification**: Precise pitch type identification
4. **Real-time Decision Making**: Live pitch characteristics
5. **Advanced Metrics**: Exit velocity, launch angle, sprint speed

#### **Retrosheet Advantages**
1. **Historical Depth**: 40+ years of data
2. **Symbolic Patterns**: Human-interpretable pitch sequences
3. **Complete Coverage**: All games since 1988
4. **Established Models**: Existing PA outcome models

#### **Model Modification Requirements**

**For Live MLB Integration:**
```python
# New features available
features.update({
    'pitch_spin_rate': pitch_data.get('breaks', {}).get('spinRate'),
    'pitch_pfx_x': pitch_data.get('coordinates', {}).get('pfxX'),
    'pitch_pfx_z': pitch_data.get('coordinates', {}).get('pfxZ'),
    'pitch_plate_x': pitch_data.get('coordinates', {}).get('x'),
    'pitch_plate_z': pitch_data.get('coordinates', {}).get('z'),
    'pitch_type_confidence': pitch_data.get('typeConfidence'),
    # ... etc
})
```

**For Unified Modeling:**
```python
# Feature engineering that works with both sources
if data_source == 'mlb_live':
    # Use physics-based features
    features['pitch_movement'] = calculate_pitch_movement(mlb_pitch_data)
    features['pitch_location'] = calculate_pitch_location(mlb_pitch_data)
elif data_source == 'retrosheet':
    # Use symbolic features
    features['pitch_sequence'] = parse_pitch_sequence(retrosheet_sequence)
    features['pitch_pattern'] = analyze_pitch_pattern(retrosheet_sequence)
```

### 📊 **Data Coverage Analysis**

#### **Retrosheet Pitch Sequence Coverage**
```sql
-- Check Retrosheet pitch data coverage
SELECT
    season,
    COUNT(*) as total_pas,
    COUNT(*) FILTER (WHERE pitch_seq_tx IS NOT NULL AND pitch_seq_tx != '') as pas_with_pitch_data,
    ROUND(
        COUNT(*) FILTER (WHERE pitch_seq_tx IS NOT NULL AND pitch_seq_tx != '')::numeric /
        COUNT(*)::numeric * 100, 1
    ) as coverage_pct
FROM core.plate_appearances
WHERE season >= 2000
GROUP BY season
ORDER BY season;
```

#### **MLB Statcast Coverage**
- **2015-2016**: Limited ballparks
- **2017**: All MLB games
- **2018+**: Enhanced tracking (sprint speed, arm strength, etc.)
- **Coverage**: Nearly 100% for pitch and batted ball data

### 🎯 **Recommendation**

**Use MLB data as PRIMARY source for live analysis** due to superior granularity, then supplement with Retrosheet patterns for historical context.

**Implementation Strategy:**
1. **Build MLB-native features** leveraging physics and coordinate data
2. **Create Retrosheet compatibility layer** for existing models
3. **Develop hybrid features** that combine both data sources
4. **Maintain backward compatibility** with existing Retrosheet-trained models

**Result**: More accurate, real-time predictions with richer feature sets while maintaining compatibility with historical analysis.

---

## Conclusion

**MLB API provides SIGNIFICANTLY more detailed pitch-by-pitch data** than Retrosheet, offering physics-based measurements vs. symbolic classifications. The data can be harmonized but will require model modifications to fully leverage the enhanced granularity. MLB data enables more sophisticated analysis but Retrosheet provides crucial historical context.
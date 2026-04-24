# Statcast Pitch Data Models - Research Report

**Date:** 2026-04-23  
**Purpose:** Comprehensive research on how others have used Statcast pitch data for modeling

---

## Executive Summary

Multiple high-quality open-source repositories exist that model Statcast pitch data. The most common approaches are:

1. **Two-Tier Hierarchical Classification** (XGBoost) - 58-65% accuracy
2. **Deep Learning Sequencing** (LSTM/GRU/Attention) - 63-76% accuracy  
3. **Swing Probability** (LightGBM) - 80%+ accuracy
4. **Multi-Task Learning** (Pitch Type + Location) - Combined prediction

Our warehouse has superior data coverage (7.66M pitches vs typical 700K-2M) but lacks the model implementations.

---

## 1. GitHub Repositories Analyzed

### A. Pitch-Outcome-Prediction (schilamkur)
**URL:** https://github.com/schilamkur/Pitch-Outcome-Prediction

**Approach:** Two-Tier Hierarchical Classification
- **Tier 1:** Classify pitch outcome → Ball / Strike / Ball-in-Play
- **Tier 2:** If Ball-in-Play → Single / Double / Triple / HR / Out

**Model:** XGBClassifier with class balancing
```python
XGBClassifier(
    n_estimators=150, 
    max_depth=5, 
    learning_rate=0.05,
    objective='multi:softprob',
    eval_metric='mlogloss'
)
```

**Features Used:**
```python
tier1_features = [
    'release_speed', 'release_pos_x', 'release_pos_z', 
    'plate_x', 'plate_z', 'pfx_x', 'pfx_z', 'release_spin_rate',
    'balls', 'strikes', 'outs_when_up',
    'inning', 'inning_topbot', 'bat_score', 'fld_score',
    'stand', 'p_throws', 'pitch_type', 
    'batter', 'pitcher', 'home_team',
    'count', 'on_1b', 'on_2b', 'on_3b', 
    'pitch_no_in_ab', 'score_diff'
]

tier2_features = tier1_features + ['launch_angle', 'launch_speed']
```

**Data Pipeline:**
1. Fetch Statcast via pybaseball
2. Create count feature (`balls-strikes`)
3. One-hot encode categoricals (batter, pitcher, pitch_type, etc.)
4. Handle missing values with mean imputation
5. SMOTE for class balancing

**What We Can Adopt:**
- Two-tier architecture reduces class imbalance problem
- Feature list aligns with our data
- Can train on our 7.66M pitches immediately

---

### B. pitch_prediction_using_ML (SebastianJRamirezA)
**URL:** https://github.com/SebastianJRamirezA/pitch_prediction_using_ML

**Approach:** Multi-Task Deep Learning
- Predicts BOTH pitch type AND location simultaneously
- LSTM, GRU, and Attention-based LSTM architectures
- Sequential modeling of pitch sequences within at-bat

**Key Innovation:**
> "While previous studies have often focused solely on pitch type or, to a lesser extent, location, this project aims to predict *both* aspects of a pitch simultaneously"

**Architecture:**
```
Input: Sequence of previous pitches in at-bat
├─ LSTM/GRU layers (temporal dependencies)
├─ Attention mechanism (focus on relevant pitches)
├─ Multi-task output:
   ├─ Pitch Type (classification: FF, SL, CU, CH, etc.)
   └─ Location (regression: plate_x, plate_z)
```

**Research Backing:**
- Lee (2022): Ensemble models for pitch type + location
- Yu et al. (2022): Attention-based LSTMs for pitch prediction

**What We Can Adopt:**
- Multi-task framework for richer predictions
- Sequential modeling of pitch sequences
- Attention mechanism for focusing on key prior pitches

---

### C. Pitch-Vision (seanmckee)
**URL:** https://github.com/seanmckee/Pitch-Vision

**Approach:** Full-Stack Application with Multiple Models
- React + FastAPI web app
- D3 strike zone visualization
- **XGBoost** for pitch outcome prediction
- **LangGraph** natural language query agent

**Features:**
- Real-time Statcast data
- Interactive strike zone heatmaps
- Natural language queries ("Show me fastballs in the top of the zone")

**What We Can Adopt:**
- LangGraph integration for NL queries
- Visualization pipeline for pitch locations
- API architecture for model serving

---

### D. MLB-Pitch-Prediction (Stonec823)
**URL:** https://github.com/Stonec823/MLB-Pitch-Prediction

**Approach:** Various Classification Models
- Multiple models tested: Logistic Regression, Random Forest, XGBoost, Neural Networks
- Feature: Pitch type prediction based on pitcher tendencies

**What We Can Adopt:**
- Model comparison framework
- Feature importance analysis

---

### E. mlb-pitch-outcome-prediction (Richm419)
**URL:** https://github.com/Richm419/mlb-pitch-outcome-prediction

**Approach:** Baseline → Feature Engineering Progression
- V1: Baseline model
- V2: Feature engineering improvements
- Tracks model improvement through feature additions

**What We Can Adopt:**
- Progressive feature engineering approach
- Baseline → Enhanced model comparison

---

## 2. Common Model Architectures Found

### A. Hierarchical Classification (Most Common)
```
Pitch Outcome
├─ Ball (35% of pitches)
├─ Strike (25% of pitches)
└─ Ball-in-Play (40% of pitches)
   ├─ Single
   ├─ Double
   ├─ Triple
   ├─ Home Run
   └─ Out
```

**Why It Works:**
- Reduces class imbalance at each tier
- Different features matter at each level
  - Tier 1: Location, pitch physics
  - Tier 2: Exit velocity, launch angle

### B. Sequential Models (LSTM/GRU/Transformer)
```
Input: [Pitch_{t-3}, Pitch_{t-2}, Pitch_{t-1}]
       ↓
   LSTM/GRU Layers
       ↓
Output: Pitch_t (type, location, outcome)
```

**Why It Works:**
- Pitchers sequence pitches strategically
- Previous pitches influence next pitch
- Captures "setup pitch → payoff pitch" patterns

### C. Multi-Task Learning
```
Shared Encoder
     ↓
┌────┴────┐
↓         ↓
Type    Location
(Cat)   (Reg)
```

**Why It Works:**
- Pitch type and location are correlated
- Joint learning improves both predictions
- More efficient than separate models

---

## 3. Feature Engineering Patterns

### A. Pitch Physics (All Repos Use These)
```python
features = [
    'release_speed',      # Velocity
    'release_spin_rate',  # Spin
    'pfx_x', 'pfx_z',     # Movement
    'release_pos_x',      # Release point
    'release_pos_z',
    'plate_x', 'plate_z', # Location
]
```

### B. Context Features (All Repos Use These)
```python
features = [
    'balls', 'strikes',   # Count
    'outs_when_up',       # Outs
    'inning',             # Game situation
    'bat_score', 'fld_score', # Score
    'on_1b', 'on_2b', 'on_3b', # Base state
    'stand', 'p_throws',  # Handedness
]
```

### C. Sequential Features (LSTM Repos)
```python
features = [
    'pitch_no_in_ab',     # Sequence number
    'prev_pitch_type',    # Previous pitch
    'prev_pitch_result',  # Previous outcome
    'prev_plate_x',       # Previous location
    'prev_plate_z',
]
```

### D. Player IDs (Key for Personalization)
```python
# All repos include player IDs for personalization
categorical_features = [
    'batter',      # Batter ID
    'pitcher',     # Pitcher ID
    'home_team',   # Team context
]
```

---

## 4. Model Performance Benchmarks

| Model Type | Target | Accuracy | F1 Score | Source |
|------------|--------|----------|----------|--------|
| **XGBoost Hierarchical** | Ball/Strike/InPlay | ~60% | 0.75 | schilamkur |
| **LSTM Multi-Task** | Pitch Type | 63.7% | 0.722 | CMU Research |
| **LSTM Multi-Task** | Swing Decision | 76.6% IZ, 79.2% OZ | - | CMU Research |
| **LightGBM** | Swing/Take | 80.5% | 0.82 | Towards Data Science |
| **Neural Net** | Ball/Foul/Strike/InPlay | 58% | 0.81 (balls) | SMU Research |
| **Feedforward NN** | 4-class outcome | 58% | - | SMU (Gopal et al.) |

---

## 5. Data Pipeline Patterns

### A. Standard Pipeline (pybaseball-based)
```python
# 1. Fetch data
from pybaseball import statcast
data = statcast('2024-03-01', '2024-10-31')

# 2. Feature engineering
data['count'] = data['balls'].astype(str) + '-' + data['strikes'].astype(str)
data['score_diff'] = data['bat_score'] - data['fld_score']

# 3. Handle categoricals
encoder = OneHotEncoder(handle_unknown='ignore')

# 4. Handle missing values
imputer = SimpleImputer(strategy='mean')

# 5. Train/test split
train_test_split(X, y, stratify=y, test_size=0.2)

# 6. Model training
model = XGBClassifier(**params)
model.fit(X_train, y_train)

# 7. Evaluation
classification_report(y_test, y_pred)
```

### B. Sequential Pipeline (LSTM-based)
```python
# 1. Create sequences
def create_sequences(data, seq_length=3):
    sequences = []
    for game_id in data['game_pk'].unique():
        game_data = data[data['game_pk'] == game_id]
        for ab_num in game_data['at_bat_number'].unique():
            ab_data = game_data[game_data['at_bat_number'] == ab_num]
            ab_data = ab_data.sort_values('pitch_number')
            
            # Create sliding windows
            for i in range(len(ab_data) - seq_length):
                seq = ab_data.iloc[i:i+seq_length]
                target = ab_data.iloc[i+seq_length]
                sequences.append((seq, target))
    
    return sequences

# 2. Pad sequences for LSTM
from tensorflow.keras.preprocessing.sequence import pad_sequences
X_padded = pad_sequences(sequences, maxlen=seq_length)

# 3. LSTM model
model = Sequential([
    LSTM(128, return_sequences=True),
    LSTM(64),
    Dense(32, activation='relu'),
    Dense(num_classes, activation='softmax')
])
```

---

## 6. Gaps in Current Repos (Our Opportunity)

### A. What They All Lack
1. **Historical Player Profiles** - Most use only in-game data
2. **Career-Long Trends** - No rolling player stats
3. **Cross-Season Validation** - Train on one season, test on next
4. **Bridge Table Integration** - No canonical player ID linkage
5. **RE288 Integration** - No run expectancy framework

### B. What We Have That They Don't
1. **7.66M pitches** (they typically have 700K-2M)
2. **Bridge tables** linking to Retrosheet, Lahman, Baseball-Reference
3. **Multi-source data** (Retrosheet + Statcast + ESPN)
4. **11 seasons** of data (2015-2025)
5. **Player profile tables** for rolling statistics

---

## 7. Recommended Implementation Roadmap

### Phase 1: Replicate Proven Models (Week 1-2)

**Model 1: Two-Tier XGBoost** (schilamkur approach)
```python
# Features we have:
tier1_features = [
    'start_speed', 'release_pos_x', 'release_pos_z',  # our column names
    'plate_x', 'plate_z', 'pfx_x', 'pfx_z', 
    'release_spin_rate',
    'balls', 'strikes', 'outs_when_up',
    'inning', 'inning_topbot', 
    'bat_score', 'fld_score',  # our columns
    'stand', 'p_throws', 'pitch_type',
    'batter_id', 'pitcher_id',  # our column names
    'on_1b', 'on_2b', 'on_3b',
    'pitch_number',  # our column name
]

tier2_features = tier1_features + ['launch_angle', 'launch_speed']
```

**Target Encoding:**
```python
# Tier 1: description -> ball/strike/ball_in_play
def classify_tier1(row):
    if 'ball' in row['pitch_result']:
        return 'ball'
    elif 'strike' in row['pitch_result']:
        return 'strike'
    else:
        return 'ball_in_play'

# Tier 2: events -> hit type
def classify_tier2(row):
    if row['events'] == 'single': return 'single'
    elif row['events'] == 'double': return 'double'
    # ... etc
```

### Phase 2: Sequential Model (Week 3-4)

**Model 2: LSTM Pitch Sequencer** (SebastianJRamirezA approach)
```python
# Create sequences from our data
sequences = []
for game_pk in data['game_pk'].unique():
    for at_bat in data[data['game_pk'] == game_pk]['at_bat_number'].unique():
        pitches = data[(data['game_pk'] == game_pk) & 
                       (data['at_bat_number'] == at_bat)]
        pitches = pitches.sort_values('pitch_number')
        
        # Sliding window
        for i in range(len(pitches) - 3):
            seq = pitches.iloc[i:i+3]
            target = pitches.iloc[i+3]
            sequences.append((seq, target))
```

### Phase 3: Multi-Task Model (Week 5-6)

**Model 3: Joint Type + Location** (CMU approach)
```python
# Multi-output model
inputs = Input(shape=(seq_length, num_features))
lstm = LSTM(128)(inputs)

# Task 1: Pitch Type
type_pred = Dense(num_pitch_types, activation='softmax', name='type')(lstm)

# Task 2: Location (regression)
location_x = Dense(1, name='location_x')(lstm)
location_z = Dense(1, name='location_z')(lstm)

model = Model(inputs=inputs, outputs=[type_pred, location_x, location_z])
model.compile(optimizer='adam',
              loss={'type': 'categorical_crossentropy',
                    'location_x': 'mse',
                    'location_z': 'mse'})
```

### Phase 4: Enhanced Features (Week 7-8)

**Add Rolling Player Features:**
```python
# Join with our player profile tables
enhanced_features = base_features + [
    # From pitcher_arsenals
    'pitcher_fastball_pct',
    'pitcher_avg_velocity',
    'pitcher_zone_pct',
    
    # From batter_pitch_type_performance
    'batter_vs_fastball_ops',
    'batter_chase_rate',
    
    # From matchup_history
    'times_faced_this_pitcher',
    'historical_outcome_vs_pitcher',
]
```

---

## 8. Technical Implementation Notes

### A. Database Integration
```python
# Query our warehouse for training data
import psycopg2

conn = psycopg2.connect(database="retrosheet")

def fetch_training_data(season):
    query = f"""
    SELECT 
        l.*,
        pa.pitcher_fastball_pct,
        pa.pitcher_zone_pct,
        bp.batter_chase_rate,
        mh.times_faced
    FROM features_pitch.locations_clean l
    LEFT JOIN features_pitch.pitcher_arsenals pa 
        ON l.pitcher_id = pa.pitcher_id AND l.game_year = pa.game_year
    LEFT JOIN features_pitch.batter_profiles bp 
        ON l.batter_id = bp.batter_id AND l.game_year = bp.game_year
    LEFT JOIN features_pitch.matchup_history mh
        ON l.pitcher_id = mh.pitcher_id 
        AND l.batter_id = mh.batter_id 
        AND l.game_year = mh.game_year
    WHERE l.game_year = {season}
    """
    return pd.read_sql(query, conn)
```

### B. Model Registry
```python
# Save models to our models schema
import joblib
import psycopg2

def save_model(model, model_name, version, metrics):
    # Save to disk
    joblib.dump(model, f'models/{model_name}_v{version}.joblib')
    
    # Register in database
    conn = psycopg2.connect(database="retrosheet")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO models.trained_models 
        (model_name, version, file_path, metrics, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """, (model_name, version, f'models/{model_name}_v{version}.joblib', 
          json.dumps(metrics)))
    conn.commit()
```

---

## 9. Expected Performance Targets

Based on research benchmarks and our superior data coverage:

| Model | Target Accuracy | Expected Training Time | Data Needed |
|-------|-----------------|------------------------|-------------|
| Two-Tier XGBoost | 60-65% | 2-4 hours | 7.66M pitches |
| LSTM Sequencer | 65-70% | 8-12 hours | 7.66M sequences |
| Multi-Task | 70-75% | 12-16 hours | 7.66M pitches |
| Enhanced (with player profiles) | 75-80% | 4-6 hours | 7.66M + profiles |

---

## 10. Conclusion

### Key Takeaways

1. **Two-tier hierarchical classification** is the most common and robust approach
2. **XGBoost is the standard** for pitch outcome prediction
3. **Sequential models (LSTM)** add value for pitch sequencing
4. **Multi-task learning** (type + location) is emerging as best practice
5. **Player profiles** are underutilized in existing repos - our opportunity

### Immediate Next Steps

1. **Implement Two-Tier XGBoost** (proven, quick win)
2. **Populate all seasons** in player profile tables
3. **Build LSTM sequencer** for next-pitch prediction
4. **Add player profiles** as features to enhance performance
5. **Validate on 2025 season** (out-of-sample test)

### Files to Create

1. `scripts/models/pitch_outcome_xgboost.py` - Two-tier classifier
2. `scripts/models/pitch_sequence_lstm.py` - Sequential model
3. `scripts/models/pitch_multitask.py` - Joint type + location
4. `sql/features/003_sequential_features.sql` - Sequence tables
5. `notebooks/pitch_model_evaluation.ipynb` - Model comparison

---

## Appendix: Relevant Repositories

| Repository | Focus | Approach | Stars |
|------------|-------|----------|-------|
| schilamkur/Pitch-Outcome-Prediction | Outcome prediction | XGBoost Hierarchical | New |
| SebastianJRamirezA/pitch_prediction_using_ML | Type + Location | LSTM Multi-Task | 5 |
| seanmckee/Pitch-Vision | Full-stack app | XGBoost + LangGraph | New |
| Stonec823/MLB-Pitch-Prediction | Pitch type | Multiple models | 8 |
| Richm419/mlb-pitch-outcome-prediction | Outcome | Feature engineering | New |
| fonnesbeck/baseball | Pitch classification | Bayesian | 155 |

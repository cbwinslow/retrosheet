# Hierarchical Baseball Prediction System (HPS)
## Multi-Layer Inference Architecture for Real-Time Betting

**Author:** Agent Cascade  
**Date:** 2026-05-01  
**Version:** 1.0

---

## Executive Summary

This system provides **5 layers of abstraction** for baseball predictions, from league-wide trends to individual pitch outcomes. It uses panel data methodology (similar to econometrics) to model nested structures:

```
Layer 1: League/Sesason Trends (HR rates, scoring environment)
Layer 2: Team/Context Factors (team form, home/away, weather)
Layer 3: Player Profiles (batter/pitcher tendencies)
Layer 4: Matchup Dynamics (historical H2H, recent encounters)
Layer 5: Situational/PA State (count, base state, pitch sequence)
```

**Goal:** Enable queries like:
> "Bottom 9th, 2-2 count, Scherzer pitching to Harper. Given:
> - Scherzer throws fastball 40% in 2-2 vs anyone
> - Scherzer throws fastball 50% to Harper historically
> - Harper has .320 BA vs Scherzer's fastball
> - League-wide 2-2 outcomes: 35% K, 15% BB, 50% BIP
> - Current game leverage: high (tied, bottom 9th)
> 
> What's the probability of Harper getting on base this pitch?"

---

## System Architecture

### 1. Panel Data Structure

Each observation exists in a nested hierarchy with random effects at each level:

```sql
-- Panel structure for pitch-level data
CREATE TABLE predictions.panel_structure (
    observation_id BIGINT PRIMARY KEY,  -- pitch_id or pa_id
    
    -- Level 1: League/Season (fixed effects)
    season INTEGER,
    league_environment_id VARCHAR,  -- 'AL_2024', 'NL_2024'
    
    -- Level 2: Team/Context
    home_team_id VARCHAR,
    away_team_id VARCHAR,
    game_context_id VARCHAR,  -- Combined: 'HOME_FAVORITE_WARM'
    
    -- Level 3: Player (random effects)
    pitcher_id VARCHAR,
    batter_id VARCHAR,
    pitcher_profile_id VARCHAR,  -- Links to rolling stats
    batter_profile_id VARCHAR,
    
    -- Level 4: Matchup
    matchup_pair_id VARCHAR,  -- Concatenation: 'pitcher_batter'
    matchup_history_count INTEGER,  -- Times faced before
    
    -- Level 5: Situational/State
    game_state_id VARCHAR,  -- inning_outs_score_diff
    pa_state_id VARCHAR,  -- count_base_state
    pitch_sequence_id VARCHAR,  -- Previous 3 pitches
    
    -- Outcome (target)
    outcome VARCHAR,  -- ball, strike, single, home_run, etc.
    outcome_probability DECIMAL(5,4),  -- Actual outcome (0 or 1, or prob if simulated)
    
    -- Timestamps for real-time
    created_at TIMESTAMP,
    game_date DATE,
    game_pk INTEGER
);
```

### 2. Five-Layer Model Hierarchy

#### Layer 1: League Environment Models (Macro Trends)

**Purpose:** Capture league-wide trends and season effects

**Targets:**
- League-wide HR rate (annual)
- League-wide K rate trends
- Scoring environment (runs per game)
- League-wide pitch type distributions

**Features:**
- Year
- Month (season progression)
- Rule changes (DH, dead ball, etc.)
- Weather patterns (seasonal)

**Model Type:** Time-series regression, ARIMA, or simple rolling averages

**Query Example:**
```
"How has the league HR rate changed from April to July?"
```

**Output:** League-wide base rates for adjustments

---

#### Layer 2: Team Context Models (Meso Factors)

**Purpose:** Team form, home field, bullpen status, weather

**Targets:**
- Team win probability (given roster, form, location)
- Team scoring rate (home vs away)
- Bullpen fatigue impact on runs allowed
- Lineup strength vs LHP/RHP

**Features:**
- Last 10 game record
- Home/away indicator
- Days rest
- Key injuries
- Weather (temp, wind, humidity)
- Park factors

**Model Type:** XGBoost with team-level aggregation

**Query Example:**
```
"Tigers are on a 7-game winning streak. What's their win prob vs Yankees at home?"
```

**Output:** Team-adjusted probabilities

---

#### Layer 3: Player Profile Models (Micro - Batter/Pitcher)

**Purpose:** Individual player tendencies and rolling performance

**Targets:**
- Batter wOBA vs pitch type
- Pitcher pitch mix by count
- Batter zone discipline (swing%, contact%)
- Pitcher stuff metrics (velocity trends, break)

**Features:**
- Rolling 30-day stats
- Career averages
- Platoon splits
- Count-specific tendencies
- Pitch type performance

**Model Type:** Random effects models, Bayesian updating

**Tables:**
```sql
-- Batter rolling profiles (updated daily)
predictions.batter_profiles_rolling (
    batter_id VARCHAR,
    as_of_date DATE,
    last_30_pa INTEGER,
    woba DECIMAL(4,3),
    k_rate DECIMAL(4,3),
    bb_rate DECIMAL(4,3),
    vs_fastball_woba DECIMAL(4,3),
    vs_breaking_woba DECIMAL(4,3),
    zone_swing_rate DECIMAL(4,3),
    o_swing_rate DECIMAL(4,3),  -- chase rate
    count_performance JSONB  -- {"0-0": .280, "2-2": .180}
);

-- Pitcher rolling profiles
predictions.pitcher_profiles_rolling (
    pitcher_id VARCHAR,
    as_of_date DATE,
    last_5_games_pitches INTEGER,
    pitch_mix JSONB,  -- {"FF": 0.45, "SL": 0.25, "CU": 0.20, "CH": 0.10}
    pitch_mix_by_count JSONB,  -- Nested by count
    avg_velocity DECIMAL(5,2),
    zone_rate DECIMAL(4,3),
    swing_rate DECIMAL(4,3),
    whiff_rate DECIMAL(4,3),
    -- Count-specific
    first_pitch_strike_rate DECIMAL(4,3),
    two_strike_k_rate DECIMAL(4,3),
    three_ball_walk_rate DECIMAL(4,3)
);
```

**Query Example:**
```
"What's Harper's wOBA vs fastballs in 2-2 counts over last 30 days?"
```

---

#### Layer 4: Matchup Models (Micro - H2H Dynamics)

**Purpose:** Historical pitcher-batter interactions

**Targets:**
- Matchup-specific outcome probabilities
- Pitch sequence patterns used
- Batter adjustment over time vs pitcher

**Features:**
- Career H2H stats (PA, hits, HRs, Ks)
- Recent H2H (last 2 seasons)
- Pitch sequences historically used
- Batter's improvement/decline vs pitcher

**Model Type:** Small sample Bayesian adjustment

**Tables:**
```sql
-- Matchup history
predictions.matchup_history (
    matchup_pair_id VARCHAR PRIMARY KEY,  -- pitcher_batter
    pitcher_id VARCHAR,
    batter_id VARCHAR,
    career_pas INTEGER,
    career_avg DECIMAL(4,3),
    career_obp DECIMAL(4,3),
    career_slg DECIMAL(4,3),
    career_hr INTEGER,
    career_so INTEGER,
    career_bb INTEGER,
    pitch_mix_faced JSONB,  -- What pitches thrown to this batter
    outcomes_distribution JSONB,  -- {"single": 5, "double": 2, "hr": 1, "so": 8}
    last_2_seasons_pas INTEGER,
    last_2_seasons_woba DECIMAL(4,3),
    times_faced_this_season INTEGER,
    most_recent_date DATE,
    trend_direction VARCHAR  -- 'improving', 'declining', 'stable'
);
```

**Query Example:**
```
"Harper is 8-23 with 2 HRs vs Scherzer career. What's his HR prob this PA?"
```

---

#### Layer 5: Situational/Pitch-Level Models (Micro - Real-Time State)

**Purpose:** Immediate game state and pitch-by-pitch predictions

**Targets:**
5A. **Next Pitch Prediction:**
   - Pitch type (FF, SL, CU, CH)
   - Location (zone vs chase)

5B. **Pitch Outcome Prediction:**
   - Swing vs take
   - Contact vs whiff
   - Ball-in-play vs foul/strike

5C. **PA Outcome Prediction (Dynamic):**
   - Final outcome (K, BB, 1B, 2B, 3B, HR, Out)
   - Updated after each pitch

5D. **Run Scoring Prediction:**
   - Runs this half-inning
   - Win probability update

**Features:**
- Current count (balls, strikes)
- Base state (runners on)
- Outs, inning, score
- Pitch sequence within PA
- Inning leverage (LI)
- Pitcher fatigue (pitches thrown)
- Platoon matchup

**Model Types:**
- Markov chains for count transitions
- LSTM for pitch sequences
- XGBoost for PA outcomes
- RE288 for run expectancy

**Tables:**
```sql
-- Real-time game state
predictions.live_game_state (
    game_pk INTEGER,
    half_inning INTEGER,
    pa_number INTEGER,
    pitch_number INTEGER,
    current_count VARCHAR,  -- "2-2"
    base_state INTEGER,  -- 0-7 encoding
    outs INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    inning_lEVERAGE_index DECIMAL(4,2),
    pitcher_id VARCHAR,
    batter_id VARCHAR,
    pitcher_pitches_thrown INTEGER,
    pitcher_days_rest INTEGER,
    -- Predictions (updated each pitch)
    pred_next_pitch_type JSONB,  -- {"FF": 0.40, "SL": 0.30, ...}
    pred_swing_probability DECIMAL(4,3),
    pred_contact_probability DECIMAL(4,3),
    pred_pa_outcome JSONB,  -- {"K": 0.35, "BB": 0.15, "1B": 0.20, "HR": 0.05, ...}
    pred_win_prob_home DECIMAL(4,3),
    timestamp TIMESTAMP
);

-- Pitch-by-pitch predictions history
predictions.pitch_predictions (
    prediction_id BIGINT PRIMARY KEY,
    game_pk INTEGER,
    pa_id VARCHAR,
    pitch_number INTEGER,
    -- Context
    count_before VARCHAR,
    base_state_before INTEGER,
    -- Predictions
    pitch_type_pred JSONB,
    pitch_location_pred JSONB,  -- {"x": 0.5, "z": 2.5}
    swing_pred DECIMAL(4,3),
    outcome_pred JSONB,
    -- Actual (populated after pitch)
    actual_pitch_type VARCHAR,
    actual_swing BOOLEAN,
    actual_outcome VARCHAR,
    model_accuracy DECIMAL(4,3),  -- Did we predict correctly?
    -- Model version
    model_version VARCHAR,
    inference_latency_ms INTEGER
);
```

---

## 3. Hierarchical Inference Pipeline

### Aggregation Flow

When making a prediction, models at each layer contribute:

```
Layer 5 (Situation): Base prediction given state
         ↓
Layer 4 (Matchup): Adjust for H2H history
         ↓
Layer 3 (Profiles): Adjust for player tendencies
         ↓
Layer 2 (Team): Adjust for context/streaks
         ↓
Layer 1 (League): Adjust for environment
         ↓
Final Probability Distribution
```

**Example Calculation (PA Outcome):**

```python
# Base: League average 2-2 count outcomes
base_probs = {"K": 0.35, "BB": 0.05, "1B": 0.15, "2B": 0.05, "3B": 0.01, "HR": 0.04, "Out": 0.35}

# Layer 3: Player adjustments
# Scherzer has 40% K rate in 2-2 (vs 35% league)
# Harper has 25% K rate vs RHP (vs 30% league)
# Adjusted K prob: (0.40 + 0.25) / 2 = 0.325? No, multiplicative:
player_adjustment = 0.35 * (0.40/0.35) * (0.25/0.30)  # 0.35 * 1.14 * 0.83 = 0.33

# Layer 4: Matchup adjustment
# Harper 8-23 with 2 HR vs Scherzer career (high SLG)
# Boost HR prob by 1.5x from matchup

# Layer 2: Context
# Bottom 9th, high leverage -> more conservative pitching
# Reduce BB prob slightly, increase K prob

# Layer 1: League trends
# 2024 is high-K environment
# Add 5% to K rate

# Final: Ensemble or multiplicative adjustment
```

### Implementation: Hierarchical Bayes

```sql
-- Hierarchical model with partial pooling
-- Each layer contributes a random effect

WITH base_prediction AS (
    -- Layer 5: Situational base rate
    SELECT 
        pa_state_id,
        AVG(CASE WHEN outcome = 'K' THEN 1 ELSE 0 END) as base_k_rate,
        AVG(CASE WHEN outcome = 'HR' THEN 1 ELSE 0 END) as base_hr_rate
    FROM predictions.panel_structure
    WHERE season = 2024
    GROUP BY pa_state_id
),

player_effects AS (
    -- Layer 3: Player deviations from base
    SELECT 
        pitcher_id,
        AVG(CASE WHEN outcome = 'K' THEN 1 ELSE 0 END) - base.base_k_rate as pitcher_k_effect,
        AVG(CASE WHEN outcome = 'HR' THEN 1 ELSE 0 END) - base.base_hr_rate as pitcher_hr_effect
    FROM predictions.panel_structure p
    JOIN base_prediction base ON p.pa_state_id = base.pa_state_id
    WHERE p.season = 2024
    GROUP BY pitcher_id, base.base_k_rate, base.base_hr_rate
),

matchup_effects AS (
    -- Layer 4: Matchup-specific adjustment
    SELECT 
        matchup_pair_id,
        AVG(CASE WHEN outcome = 'K' THEN 1 ELSE 0 END) - 
            (base.base_k_rate + COALESCE(pe.pitcher_k_effect, 0)) as matchup_k_effect
    FROM predictions.panel_structure p
    JOIN base_prediction base ON p.pa_state_id = base.pa_state_id
    LEFT JOIN player_effects pe ON p.pitcher_id = pe.pitcher_id
    WHERE p.season = 2024
    GROUP BY matchup_pair_id, base.base_k_rate, pe.pitcher_k_effect
)

-- Combine all effects
SELECT 
    p.*,
    base.base_k_rate + 
        COALESCE(pe.pitcher_k_effect, 0) + 
        COALESCE(me.matchup_k_effect, 0) as adjusted_k_prob
FROM predictions.panel_structure p
JOIN base_prediction base ON p.pa_state_id = base.pa_state_id
LEFT JOIN player_effects pe ON p.pitcher_id = pe.pitcher_id
LEFT JOIN matchup_effects me ON p.matchup_pair_id = me.matchup_pair_id;
```

---

## 4. Real-Time Inference System

### Live Game Integration

```python
# Real-time inference pipeline
class LiveInferenceEngine:
    """
    Continuously ingests live game data and updates predictions
    after each pitch.
    """
    
    async def on_pitch_received(self, pitch_event: LivePitchEvent):
        """Called for each live pitch."""
        
        # 1. Update game state
        current_state = await self.update_game_state(pitch_event)
        
        # 2. Fetch all layer predictions
        layer_1 = await self.league_model.get_adjustment(current_state)
        layer_2 = await self.team_model.get_adjustment(current_state)
        layer_3 = await self.player_model.get_profiles(current_state)
        layer_4 = await self.matchup_model.get_history(current_state)
        layer_5 = await self.situational_model.predict(current_state)
        
        # 3. Combine hierarchically
        final_prediction = self.combine_predictions(
            layer_1, layer_2, layer_3, layer_4, layer_5
        )
        
        # 4. Compare to betting odds
        betting_edges = await self.find_betting_edges(
            current_state, final_prediction
        )
        
        # 5. Alert if edge found
        if betting_edges:
            await self.alert_betting_opportunity(betting_edges)
        
        # 6. Store prediction for evaluation
        await self.store_prediction(
            pitch_event, final_prediction, betting_edges
        )
        
    async def find_betting_edges(self, state, prediction):
        """Compare model predictions to betting odds."""
        
        # Get current odds
        odds = await self.odds_service.get_live_odds(
            game_pk=state.game_pk,
            market_type="pa_outcome"  # or "pitch_result", "run_scored"
        )
        
        edges = []
        for outcome, model_prob in prediction.outcomes.items():
            # Convert odds to implied probability
            if outcome in odds:
                implied_prob = odds[outcome].to_implied_probability()
                
                # Calculate edge
                edge = model_prob - implied_prob
                
                if edge > 0.05:  # 5% edge threshold
                    edges.append({
                        "outcome": outcome,
                        "model_prob": model_prob,
                        "implied_prob": implied_prob,
                        "edge": edge,
                        "odds": odds[outcome],
                        "kelly_stake": self.calculate_kelly(model_prob, odds[outcome])
                    })
        
        return edges
```

### Fast Query Interface

```python
# Natural language query handler
class PredictionQueryHandler:
    """
    Handles natural language queries about predictions.
    """
    
    async def query(self, nl_query: str, context: GameContext = None):
        """
        Examples:
        - "What's Harper's chance of homering vs Scherzer?"
        - "Given 2-2 count, what's next pitch?"
        - "Tigers are on a streak, win probability?"
        - "Is there betting value on Harper HR?"
        """
        
        # Parse intent
        parsed = await self.nlp_parser.parse(nl_query)
        
        # Route to appropriate layer
        if parsed.intent == "player_matchup":
            return await self.query_matchup_prediction(parsed, context)
        elif parsed.intent == "pitch_prediction":
            return await self.query_pitch_prediction(parsed, context)
        elif parsed.intent == "team_win_prob":
            return await self.query_team_prediction(parsed, context)
        elif parsed.intent == "betting_edge":
            return await self.query_betting_edge(parsed, context)
        
    async def query_matchup_prediction(self, parsed, context):
        """Harper vs Scherzer style query."""
        
        # Fetch all layers
        league_adj = await self.get_league_adjustment(parsed.season)
        team_context = await self.get_team_context(
            parsed.home_team, parsed.away_team
        )
        profiles = await self.get_player_profiles(
            parsed.pitcher_id, parsed.batter_id, as_of=parsed.date
        )
        matchup = await self.get_matchup_history(
            parsed.pitcher_id, parsed.batter_id
        )
        
        # If live context provided, add situational
        if context:
            situational = await self.get_situational_prediction(context)
        
        # Combine and return explanation
        prediction = self.combine_with_explanation(
            league_adj, team_context, profiles, matchup, situational
        )
        
        return {
            "prediction": prediction.probabilities,
            "explanation": prediction.explanation,
            "confidence": prediction.confidence,
            "data_sources": prediction.sources_used,
            "query_time_ms": prediction.latency
        }
```

---

## 5. Betting Edge Detection System

### Odds Comparison Pipeline

```sql
-- View: Current betting edges
CREATE VIEW predictions.betting_edges_live AS
WITH model_predictions AS (
    SELECT 
        game_pk,
        pa_id,
        outcome,
        probability as model_prob
    FROM predictions.current_pa_predictions
    WHERE timestamp > NOW() - INTERVAL '1 minute'
),

odds AS (
    SELECT 
        game_pk,
        market_type,
        outcome,
        odds_decimal,
        1 / odds_decimal as implied_prob,
        bookmaker
    FROM odds.live_odds
    WHERE timestamp > NOW() - INTERVAL '1 minute'
),

edges AS (
    SELECT 
        m.game_pk,
        m.pa_id,
        m.outcome,
        m.model_prob,
        o.implied_prob,
        m.model_prob - o.implied_prob as edge,
        o.odds_decimal,
        o.bookmaker,
        -- Kelly criterion stake fraction
        CASE 
            WHEN m.model_prob > o.implied_prob 
            THEN (m.model_prob * o.odds_decimal - 1) / (o.odds_decimal - 1)
            ELSE 0 
        END as kelly_fraction,
        -- Expected value
        m.model_prob * (o.odds_decimal - 1) - (1 - m.model_prob) as ev
    FROM model_predictions m
    JOIN odds o ON m.outcome = o.outcome AND m.game_pk = o.game_pk
    WHERE o.market_type = 'pa_outcome'
)

SELECT *
FROM edges
WHERE edge > 0.05  -- 5% minimum edge
  AND ev > 0.02    -- Positive expected value
ORDER BY ev DESC;
```

### Alert System

```python
class BettingAlertService:
    """
    Sends alerts when high-confidence edges are detected.
    """
    
    async def check_and_alert(self):
        """Run every 30 seconds during live games."""
        
        edges = await self.db.fetch("""
            SELECT * FROM predictions.betting_edges_live
            WHERE edge > 0.08  -- 8% edge
              AND model_prob > 0.25  -- Not too rare
            ORDER BY edge DESC
            LIMIT 5
        """)
        
        for edge in edges:
            # Check if we already alerted
            if not await self.already_alerted(edge):
                
                # Format alert
                alert = self.format_alert(edge)
                
                # Send to user
                await self.send_alert(alert)
                
                # Log
                await self.log_alert(edge)
    
    def format_alert(self, edge):
        """Format betting opportunity for display."""
        
        return f"""
🎯 **BETTING OPPORTUNITY DETECTED**

**Game:** {edge.game_teams}
**Situation:** {edge.inning}, {edge.count}, {edge.base_state}
**Matchup:** {edge.batter_name} vs {edge.pitcher_name}

**Prediction:** {edge.outcome}
- Model Probability: {edge.model_prob:.1%}
- Market Odds: {edge.odds_decimal} (implied: {edge.implied_prob:.1%})
- **Edge: +{edge.edge:.1%}**

**Expected Value:** {edge.ev:.1%}
**Kelly Stake:** {edge.kelly_fraction:.1%} of bankroll

**Model Confidence:** {edge.confidence}
**Data Sources:** {edge.sources}

**Quick Action:**
Place bet on {edge.outcome} at {edge.bookmaker}
        """
```

---

## 6. Training Pipeline

### Model Training Schedule

```python
# Automated training pipeline
class HierarchicalTrainingPipeline:
    """
    Trains all 5 layers on schedule.
    """
    
    # Layer 1: League models - Train once per season
    async def train_league_models(self, season: int):
        """Train league environment models."""
        data = await self.load_season_data(season)
        
        model = LeagueEnvironmentModel()
        model.fit(data)
        
        await self.save_model(model, f"league_{season}")
    
    # Layer 2: Team models - Train weekly
    async def train_team_models(self, as_of_date: date):
        """Train team context models."""
        data = await self.load_team_data(
            window_start=as_of_date - timedelta(days=30),
            window_end=as_of_date
        )
        
        model = TeamContextModel()
        model.fit(data)
        
        await self.save_model(model, f"team_{as_of_date}")
    
    # Layer 3: Player profiles - Update daily
    async def train_player_profiles(self, as_of_date: date):
        """Update rolling player statistics."""
        
        # Batters
        batter_stats = await self.calculate_rolling_stats(
            entity_type="batter",
            window_days=30,
            as_of=as_of_date
        )
        await self.save_to_db(batter_stats, "predictions.batter_profiles_rolling")
        
        # Pitchers
        pitcher_stats = await self.calculate_rolling_stats(
            entity_type="pitcher",
            window_days=30,
            as_of=as_of_date
        )
        await self.save_to_db(pitcher_stats, "predictions.pitcher_profiles_rolling")
    
    # Layer 4: Matchup models - Update weekly
    async def train_matchup_models(self, as_of_date: date):
        """Update matchup histories."""
        
        matchups = await self.calculate_matchup_stats(
            min_pas=5,
            as_of=as_of_date
        )
        await self.save_to_db(matchups, "predictions.matchup_history")
    
    # Layer 5: Situational models - Train monthly
    async def train_situational_models(self):
        """Train pitch-level and PA-level models."""
        
        # Markov chain for count transitions
        markov = MarkovChainModel()
        markov.fit(await self.load_pitch_sequence_data())
        await self.save_model(markov, "markov_pitch_transitions")
        
        # XGBoost for PA outcomes
        xgb = XGBoostPAOutcomeModel()
        xgb.fit(await self.load_pa_outcome_data())
        await self.save_model(xgb, "xgboost_pa_outcomes")
        
        # LSTM for pitch sequences (if enough data)
        lstm = LSTMPitchSequenceModel()
        lstm.fit(await self.load_pitch_sequences())
        await self.save_model(lstm, "lstm_pitch_sequence")
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. ✅ **Panel data schema** - Create `predictions.panel_structure`
2. **Player profile tables** - Rolling 30-day stats
3. **Matchup history table** - Career H2H aggregation
4. **Base Markov model** - Count transitions

### Phase 2: Models (Week 3-4)
1. **Train Layer 1** - League environment (quick)
2. **Train Layer 2** - Team context models
3. **Train Layer 3** - Player profile system
4. **Train Layer 4** - Matchup model
5. **Train Layer 5** - XGBoost PA outcome + Markov pitch

### Phase 3: Real-Time (Week 5-6)
1. **Live inference engine** - Sub-second predictions
2. **Odds integration** - Compare to live markets
3. **Alert system** - Send opportunities to user
4. **Query interface** - Natural language handler

### Phase 4: Betting Integration (Week 7-8)
1. **Paper trading system** - Track simulated bets
2. **Kelly staking** - Optimal bet sizing
3. **Performance tracking** - Model accuracy, ROI
4. **Model retraining** - Feedback loop

---

## 8. Usage Examples

### Example 1: Live Game Query

```python
# User asks: "Bottom 9th, Harper vs Scherzer, 2-2 count, what's the HR chance?"

response = await query_engine.query(
    "Harper home run probability vs Scherzer in 2-2 count bottom 9th"
)

# Response:
{
    "prediction": {
        "home_run": 0.08,  # 8% HR chance
        "single": 0.12,
        "double": 0.05,
        "triple": 0.01,
        "walk": 0.05,
        "strikeout": 0.38,
        "out_in_play": 0.31
    },
    "explanation": {
        "base_rate": "2-2 count league avg: 4% HR, 35% K",
        "pitcher_adjustment": "Scherzer 2-strike K rate: 42% (+7%)",
        "batter_adjustment": "Harper power: +3% HR vs RHP",
        "matchup_history": "Harper 2 HR in 23 PA vs Scherzer (+4% HR)",
        "context": "Bottom 9th high leverage: Scherzer more likely to throw strikes",
        "final_calculation": "4% * 1.10 (power) * 1.80 (H2H) = 8%"
    },
    "betting": {
        "market_odds": "+850 (implied 10.5%)",
        "model_prob": "8.0%",
        "edge": "-2.5%",  # No edge, odds too short
        "recommendation": "NO BET"
    }
}
```

### Example 2: Pitch-by-Pitch Prediction

```python
# Before each pitch
prediction = await inference_engine.predict_next_pitch(
    game_pk=716190,
    current_count="2-2",
    pitcher_id="scherzer_max",
    batter_id="harper_bryce",
    previous_pitches=["FF", "SL", "FF"],  # Fastball, Slider, Fastball
    base_state="runners_1_2",
    outs=2,
    inning=9,
    score_diff=0
)

# Response:
{
    "pitch_prediction": {
        "fastball": 0.45,
        "slider": 0.35,
        "curveball": 0.15,
        "changeup": 0.05
    },
    "location_prediction": {
        "zone_probability": 0.65,
        "expected_location": {"x": 0.2, "z": 2.8},  # High and away
        "pitch_shape": {"velocity": 94.5, "spin": 2300}
    },
    "outcome_prediction": {
        "swing": 0.72,
        "contact": 0.58,
        "fair_ball": 0.35,
        "home_run": 0.06
    },
    "sequence_analysis": {
        "pattern": "Fastball setup → Slider away → Fastball up",
        "historical_use": "Scherzer uses this sequence 12% of time in 2-2",
        "effectiveness": "58% K rate with this sequence"
    }
}
```

### Example 3: Macro Trend Query

```python
# User asks: "Are HRs down this year? Tigers winning streak impact?"

response = await query_engine.query(
    "League HR trends 2024 and Tigers streak analysis"
)

# Response:
{
    "league_trends": {
        "current_hr_rate": "2.15 per game (down 8% from 2023)",
        "trend": "declining since All-Star break",
        "park_factors": "Comerica Park HR factor: 0.85 (suppresses HRs)",
        "ball_changes": "2024 ball has 5% less carry"
    },
    "team_analysis": {
        "tigers_streak": "7-game winning streak",
        "win_prob_next": "62% vs Yankees (up from 45% neutral)",
        "streak_factors": {
            "offense": "OPS +.120 over last 7 games",
            "pitching": "ERA 2.85 over streak",
            "bullpen": "Fresh, only 12 IP in last 7 games"
        },
        "regression_warning": "Streaks historically add ~5% win prob, not 17%"
    }
}
```

---

## 9. Technical Stack

**Data Layer:**
- PostgreSQL with hierarchical schema
- Materialized views for fast queries
- Redis for real-time state cache

**Model Layer:**
- XGBoost for structured predictions (PA outcomes, pitch types)
- LSTM/GRU for sequences (pitch sequences, at-bat progression)
- Markov chains for count transitions
- Bayesian models for small sample adjustments

**Inference Layer:**
- FastAPI for real-time API
- WebSocket for live game updates
- Async processing for sub-second predictions

**Integration Layer:**
- Odds API integration (multiple bookmakers)
- MLB Stats API for live data
- Redis pub/sub for alerts

**Presentation Layer:**
- CLI for quick queries (`baseball predict "Harper vs Scherzer"`)
- Chatbot for natural language
- Dashboard for visualization

---

## Summary

This system provides **hierarchical predictions from league trends to individual pitches**, enabling:

1. **Macro analysis:** "HRs are down 8% this year"
2. **Team context:** "Tigers 7-game streak adds 5% win probability"
3. **Player profiles:** "Harper hits .320 vs fastballs, .180 vs sliders"
4. **Matchup dynamics:** "Harper 8-23 with 2 HRs vs Scherzer career"
5. **Situational:** "2-2 count, 2 outs, RISP: 45% K, 12% BB, 43% BIP"
6. **Real-time:** "Next pitch: 45% fastball, 35% slider, expected location: high/away"

**All combined:** "70% chance this PA ends in a hit given all factors"

**Betting application:** Compare 70% model probability to 55% implied odds = 15% edge → BET

This is the complete system architecture. Ready to implement?

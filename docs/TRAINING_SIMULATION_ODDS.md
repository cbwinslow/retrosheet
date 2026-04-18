# Simulation and Odds Calculation Training Guide

This guide provides step-by-step instructions for using the baseball state transition engine for simulation and odds calculation.

## Overview

The simulation engine implements a baseball state machine that models game state transitions, enabling Monte Carlo simulation for game outcomes and odds calculation for betting markets.

## Architecture

### State Machine

The state machine is implemented in `retrosheet/simulation/baseball_state.py` and models:

- **Base occupancy**: Which bases are occupied (0-7)
- **Out count**: Number of outs (0-2)
- **Score**: Home and away scores
- **Inning**: Current inning (1-9+)
- **Top/bottom**: Whether it's top or bottom of inning
- **Batting order**: Current batter position

### State Transitions

The `apply_event()` function applies an event type to a state and returns the new state:

- `single`: Single hit
- `double`: Double hit
- `triple`: Triple hit
- `home_run`: Home run
- `walk`: Walk
- `strikeout`: Strikeout
- `out`: Other out (fly out, ground out, etc.)
- `sac_fly`: Sacrifice fly
- `sac_bunt`: Sacrifice bunt
- `double_play`: Double play
- `fielders_choice`: Fielder's choice

## Basic Usage

### Create Initial State

```python
from retrosheet.simulation.baseball_state import BaseballState

state = BaseballState(
    bases=0,           # No runners on base
    outs=0,            # 0 outs
    home_score=0,      # Home team score
    away_score=0,      # Away team score
    inning=1,          # 1st inning
    is_bottom_inning=False,  # Top of inning
)
```

### Apply Event

```python
from retrosheet.simulation.baseball_state import apply_event

# Apply a single
new_state = apply_event(state, event_type='single')

# Apply a home run
new_state = apply_event(state, event_type='home_run')

# Apply a strikeout
new_state = apply_event(state, event_type='strikeout')
```

### Access State Properties

```python
print(f"Bases: {new_state.bases}")           # Base occupancy (0-7)
print(f"Outs: {new_state.outs}")             # Out count (0-2)
print(f"Home score: {new_state.home_score}")
print(f"Away score: {new_state.away_score}")
print(f"Inning: {new_state.inning}")
print(f"Bottom: {new_state.is_bottom_inning}")
```

## Monte Carlo Simulation

### Simulate Single Plate Appearance

```python
from retrosheet.simulation.baseball_state import BaseballState, apply_event
import random

# Define event probabilities (from model)
event_probs = {
    'single': 0.20,
    'double': 0.05,
    'triple': 0.01,
    'home_run': 0.03,
    'walk': 0.08,
    'strikeout': 0.20,
    'out': 0.38,
    'sac_fly': 0.02,
    'sac_bunt': 0.01,
    'double_play': 0.01,
    'fielders_choice': 0.01,
}

# Sample event type
event_type = random.choices(
    list(event_probs.keys()),
    weights=list(event_probs.values())
)[0]

# Apply event
new_state = apply_event(state, event_type=event_type)
```

### Simulate Half-Inning

```python
def simulate_half_inning(initial_state, event_probs):
    """Simulate a half-inning until 3 outs."""
    state = initial_state
    outs = 0
    
    while outs < 3:
        # Sample event type
        event_type = random.choices(
            list(event_probs.keys()),
            weights=list(event_probs.values())
        )[0]
        
        # Apply event
        state = apply_event(state, event_type=event_type)
        
        # Count outs
        if event_type in ['strikeout', 'out', 'double_play']:
            outs += 1
            if event_type == 'double_play' and state.outs >= 2:
                outs += 1  # Double play counts as 2 outs
        
        # End of inning
        if state.outs >= 3:
            break
    
    return state
```

### Simulate Full Game

```python
def simulate_game(event_probs):
    """Simulate a full 9-inning game."""
    # Initialize state
    state = BaseballState(
        bases=0,
        outs=0,
        home_score=0,
        away_score=0,
        inning=1,
        is_bottom_inning=False,
    )
    
    # Simulate 9 innings
    for _ in range(9):
        # Top of inning (away team batting)
        state = simulate_half_inning(state, event_probs)
        
        # Switch to bottom
        state = BaseballState(
            bases=0,
            outs=0,
            home_score=state.home_score,
            away_score=state.away_score,
            inning=state.inning,
            is_bottom_inning=True,
        )
        
        # Bottom of inning (home team batting)
        state = simulate_half_inning(state, event_probs)
        
        # Switch to next inning
        state = BaseballState(
            bases=0,
            outs=0,
            home_score=state.home_score,
            away_score=state.away_score,
            inning=state.inning + 1,
            is_bottom_inning=False,
        )
    
    return state
```

### Monte Carlo Simulation

```python
def monte_carlo_simulation(event_probs, num_simulations=1000):
    """Run Monte Carlo simulation for game outcome."""
    results = []
    
    for _ in range(num_simulations):
        final_state = simulate_game(event_probs)
        results.append({
            'home_score': final_state.home_score,
            'away_score': final_state.away_score,
            'winner': 'home' if final_state.home_score > final_state.away_score else 'away'
        })
    
    # Calculate probabilities
    home_win_prob = sum(1 for r in results if r['winner'] == 'home') / len(results)
    away_win_prob = sum(1 for r in results if r['winner'] == 'away') / len(results)
    
    return {
        'home_win_prob': home_win_prob,
        'away_win_prob': away_win_prob,
        'results': results
    }
```

## Odds Calculation

### Convert Probabilities to American Odds

```python
def probability_to_american_odds(prob):
    """Convert probability to American odds."""
    if prob >= 0.5:
        # Favorite: negative odds
        return round((prob / (1 - prob)) * -100)
    else:
        # Underdog: positive odds
        return round(((1 - prob) / prob) * 100)
```

### Convert Probabilities to Decimal Odds

```python
def probability_to_decimal_odds(prob):
    """Convert probability to decimal odds."""
    return round(1 / prob, 2)
```

### Calculate Implied Probability

```python
def decimal_odds_to_probability(decimal_odds):
    """Convert decimal odds to implied probability."""
    return round(1 / decimal_odds, 4)
```

### Calculate Edge

```python
def calculate_edge(model_prob, market_prob):
    """Calculate edge between model and market."""
    return model_prob - market_prob
```

## Using Model Predictions

### Load Model Probabilities

```python
from retrosheet.prediction import load_registered_model, apply_calibration

# Load model
model = load_registered_model(model_id='pa_outcome_distribution_2025')

# Get prediction for a plate appearance
# (Use scripts/predict_pa_outcome_distribution.py for full prediction workflow)
```

### Map Model Outcomes to Simulation Events

```python
outcome_to_event = {
    'pa_batter_hit': 'single',  # Simplified mapping
    'pa_batter_walk': 'walk',
    'pa_batter_strikeout': 'strikeout',
    'pa_batter_home_run': 'home_run',
    # Map other outcomes as needed
}
```

## Validation

### Validate State Transitions

```python
from retrosheet.simulation.test_baseball_state import test_state_transitions

# Run unit tests
pytest retrosheet/simulation/test_baseball_state.py -v
```

### Validate Against Historical Data

```python
# Compare simulation results with historical game outcomes
# Use scripts/test_validation_simulation.py for validation
```

### Validate Reproducibility

```python
from retrosheet.simulation.test_reproducibility import test_reproducibility

# Run reproducibility tests
pytest retrosheet/simulation/test_reproducibility.py -v
```

## Advanced Usage

### Custom Event Probabilities

```python
# Context-specific probabilities based on game state
def get_contextual_probabilities(state, batter_stats, pitcher_stats):
    """Get event probabilities based on context."""
    base_prob = {
        'single': 0.20,
        'double': 0.05,
        # ...
    }
    
    # Adjust based on batter stats
    if batter_stats['hit_rate'] > 0.30:
        base_prob['single'] *= 1.2
    
    # Adjust based on pitcher stats
    if pitcher_stats['strikeout_rate'] > 0.25:
        base_prob['strikeout'] *= 1.2
    
    # Normalize probabilities
    total = sum(base_prob.values())
    for key in base_prob:
        base_prob[key] /= total
    
    return base_prob
```

### Track Lineup Progression

```python
def simulate_with_lineup(state, event_probs, lineup):
    """Simulate with lineup progression."""
    batter_index = 0
    
    while state.outs < 3:
        # Get current batter
        batter = lineup[batter_index]
        
        # Get batter-specific probabilities
        batter_probs = get_batter_probabilities(batter)
        
        # Apply event
        state = apply_event(state, event_type=sample_event(batter_probs))
        
        # Advance lineup
        batter_index = (batter_index + 1) % len(lineup)
```

## Troubleshooting

### Issue: Invalid State Transitions

**Symptoms:** State transitions produce invalid baseball states

**Solutions:**
1. Check event type is valid
2. Verify state machine logic in `baseball_state.py`
3. Run unit tests to validate transitions
4. Check for edge cases (e.g., 3rd out with runners on base)

### Issue: Simulation Results Don't Match Historical

**Symptoms:** Simulated game outcomes differ significantly from historical averages

**Solutions:**
1. Verify event probabilities match historical rates
2. Check for missing event types
3. Validate state machine rules against baseball rules
4. Run validation tests against historical data

### Issue: Reproducibility Fails

**Symptoms:** Same simulation produces different results

**Solutions:**
1. Set random seed for reproducibility
2. Use deterministic event sampling
3. Run reproducibility tests
4. Check for non-deterministic code

## Best Practices

1. **Use unit tests:** Always validate state transitions with tests
2. **Set random seed:** For reproducibility in testing
3. **Validate against historical:** Compare simulation results with historical data
4. **Document assumptions:** Document any simplifications or assumptions in simulation
5. **Monitor performance:** Large-scale simulations can be computationally expensive
6. **Use caching:** Cache simulation results for repeated analysis

## References

- `retrosheet/simulation/baseball_state.py` - State machine implementation
- `retrosheet/simulation/test_baseball_state.py` - State transition tests
- `retrosheet/simulation/test_reproducibility.py` - Reproducibility tests
- `docs/MLB_SIMULATION.md` - Simulation architecture documentation
- `docs/MARKET_INTEGRATION.md` - Market integration design
- `scripts/test_validation_simulation.py` - Simulation validation tests

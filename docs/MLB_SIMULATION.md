# MLB Baseball State Machine Rules

This document describes the canonical baseball state transition rules implemented in `retrosheet/simulation/baseball_state.py`.

## State Components

### GameState
The complete game state consists of:
- `inning`: Current inning (1-99)
- `top_inning`: Boolean indicating top (away batting) or bottom (home batting)
- `outs`: Current out count (0-3)
- `bases`: BaseOccupancy object representing runners on base
- `home_score`: Home team runs
- `away_score`: Away team runs

### BaseOccupancy
Represents the state of base runners:
- `first`: Runner on first base (boolean)
- `second`: Runner on second base (boolean)
- `third`: Runner on third base (boolean)

Helper methods:
- `runners_on()`: Count total runners (0-3)
- `is_loaded()`: Check if all three bases are occupied
- `is_empty()`: Check if no runners on base

## State Transition Rules

### Base Occupancy Transitions

#### Home Run
- All runners on base score
- Batter scores
- Bases are cleared after the play
- Runs scored = 1 (batter) + runners_on()

#### Triple
- Runner on third scores
- Runner on second advances to third (if present)
- Runner on first advances to second (if present)
- Batter reaches third
- Bases: first=False, second=False, third=True (or loaded if runners advanced)

#### Double
- Runner on third scores
- Runner on first advances to second (if present)
- Runner on second advances to third (if present)
- Batter reaches second
- Bases: first=False, second=True, third=True (if runners present)

#### Single
- Runner on third scores
- Runner on first advances to second (if present)
- Runner on second advances to third (if present)
- Batter reaches first
- Bases: first=True, second=True, third=True (if runners present)

#### Walk / Hit by Pitch
- If bases are not loaded: batter reaches first, runners advance one base if forced
- If bases are loaded: runner from third scores, bases remain loaded
- Bases: Always loaded after walk if any runners were present

#### Sacrifice Fly
- Runner on third scores (if fewer than 2 outs)
- Batter is out
- Other runners do not advance
- Bases: third cleared if runner scored

#### Outs (Strikeout, Ground Out, Fly Out, etc.)
- No base advancement
- Batter is out
- Bases unchanged

### Out Count Transitions

#### Adding Outs
- Outs increment by 1 for standard outs
- Outs increment by 2 for double plays
- Outs increment by 3 for triple plays
- Outs capped at 3

#### Half-Inning End
- When outs reach 3:
  - Bases are cleared
  - Outs reset to 0
  - If top inning: switch to bottom inning
  - If bottom inning: advance to next inning, switch to top

## Play Outcomes

Standard play outcomes that affect state:

### Outs
- `STRIKEOUT`: Batter strikes out
- `GROUND_OUT`: Batter grounds out
- `FLY_OUT`: Batter flies out
- `LINE_OUT`: Batter lines out
- `POP_OUT`: Batter pops out
- `SACRIFICE_FLY`: Fly out that advances runner
- `SACRIFICE_BUNT`: Bunt out that advances runner

### Hits
- `SINGLE`: Batter reaches first
- `DOUBLE`: Batter reaches second
- `TRIPLE`: Batter reaches third
- `HOME_RUN`: Batter scores

### Walks
- `WALK`: Batter walks
- `HIT_BY_PITCH`: Batter hit by pitch

### Other
- `FIELDERS_CHOICE`: Batter reaches first, out recorded elsewhere
- `ERROR`: Batter reaches first due to error
- `DOUBLE_PLAY`: Two outs recorded
- `TRIPLE_PLAY`: Three outs recorded

## Validation Rules

A GameState is legal if:
- Inning is between 1 and 99
- Outs is between 0 and 3
- Home score is non-negative
- Away score is non-negative

## Testing

The state machine is validated by:
1. Unit tests for all base occupancy transitions
2. Unit tests for all out count transitions
3. Unit tests for complete play transitions
4. Validation against historical Retrosheet data (pending)
5. Fixed-seed reproducibility tests (pending)

## Limitations

Current implementation is a simplified state machine:
- Does not handle all edge cases (e.g., fielder's choice specifics)
- Does not implement full lineup progression logic
- Does not implement substitution handling
- Does not account for specific game situations (e.g., infield fly rule)

These limitations will be addressed as the simulation engine matures.

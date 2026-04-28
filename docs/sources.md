# Data Sources

**Purpose**: Documentation for all data sources used in the baseball platform.

---

## Retrosheet

**URL**: https://www.retrosheet.org

**Data Types**:
- Game files (game logs)
- Event files (play-by-play)
- Roster files
- Park information

**Schema**: `raw_retrosheet`

**Adapter**: `baseball.sources.retrosheet.RetrosheetSource`

**CLI Commands**:
- `baseball retrosheet download --seasons 1900-2025`
- `baseball retrosheet ingest --seasons 1900-2025`
- `baseball retrosheet validate --seasons 1900-2025`

---

## MLB Stats API

**URL**: https://statsapi.mlb.com

**Data Types**:
- Schedules
- Live game feeds
- Player statistics
- Team statistics
- Statcast pitch-level data

**Schema**: `raw_mlb`

**Adapter**: `baseball.sources.mlb.MlbSource`

**CLI Commands**:
- `baseball mlb download --date 2026-04-26`
- `baseball mlb ingest --date 2026-04-26`
- `baseball mlb validate --date 2026-04-26`
- `baseball mlb today`                           # Today's schedule
- `baseball mlb stream --game 716190 --interval 15`  # Live streaming
- `baseball mlb stream --duration 60 --no-save`      # Stream all games

---

## ESPN

**URL**: http://site.api.espn.com/apis/site/v2/sports/baseball/mlb

**Data Types**:
- Game scores
- Schedules
- Player statistics
- Team statistics

**Schema**: `raw_espn`

**Adapter**: `baseball.sources.espn.EspnSource`

**CLI Commands**:
- `baseball espn download --seasons 2020-2025`
- `baseball espn ingest --seasons 2020-2025`
- `baseball espn validate --seasons 2020-2025`

---

## Statcast

**URL**: https://baseballsavant.mlb.com

**Data Types**:
- Pitch-level tracking data
- Batted ball data
- Player statistics

**Schema**: `raw_statcast`

**Adapter**: `baseball.sources.statcast.StatcastSource`

**CLI Commands**:
- `baseball statcast download --seasons 2015-2025`
- `baseball statcast ingest --seasons 2015-2025`
- `baseball statcast validate --seasons 2015-2025`

---

## Lahman

**URL**: https://github.com/chadwickbureau/baseballdatabank

**Data Types**:
- Historical batting statistics
- Historical pitching statistics
- Fielding statistics
- Team data

**Schema**: `raw_lahman`

**Adapter**: `baseball.sources.lahman.LahmanSource`

**CLI Commands**:
- `baseball lahman download --tables all`
- `baseball lahman ingest --tables all`
- `baseball lahman validate --tables all`

---

---

## Live Data Infrastructure

**Purpose**: Real-time game state tracking and prediction

**Components**:
- **Live Feed Poller**: `baseball/services/live_feed.py` - Continuous polling
- **WebSocket Server**: `baseball/live_server.py` - Real-time client updates
- **Live Dashboard**: `static/live_dashboard.html` - Web monitoring UI

**Database Tables**:
- `raw_mlb.live_feed_snapshots` - Deduplicated live feed JSON
- `core.live_games` - Canonical live game state
- `core.live_events` - Live play-by-play events
- `features.live_game_state_features` - Pre-calculated model features

**CLI Commands**:
- `baseball live games`      # List active games
- `baseball live watch 716190`  # Watch specific game
- `baseball live server`     # Start WebSocket server
- `baseball live dashboard`  # Launch web dashboard

---

## Future Sources

### FanGraphs
- Advanced sabermetric statistics
- Pitcher arsenals
- Park factors

### Baseball Reference
- Historical data
- Player biographies
- Franchise information

### Weather
- Game-time weather data
- Temperature, humidity, wind

### Park Factors
- Stadium-specific adjustments
- Historical park effects

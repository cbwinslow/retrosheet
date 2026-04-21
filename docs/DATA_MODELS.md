# Data Models and API Documentation

This document provides comprehensive documentation on the data models and APIs for all baseball data sources used in the retrosheet prediction warehouse.

## Table of Contents

- [Retrosheet](#retrosheet)
- [MLB Stats API / GUMBO](#mlb-stats-api--gumbo)
- [ESPN MLB API](#espn-mlb-api)
- [Statcast](#statcast)
- [Lahman Database](#lahman-database)
- [Baseball Reference](#baseball-reference)
- [Chadwick Baseball Bureau](#chadwick-baseball-bureau)

---

## Retrosheet

### Overview
Retrosheet is a non-profit organization that has digitized play-by-play accounts of baseball games. It provides historical game data dating back to the early 1900s.

### Data Format
Retrosheet data is provided as ASCII text files with comma-separated values. Each game contains multiple record types.

### Record Types

#### ID Record
- **Purpose**: Identifies the date, location, and game number
- **Format**: 12-character ID (e.g., `BAL198304040`)
- **Structure**: 
  - Characters 1-3: Home team abbreviation
  - Characters 4-5: Last two digits of year
  - Characters 6-7: Month
  - Characters 8-9: Day
  - Character 10: Game number (0=single game, 1=first of DH, 2=second of DH)

#### Version Record
- **Purpose**: Tracks when the file was created
- **Current Version**: `1`

#### Info Records
- **Purpose**: Contains single pieces of information per record
- **Examples**: Temperature, attendance, umpire identities
- **Maximum**: 30 info records per game

#### Start Records
- **Purpose**: Identifies starting lineups
- **Count**: 18 (NL/pre-DH AL) or 20 (AL with DH) records
- **Fields**:
  1. Retrosheet ID code (8 digits: first 4 letters of last name + first initial + 3-digit number)
  2. Player name
  3. Team (0=visiting, 1=home)
  4. Batting order position
  5. Starting fielding position (10=designated hitter)

#### Play Records
- **Purpose**: Contains the events of the game
- **Fields**:
  1. Inning
  2. Batting team (0=visiting, 1=home)
  3. Retrosheet ID code
  4. Count on batter (balls/strikes) - `??` if unavailable
  5. Pitch sequence (variable length)
  6. Play description (variable length)

##### Pitch Sequence Codes
- `C` - called strike
- `S` - swinging strike
- `B` - ball
- `F` - foul ball
- `X` - ball put into play
- `T` - foul tip
- `H` - hit by pitch
- `L` - foul bunt
- `M` - missed bunt
- `P` - pitchout
- `N` - no pitch (balks, etc.)
- `V` - automatic ball (no pitch)
- `K` - strike of unknown type
- `U` - unknown/missing pitch
- `Q` - swinging strike on pitchout
- `R` - foul ball on pitchout
- `1`, `2`, `3` - pickoff throws to base
- `+1`, `+2`, `+3` - pickoff throws by catcher
- `>` - runner going on pitch
- `*` - wild pitch blocked by catcher

##### Play Description Structure
- **Basic play**: Standard baseball notation (e.g., `8` = fly to CF, `43` = ground to 2B)
- **Base hits**: Letter + fielder (e.g., `S7` = single to LF, `D8` = double to CF)
- **Modifiers**: Separated by `/` (e.g., `D8/78` = double to left-center, `SH` = sacrifice hit)
- **Runner advancement**: Separated by `.` (e.g., `S9/L9S.2-H;1-3` = single to RF, runner on 2nd scores, runner on 1st to 3rd)

#### Comment Records
- **Purpose**: Special comments for plays requiring additional description

#### Substitute Records
- **Purpose**: Indicates lineup changes
- **Fields**:
  1. Retrosheet ID code
  2. Player name
  3. Team (0=visiting, 1=home)
  4. Batting order position
  5. Position to play (11=pinch hitter, 12=pinch runner)
- **Note**: Preceded by a play record with event `NP` (No Play)

#### Data Records
- **Purpose**: Contains earned runs allowed by each pitcher
- **Fields**: Project Scoresheet code + earned runs

### BEVENT Tool Fields (96 available)

| Field # | Field Name | Description |
|---------|------------|-------------|
| 0 | game id | Game identifier |
| 1 | visiting team | Visiting team code |
| 2 | inning | Inning number |
| 3 | batting team | 0=visiting, 1=home |
| 4 | outs | Number of outs before play |
| 5 | balls | Ball count |
| 6 | strikes | Strike count |
| 7 | pitch sequence | Pitch sequence string |
| 8 | vis score | Visiting team score |
| 9 | home score | Home team score |
| 10 | batter | Batter ID |
| 11 | batter hand | Batter handedness |
| 12 | res batter | Retrosheet batter ID |
| 13 | res batter hand | Retrosheet batter handedness |
| 14 | pitcher | Pitcher ID |
| 15 | pitcher hand | Pitcher handedness |
| 16 | res pitcher | Retrosheet pitcher ID |
| 17 | res pitcher hand | Retrosheet pitcher handedness |
| 18-25 | fielders | Catcher through RF positions |
| 26-28 | runners | Runners on 1B, 2B, 3B |
| 29 | event text | Play description |
| 30 | leadoff flag | First batter of inning |
| 31 | pinchhit flag | Pinch hitter |
| 32 | defensive position | Fielding position |
| 33 | lineup position | Batting order position |
| 34 | event type | Type of event |
| 35 | batter event flag | Batter event |
| 36 | ab flag | At-bat flag |
| 37 | hit value | 1=single, 2=double, 3=triple, 4=HR |
| 38 | SH flag | Sacrifice hit |
| 39 | SF flag | Sacrifice fly |
| 40 | outs on play | Outs recorded |
| 41 | double play flag | DP indicator |
| 42 | triple play flag | TP indicator |
| 43 | RBI on play | RBI credited |
| 44-45 | WP/PB flags | Wild pitch, passed ball |
| 46 | fielded by | Fielder who played ball |
| 47 | batted ball type | F=fly, L=line, P=pop-up, G=ground |
| 48 | bunt flag | Bunt indicator |
| 49 | foul flag | Foul ground indicator |
| 50 | hit location | Field zone |
| 51 | num errors | Number of errors (max 3) |
| 52-57 | error players/types | Error players and types |
| 58 | batter dest | Batter's destination base |
| 59-61 | runner dest | Each runner's destination |
| 62-65 | plays | Plays on batter/runners |
| 66-74 | SB/CS/PO flags | Stolen base/caught stealing/pickoff |
| 75-77 | responsible pitcher | Pitcher responsible for runners |
| 78-79 | new/end game flags | Game start/end indicators |
| 80-82 | pinchrunners | Pinch runner indicators |
| 83-85 | removed runners | Players removed for PR |
| 86 | removed batter | Batter removed for PH |
| 87 | removed batter position | Removed batter's position |
| 88-90 | fielder putouts | Putout fielders |
| 91-95 | fielder assists | Assist fielders |
| 96 | event num | Event number |

### BGAME Tool Fields (81 available)

| Field # | Field Name | Description |
|---------|------------|-------------|
| 0 | game id | Game identifier |
| 1 | date | Game date |
| 2 | game number | 0=single, 1=first DH, 2=second DH |
| 3 | day of week | Day of week |
| 4 | start time | Game start time |
| 5 | DH used flag | Designated hitter used |
| 6 | day/night flag | Day or night game |
| 7-8 | teams | Visiting/home team codes |
| 9 | game site | Ballpark code |
| 10-11 | starting pitchers | Visiting/home starting pitchers |
| 12-17 | umpires | HP to RF umpires |
| 18 | attendance | Attendance figure |
| 19-21 | scorer info | PS scorer, translator, inputter |
| 22-23 | times | Input/edit time |
| 24 | how scored | Scoring method |
| 25 | pitches entered | Pitch data availability |
| 26 | temperature | Game temperature |
| 27-28 | wind | Direction and speed |
| 29-31 | conditions | Field condition, precipitation, sky |
| 32 | time of game | Game duration |
| 33 | number of innings | Innings played |
| 34-41 | final stats | Final scores, hits, errors, LOB |
| 42-45 | pitching | Winning/losing pitchers, save, GW RBI |
| 46-63 | lineups | Visiting/home starting lineups (9 players each with positions) |

### Documentation Source
- Official Retrosheet Documentation: https://www.retrosheet.org/datause.txt
- Event File Format: https://www.retrosheet.org/eventfile.htm

---

## MLB Stats API / GUMBO

### Overview
The MLB Stats API provides live and historical baseball data, including schedules, game feeds, player statistics, and Statcast pitch-level tracking data.

### Base URL
- Production: `https://statsapi.mlb.com/api/v1/`

### Key Endpoints

#### Schedule
- **Endpoint**: `/schedule`
- **Parameters**: `sportId=1`, `date`, `startDate`, `endDate`, `gameType`
- **Returns**: Game schedules with game_pk, teams, venue, status

#### Game Feed (GUMBO)
- **Endpoint**: `/game/{game_pk}/feed/live`
- **Returns**: Complete live game data including:
  - Game info (date, time, venue, weather)
  - Lineups and player data
  - Play-by-play events
  - Pitch-by-pitch data
  - Game state (runners, outs, count)
  - Box scores and statistics

#### Players
- **Endpoint**: `/people/{player_id}`
- **Returns**: Player information including:
  - Personal details (name, birth date, height, weight)
  - Handedness (bats, throws)
  - Current team and position
  - Stats links

#### Teams
- **Endpoint**: `/teams`
- **Parameters**: `sportId=1`, `season`
- **Returns**: Team information including:
  - Team details (name, abbreviation, location)
  - Venue information
  - League and division
  - Spring/regular/postseason info

#### Venues
- **Endpoint**: `/venues`
- **Returns**: Ballpark information including:
  - Venue name and location
  - Capacity and surface type
  - Field dimensions

### Schema in Warehouse

#### raw_mlb Schema
- `live_feed_snapshots`: Raw JSON from game feed endpoint
  - `game_pk`: Integer (primary key)
  - `fetched_at`: Timestamp
  - `raw_payload`: JSONB
  - `request_params`: JSONB
  - `http_status`: Integer
  - `response_time_ms`: Integer
  - `checksum`: TEXT
  - `game_date`: DATE
  - `season`: INTEGER

- `api_teams_snapshots`: Raw JSON from teams endpoint
- `api_venues_snapshots`: Raw JSON from venues endpoint
- `statcast`: Pitch-level Statcast data
- `gameday_xml`: Historical Gameday XML data

#### core Schema (Transformed)
- `live_games`: Canonical live game data
  - `game_pk`: Integer (primary key)
  - `game_date`: DATE
  - `season`: INTEGER
  - `home_team_id`: INTEGER
  - `away_team_id`: INTEGER
  - `venue_id`: INTEGER
  - `game_status`: TEXT
  - `home_score`: INTEGER
  - `away_score`: INTEGER
  - `inning`: INTEGER
  - `inning_half`: TEXT
  - `outs`: INTEGER
  - `runners_on_base`: TEXT
  - `raw_payload`: JSONB (source-preserved)

- `live_events`: Canonical live event data
  - `event_id`: TEXT (primary key)
  - `game_pk`: Integer
  - `inning`: INTEGER
  - `inning_half`: TEXT
  - `event_type`: TEXT
  - `description`: TEXT
  - `raw_play`: JSONB (source-preserved)

### Documentation Source
- MLB Stats API: https://statsapi.mlb.com/docs/
- GitHub Discussions: https://github.com/toddrob99/MLB-StatsAPI

---

## ESPN MLB API

### Overview
ESPN provides MLB data through their public API, including game scores, schedules, player statistics, and team statistics.

### Base URL
- Production: `http://site.api.espn.com/apis/site/v2/sports/baseball/mlb`

### Key Endpoints

#### Scoreboard
- **Endpoint**: `/scoreboard`
- **Parameters**: `dates`, `groups`, `limit`
- **Returns**: Game scores, status, basic game info

#### Schedule
- **Endpoint**: `/scoreboard` (with date parameters)
- **Returns**: Daily schedules with game IDs, teams, times

#### Player Statistics
- **Endpoint**: `/statistics/athlete/{player_id}`
- **Returns**: Season and career statistics for players

#### Team Statistics
- **Endpoint**: `/statistics/team/{team_id}`
- **Returns**: Team statistics and rankings

### Schema in Warehouse

#### raw_espn Schema
- `game_snapshots`: Raw JSON from scoreboard API
  - `id`: SERIAL (primary key)
  - `game_id`: TEXT
  - `game_date`: DATE
  - `season`: INTEGER
  - `fetched_at`: TIMESTAMP
  - `raw_payload`: JSONB
  - `request_params`: JSONB
  - `http_status`: INTEGER
  - `response_time_ms`: INTEGER
  - `checksum`: TEXT
  - `source_name`: TEXT

- `schedule_snapshots`: Raw JSON from schedule API
- `player_stats_snapshots`: Raw JSON from player stats API
- `team_stats_snapshots`: Raw JSON from team stats API

### Data Limitations
- Play-by-play data only available for recent games (2024-2026)
- Historical games (2000-2015) have empty plays arrays
- ESPN Core API v2 plays endpoint returns 404

### Scripts
- `scripts/fetch_espn_mlb.py`: Generalized ESPN data fetcher
- `sql/220_espn_schema.sql`: Schema definition

### Documentation Source
- ESPN API is undocumented public API
- Discovered through network inspection and community research

---

## Statcast

### Overview
Statcast is MLB's advanced tracking system that provides pitch-level data, batted ball metrics, swing mechanics, and defensive statistics.

### Data Access

#### Baseball Savant Website
- **URL**: https://baseballsavant.mlb.com/statcast_search
- **Features**: Interactive query builder for Statcast data
- **Export**: CSV download available

#### Custom Leaderboard API
- **Base URL**: https://baseballsavant.mlb.com/leaderboard/custom
- **Parameters**:
  - `year`: Season year (e.g., 2026)
  - `type`: `batter` or `pitcher`
  - `filter`: Filter criteria
  - `min`: Minimum qualification (e.g., `q` = qualified)
  - `selections`: Comma-separated metric names
  - `chart`: Chart display flag
  - `x`, `y`: Chart axes

#### Example Batter Leaderboard URL
```
https://baseballsavant.mlb.com/leaderboard/custom?year=2026&type=batter&filter=&min=q&selections=player_age,ab,pa,hit,single,double,triple,home_run,strikeout,walk,k_percent,bb_percent,batting_avg,slg_percent,on_base_percent,on_base_plus_slg,isolated_power,babip,b_rbi,b_lob,b_total_bases,r_total_caught_stealing,r_total_stolen_base,exit_velocity_avg,launch_angle_avg,sweet_spot_percent,barrel,hard_hit_percent,swing_percent,whiff_percent&chart=false&x=player_age&y=player_age&r=no&chartType=beeswarm&sort=1&sortDir=desc
```

### Key Metrics

#### Batted Ball Metrics
- `exit_velocity_avg`: Average exit velocity
- `launch_angle_avg`: Average launch angle
- `sweet_spot_percent`: Optimal launch angle percentage
- `barrel`: Barrel percentage
- `barrel_batted_rate`: Barrels per batted ball
- `hard_hit_percent`: Hard-hit ball percentage
- `solidcontact_percent`: Solid contact percentage

#### Swing Mechanics
- `avg_swing_speed`: Average swing speed
- `fast_swing_rate`: Fast swing percentage
- `blasts_contact`: Blast contact percentage
- `squared_up_contact`: Squared up contact percentage
- `avg_swing_length`: Average swing length
- `swords`: Swing length
- `attack_angle`: Average attack angle
- `attack_direction`: Average attack direction
- `ideal_angle_rate`: Ideal angle percentage
- `vertical_swing_path`: Vertical swing path

#### Plate Discipline
- `z_swing_percent`: Zone swing percentage
- `z_swing_miss_percent`: Zone swing and miss percentage
- `oz_swing_percent`: Out-of-zone swing percentage
- `oz_swing_miss_percent`: Out-of-zone swing and miss percentage
- `oz_contact_percent`: Out-of-zone contact percentage
- `out_zone_swing_miss`: Out-of-zone swing and miss
- `out_zone_swing`: Out-of-zone swings
- `out_zone_percent`: Out-of-zone percentage
- `in_zone_swing_miss`: In-zone swing and miss
- `in_zone_swing`: In-zone swings
- `in_zone_percent`: In-zone percentage
- `edge_percent`: Edge percentage
- `whiff_percent`: Whiff percentage
- `swing_percent`: Swing percentage

#### Pitch Classification
- `pitch_count_offspeed`: Offspeed pitch count
- `pitch_count_fastball`: Fastball pitch count
- `pitch_count_breaking`: Breaking ball pitch count
- `pitch_count`: Total pitch count

#### Batted Ball Direction
- `pull_percent`: Pull percentage
- `straightaway_percent`: Straightaway percentage
- `opposite_percent`: Opposite field percentage

#### Batted Ball Type
- `groundballs_percent`: Ground ball percentage
- `flyballs_percent`: Fly ball percentage
- `linedrives_percent`: Line drive percentage
- `popups_percent`: Pop-up percentage

#### Advanced Offensive Metrics
- `xba`: Expected batting average
- `xslg`: Expected slugging percentage
- `woba`: Weighted on-base average
- `xwoba`: Expected weighted on-base average
- `xobp`: Expected on-base percentage
- `xiso`: Expected isolated power
- `wobacon`: WOBA on contact
- `xwobacon`: Expected WOBA on contact

#### Defensive Metrics
- `n_outs_above_average`: Outs above average
- `n_fieldout_5stars`: 5-star field outs
- `n_opp_5stars`: 5-star opportunities
- `n_5star_percent`: 5-star percentage
- `rel_league_reaction_distance`: Relative league reaction distance
- `rel_league_burst_distance`: Relative league burst distance
- `rel_league_routing_distance`: Relative league routing distance
- `rel_league_bootup_distance`: Relative league bootup distance
- `n_bolts`: Bolts (high-effort plays)

#### Baserunning Metrics
- `r_total_stolen_base`: Total stolen bases
- `r_total_caught_stealing`: Total caught stealing
- `r_stolen_base_pct`: Stolen base percentage
- `pop_2b_sba`: Second base attempts
- `pop_2b_sb`: Second base steals
- `pop_2b_cs`: Second base caught stealing
- `pop_3b_sba`: Third base attempts
- `pop_3b_sb`: Third base steals
- `pop_3b_cs`: Third base caught stealing
- `exchange_2b_3b_sba`: 2B to 3B attempts
- `hp_to_1b`: Home to first time

### Schema in Warehouse
- `raw_mlb.statcast`: Pitch-level Statcast data
- Scripts: `scripts/download_statcast_pitch_level.py`, `scripts/external_data/load_statcast.py`

### Documentation Source
- Baseball Savant: https://baseballsavant.mlb.com/
- Statcast Search: https://baseballsavant.mlb.com/statcast_search

---

## Lahman Database

### Overview
The Lahman Baseball Database is a comprehensive collection of statistics covering Major League Baseball from 1871 to the present, maintained by Sean Lahman.

### Data Format
- CSV files for each table
- Annual releases with updated data
- Historical and current season data

### Key Tables

#### People
- `playerID`: Unique player identifier
- `birthYear`, `birthMonth`, `birthDay`: Birth date
- `birthCountry`, `birthState`, `birthCity`: Birth location
- `deathYear`, `deathMonth`, `deathDay`: Death date
- `deathCountry`, `deathState`, `deathCity`: Death location
- `nameFirst`, `nameLast`, `nameGiven`: Player names
- `weight`, `height`: Physical attributes
- `bats`, `throws`: Handedness
- `debut`, `finalGame`: MLB debut and final game dates
- `retroID`: Retrosheet player ID
- `bbrefID`: Baseball Reference player ID

#### Batting
- `playerID`: Player identifier
- `yearID`: Season year
- `stint`: Player stint (multiple stints possible)
- `teamID`, `lgID`: Team and league
- `G`: Games played
- `AB`: At-bats
- `R`: Runs scored
- `H`: Hits
- `2B`, `3B`, `HR`: Doubles, triples, home runs
- `RBI`: Runs batted in
- `SB`, `CS`: Stolen bases, caught stealing
- `BB`: Walks
- `SO`: Strikeouts
- `IBB`: Intentional walks
- `HBP`: Hit by pitch
- `SH`, `SF`: Sacrifice hits, sacrifice flies
- `GIDP`: Grounded into double plays

#### Pitching
- `playerID`: Player identifier
- `yearID`: Season year
- `stint`: Player stint
- `teamID`, `lgID`: Team and league
- `W`, `L`: Wins, losses
- `G`: Games pitched
- `GS`: Games started
- `CG`: Complete games
- `SHO`: Shutouts
- `SV`: Saves
- `IPouts`: Innings pitched (outs)
- `H`: Hits allowed
- `ER`: Earned runs
- `HR`: Home runs allowed
- `BB`, `SO`: Walks, strikeouts
- `BAOpp`: Opponent batting average
- `ERA`: Earned run average
- `IPOuts`: Innings pitched (outs, duplicate field)
- `GF`: Games finished
- `R`: Runs allowed
- `SH`, `SF`: Sacrifice hits, sacrifice flies allowed
- `GIDP`: Grounded into double plays

#### Fielding
- `playerID`: Player identifier
- `yearID`: Season year
- `stint`: Player stint
- `teamID`, `lgID`: Team and league
- `POS`: Position
- `G`: Games played
- `GS`: Games started
- `InnOuts`: Innings played (outs)
- `PO`: Putouts
- `A`: Assists
- `E`: Errors
- `DP`: Double plays
- `PB`: Passed balls (catchers only)
- `WP`: Wild pitches (pitchers only)
- `SB`, `CS`: Stolen bases, caught stealing (catchers only)
- `ZR`: Zone rating

#### Teams
- `yearID`: Season year
- `lgID`: League
- `teamID`, `franchID`: Team and franchise IDs
- `divID`: Division
- `Rank`: League rank
- `G`: Games played
- `Ghome`: Home games
- `W`, `L`: Wins, losses
- `DivWin`: Division winner flag
- `WCWin`: Wild card winner flag
- `LgWin`: League winner flag
- `WSWin`: World Series winner flag
- `R`, `AB`: Runs, at-bats
- `H`, `2B`, `3B`, `HR`: Hits, doubles, triples, home runs
- `BB`, `SO`: Walks, strikeouts
- `SB`, `CS`: Stolen bases, caught stealing
- `HA`, `HRA`: Hits allowed, home runs allowed
- `BB`, `SO`: Walks allowed, strikeouts allowed
- `ERA`: Earned run average
- `park`: Park name
- `attendance`: Attendance
- `BPF`, `PPF`: Park factors

#### Salaries
- `yearID`: Season year
- `teamID`, `lgID`: Team and league
- `playerID`: Player identifier
- `salary`: Player salary

#### Awards
- `playerID`: Player identifier
- `awardID`: Award identifier
- `yearID`: Season year
- `lgID`: League
- `tie`: Tie flag
- `notes`: Notes

#### AllStarFull
- `playerID`: Player identifier
- `yearID`: Season year
- `gameNum`: Game number (1 or 2)
- `gameID`: Game identifier
- `teamID`, `lgID`: Team and league
- `GP`: Games played
- `startingPos`: Starting position

#### Managers
- `playerID`: Manager identifier (links to People table)
- `yearID`: Season year
- `teamID`, `lgID`: Team and league
- `inseason`: In-season flag
- `G`: Games managed
- `W`, `L`: Wins, losses
- `rank`: Team rank
- `plyrMgr`: Player-manager flag

### Schema in Warehouse
- Loaded into `lahman` schema
- Script: `scripts/external_data/load_lahman.py`

### Documentation Source
- Lahman Database: https://www.seanlahman.com/baseball-archive/statistics/
- GitHub Repository: https://github.com/chadwickbureau/lahman

---

## Baseball Reference

### Overview
Baseball Reference provides comprehensive baseball statistics, player biographies, and team histories. It is one of the most widely used baseball statistics websites.

### Data Access

#### Website
- **URL**: https://www.baseball-reference.com/
- **Features**: Interactive tables, player pages, team pages

#### Baseball-Data.com API
- **URL**: https://www.baseballdata.com/
- **Features**: CSV downloads of Baseball Reference data
- **Tables**: Batting, pitching, fielding, team statistics

### Key Data Points

#### Player Statistics
- Season statistics (batting, pitching, fielding)
- Career totals
- Advanced metrics (WAR, OPS+, etc.)
- Split statistics (home/away, vs LHP/RHP)
- Playoff statistics
- Minor league statistics

#### Team Statistics
- Season team statistics
- Franchise history
- Year-by-year records
- Park factors
- Attendance data

#### Player Information
- Biographical data
- Draft information
- Salary history
- Transaction history
- Awards and honors

### Schema in Warehouse
- `raw_external.baseball_data_com`: External Baseball Reference data
- Script: `scripts/external_data/load_baseball_reference.py`

### Documentation Source
- Baseball Reference: https://www.baseball-reference.com/
- Baseball Data: https://www.baseballdata.com/

---

## Chadwick Baseball Bureau

### Overview
The Chadwick Baseball Bureau provides tools and data for parsing and standardizing baseball data, particularly Retrosheet event files.

### Tools

#### cwevent
- **Purpose**: Extract event/play-level rows from Retrosheet event files
- **Output**: CSV with play-by-play data
- **Options**: `-n` for new extracts with column headers

#### cwgame
- **Purpose**: Extract game metadata from Retrosheet event files
- **Output**: CSV with game information
- **Includes**: Lineups, final scores, linescores, managers, umpires

#### cwdaily
- **Purpose**: Generate player game-by-game summaries
- **Output**: CSV with daily batting, pitching, and fielding stats
- **Includes**: Player-level statistics per game

#### cwsub
- **Purpose**: Extract substitution records
- **Output**: CSV with all substitutions

#### cwcomment
- **Purpose**: Extract comments, ejections, and umpire changes
- **Output**: CSV with special comments

#### cwbox
- **Purpose**: Generate boxscore rendering
- **Output**: Text boxscores
- **Use**: Useful for display, not primary data source

### Chadwick Register (Bureau Register)
- **Purpose**: Comprehensive player and team ID mappings
- **Contains**: 
  - Player IDs across systems (Retrosheet, MLB, Baseball Reference, Lahman)
  - Team ID mappings
  - Name standardization
  - Handedness information
- **Usage**: Source of truth for bridge table population

### Schema in Warehouse
- Used via `scripts/populate_bridge_tables.py`
- Downloads Chadwick Register and populates `bridge.player_xref`, `bridge.team_xref`, `bridge.park_xref`

### Documentation Source
- Chadwick Bureau: https://github.com/chadwickbureau/chadwick
- Chadwick Tools Documentation: Included with tool downloads

---

## Bridge Tables

### Purpose
Bridge tables cross-reference IDs between different data sources (Retrosheet, MLB, Lahman, ESPN, Baseball Reference, etc.).

### Schema

#### bridge.player_xref
```sql
CREATE TABLE bridge.player_xref (
    retrosheet_player_id TEXT PRIMARY KEY,
    mlb_player_id INTEGER UNIQUE,
    chadwick_register_id TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    bats TEXT CHECK (bats IN ('L', 'R', 'B', 'U')),
    throws TEXT CHECK (throws IN ('L', 'R', 'U')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

#### bridge.team_xref
```sql
CREATE TABLE bridge.team_xref (
    retrosheet_team_id TEXT PRIMARY KEY,
    mlb_team_id INTEGER UNIQUE,
    team_name TEXT,
    league TEXT,
    division TEXT,
    valid_from_season INTEGER,
    valid_to_season INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

#### bridge.park_xref
```sql
CREATE TABLE bridge.park_xref (
    retrosheet_park_id TEXT PRIMARY KEY,
    mlb_venue_id INTEGER UNIQUE,
    park_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

#### bridge.game_xref
```sql
CREATE TABLE bridge.game_xref (
    retrosheet_game_id TEXT PRIMARY KEY,
    mlb_game_pk INTEGER UNIQUE,
    game_date DATE,
    retrosheet_home_team_id TEXT,
    retrosheet_away_team_id TEXT,
    mlb_home_team_id INTEGER,
    mlb_away_team_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

#### bridge.coach_xref
```sql
CREATE TABLE bridge.coach_xref (
    retrosheet_coach_id TEXT,
    mlb_coach_id TEXT,
    lahman_coach_id TEXT,
    espn_coach_id TEXT,
    source_system TEXT NOT NULL,
    coach_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uk_coach_xref_retrosheet UNIQUE (retrosheet_coach_id),
    CONSTRAINT uk_coach_xref_mlb UNIQUE (mlb_coach_id),
    CONSTRAINT uk_coach_xref_lahman UNIQUE (lahman_coach_id),
    CONSTRAINT uk_coach_xref_espn UNIQUE (espn_coach_id)
);
```

#### bridge.umpire_xref
```sql
CREATE TABLE bridge.umpire_xref (
    retrosheet_umpire_id TEXT,
    mlb_umpire_id TEXT,
    lahman_umpire_id TEXT,
    espn_umpire_id TEXT,
    source_system TEXT NOT NULL,
    umpire_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uk_umpire_xref_retrosheet UNIQUE (retrosheet_umpire_id),
    CONSTRAINT uk_umpire_xref_mlb UNIQUE (mlb_umpire_id),
    CONSTRAINT uk_umpire_xref_lahman UNIQUE (lahman_umpire_id),
    CONSTRAINT uk_umpire_xref_espn UNIQUE (espn_umpire_id)
);
```

#### bridge.external_player_xref
```sql
CREATE TABLE bridge.external_player_xref (
    external_source TEXT NOT NULL,
    external_player_id TEXT NOT NULL,
    retrosheet_player_id TEXT NOT NULL,
    PRIMARY KEY (external_source, external_player_id)
);
```

#### bridge.external_team_xref
```sql
CREATE TABLE bridge.external_team_xref (
    external_source TEXT NOT NULL,
    external_team_id TEXT NOT NULL,
    retrosheet_team_id TEXT NOT NULL,
    PRIMARY KEY (external_source, external_team_id)
);
```

### Population Scripts
- `scripts/populate_bridge_tables.py`: Populates player_xref, team_xref, park_xref from Chadwick Register
- `scripts/bridge/populate_season_aware_team_xref.py`: Adds season-aware columns to team_xref
- `scripts/bridge/populate_external_bridge.py`: Populates external_player_xref and external_team_xref from Statcast, Baseball Reference, Lahman
- `scripts/bridge/populate_coach_umpire_bridge.py`: Populates coach_xref and umpire_xref from Retrosheet

---

## Data Layer Architecture

### Raw Layer
- `raw_retrosheet`: Source-preserved Chadwick extracts and Retrosheet reference tables
- `raw_mlb`: Source-preserved MLB Stats API / GUMBO data
- `raw_espn`: Source-preserved ESPN API data
- `raw_external`: External data sources (Baseball Reference, Baseball-Data.com)

### Bridge Layer
- `bridge.*`: Cross-reference tables between different ID systems
- Enables translation between Retrosheet, MLB, Lahman, ESPN, and other IDs

### Core Layer
- `core.*`: Canonical baseball entities and game-state views
- Shared by historical and live data sources
- Typed and constrained for ML use

### Features Layer
- `features.*`: ML-ready training and inference tables
- Derived from core layer

### Predictions Layer
- `predictions.*`: Model outputs, backtests, and live prediction snapshots

---

## Best Practices

### Data Preservation
- Keep source-preserved raw data
- Do not overwrite or discard raw payloads
- Store request parameters, HTTP status, response time, and checksum

### Schema Design
- Prefer additive migrations over destructive schema changes
- Put database typing, constraints, foreign keys, indexes in core/features/models/predictions
- Use Chadwick-generated headers and documented field names

### ID Mapping
- Use `bridge.player_xref` as canonical source of truth for player ID mappings
- Implement season-aware team bridging for franchise moves
- Filter for valid Retrosheet IDs to avoid null constraint violations

### Reproducibility
- Scripts should run from a clean checkout with documented dependencies
- Database metadata must be enough to regenerate artifacts
- Keep generated data and model binaries out of git

---

## Related Documentation

- `AGENTS.md`: Project mission, non-negotiables, and procedures
- `docs/agents/FILE_INVENTORY.md`: Complete file inventory
- `docs/agents/PROCEDURES.md`: Canonical workflows
- `docs/agents/MODELING_WORKFLOWS.md`: Target/model inventory
- `docs/CORE_SCHEMA.md`: Core schema documentation

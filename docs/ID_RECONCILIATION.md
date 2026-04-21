# ID Reconciliation Methods for Baseball Data Sources

This document compiles research on how the baseball analytics community has reconciled primary keys across different data sources (Retrosheet, ESPN, Lahman, MLB Stats, MLB PBP, etc.).

## Table of Contents

- [Overview](#overview)
- [Key Crosswalk Sources](#key-crosswalk-sources)
- [Player ID Reconciliation](#player-id-reconciliation)
- [Team ID Reconciliation](#team-id-reconciliation)
- [Game ID Reconciliation](#game-id-reconciliation)
- [Park/Venue ID Reconciliation](#parkvenue-id-reconciliation)
- [Common Reconciliation Strategies](#common-reconciliation-strategies)
- [Challenges and Limitations](#challenges-and-limitations)
- [Best Practices](#best-practices)
- [References](#references)

---

## Overview

Every baseball data source assigns its own internal identifier to entities (players, teams, games, parks). These identifiers rarely agree across systems, creating challenges for data integration and cross-referencing. The baseball analytics community has developed several approaches to reconcile these IDs.

### The Problem
- **Retrosheet**: Uses 8-character IDs (first 4 letters of last name + first initial + 3-digit number)
- **MLB Stats API**: Uses integer MLBAM IDs (e.g., 477132 for Clayton Kershaw)
- **Lahman Database**: Uses playerID strings (e.g., "kersc001")
- **Baseball Reference**: Uses player IDs (e.g., "kershcl01")
- **ESPN**: Uses internal IDs (integer format)
- **Fangraphs**: Uses BIS IDs (Baseball Information Solutions)
- **Statcast**: Uses MLBAM IDs

### Why It Matters
Unresolved ID mismatches produce inconsistent player values for the same athlete, surfacing as confusing and contradictory information for end users. Cross-platform matching is essential for:
- Merging historical and live data
- Building comprehensive player databases
- Creating projection aggregations
- Cross-referencing statistics across sources
- Building unified analytics platforms

---

## Key Crosswalk Sources

### Chadwick Register (Recommended)

**Status**: Actively maintained, authoritative source

**Description**: The Chadwick Bureau maintains the most comprehensive and regularly updated crosswalk of baseball player and team IDs across multiple systems.

**URL**: http://chadwick-bureau.com/the-register/

**Coverage**: 
- Player IDs across multiple systems
- Team IDs with historical franchise tracking
- Park/venue mappings
- Name standardization

**ID Systems Covered**:
- Retrosheet IDs
- MLBAM IDs (mlb.com)
- Lahman IDs
- Baseball Reference IDs
- Fangraphs (BIS) IDs
- Baseball Prospectus IDs
- STATS Inc IDs
- And more

**Usage in This Project**:
- Downloaded via `scripts/populate_bridge_tables.py`
- Used to populate `bridge.player_xref`, `bridge.team_xref`, `bridge.park_xref`
- Considered the source of truth for ID mappings

### mlb_rosetta (Discontinued)

**Status**: Discontinued

**Description**: Previously a universal crosswalk of baseball player ID systems. Now points users to the Chadwick Register.

**ID Systems Previously Mapped**:
- `id` - MLBAM ID number (mlb.com URLs)
- `bis_id` - Baseball Information Solutions ID (Fangraphs, Bill James)
- `bis_milb_id` - BIS IDs for minor league players
- `retrosheet_id` - Retrosheet IDs
- `baseball_prospectus_id` - Baseball Prospectus IDs
- `stats_inc_id` - STATS, Inc. IDs
- `baseball_db_id` - Baseball DataBank IDs
- `baseball_reference_id` - Baseball Reference IDs
- `westbay_id` - Westbay IDs for Japanese players
- `japan_npb_id` - Nippon Pro Baseball IDs
- `korea_kbo_id` - Korea Baseball Organization IDs
- `lahman_id` - Lahman ID system

**Note**: Project discontinued; use Chadwick Register instead.

### Lahman Database Crosswalk

**Status**: Embedded in Lahman database

**Description**: The Lahman People table includes a `retroID` field that provides the Retrosheet ID for each player.

**Key Field**: `retroID` in the People table

**Usage**: Can be used to merge Lahman data with Retrosheet data directly via the retrosheet ID.

**Limitation**: Only provides Lahman ↔ Retrosheet mapping, not other systems.

### pybaseball ID System

**Status**: Active Python library

**Description**: The pybaseball library includes a player ID lookup system that maps between player names and various identification codes.

**ID Keys Provided**:
- `key_mlbam` - MLBAM ID
- `key_retro` - Retrosheet ID
- `key_bbref` - Baseball Reference ID
- `key_fangraphs` - Fangraphs ID

**Example**:
```python
# Clayton Kershaw
key_mlbam: 477132
key_retro: kersc001
key_bbref: kershcl01
key_fangraphs: 2036
```

**Usage**: Can be used programmatically to look up IDs by player name.

### baseball_id Library

**Status**: Active GitHub project

**Description**: Maps baseball IDs from a variety of sources (MLB, Yahoo!, CBS, ESPN, etc.)

**Coverage**: 
- Fantasy platform IDs (Yahoo!, CBS, ESPN)
- Statistical database IDs (MLB, Baseball Reference, Fangraphs, Lahman)

**Usage**: Enables cross-referencing data from fantasy sites with statistical databases.

---

## Player ID Reconciliation

### Primary Strategy: Chadwick Register

The Chadwick Register is the recommended authoritative source for player ID reconciliation. It provides:

1. **Comprehensive Coverage**: Maps player IDs across all major baseball data systems
2. **Regular Updates**: Maintained by the Chadwick Bureau with ongoing updates
3. **Name Standardization**: Handles name variations and inconsistencies
4. **Historical Tracking**: Accounts for name changes, position changes, etc.

### Secondary Strategy: Name Matching

When crosswalks are unavailable, name matching is used as a fallback:

#### Fuzzy Name Matching
- Match on last name + first initial
- Use Levenshtein distance for spelling variations
- Handle name changes (maiden names, nicknames)
- Account for diacritics and special characters

#### Additional Attributes
- Birth date (year, month, day)
- Birth location (city, state, country)
- Handedness (bats, throws)
- Physical attributes (height, weight)
- Debut date
- Career span

#### Example Matching Logic
```python
# Match players by name + birth year + handedness
def match_player(last_name, first_initial, birth_year, bats, throws):
    candidates = query_players_by_name(last_name, first_initial)
    for candidate in candidates:
        if (candidate.birth_year == birth_year and
            candidate.bats == bats and
            candidate.throws == throws):
            return candidate
    return None
```

### Lahman ↔ Retrosheet Direct Mapping

The Lahman database includes `retroID` in the People table, enabling direct joins:

```sql
-- Join Lahman batting with Retrosheet events
SELECT b.*, e.*
FROM lahman.batting b
JOIN lahman.people p ON b.playerID = p.playerID
JOIN retrosheet.events e ON p.retroID = e.retrosheet_id
WHERE b.yearID = e.year
```

### MLBAM ID as Universal Key

Many modern systems use MLBAM IDs as a common identifier:
- MLB Stats API
- Statcast
- Baseball Savant
- mlb.com player pages

This makes MLBAM ID a good "universal" key for modern data (post-2000s).

### Fantasy Platform ID Mapping

Fantasy platforms (Yahoo!, CBS, ESPN) use their own internal IDs. Reconciliation requires:

1. **Name Matching**: Match player names across platforms
2. **Team Matching**: Match team abbreviations
3. **Position Matching**: Match position designations
3. **Season Matching**: Match season-specific rosters

The `baseball_id` library provides pre-built mappings for fantasy platforms.

---

## Team ID Reconciliation

### Challenges

Team ID reconciliation is complicated by:
- **Franchise Moves**: Teams relocate (Montreal Expos → Washington Nationals)
- **Name Changes**: Team names change over time (Florida Marlins → Miami Marlins)
- **League Realignment**: Teams change leagues/divisions
- **Abbreviation Variations**: Different abbreviations across systems

### Primary Strategy: Season-Aware Mapping

The recommended approach is season-aware team mapping:

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

**Example Entries**:
```sql
-- Montreal Expos (1969-2004)
('MON', 120, 'Montreal Expos', 'NL', 'East', 1969, 2004)

-- Washington Nationals (2005-present)
('WSN', 120, 'Washington Nationals', 'NL', 'East', 2005, NULL)

-- Florida Marlins (1993-2011)
('FLO', 146, 'Florida Marlins', 'NL', 'East', 1993, 2011)

-- Miami Marlins (2012-present)
('MIA', 146, 'Miami Marlins', 'NL', 'East', 2012, NULL)
```

### Franchise Tracking

Track franchise moves and name changes:

1. **Franchise ID**: Assign a persistent franchise ID
2. **Team ID**: Assign season-specific team IDs
3. **Location History**: Track city/state changes
4. **Name History**: Track name changes
5. **League/Division History**: Track realignment

### Common Team Abbreviations

Different systems use different abbreviations:

| Retrosheet | MLB Stats | Baseball Reference | ESPN |
|------------|------------|-------------------|------|
| BOS | 111 | BOS | 2 |
| NYY | 147 | NYY | 17 |
| LAA | 108 | LAA | 3 |
| LAN | 119 | LAD | 19 |
| CHC | 112 | CHC | 16 |

### Abbreviation Mapping Tables

Create mapping tables for abbreviations:

```sql
CREATE TABLE bridge.team_abbreviation_xref (
    source_system TEXT NOT NULL,
    abbreviation TEXT NOT NULL,
    retrosheet_team_id TEXT NOT NULL,
    valid_from_season INTEGER,
    valid_to_season INTEGER,
    PRIMARY KEY (source_system, abbreviation, valid_from_season)
);
```

---

## Game ID Reconciliation

### Challenges

Game ID reconciliation is particularly challenging because:
- Different systems use different game ID formats
- Game IDs may not be consistent across systems
- Doubleheaders create multiple games on same date
- Tiebreaker games and playoff games have special handling

### Primary Strategy: Multi-Field Matching

Game reconciliation typically requires matching on multiple fields:

1. **Date**: Game date
2. **Teams**: Home and away team IDs
3. **Game Number**: 0=single, 1=first of DH, 2=second of DH
4. **League**: League identifier (if needed for disambiguation)

### Example Matching Logic

```sql
-- Match Retrosheet game to MLB game
SELECT r.game_id AS retrosheet_game_id,
       m.game_pk AS mlb_game_pk
FROM retrosheet.games r
JOIN mlb.schedule m ON 
    r.game_date = m.game_date AND
    r.home_team_id = bridge.retrosheet_to_mlb_team(r.home_team_id) AND
    r.away_team_id = bridge.retrosheet_to_mlb_team(r.away_team_id) AND
    r.game_number = m.game_number;
```

### Retrosheet Game ID Format

Retrosheet game IDs encode game information:
- Format: `HHHYYMMDDN`
- `HHH`: Home team abbreviation (3 chars)
- `YY`: Last two digits of year
- `MM`: Month
- `DD`: Day
- `N`: Game number (0=single, 1=first DH, 2=second DH)

Example: `BAL198304040` = Baltimore Orioles, April 4, 1983, game 0

### MLB Stats API Game PK

MLB Stats API uses integer game PKs:
- Format: Integer (e.g., 632850)
- Not human-readable
- Must be looked up via schedule API
- Unique per game

### Matching Strategy

1. **Primary Match**: Date + home team + away team + game number
2. **Secondary Match**: Date + home team + away team (if game number unknown)
3. **Fallback**: Date + one team + score (if partial data available)

### Doubleheader Handling

Critical to distinguish doubleheader games:
- Check game number field
- Verify start times if available
- Cross-reference with attendance or other metadata

---

## Park/Venue ID Reconciliation

### Challenges

Park/venue ID reconciliation is complicated by:
- **Name Changes**: Park names change (e.g., corporate sponsorship)
- **Multiple Names**: Same park may have multiple names simultaneously
- **Renovations**: Parks may be renovated but retain same ID
- **Location Changes**: Parks may be relocated but keep same name

### Primary Strategy: Geographic + Historical Matching

Match parks using:
1. **Location**: City, state, country
2. **Team**: Primary team that uses the park
3. **Time Period**: Years when park was active
4. **Name Variants**: All known names for the park

### Chadwick Register Park Mapping

The Chadwick Register includes park/venue mappings:
- Retrosheet park IDs
- MLB venue IDs
- Park names
- Geographic location
- Active years

### Example Park Mappings

| Retrosheet Park ID | MLB Venue ID | Park Name | City | Active Years |
|-------------------|--------------|-----------|------|-------------|
| BOS01 | 3 | Fenway Park | Boston | 1912-present |
| NYC16 | 31 | Yankee Stadium | New York | 2009-present |
| NYC17 | 3288 | Yankee Stadium (old) | New York | 1923-2008 |
| CHI12 | 17 | Wrigley Field | Chicago | 1914-present |

### Season-Aware Park Mapping

Similar to teams, parks may need season-aware mapping for name changes:

```sql
CREATE TABLE bridge.park_xref (
    retrosheet_park_id TEXT PRIMARY KEY,
    mlb_venue_id INTEGER UNIQUE,
    park_name TEXT,
    city TEXT,
    state TEXT,
    valid_from_season INTEGER,
    valid_to_season INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

---

## Common Reconciliation Strategies

### 1. Hierarchical Matching

Use a hierarchy of matching strategies from most reliable to least:

1. **Direct Crosswalk Lookup** (Chadwick Register)
2. **Exact ID Match** (if IDs are compatible)
3. **Multi-Field Exact Match** (date + teams + game number)
4. **Fuzzy Name Match** (with confidence score)
5. **Manual Review** (for low-confidence matches)

### 2. Confidence Scoring

Assign confidence scores to matches:

```python
def calculate_confidence(match_type, attributes_matched):
    score = 0
    
    if match_type == 'crosswalk':
        score = 100
    elif match_type == 'exact_id':
        score = 95
    elif match_type == 'multi_field':
        score = 90 + (attributes_matched * 2)
    elif match_type == 'fuzzy_name':
        score = 50 + (name_similarity * 40)
    
    return score
```

### 3. Manual Review Queue

Create a review queue for low-confidence matches:

```sql
CREATE TABLE reconciliation.review_queue (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_system TEXT NOT NULL,
    proposed_match_id TEXT,
    confidence_score INTEGER,
    match_attributes JSONB,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewer TEXT,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### 4. Audit Trail

Maintain an audit trail of all reconciliation decisions:

```sql
CREATE TABLE reconciliation.audit_log (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_system TEXT NOT NULL,
    match_id TEXT,
    match_method TEXT NOT NULL,
    confidence_score INTEGER,
    matched_by TEXT NOT NULL,
    matched_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### 5. Periodic Reconciliation

Reconcile data periodically to:
- Catch new players/teams
- Update mappings for franchise moves
- Correct errors in previous mappings
- Incorporate new data sources

---

## Challenges and Limitations

### Name Variations

Player names can vary across sources:
- **Spelling variations**: "Jon" vs "Jonathan"
- **Nicknames**: "A-Rod" vs "Alex Rodriguez"
- **Diactrics**: "José" vs "Jose"
- **Name changes**: Marriage, legal name changes

### Duplicate Names

Multiple players can have the same name:
- **Common names**: Multiple "John Smith"s
- **Father-son**: Same name, different eras
- **Name changes**: Player changes name mid-career

### Missing Data

Some sources may be missing key attributes:
- Birth dates missing for historical players
- Handedness unknown for some players
- Debut dates missing
- Physical attributes unavailable

### Historical Coverage

Historical data has limitations:
- **Pre-1900s**: Limited data availability
- **Negro Leagues**: Separate ID systems, incomplete coverage
- **Minor Leagues**: Inconsistent ID systems
- **International Leagues**: Different ID conventions

### System-Specific Issues

Each data source has unique issues:
- **Retrosheet**: ID format changed over time
- **Lahman**: Some retroIDs missing or incorrect
- **MLB Stats API**: IDs only available for modern era
- **ESPN**: IDs change periodically, undocumented

---

## Best Practices

### 1. Use Authoritative Crosswalks First

Always use the Chadwick Register as the primary source for ID mappings. It is:
- Actively maintained
- Comprehensive
- Standardized across the industry
- Free for research purposes

### 2. Implement Season-Aware Mappings

For teams and parks, use season-aware mappings to handle:
- Franchise moves
- Name changes
- League realignment
- Park renovations

### 3. Maintain Audit Trails

Track all reconciliation decisions including:
- Match method used
- Confidence score
- Who made the decision
- When it was made
- Reasoning for the decision

### 4. Use Multi-Field Matching

Never rely on a single field for matching. Use multiple attributes:
- Players: Name + birth date + handedness + debut
- Teams: Name + location + league + era
- Games: Date + teams + game number
- Parks: Location + team + era

### 5. Implement Confidence Scoring

Assign confidence scores to all matches:
- High confidence (>90%): Crosswalk or exact ID match
- Medium confidence (70-90%): Multi-field match
- Low confidence (<70%): Fuzzy match or partial match

### 6. Manual Review Low-Confidence Matches

Create a review process for low-confidence matches:
- Queue for manual review
- Provide supporting evidence
- Track reviewer decisions
- Learn from corrections to improve matching algorithms

### 7. Periodic Validation

Regularly validate your mappings:
- Sample check matches
- Verify against authoritative sources
- Check for orphaned IDs
- Update mappings as needed

### 8. Document Your Process

Document your reconciliation process including:
- Crosswalk sources used
- Matching algorithms implemented
- Confidence thresholds
- Review procedures
- Known limitations

### 9. Handle Edge Cases

Explicitly handle edge cases:
- Doubleheaders
- Tiebreaker games
- All-Star games
- Playoff games
- Exhibition games
- Players with same name
- Franchise moves
- Park name changes

### 10. Preserve Source IDs

Always preserve source IDs in addition to canonical IDs:
- Store all source IDs in bridge tables
- Maintain reverse mappings
- Enable traceability back to original sources

---

## References

### Primary Sources

1. **Chadwick Register**: http://chadwick-bureau.com/the-register/
   - Authoritative crosswalk for player and team IDs
   - Actively maintained by Chadwick Bureau

2. **mlb_rosetta** (Discontinued): https://github.com/geoffharcourt/mlb_rosetta
   - Historical reference for ID systems
   - Now points to Chadwick Register

3. **Lahman Database**: https://www.seanlahman.com/baseball-archive/statistics/
   - Includes retroID field in People table
   - Direct Lahman ↔ Retrosheet mapping

4. **pybaseball**: https://pypi.org/project/pybaseball/
   - Python library with ID lookup system
   - Maps player names to multiple ID systems

5. **baseball_id**: https://github.com/spilchen/baseball_id
   - Maps fantasy platform IDs to statistical databases
   - Covers Yahoo!, CBS, ESPN, etc.

### Community Discussions

1. **Reddit - r/Sabermetrics**: "Matching Lahman and Retrosheet?"
   - Discussion on Lahman's retroID field
   - Community insights on ID matching

2. **Fantasy Player Database**: "Player ID Systems and Cross-Platform Data Matching"
   - Article on cross-platform ID matching challenges
   - Discusses fantasy platform ID systems

3. **Smart Fantasy Baseball**: "Everything You Need to Know About the Player ID Map"
   - Article on player ID maps for fantasy baseball
   - Practical advice on ID reconciliation

4. **Major Saber**: "Mapping MLBAM Player IDs to the Lahman Database"
   - Blog post on MLBAM ↔ Lahman mapping
   - R code examples for merging data

### Academic and Industry Sources

1. **SABR - Society for American Baseball Research**
   - "A Guide to Sabermetric Research: How to Find Raw Data"
   - "How to Do Baseball Research: Statistical Databases and Websites"

2. **Sportradar Documentation**
   - "ID Handling" for MLB data
   - UUID-based matching approach

3. **SportsDataIO**
   - Baseball data provider documentation
   - ID system descriptions

---

## Implementation in This Project

### Current Implementation

This project uses the following reconciliation approach:

1. **Primary Crosswalk**: Chadwick Register via `scripts/populate_bridge_tables.py`
2. **Bridge Tables**: 
   - `bridge.player_xref`: Player ID mappings
   - `bridge.team_xref`: Team ID mappings (with season-aware columns)
   - `bridge.park_xref`: Park/venue ID mappings
   - `bridge.game_xref`: Game ID mappings
   - `bridge.coach_xref`: Coach ID mappings
   - `bridge.umpire_xref`: Umpire ID mappings
   - `bridge.external_player_xref`: External player ID mappings
   - `bridge.external_team_xref`: External team ID mappings

3. **Season-Aware Team Mapping**: `scripts/bridge/populate_season_aware_team_xref.py`
   - Adds `valid_from_season` and `valid_to_season` columns
   - Handles franchise moves (Expos → Nationals, Marlins → Marlins)

4. **External Bridge Population**: `scripts/bridge/populate_external_bridge.py`
   - Uses Statcast, Baseball Reference, Lahman data
   - Joins with `bridge.player_xref` as source of truth
   - Filters for valid Retrosheet IDs

### Recommended Improvements

Based on community research, consider:

1. **Enhanced Game Matching**: Implement multi-field game matching with confidence scoring
2. **Manual Review Queue**: Create review process for low-confidence matches
3. **Audit Trail**: Add audit logging for all reconciliation decisions
4. **Periodic Validation**: Implement scheduled validation of mappings
5. **ESPN ID Integration**: Add ESPN IDs to bridge tables when reliable mapping available
6. **Negro Leagues**: Consider adding Negro Leagues ID mappings
7. **International Leagues**: Add mappings for NPB, KBO, etc. if needed

### Scripts and Procedures

See `docs/agents/PROCEDURES.md` for detailed procedures on:
- Bridge table population
- Season-aware team mapping
- External bridge population
- Coach and umpire bridge population

---

## Conclusion

ID reconciliation across baseball data sources is a complex but well-understood problem in the baseball analytics community. The key insights are:

1. **Use authoritative crosswalks** (Chadwick Register) as the primary source
2. **Implement season-aware mappings** for teams and parks to handle historical changes
3. **Use multi-field matching** with confidence scoring for entities without crosswalks
4. **Maintain audit trails** and manual review processes for quality assurance
5. **Preserve source IDs** to enable traceability and debugging

By following these best practices, you can build a robust ID reconciliation system that enables seamless integration of data from multiple baseball sources.

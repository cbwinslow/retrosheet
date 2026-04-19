# Issue #9: Comprehensive Retrosheet Data Acquisition

**Status**: Completed
**Date**: April 18, 2026
**Related Docs**: 
- [AGENTS.md](../AGENTS.md) - Updated with new data sources
- [docs/agents/FILE_INVENTORY.md](../docs/agents/FILE_INVENTORY.md) - Added Retrosheet data files section

## Overview

Acquired comprehensive Retrosheet data from retrosheet.org to enrich the baseball prediction warehouse. Total data downloaded: 1,748.81 MB across 8 zip files covering historical data from 1898-2025.

## Data Files Downloaded

### 1. retrosheet_alldata.zip (326 MB)
- URL: https://retrosheet.org/downloads/alldata.zip
- Size: 342,011,604 bytes
- Contents: Traditional Retrosheet data (event files, box-score files, game logs, etc.)
- Purpose: Core play-by-play and game-level data for historical analysis

### 2. retrosheet_biodata.zip (1.3 MB)
- URL: https://www.retrosheet.org/downloads/biodata.zip
- Size: 1,411,227 bytes
- Contents: Biographical data including biofile0.csv, relatives.csv, coaches0.csv, ballparks0.csv, managers0.csv, teams0.csv, umpires0.csv
- Purpose: Player, manager, coach, umpire biographical information and team/park directories

### 3. retrosheet_csv_downloads.zip (710 MB)
- URL: https://www.retrosheet.org/downloads/csvdownloads.zip
- Size: 745,059,614 bytes
- Contents: CSV files with daily logs, parsed play-by-play data, player/team statistics (1898-2025)
- Files: allplayers.csv, gameinfo.csv, teamstats.csv, batting.csv, pitching.csv, fielding.csv, plays.csv
- Purpose: ML-ready structured data for feature engineering and model training

### 4. retrosheet_allstar.zip (630 KB)
- URL: https://www.retrosheet.org/downloads/allstar.zip
- Size: 644,947 bytes
- Contents: All-Star game data (1933-2025)
- Purpose: Special event data for analysis and feature engineering

### 5. retrosheet_postseason.zip (7.3 MB)
- URL: https://www.retrosheet.org/downloads/postseason.zip
- Size: 7,643,026 bytes
- Contents: Postseason game data (1903-2025)
- Purpose: Playoff and World Series data for high-stakes game analysis

### 6. retrosheet_negroleagues.zip (6.9 MB)
- URL: https://www.retrosheet.org/downloads/negroleagues.zip
- Size: 7,258,475 bytes
- Contents: Negro Leagues data (1903-1962)
- Purpose: Historical Negro Leagues data for comprehensive baseball history

### 7. retrosheet_regular.zip (696 MB)
- URL: https://www.retrosheet.org/downloads/regular.zip
- Size: 729,596,108 bytes
- Contents: Regular season games (1898-2025, includes tiebreaker playoffs)
- Purpose: Complete regular season game dataset

### 8. retrosheet_tiebreakers.zip (127 KB)
- URL: https://www.retrosheet.org/downloads/tiebreakers.zip
- Size: 130,530 bytes
- Contents: Tiebreaker playoff games (1946-2018)
- Purpose: Special tiebreaker game data for edge case analysis

## Database Monitoring Records

All downloads recorded in `raw_retrosheet.ingest_runs` table with run IDs:
- Run ID 27: retrosheet_alldata
- Run ID 28: retrosheet_biodata
- Run ID 29: retrosheet_csv_downloads
- Run ID 30: retrosheet_allstar
- Run ID 31: retrosheet_postseason
- Run ID 32: retrosheet_negroleagues
- Run ID 33: retrosheet_regular
- Run ID 34: retrosheet_tiebreakers

Script used: `scripts/record_retrosheet_downloads.py`
Download method: wget command-line tool
Download date: 2026-04-18

## Data Storage Location

All files stored in: `/home/cbwinslow/workspace/retrosheet/data/`

## Completed Work

### Documentation Updates
- Updated [AGENTS.md](../AGENTS.md) Data Layers section with comprehensive Retrosheet data description
- Updated [AGENTS.md](../AGENTS.md) Recommended Workflow to include `record_retrosheet_downloads.py` step
- Updated [docs/agents/FILE_INVENTORY.md](../docs/agents/FILE_INVENTORY.md) with new Retrosheet Data Files section
- Updated [docs/agents/FILE_INVENTORY.md](../docs/agents/FILE_INVENTORY.md) scripts section with `record_retrosheet_downloads.py`

### Letta Memory
Created comprehensive memory documenting all aspects of the data acquisition including file sizes, URLs, contents, and monitoring records.

## Next Steps

1. Extract and organize downloaded data
2. Create database schema for new data types (All-Star, Postseason, Negro Leagues, Tiebreakers)
3. Develop ETL scripts to load data into warehouse
4. Update feature engineering pipelines with new data sources
5. Document data schemas and relationships in docs/agents/

## Notes

- Data is source-preserved in zip files - no extraction or transformation yet
- Monitoring table successfully populated with download records
- All data downloaded from official Retrosheet sources
- Data includes coverage from 1898-2025 with special collections for Negro Leagues and postseason

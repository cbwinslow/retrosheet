# MLB Data API Documentation

## Overview

- **Getting Started**
  - 1. Request Structure
  - 2. Example Request
  - 3. Using col_in & col_ex

## Player Data

- **Search For Player(s)**: GET /json/named.search_player_all.bam
- **Get Player Details**: GET /json/named.player_info.bam
- **Get Teams Played For**: GET /json/named.player_teams.bam

## Stats Data

- **Season Hitting Stats**: GET /json/named.sport_hitting_tm.bam
- **Season Pitching Stats**: GET /json/named.sport_pitching_tm.bam
- **Career Hitting Stats**: GET /json/named.sport_career_hitting.bam
- **Career Pitching Stats**: GET /json/named.sport_career_pitching.bam
- **League Hitting Stats**: GET /json/named.sport_career_hitting_lg.bam
- **League Pitching Stats**: GET /json/named.sport_career_pitching_lg.bam
- **Projected Pitching Stats**: GET /json/named.proj_pecota_pitching.bam
- **Projected Hitting Stats**: GET /json/named.proj_pecota_batting.bam

## Team Data

- **Get Teams By Season**: GET /json/named.team_all_season.bam
- **Get 40-Man Roster**: GET /json/named.roster_40.bam
- **Get Roster By Seasons**: GET /json/named.roster_team_alltime.bam

## Game Data

- **Get Info Per Game Type**: GET /json/named.org_game_type_date_info.bam

## Reports

- **Get Transactions Over Period**: GET /json/named.transaction_all.bam
- **Get Broadcasts Over Period**: GET /json/named.mlb_broadcast_info.bam
- **Get Current Injuries**: GET /fantasylookup/json/json/named.wsfb_news_injury.bam
- **Get Hitting Leaders**: GET /json/named.leader_hitting_repeater.bam
- **Get Pitching Leaders**: GET /json/named.leader_pitching_repeater.bam

## Base URL
http://lookup-service-prod.mlb.com

## Notes
All data is property of MLB/MLB Advanced Media. Refer to their terms of use before using in projects.
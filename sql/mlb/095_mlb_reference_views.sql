-- File: sql/mlb/095_mlb_reference_views.sql
-- Purpose: Parse MLB API reference snapshots into relational views
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS core;

CREATE OR REPLACE VIEW core.mlb_api_teams AS
WITH latest AS (
    SELECT DISTINCT ON (season, resource_key)
        season,
        payload
    FROM raw_mlb.reference_snapshots
    WHERE
        endpoint_family = 'teams'
        AND http_status = 200
    ORDER BY season ASC, resource_key ASC, fetched_at DESC, snapshot_id DESC
)

SELECT
    latest.season,
    (team ->> 'id')::bigint AS mlb_team_id,
    (team -> 'venue' ->> 'id')::bigint AS venue_id,
    team AS raw_team,
    team ->> 'name' AS team_name,
    team ->> 'teamCode' AS team_code,
    team ->> 'fileCode' AS file_code,
    team ->> 'abbreviation' AS abbreviation,
    team ->> 'teamName' AS team_nickname,
    team ->> 'locationName' AS location_name,
    team ->> 'shortName' AS short_name,
    team -> 'league' ->> 'id' AS league_id,
    team -> 'league' ->> 'name' AS league_name,
    team -> 'division' ->> 'id' AS division_id,
    team -> 'division' ->> 'name' AS division_name,
    team -> 'venue' ->> 'name' AS venue_name,
    COALESCE((team ->> 'active')::boolean, true) AS is_active
FROM latest
CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(latest.payload -> 'teams') AS team;

CREATE OR REPLACE VIEW core.mlb_api_team_rosters AS
WITH latest AS (
    SELECT DISTINCT ON (season, resource_key)
        season,
        resource_key,
        payload
    FROM raw_mlb.reference_snapshots
    WHERE
        endpoint_family = 'rosters'
        AND http_status = 200
    ORDER BY season ASC, resource_key ASC, fetched_at DESC, snapshot_id DESC
)

SELECT
    latest.season,
    SPLIT_PART(latest.resource_key, ':', 4)::bigint AS mlb_team_id,
    (roster_entry -> 'person' ->> 'id')::bigint AS mlb_player_id,
    roster_entry AS raw_roster_entry,
    roster_entry -> 'person' ->> 'fullName' AS player_name,
    roster_entry ->> 'jerseyNumber' AS jersey_number,
    roster_entry -> 'position' ->> 'code' AS position_code,
    roster_entry -> 'position' ->> 'name' AS position_name,
    roster_entry -> 'position' ->> 'abbreviation' AS position_abbreviation,
    roster_entry -> 'status' ->> 'code' AS roster_status_code,
    roster_entry -> 'status' ->> 'description' AS roster_status_description
FROM latest
CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(latest.payload -> 'roster') AS roster_entry;

CREATE OR REPLACE VIEW core.mlb_api_players AS
WITH latest AS (
    SELECT DISTINCT ON (resource_key)
        resource_key,
        season,
        payload
    FROM raw_mlb.reference_snapshots
    WHERE
        endpoint_family = 'people'
        AND http_status = 200
    ORDER BY resource_key ASC, fetched_at DESC, snapshot_id DESC
)

SELECT DISTINCT ON ((person ->> 'id'))
    latest.season,
    (person ->> 'id')::bigint AS mlb_player_id,
    (person -> 'currentTeam' ->> 'id')::bigint AS current_team_id,
    person AS raw_person,
    person ->> 'fullName' AS full_name,
    person ->> 'firstName' AS first_name,
    person ->> 'lastName' AS last_name,
    person ->> 'primaryNumber' AS primary_number,
    person ->> 'birthDate' AS birth_date_text,
    person ->> 'currentAge' AS current_age_text,
    person ->> 'height' AS height_text,
    person ->> 'weight' AS weight_text,
    person -> 'batSide' ->> 'code' AS bat_side,
    person -> 'pitchHand' ->> 'code' AS pitch_hand,
    person -> 'primaryPosition' ->> 'code' AS primary_position_code,
    person -> 'primaryPosition' ->> 'name' AS primary_position_name,
    person -> 'primaryPosition' ->> 'abbreviation' AS primary_position_abbreviation,
    COALESCE((person ->> 'active')::boolean, true) AS is_active
FROM latest
CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(latest.payload -> 'people') AS person
ORDER BY (person ->> 'id'), latest.season DESC NULLS LAST;

CREATE OR REPLACE VIEW core.mlb_api_venues AS
WITH latest AS (
    SELECT DISTINCT ON (resource_key)
        season,
        resource_key,
        payload
    FROM raw_mlb.reference_snapshots
    WHERE
        endpoint_family = 'venues'
        AND http_status = 200
    ORDER BY resource_key ASC, fetched_at DESC, snapshot_id DESC
)

SELECT
    latest.season,
    (venue ->> 'id')::bigint AS venue_id,
    venue AS raw_venue,
    venue ->> 'name' AS venue_name,
    venue -> 'location' ->> 'city' AS city,
    venue -> 'location' ->> 'state' AS state,
    venue -> 'location' ->> 'stateAbbrev' AS state_abbrev,
    venue -> 'location' ->> 'country' AS country,
    venue -> 'timeZone' ->> 'id' AS time_zone_id,
    venue -> 'timeZone' ->> 'tz' AS time_zone_abbrev,
    venue -> 'fieldInfo' ->> 'capacity' AS capacity_text,
    venue -> 'fieldInfo' ->> 'turfType' AS turf_type,
    venue -> 'fieldInfo' ->> 'roofType' AS roof_type,
    venue -> 'fieldInfo' ->> 'leftLine' AS left_line_text,
    venue -> 'fieldInfo' ->> 'leftCenter' AS left_center_text,
    venue -> 'fieldInfo' ->> 'center' AS center_text,
    venue -> 'fieldInfo' ->> 'rightCenter' AS right_center_text,
    venue -> 'fieldInfo' ->> 'rightLine' AS right_line_text
FROM latest
CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(latest.payload -> 'venues') AS venue;

CREATE OR REPLACE VIEW core.mlb_api_standings AS
WITH latest AS (
    SELECT DISTINCT ON (season, resource_key)
        season,
        payload
    FROM raw_mlb.reference_snapshots
    WHERE
        endpoint_family = 'standings'
        AND http_status = 200
    ORDER BY season ASC, resource_key ASC, fetched_at DESC, snapshot_id DESC
)

SELECT
    latest.season,
    (record -> 'league' ->> 'id')::bigint AS league_id,
    (record -> 'division' ->> 'id')::bigint AS division_id,
    (team_record -> 'team' ->> 'id')::bigint AS mlb_team_id,
    (team_record ->> 'wins')::integer AS wins,
    (team_record ->> 'losses')::integer AS losses,
    (team_record ->> 'gamesPlayed')::integer AS games_played,
    (team_record ->> 'runsScored')::integer AS runs_scored,
    (team_record ->> 'runsAllowed')::integer AS runs_allowed,
    (team_record ->> 'divisionRank')::integer AS division_rank,
    team_record AS raw_team_record,
    record -> 'league' ->> 'name' AS league_name,
    record -> 'division' ->> 'name' AS division_name,
    team_record -> 'team' ->> 'name' AS team_name,
    team_record ->> 'winningPercentage' AS winning_percentage_text,
    team_record ->> 'runDifferential' AS run_differential_text
FROM latest
CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(latest.payload -> 'records') AS record
CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(record -> 'teamRecords') AS team_record;


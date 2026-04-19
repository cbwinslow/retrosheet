-- =============================================================================
-- External Data Mart Definitions
-- =============================================================================
-- This file defines schemas and tables for supplemental free data sources that
-- are ingested into their own data marts. The tables are kept separate from
-- the core Retrosheet warehouse and later joined via bridge tables or view
-- definitions.
-- =============================================================================

-- 1. Statcast raw data (pitch‑level metrics)
CREATE SCHEMA IF NOT EXISTS raw_mlb;
CREATE TABLE IF NOT EXISTS raw_mlb.statcast (
    pitch_type TEXT,
    game_date TEXT,
    release_speed REAL,
    release_pos_x REAL,
    release_pos_z REAL,
    player_name TEXT,
    batter INT,
    pitcher INT,
    events TEXT,
    description TEXT,
    spin_dir REAL,
    spin_rate_deprecated REAL,
    break_angle_deprecated REAL,
    break_length_deprecated REAL,
    zone TEXT,
    des TEXT,
    game_type TEXT,
    stand TEXT,
    p_throws TEXT,
    home_team TEXT,
    away_team TEXT,
    type TEXT,
    hit_location TEXT,
    bb_type TEXT,
    balls INT,
    strikes INT,
    game_year INT,
    pfx_x REAL,
    pfx_z REAL,
    plate_x REAL,
    plate_z REAL,
    on_3b INT,
    on_2b INT,
    on_1b INT,
    outs_when_up INT,
    inning INT,
    inning_topbot TEXT,
    hc_x REAL,
    hc_y REAL,
    tfs_deprecated TEXT,
    tfs_zulu_deprecated TEXT,
    umpire TEXT,
    sv_id TEXT,
    vx0 REAL,
    vy0 REAL,
    vz0 REAL,
    ax REAL,
    ay REAL,
    az REAL,
    sz_top REAL,
    sz_bot REAL,
    hit_distance_sc REAL,
    launch_speed REAL,
    launch_angle REAL,
    effective_speed REAL,
    release_spin_rate REAL,
    release_extension REAL,
    game_pk BIGINT NOT NULL,
    fielder_2 INT,
    fielder_3 INT,
    fielder_4 INT,
    fielder_5 INT,
    fielder_6 INT,
    fielder_7 INT,
    fielder_8 INT,
    fielder_9 INT,
    release_pos_y REAL,
    estimated_ba_using_speedangle REAL,
    estimated_woba_using_speedangle REAL,
    woba_value REAL,
    woba_denom REAL,
    babip_value REAL,
    iso_value REAL,
    launch_speed_angle REAL,
    at_bat_number INT,
    pitch_number INT,
    pitch_name TEXT,
    home_score INT,
    away_score INT,
    bat_score INT,
    fld_score INT,
    post_away_score INT,
    post_home_score INT,
    post_bat_score INT,
    post_fld_score INT,
    if_fielding_alignment TEXT,
    of_fielding_alignment TEXT,
    spin_axis REAL,
    delta_home_win_exp REAL,
    delta_run_exp REAL,
    bat_speed REAL,
    swing_length REAL,
    estimated_slg_using_speedangle REAL,
    delta_pitcher_run_exp REAL,
    hyper_speed REAL,
    home_score_diff INT,
    bat_score_diff INT,
    home_win_exp REAL,
    bat_win_exp REAL,
    age_pit_legacy INT,
    age_bat_legacy INT,
    age_pit INT,
    age_bat INT,
    n_thruorder_pitcher INT,
    n_priorpa_thisgame_player_at_bat INT,
    pitcher_days_since_prev_game INT,
    batter_days_since_prev_game INT,
    pitcher_days_until_next_game INT,
    batter_days_until_next_game INT,
    api_break_z_with_gravity REAL,
    api_break_x_arm REAL,
    api_break_x_batter_in REAL,
    arm_angle REAL,
    attack_angle REAL,
    attack_direction REAL,
    swing_path_tilt REAL,
    intercept_ball_minus_batter_pos_x_inches REAL,
    intercept_ball_minus_batter_pos_y_inches REAL,
    PRIMARY KEY (game_pk, at_bat_number, pitch_number)
);

-- 2. Baseball‑Data.com play‑by‑play (historical)
CREATE SCHEMA IF NOT EXISTS raw_external;
CREATE TABLE IF NOT EXISTS raw_external.baseball_data_com (
    event_id           BIGINT      NOT NULL,
    game_id            BIGINT,
    inning             INT,
    half               TEXT,       -- \"top\" or \"bottom\"
    batter_id          INT,
    pitcher_id         INT,
    event_type         TEXT,
    description        TEXT,
    -- keep columns generic; mapping to core schema is done in a view
    PRIMARY KEY (event_id)
);

-- 3. Gameday XML raw snapshots (near‑real‑time)
CREATE TABLE IF NOT EXISTS raw_mlb.gameday_xml (
    game_date          DATE        NOT NULL,
    game_pk            BIGINT,
    xml_payload        TEXT,       -- raw XML string
    fetched_at         TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_date, game_pk)
);

-- 4. Bridge tables for external IDs (if not already present)
-- These tables map external player/team IDs to the canonical Retrosheet IDs.
CREATE TABLE IF NOT EXISTS bridge.external_player_xref (
    external_source     TEXT        NOT NULL,   -- e.g., ''statcast'', ''baseball_data_com''
    external_player_id  INT         NOT NULL,
    retrosheet_player_id INT        NOT NULL,
    PRIMARY KEY (external_source, external_player_id)
);

CREATE TABLE IF NOT EXISTS bridge.external_team_xref (
    external_source     TEXT        NOT NULL,
    external_team_id    INT         NOT NULL,
    retrosheet_team_id  INT         NOT NULL,
    PRIMARY KEY (external_source, external_team_id)
);
CREATE SCHEMA IF NOT EXISTS raw_mlb;

CREATE TABLE IF NOT EXISTS raw_mlb.schedule_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    endpoint TEXT NOT NULL,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    request_params JSONB,
    http_status INTEGER,
    response_time_ms INTEGER,
    error_text TEXT
);

CREATE INDEX IF NOT EXISTS schedule_snapshots_date_idx ON raw_mlb.schedule_snapshots (snapshot_date);
CREATE INDEX IF NOT EXISTS schedule_snapshots_fetched_at_idx ON raw_mlb.schedule_snapshots (fetched_at);

COMMENT ON TABLE raw_mlb.schedule_snapshots IS 'Source-preserved MLB Stats API schedule snapshots';
COMMENT ON COLUMN raw_mlb.schedule_snapshots.snapshot_date IS 'Date covered by the schedule payload';
COMMENT ON COLUMN raw_mlb.schedule_snapshots.endpoint IS 'API endpoint used to fetch the schedule payload';
COMMENT ON COLUMN raw_mlb.schedule_snapshots.payload IS 'Full JSON response from MLB schedule API';
COMMENT ON COLUMN raw_mlb.schedule_snapshots.request_params IS 'Normalized request parameters used for the fetch';
COMMENT ON COLUMN raw_mlb.schedule_snapshots.http_status IS 'HTTP status code returned by the MLB API';
COMMENT ON COLUMN raw_mlb.schedule_snapshots.error_text IS 'Error captured during fetch when a request fails or returns unexpected content';

CREATE TABLE IF NOT EXISTS raw_mlb.live_feed_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    endpoint TEXT NOT NULL,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

ALTER TABLE raw_mlb.live_feed_snapshots
    ADD COLUMN IF NOT EXISTS request_params JSONB,
    ADD COLUMN IF NOT EXISTS http_status INTEGER,
    ADD COLUMN IF NOT EXISTS error_text TEXT,
    ADD COLUMN IF NOT EXISTS payload_checksum TEXT,
    ADD COLUMN IF NOT EXISTS game_date DATE,
    ADD COLUMN IF NOT EXISTS season INTEGER;

CREATE INDEX IF NOT EXISTS live_feed_snapshots_game_pk_idx ON raw_mlb.live_feed_snapshots (game_pk);
CREATE INDEX IF NOT EXISTS live_feed_snapshots_fetched_at_idx ON raw_mlb.live_feed_snapshots (fetched_at);
CREATE INDEX IF NOT EXISTS live_feed_snapshots_game_date_idx ON raw_mlb.live_feed_snapshots (game_date);
CREATE INDEX IF NOT EXISTS live_feed_snapshots_checksum_idx ON raw_mlb.live_feed_snapshots (payload_checksum);

COMMENT ON TABLE raw_mlb.live_feed_snapshots IS 'Source-preserved MLB Stats API live game feed snapshots';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.game_pk IS 'MLB game primary key';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.endpoint IS 'API endpoint used to fetch data';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.payload IS 'Full JSON response from MLB API';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.request_params IS 'Normalized request parameters used for the fetch';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.http_status IS 'HTTP status code returned by the MLB API';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.error_text IS 'Error captured during fetch when a request fails or returns unexpected content';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.payload_checksum IS 'Checksum for payload-level deduping and replay audit';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.game_date IS 'Game date parsed from the MLB payload when available';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.season IS 'Season parsed from the MLB payload when available';

-- -----------------------------------------------------------------
--  Feature table for ML models (extends the core play snapshot)
-- -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS features;

CREATE TABLE IF NOT EXISTS features.play_snapshot (
    game_pk      BIGINT NOT NULL,
    play_id      BIGINT NOT NULL,
    inning       INT NOT NULL,
    half_inning  TEXT NOT NULL,
    outs         INT NOT NULL,
    balls        INT NOT NULL,
    strikes      INT NOT NULL,
    base_state   TEXT,
    home_score   INT,
    away_score   INT,
    score_diff   INT,
    home_team_id INT,
    away_team_id INT,
    batter_id    BIGINT,
    pitcher_id   BIGINT,
    batter_hand  TEXT,
    pitcher_hand TEXT,
    leverage_idx NUMERIC,
    is_hit       BOOLEAN,
    is_strikeout BOOLEAN,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (game_pk, play_id)
);

CREATE INDEX IF NOT EXISTS idx_features_play_snapshot_game ON features.play_snapshot (game_pk);

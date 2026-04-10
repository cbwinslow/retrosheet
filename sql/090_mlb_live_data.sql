CREATE SCHEMA IF NOT EXISTS raw_mlb;

CREATE TABLE raw_mlb.live_feed_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    endpoint TEXT NOT NULL,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX live_feed_snapshots_game_pk_idx ON raw_mlb.live_feed_snapshots (game_pk);
CREATE INDEX live_feed_snapshots_fetched_at_idx ON raw_mlb.live_feed_snapshots (fetched_at);

COMMENT ON TABLE raw_mlb.live_feed_snapshots IS 'Source-preserved MLB Stats API live game feed snapshots';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.game_pk IS 'MLB game primary key';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.endpoint IS 'API endpoint used to fetch data';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.payload IS 'Full JSON response from MLB API';

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
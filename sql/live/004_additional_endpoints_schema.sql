-- Additional MLB Live Endpoints Raw Schema
-- All tables immutable, append only, idempotent inserts

-- Play By Play endpoint raw data
CREATE TABLE IF NOT EXISTS raw_mlb.play_by_play_snapshots (
    id bigserial PRIMARY KEY,
    game_pk bigint NOT NULL,
    raw_payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT NOW(),
    sha256_checksum text NOT NULL,
    http_status integer DEFAULT 200,
    UNIQUE (game_pk, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_mlb_playbyplay_game ON raw_mlb.play_by_play_snapshots (game_pk);
CREATE INDEX IF NOT EXISTS idx_mlb_playbyplay_fetched ON raw_mlb.play_by_play_snapshots (fetched_at);

-- Pitch Metrics endpoint raw data
CREATE TABLE IF NOT EXISTS raw_mlb.pitch_metrics_snapshots (
    id bigserial PRIMARY KEY,
    game_pk bigint NOT NULL,
    raw_payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT NOW(),
    sha256_checksum text NOT NULL,
    http_status integer DEFAULT 200,
    UNIQUE (game_pk, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_mlb_pitchmetrics_game ON raw_mlb.pitch_metrics_snapshots (game_pk);
CREATE INDEX IF NOT EXISTS idx_mlb_pitchmetrics_fetched ON raw_mlb.pitch_metrics_snapshots (fetched_at);

-- Win Probability endpoint raw data
CREATE TABLE IF NOT EXISTS raw_mlb.win_probability_snapshots (
    id bigserial PRIMARY KEY,
    game_pk bigint NOT NULL,
    raw_payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT NOW(),
    sha256_checksum text NOT NULL,
    http_status integer DEFAULT 200,
    UNIQUE (game_pk, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_mlb_winprob_game ON raw_mlb.win_probability_snapshots (game_pk);
CREATE INDEX IF NOT EXISTS idx_mlb_winprob_fetched ON raw_mlb.win_probability_snapshots (fetched_at);

-- Boxscore endpoint raw data
CREATE TABLE IF NOT EXISTS raw_mlb.boxscore_snapshots (
    id bigserial PRIMARY KEY,
    game_pk bigint NOT NULL,
    raw_payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT NOW(),
    sha256_checksum text NOT NULL,
    http_status integer DEFAULT 200,
    UNIQUE (game_pk, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_mlb_boxscore_game ON raw_mlb.boxscore_snapshots (game_pk);
CREATE INDEX IF NOT EXISTS idx_mlb_boxscore_fetched ON raw_mlb.boxscore_snapshots (fetched_at);

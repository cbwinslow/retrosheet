-- Live odds materialized views (derived from features.play_snapshot)

-- Hit probability per batter (historical frequency up to current play)
CREATE MATERIALIZED VIEW features.vw_hit_odds AS
SELECT
    game_pk,
    play_id,
    batter_id,
    COUNT(*) FILTER (WHERE is_hit) AS hit_events,
    COUNT(*) AS total_events,
    (COUNT(*) FILTER (WHERE is_hit))::numeric / NULLIF(COUNT(*), 0) AS hit_prob
FROM features.play_snapshot
GROUP BY game_pk, play_id, batter_id
WITH DATA;

CREATE UNIQUE INDEX idx_vw_hit_odds_pk ON features.vw_hit_odds (game_pk, play_id);

-- Strikeout probability per pitcher
CREATE MATERIALIZED VIEW features.vw_strikeout_odds AS
SELECT
    game_pk,
    play_id,
    pitcher_id,
    COUNT(*) FILTER (WHERE is_strikeout) AS so_events,
    COUNT(*) AS total_events,
    (COUNT(*) FILTER (WHERE is_strikeout))::numeric / NULLIF(COUNT(*), 0) AS so_prob
FROM features.play_snapshot
GROUP BY game_pk, play_id, pitcher_id
WITH DATA;

CREATE UNIQUE INDEX idx_vw_so_odds_pk ON features.vw_strikeout_odds (game_pk, play_id);

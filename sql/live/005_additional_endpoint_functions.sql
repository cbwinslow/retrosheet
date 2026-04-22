-- Ingestion functions for all additional MLB live endpoints

CREATE OR REPLACE FUNCTION raw_mlb.ingest_endpoint(game_pk bigint, endpoint_suffix text, target_table text)
RETURNS void AS $$
    import httpx
    import hashlib
    
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/{endpoint_suffix}"
        r = httpx.get(url, timeout=15)
        
        checksum = hashlib.sha256(r.content).hexdigest()
        
        plpy.execute(f"""
            INSERT INTO {target_table} (game_pk, raw_payload, fetched_at, http_status, sha256_checksum)
            VALUES ($1, $2, NOW(), $3, $4)
            ON CONFLICT (game_pk, fetched_at) DO NOTHING
        """, [game_pk, r.json(), r.status_code, checksum])
        
    except Exception as e:
        NULL;
$$ LANGUAGE plpython3u;


CREATE OR REPLACE FUNCTION raw_mlb.ingest_all_endpoints_for_game(game_pk bigint)
RETURNS void AS $$
BEGIN
    PERFORM raw_mlb.ingest_endpoint(game_pk, 'feed/live', 'raw_mlb.live_feed_snapshots');
    PERFORM raw_mlb.ingest_endpoint(game_pk, 'playByPlay', 'raw_mlb.play_by_play_snapshots');
    PERFORM raw_mlb.ingest_endpoint(game_pk, 'pitchMetrics', 'raw_mlb.pitch_metrics_snapshots');
    PERFORM raw_mlb.ingest_endpoint(game_pk, 'winProbability', 'raw_mlb.win_probability_snapshots');
    PERFORM raw_mlb.ingest_endpoint(game_pk, 'boxscore', 'raw_mlb.boxscore_snapshots');
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION raw_mlb.poll_all_active_endpoints()
RETURNS integer AS $$
DECLARE
    active_game bigint;
    count integer := 0;
BEGIN
    FOR active_game IN
        SELECT DISTINCT game_pk
        FROM core.live_games
        WHERE status_code IN ('I', 'P')
        AND game_date >= CURRENT_DATE - INTERVAL '1 day'
    LOOP
        PERFORM raw_mlb.ingest_all_endpoints_for_game(active_game);
        count := count + 1;
    END LOOP;
    
    RETURN count;
END;
$$ LANGUAGE plpgsql;

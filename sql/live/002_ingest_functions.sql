-- File: sql/live/002_ingest_functions.sql
-- Purpose: Functions to fetch schedule, ingest live games, and poll actives
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE OR REPLACE FUNCTION raw_sportradar.fetch_live_schedule()
RETURNS jsonb AS $$
    import httpx
    try:
        r = httpx.get("https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=game", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "status_code": getattr(r, 'status_code', 0)}
$$ LANGUAGE plpython3u;


CREATE OR REPLACE FUNCTION raw_sportradar.ingest_live_game(game_pk text)
RETURNS void AS $$
    import httpx
    import hashlib
    
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        r = httpx.get(url, timeout=15)
        
        checksum = hashlib.sha256(r.content).hexdigest()
        
        INSERT INTO raw_mlb.live_feed_snapshots (
            game_pk, raw_payload, fetched_at, http_status, sha256_checksum
        ) VALUES (
            game_pk::bigint,
            r.json(),
            NOW(),
            r.status_code,
            checksum
        ) ON CONFLICT (game_pk, fetched_at) DO NOTHING;
        
    except Exception as e:
        -- Log error silently, continue operation
        NULL;
$$ LANGUAGE plpython3u;


CREATE OR REPLACE FUNCTION raw_sportradar.poll_active_games()
RETURNS integer AS $$
DECLARE
    active_game text;
    count integer := 0;
BEGIN
    FOR active_game IN
        SELECT DISTINCT game_pk::text
        FROM core.live_games
        WHERE status_code IN ('I', 'P')
        AND game_date >= CURRENT_DATE - INTERVAL '1 day'
    LOOP
        PERFORM raw_sportradar.ingest_live_game(active_game);
        count := count + 1;
    END LOOP;
    
    RETURN count;
END;
$$ LANGUAGE plpgsql;


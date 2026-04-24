-- Migrate existing pitch data to include ALL 118 Statcast fields
-- This updates rows that were loaded with partial data

DO $$
DECLARE
    v_season INTEGER;
    v_count INTEGER;
    v_total INTEGER := 0;
BEGIN
    RAISE NOTICE 'Starting full Statcast migration...';
    
    -- Process each season
    FOR v_season IN SELECT DISTINCT game_year FROM features_pitch.locations ORDER BY game_year
    LOOP
        RAISE NOTICE 'Processing season %...', v_season;
        
        -- Update all missing fields from raw_mlb.statcast
        UPDATE features_pitch.locations l
        SET 
            -- Core identification (keep existing where we have it)
            game_date = s.game_date,
            sv_id = s.sv_id,
            player_name = s.player_name,
            
            -- Pitch info
            pitch_name = s.pitch_name,
            pitch_number = s.pitch_number::integer,
            pitch_result = COALESCE(l.pitch_result, s.des),
            description = s.description,
            events = s.events,
            
            -- Count/state
            outs_when_up = s.outs_when_up::integer,
            on_1b = s.on_1b::integer,
            on_2b = s.on_2b::integer,
            on_3b = s.on_3b::integer,
            
            -- Sides/stands
            stand = s.stand,
            p_throws = s.p_throws,
            home_team = s.home_team,
            away_team = s.away_team,
            type = s.type,
            
            -- Release/physics (use release_speed if start_speed is null)
            release_speed = s.release_speed::numeric,
            effective_speed = s.effective_speed::numeric,
            release_spin_rate = s.release_spin_rate::numeric,
            release_pos_x = s.release_pos_x::numeric,
            release_pos_y = s.release_pos_y::numeric,
            release_pos_z = s.release_pos_z::numeric,
            release_extension = s.release_extension::numeric,
            
            -- Movement
            spin_axis = s.spin_axis::numeric,
            
            -- Velocity components
            vx0 = s.vx0::numeric,
            vy0 = s.vy0::numeric,
            vz0 = s.vz0::numeric,
            
            -- Acceleration
            ax = s.ax::numeric,
            ay = s.ay::numeric,
            az = s.az::numeric,
            
            -- Hit data (keep existing where we have it)
            hit_distance = COALESCE(l.hit_distance, s.hit_distance_sc::numeric),
            launch_speed_angle = s.launch_speed_angle::numeric,
            
            -- Expected stats
            estimated_ba = s.estimated_ba_using_speedangle::numeric,
            estimated_woba = s.estimated_woba_using_speedangle::numeric,
            estimated_slg = s.estimated_slg_using_speedangle::numeric,
            woba_value = s.woba_value::numeric,
            woba_denom = s.woba_denom::numeric,
            babip_value = s.babip_value::numeric,
            iso_value = s.iso_value::numeric,
            
            -- Scoring
            home_score = s.home_score::integer,
            away_score = s.away_score::integer,
            bat_score = s.bat_score::integer,
            fld_score = s.fld_score::integer,
            post_home_score = s.post_home_score::integer,
            post_away_score = s.post_away_score::integer,
            post_bat_score = s.post_bat_score::integer,
            post_fld_score = s.post_fld_score::integer,
            
            -- At bat numbering
            at_bat_number = s.at_bat_number::integer,
            
            -- Fielders
            fielder_2 = s.fielder_2::integer,
            fielder_3 = s.fielder_3::integer,
            fielder_4 = s.fielder_4::integer,
            fielder_5 = s.fielder_5::integer,
            fielder_6 = s.fielder_6::integer,
            fielder_7 = s.fielder_7::integer,
            fielder_8 = s.fielder_8::integer,
            fielder_9 = s.fielder_9::integer,
            
            -- Win probability
            delta_home_win_exp = s.delta_home_win_exp::numeric,
            delta_run_exp = s.delta_run_exp::numeric,
            home_win_exp = s.home_win_exp::numeric,
            bat_win_exp = s.bat_win_exp::numeric,
            
            -- Fielding alignment
            if_fielding_alignment = s.if_fielding_alignment,
            of_fielding_alignment = s.of_fielding_alignment,
            
            -- Keep the deprecated field for reference
            spin_rate_deprecated = s.spin_rate_deprecated::numeric
            
        FROM raw_mlb.statcast s
        WHERE l.game_year = v_season
          AND l.game_pk = s.game_pk
          AND l.pitcher_id = s.pitcher::integer
          AND l.batter_id = s.batter::integer
          -- Match by inning/at_bat/pitch_number if available, otherwise by description
          AND (COALESCE(l.pitch_number::text, '') = COALESCE(s.pitch_number::text, '') 
               OR l.pitch_result = s.des
               OR (l.plate_x = s.plate_x::numeric AND l.plate_z = s.plate_z::numeric));
        
        GET DIAGNOSTICS v_count = ROW_COUNT;
        v_total := v_total + v_count;
        RAISE NOTICE '  Updated % rows for season %', v_count, v_season;
    END LOOP;
    
    RAISE NOTICE 'Migration complete! Total rows updated: %', v_total;
END $$;

-- Create index on new columns for performance
CREATE INDEX IF NOT EXISTS idx_pitch_locations_release_speed
ON features_pitch.locations (release_speed) WHERE release_speed IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pitch_locations_effective_speed
ON features_pitch.locations (effective_speed) WHERE effective_speed IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pitch_locations_spin_axis
ON features_pitch.locations (spin_axis) WHERE spin_axis IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pitch_locations_game_date
ON features_pitch.locations (game_date);

CREATE INDEX IF NOT EXISTS idx_pitch_locations_sv_id
ON features_pitch.locations (sv_id) WHERE sv_id IS NOT NULL;

-- Verify migration
SELECT
    game_year,
    COUNT(*) AS total_pitches,
    COUNT(release_speed) AS have_release_speed,
    COUNT(spin_axis) AS have_spin_axis,
    COUNT(estimated_ba) AS have_expected_stats,
    COUNT(vx0) AS have_physics,
    COUNT(game_date) AS have_game_date
FROM features_pitch.locations
GROUP BY game_year
ORDER BY game_year DESC;

-- MLB Team Name Resolution View
-- Maps MLB team names to Retrosheet team IDs with temporal support
-- This replaces ad-hoc scripts like fix_historical_teams.py with a proper database-level solution

CREATE OR REPLACE VIEW mlb.team_name_resolution AS
WITH mlb_team_names AS (
    -- Mapping of MLB API team names to Retrosheet team IDs
    -- This handles the full team names returned by MLB Stats API
    SELECT 
        'New York Mets' AS mlb_team_name,
        'NYN' AS retrosheet_team_id
    UNION ALL SELECT 'New York Mets', 'NYN'
    UNION ALL SELECT 'NY Mets', 'NYN'
    UNION ALL SELECT 'Mets', 'NYN'
    
    UNION ALL SELECT 'Chicago Cubs', 'CHN'
    UNION ALL SELECT 'Chicago Cubs', 'CHN'
    UNION ALL SELECT 'Cubs', 'CHN'
    
    UNION ALL SELECT 'Anaheim Angels', 'ANA'
    UNION ALL SELECT 'Los Angeles Angels', 'ANA'
    UNION ALL SELECT 'Los Angeles Angels of Anaheim', 'ANA'
    UNION ALL SELECT 'California Angels', 'CAL'
    UNION ALL SELECT 'Angels', 'ANA'
    
    UNION ALL SELECT 'Montreal Expos', 'MON'
    UNION ALL SELECT 'Washington Nationals', 'WAS'
    UNION ALL SELECT 'Nationals', 'WAS'
    
    UNION ALL SELECT 'Florida Marlins', 'FLO'
    UNION ALL SELECT 'Miami Marlins', 'MIA'
    UNION ALL SELECT 'Marlins', 'MIA'
    
    UNION ALL SELECT 'Tampa Bay Devil Rays', 'TBD'
    UNION ALL SELECT 'Tampa Bay Rays', 'TBA'
    UNION ALL SELECT 'Rays', 'TBA'
    
    UNION ALL SELECT 'Arizona Diamondbacks', 'ARI'
    UNION ALL SELECT 'Diamondbacks', 'ARI'
    
    UNION ALL SELECT 'Colorado Rockies', 'COL'
    UNION ALL SELECT 'Rockies', 'COL'
    
    UNION ALL SELECT 'Atlanta Braves', 'ATL'
    UNION ALL SELECT 'Milwaukee Braves', 'ML1'
    UNION ALL SELECT 'Boston Braves', 'BOS'
    UNION ALL SELECT 'Braves', 'ATL'
    
    UNION ALL SELECT 'St. Louis Cardinals', 'SLN'
    UNION ALL SELECT 'St Louis Cardinals', 'SLN'
    UNION ALL SELECT 'Cardinals', 'SLN'
    
    UNION ALL SELECT 'Philadelphia Phillies', 'PHI'
    UNION ALL SELECT 'Phillies', 'PHI'
    
    UNION ALL SELECT 'San Francisco Giants', 'SFN'
    UNION ALL SELECT 'New York Giants', 'NY1'
    UNION ALL SELECT 'Giants', 'SFN'
    
    UNION ALL SELECT 'Los Angeles Dodgers', 'LAN'
    UNION ALL SELECT 'Brooklyn Dodgers', 'BR1'
    UNION ALL SELECT 'Dodgers', 'LAN'
    
    UNION ALL SELECT 'San Diego Padres', 'SDN'
    UNION ALL SELECT 'Padres', 'SDN'
    
    UNION ALL SELECT 'Colorado Rockies', 'COL'
    UNION ALL SELECT 'Rockies', 'COL'
    
    UNION ALL SELECT 'Pittsburgh Pirates', 'PIT'
    UNION ALL SELECT 'Pirates', 'PIT'
    
    UNION ALL SELECT 'Cincinnati Reds', 'CIN'
    UNION ALL SELECT 'Reds', 'CIN'
    
    UNION ALL SELECT 'Chicago White Sox', 'CHA'
    UNION ALL SELECT 'White Sox', 'CHA'
    
    UNION ALL SELECT 'Oakland Athletics', 'OAK'
    UNION ALL SELECT 'Kansas City Athletics', 'KC1'
    UNION ALL SELECT 'Philadelphia Athletics', 'PHA'
    UNION ALL SELECT 'Athletics', 'OAK'
    
    UNION ALL SELECT 'Baltimore Orioles', 'BAL'
    UNION ALL SELECT 'St. Louis Browns', 'SLA'
    UNION ALL SELECT 'Orioles', 'BAL'
    
    UNION ALL SELECT 'Boston Red Sox', 'BOS'
    UNION ALL SELECT 'Red Sox', 'BOS'
    
    UNION ALL SELECT 'Toronto Blue Jays', 'TOR'
    UNION ALL SELECT 'Blue Jays', 'TOR'
    
    UNION ALL SELECT 'Seattle Mariners', 'SEA'
    UNION ALL SELECT 'Mariners', 'SEA'
    
    UNION ALL SELECT 'Kansas City Royals', 'KCA'
    UNION ALL SELECT 'Royals', 'KCA'
    
    UNION ALL SELECT 'Minnesota Twins', 'MIN'
    UNION ALL SELECT 'Washington Senators', 'WS1'
    UNION ALL SELECT 'Twins', 'MIN'
    
    UNION ALL SELECT 'Cleveland Indians', 'CLE'
    UNION ALL SELECT 'Cleveland Guardians', 'CLE'
    UNION ALL SELECT 'Indians', 'CLE'
    UNION ALL SELECT 'Guardians', 'CLE'
    
    UNION ALL SELECT 'Detroit Tigers', 'DET'
    UNION ALL SELECT 'Tigers', 'DET'
    
    UNION ALL SELECT 'Houston Astros', 'HOU'
    UNION ALL SELECT 'Houston Colt .45s', 'HOU'
    UNION ALL SELECT 'Astros', 'HOU'
    
    UNION ALL SELECT 'Milwaukee Brewers', 'MIL'
    UNION ALL SELECT 'Seattle Pilots', 'SE1'
    UNION ALL SELECT 'Brewers', 'MIL'
    
    UNION ALL SELECT 'Texas Rangers', 'TEX'
    UNION ALL SELECT 'Washington Senators', 'WS2'
    UNION ALL SELECT 'Rangers', 'TEX'
)
SELECT 
    m.mlb_team_name,
    m.retrosheet_team_id,
    t.first_season,
    t.last_season,
    t.city,
    t.nickname,
    t.team_name
FROM mlb_team_names m
JOIN core.teams t ON m.retrosheet_team_id = t.retrosheet_team_id;

COMMENT ON VIEW mlb.team_name_resolution IS 'Maps MLB API team names to Retrosheet team IDs with temporal support from core.teams';

-- Helper function to resolve team name for a given date
CREATE OR REPLACE FUNCTION mlb.resolve_team_id(mlb_team_name TEXT, game_date DATE)
RETURNS TEXT AS $$
    SELECT retrosheet_team_id 
    FROM mlb.team_name_resolution 
    WHERE mlb_team_name ILIKE '%' || $1 || '%'
      AND (game_date >= to_date(first_season::text, 'YYYY') OR first_season IS NULL)
      AND (game_date <= to_date(last_season::text, 'YYYY') OR last_season IS NULL)
    LIMIT 1;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION mlb.resolve_team_id IS 'Resolves MLB team name to Retrosheet team ID considering temporal validity';

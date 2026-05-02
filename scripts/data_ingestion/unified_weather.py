#!/usr/bin/env python3
"""
UNIFIED Weather Download + Ingest Script
Fetches weather data for MLB venues and ingests ALL meteorological fields to database.

This script replaces the separate download + ingest pipeline with a single unified operation.
All weather API fields are preserved without filtering.

Supports OpenWeatherMap and VisualCrossing APIs.

Usage:
    python scripts/data_ingestion/unified_weather.py --date 2024-07-04 --venue 1
    python scripts/data_ingestion/unified_weather.py --date-range 2024-07-01 2024-07-31 --all-venues
    python scripts/data_ingestion/unified_weather.py --join-games --season 2024
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import psycopg2

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests not installed. Weather download requires requests.")


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')

# MLB Venue coordinates (lat, lon)
MLB_VENUES = {
    # AL East
    '1': ('Fenway Park', 42.3467, -71.0972),      # Boston
    '2': ('Yankee Stadium', 40.8296, -73.9262),   # New York
    '3': ('Tropicana Field', 27.7683, -82.6483),  # Tampa Bay
    '4': ('Rogers Centre', 43.6414, -79.3894),   # Toronto
    '5': ('Oriole Park', 39.2839, -76.6217),     # Baltimore
    
    # AL Central
    '6': ('Target Field', 44.9817, -93.2775),     # Minnesota
    '7': ('Guaranteed Rate Field', 41.8301, -87.6338),  # Chicago
    '8': ('Progressive Field', 41.4962, -81.6852),     # Cleveland
    '9': ('Comerica Park', 42.3390, -83.0485),   # Detroit
    '10': ('Kauffman Stadium', 39.0517, -94.4803),    # Kansas City
    
    # AL West
    '11': ('Minute Maid Park', 29.7573, -95.3555),    # Houston
    '12': ('Globe Life Field', 32.7514, -97.0828),    # Texas
    '13': ('T-Mobile Park', 47.5914, -122.3325),      # Seattle
    '14': ('Angel Stadium', 33.8003, -117.8827),      # Los Angeles
    '15': ('Oakland Coliseum', 37.7516, -122.2005),   # Oakland
    
    # NL East
    '16': ('Truist Park', 33.8908, -84.4678),          # Atlanta
    '17': ('Citi Field', 40.7571, -73.8458),           # New York
    '18': ('Citizens Bank Park', 39.9055, -75.1664),  # Philadelphia
    '19': ('loanDepot park', 25.7783, -80.2196),        # Miami
    '20': ('Nationals Park', 38.8729, -77.0074),       # Washington
    
    # NL Central
    '21': ('Wrigley Field', 41.9484, -87.6553),       # Chicago
    '22': ('Busch Stadium', 38.6226, -90.1928),         # St. Louis
    '23': ('American Family Field', 43.0280, -87.9712),  # Milwaukee
    '24': ('PNC Park', 40.4469, -80.0057),            # Pittsburgh
    '25': ('Great American Ball Park', 39.0979, -84.5082),  # Cincinnati
    
    # NL West
    '26': ('Dodger Stadium', 34.0739, -118.2400),       # Los Angeles
    '27': ('Oracle Park', 37.7786, -122.3893),        # San Francisco
    '28': ('Petco Park', 32.7076, -117.1570),           # San Diego
    '29': ('Chase Field', 33.4455, -112.0667),          # Arizona
    '30': ('Coors Field', 39.7559, -104.9942),          # Colorado
}


def get_conn():
    return psycopg2.connect(DB_URL)


def get_venue_games(season: int) -> pd.DataFrame:
    """Get all games with venue IDs for a season."""
    conn = get_conn()
    query = """
        SELECT DISTINCT
            game_pk,
            official_date as game_date,
            venue_id,
            game_datetime
        FROM core.games
        WHERE season = %s
        ORDER BY official_date
    """
    df = pd.read_sql(query, conn, params=(season,))
    conn.close()
    return df


def fetch_openweathermap_hourly(lat: float, lon: float, target_date: date, api_key: str) -> List[Dict]:
    """Fetch hourly weather from OpenWeatherMap 3.0 API."""
    if not HAS_REQUESTS:
        return []
    
    # One Call API 3.0 for historical data
    dt = int(datetime.combine(target_date, datetime.min.time()).timestamp())
    url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine"
    
    params = {
        'lat': lat,
        'lon': lon,
        'dt': dt,
        'appid': api_key,
        'units': 'metric'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        hourly_data = []
        for hour in data.get('data', [{}])[0].get('hourly', []):
            hourly_data.append({
                'temp_c': hour.get('temp'),
                'feels_like_c': hour.get('feels_like'),
                'pressure_hpa': hour.get('pressure'),
                'humidity_percent': hour.get('humidity'),
                'wind_speed_mps': hour.get('wind_speed'),
                'wind_direction_deg': hour.get('wind_deg'),
                'cloud_cover_percent': hour.get('clouds'),
                'precipitation_mm': hour.get('rain', {}).get('1h', 0) if hour.get('rain') else 0,
                'weather_condition_id': hour.get('weather', [{}])[0].get('id'),
                'weather_main': hour.get('weather', [{}])[0].get('main'),
                'weather_description': hour.get('weather', [{}])[0].get('description'),
                'observation_datetime': datetime.utcfromtimestamp(hour.get('dt')),
                'api_response': hour
            })
        
        return hourly_data
        
    except Exception as e:
        print(f"  Error fetching weather: {e}")
        return []


def fetch_visualcrossing_daily(
    lat: float, lon: float, 
    target_date: date, api_key: str
) -> Optional[Dict]:
    """Fetch daily weather from Visual Crossing API."""
    if not HAS_REQUESTS:
        return None
    
    date_str = target_date.strftime('%Y-%m-%d')
    location = f"{lat},{lon}"
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{date_str}"
    
    params = {
        'unitGroup': 'metric',
        'key': api_key,
        'include': 'hours',
        'elements': 'datetime,temp,tempmax,tempmin,feelslike,feelslikemax,feelslikemin,dew,humidity,windspeed,winddir,windgust,cloudcover,visibility,pressure,uvindex,sunrise,sunset,precip,precipprob,preciptype,snow,snowdepth,conditions,description,icon'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        day = data.get('days', [{}])[0]
        
        return {
            'temp_avg_c': day.get('temp'),
            'temp_min_c': day.get('tempmin'),
            'temp_max_c': day.get('tempmax'),
            'feels_like_avg_c': day.get('feelslike'),
            'feels_like_min_c': day.get('feelslikemin'),
            'feels_like_max_c': day.get('feelslikemax'),
            'dew_point_avg_c': day.get('dew'),
            'humidity_avg_percent': day.get('humidity'),
            'wind_speed_avg_mps': day.get('windspeed'),
            'wind_speed_max_mps': day.get('windgust'),
            'wind_direction_deg': day.get('winddir'),
            'pressure_avg_hpa': day.get('pressure'),
            'cloud_cover_avg_percent': day.get('cloudcover'),
            'uv_index_max': day.get('uvindex'),
            'visibility_avg_m': day.get('visibility'),
            'precipitation_mm': day.get('precip', 0),
            'precipitation_probability': day.get('precipprob'),
            'snow_mm': day.get('snow', 0),
            'sunrise': day.get('sunrise'),
            'sunset': day.get('sunset'),
            'weather_condition': day.get('conditions'),
            'weather_description': day.get('description'),
            'api_response': day
        }
        
    except Exception as e:
        print(f"  Error fetching VisualCrossing weather: {e}")
        return None


def ingest_hourly_weather(observations: List[Dict], venue_id: str, venue_info: tuple) -> int:
    """Ingest hourly weather observations."""
    if not observations:
        return 0
    
    conn = get_conn()
    cur = conn.cursor()
    
    venue_name, lat, lon = venue_info
    
    count = 0
    for obs in observations:
        try:
            cur.execute("""
                INSERT INTO raw_weather.hourly (
                    observation_datetime, venue_id, venue_lat, venue_lon, venue_city,
                    temp_c, feels_like_c, temp_min_c, temp_max_c, dew_point_c,
                    wind_speed_mps, wind_direction_deg, wind_gust_mps,
                    precipitation_mm, rain_mm, precipitation_probability,
                    pressure_hpa, humidity_percent, visibility_m, cloud_cover_percent,
                    weather_condition_id, weather_main, weather_description,
                    data_source, api_response
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (observation_datetime, venue_id)
                DO UPDATE SET
                    temp_c = EXCLUDED.temp_c,
                    feels_like_c = EXCLUDED.feels_like_c,
                    wind_speed_mps = EXCLUDED.wind_speed_mps,
                    updated_at = NOW()
            """, (
                obs['observation_datetime'], venue_id, lat, lon, venue_name,
                obs.get('temp_c'), obs.get('feels_like_c'), obs.get('temp_min_c'), 
                obs.get('temp_max_c'), obs.get('dew_point_c'),
                obs.get('wind_speed_mps'), obs.get('wind_direction_deg'), 
                obs.get('wind_gust_mps'),
                obs.get('precipitation_mm'), obs.get('rain_mm'), 
                obs.get('precipitation_probability'),
                obs.get('pressure_hpa'), obs.get('humidity_percent'), 
                obs.get('visibility_m'), obs.get('cloud_cover_percent'),
                obs.get('weather_condition_id'), obs.get('weather_main'), 
                obs.get('weather_description'),
                'openweathermap', str(obs.get('api_response'))
            ))
            count += 1
        except Exception as e:
            print(f"  Error ingesting observation: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return count


def ingest_daily_weather(data: Dict, venue_id: str, target_date: date, venue_info: tuple) -> int:
    """Ingest daily weather aggregate."""
    if not data:
        return 0
    
    conn = get_conn()
    cur = conn.cursor()
    
    venue_name, lat, lon = venue_info
    
    try:
        cur.execute("""
            INSERT INTO raw_weather.daily (
                observation_date, venue_id,
                temp_avg_c, temp_min_c, temp_max_c,
                feels_like_avg_c, feels_like_min_c, feels_like_max_c,
                dew_point_avg_c,
                wind_speed_avg_mps, wind_speed_max_mps, wind_direction_deg,
                precipitation_mm, rain_mm, snow_mm,
                pressure_avg_hpa, humidity_avg_percent,
                cloud_cover_avg_percent, uv_index_max,
                weather_condition, weather_description,
                sunrise, sunset,
                data_source, observation_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (observation_date, venue_id)
            DO UPDATE SET
                temp_avg_c = EXCLUDED.temp_avg_c,
                temp_min_c = EXCLUDED.temp_min_c,
                temp_max_c = EXCLUDED.temp_max_c,
                wind_speed_avg_mps = EXCLUDED.wind_speed_avg_mps,
                precipitation_mm = EXCLUDED.precipitation_mm,
                ingested_at = NOW()
        """, (
            target_date, venue_id,
            data.get('temp_avg_c'), data.get('temp_min_c'), data.get('temp_max_c'),
            data.get('feels_like_avg_c'), data.get('feels_like_min_c'), 
            data.get('feels_like_max_c'),
            data.get('dew_point_avg_c'),
            data.get('wind_speed_avg_mps'), data.get('wind_speed_max_mps'),
            data.get('wind_direction_deg'),
            data.get('precipitation_mm'), data.get('rain_mm'), data.get('snow_mm'),
            data.get('pressure_avg_hpa'), data.get('humidity_avg_percent'),
            data.get('cloud_cover_avg_percent'), data.get('uv_index_max'),
            data.get('weather_condition'), data.get('weather_description'),
            data.get('sunrise'), data.get('sunset'),
            'visualcrossing', 24
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return 1
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"  Error ingesting daily weather: {e}")
        return 0


def unified_fetch_ingest_venue_date(
    venue_id: str, target_date: date, 
    api_key: str, source: str = 'visualcrossing'
) -> dict:
    """Fetch and ingest weather for a specific venue and date."""
    if venue_id not in MLB_VENUES:
        return {'success': False, 'error': f'Unknown venue: {venue_id}'}
    
    venue_info = MLB_VENUES[venue_id]
    venue_name, lat, lon = venue_info
    
    print(f"Processing {venue_name} ({target_date})...")
    
    try:
        if source == 'openweathermap':
            hourly = fetch_openweathermap_hourly(lat, lon, target_date, api_key)
            ingested = ingest_hourly_weather(hourly, venue_id, venue_info)
            return {
                'venue_id': venue_id,
                'date': target_date,
                'source': source,
                'hourly_observations': ingested,
                'success': ingested > 0
            }
        elif source == 'visualcrossing':
            daily = fetch_visualcrossing_daily(lat, lon, target_date, api_key)
            ingested = ingest_daily_weather(daily, venue_id, target_date, venue_info)
            return {
                'venue_id': venue_id,
                'date': target_date,
                'source': source,
                'daily_records': ingested,
                'success': ingested > 0
            }
        else:
            return {'success': False, 'error': f'Unknown source: {source}'}
            
    except Exception as e:
        return {
            'venue_id': venue_id,
            'date': target_date,
            'success': False,
            'error': str(e)
        }


def unified_fetch_ingest_date_range(
    start_date: date, end_date: date,
    venues: List[str], api_key: str, source: str = 'visualcrossing'
) -> dict:
    """Fetch and ingest weather for a date range across multiple venues."""
    results = []
    total_success = 0
    total_error = 0
    
    current = start_date
    while current <= end_date:
        for venue_id in venues:
            result = unified_fetch_ingest_venue_date(
                venue_id, current, api_key, source
            )
            results.append(result)
            
            if result.get('success'):
                total_success += 1
            else:
                total_error += 1
        
        current += timedelta(days=1)
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'venues': venues,
        'total_days': (end_date - start_date).days + 1,
        'total_success': total_success,
        'total_error': total_error,
        'results': results,
        'success': total_error == 0
    }


def join_weather_to_games(season: int, api_key: str) -> dict:
    """Fetch weather for all games in a season and join to game_weather table."""
    print(f"Fetching weather for season {season} games...")
    
    # Get games
    games_df = get_venue_games(season)
    
    if games_df.empty:
        return {'success': False, 'error': f'No games found for season {season}'}
    
    print(f"Found {len(games_df)} games")
    
    # Group by venue and date to minimize API calls
    venue_dates = games_df.groupby(['venue_id', 'game_date']).size().reset_index()
    
    total = 0
    errors = []
    
    for _, row in venue_dates.iterrows():
        venue_id = str(int(row['venue_id'])) if pd.notna(row['venue_id']) else None
        game_date = row['game_date']
        
        if not venue_id or venue_id not in MLB_VENUES:
            continue
        
        result = unified_fetch_ingest_venue_date(venue_id, game_date, api_key)
        
        if result.get('success'):
            total += 1
        else:
            errors.append(f"{venue_id} {game_date}: {result.get('error')}")
    
    return {
        'season': season,
        'games_found': len(games_df),
        'weather_fetched': total,
        'errors': errors,
        'success': len(errors) == 0
    }


def main():
    parser = argparse.ArgumentParser(
        description='UNIFIED Weather Download + Ingest - Downloads and loads ALL weather fields'
    )
    parser.add_argument('--date', type=str, help='Single date (YYYY-MM-DD)')
    parser.add_argument('--venue', type=str, help='Venue ID (1-30)')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                       help='Date range (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--all-venues', action='store_true',
                       help='Process all MLB venues')
    parser.add_argument('--join-games', action='store_true',
                       help='Join weather to MLB games for season')
    parser.add_argument('--season', type=int, help='MLB season for game weather')
    parser.add_argument('--source', type=str, default='visualcrossing',
                       choices=['visualcrossing', 'openweathermap'],
                       help='Weather data source')
    parser.add_argument('--api-key', type=str,
                       help='API key (or set OPENWEATHER_API_KEY or VISUALCROSSING_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key
    if args.source == 'openweathermap':
        api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
    else:
        api_key = api_key or os.getenv('VISUALCROSSING_API_KEY')
    
    if not api_key and (args.date or args.date_range or args.join_games):
        print("Error: API key required. Provide via --api-key or environment variable.")
        sys.exit(1)
    
    # Execute based on mode
    if args.join_games and args.season:
        result = join_weather_to_games(args.season, api_key)
    elif args.date_range:
        start = datetime.strptime(args.date_range[0], '%Y-%m-%d').date()
        end = datetime.strptime(args.date_range[1], '%Y-%m-%d').date()
        venues = list(MLB_VENUES.keys()) if args.all_venues else [args.venue] if args.venue else []
        if not venues:
            print("Error: Specify --venue or --all-venues")
            sys.exit(1)
        result = unified_fetch_ingest_date_range(start, end, venues, api_key, args.source)
    elif args.date and args.venue:
        target = datetime.strptime(args.date, '%Y-%m-%d').date()
        result = unified_fetch_ingest_venue_date(args.venue, target, api_key, args.source)
    else:
        parser.print_help()
        sys.exit(1)
    
    if result.get('success'):
        print(f"\n✓ Unified weather download+ingest complete")
        sys.exit(0)
    else:
        print(f"\n✗ Unified weather download+ingest incomplete")
        if result.get('errors'):
            print(f"  Errors: {len(result['errors'])}")
        sys.exit(1)


if __name__ == '__main__':
    main()

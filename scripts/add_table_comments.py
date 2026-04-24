#!/usr/bin/env python3
"""Add COMMENT ON TABLE statements to SQL files that are missing them."""

import re
from pathlib import Path

PROJECT_ROOT = Path("/home/cbwinslow/workspace/retrosheet")

# Mapping of schema.table -> comment (for well-known tables)
KNOWN_COMMENTS = {
    # Core
    "core.plate_appearances": "Enriched plate appearance records with game state and outcome flags",
    # Reference metadata
    "raw_retrosheet.biofile": "Player biographical and career metadata from Retrosheet",
    "raw_retrosheet.teams_reference": "Team reference data with league, city, and active seasons",
    "raw_retrosheet.ballparks_reference": "Ballpark reference data with name, location, and league",
    # Auxiliary
    "raw_retrosheet.biofile_legacy": "Legacy-format player biographical data from Retrosheet",
    "raw_retrosheet.coaches": "Coaching assignments by season, team, and role",
    "raw_retrosheet.ejections": "Game ejection records with ejectee, umpire, and reason",
    "raw_retrosheet.relatives": "Player relationship records",
    "raw_retrosheet.allstar": "All-Star game rosters and selections",
    "raw_retrosheet.schedules": "Season schedules with dates and matchups",
    "raw_retrosheet.umpires": "Umpire assignments by game and position",
    # External
    "raw_statcast.events": "Statcast pitch-level events with physics and outcome data",
    "raw_weather.daily": "Daily weather conditions by venue",
    "raw_mlb_rosters.roster_snapshots": "MLB roster snapshots with JSON payload data",
    "raw_park_factors.factors": "Park factors from Baseball Savant by season and park",
    "raw_baseball_reference.game_logs": "Baseball-Reference game logs with per-game stats",
    "raw_fangraphs.player_season": "Fangraphs player season statistics",
    "raw_fangraphs.team_season": "Fangraphs team season statistics",
    "raw_lahman.players": "Lahman database player biographical data",
    "raw_lahman.teams": "Lahman database team information",
    "raw_lahman.batting": "Lahman database batting statistics",
    "raw_lahman.pitching": "Lahman database pitching statistics",
    "raw_lahman.salaries": "Lahman database player salary data",
    "raw_espn.game_snapshots": "ESPN API game snapshot data",
    "raw_espn.schedules": "ESPN API schedule data",
    # Live
    "raw_sportradar.push_events": "Sportradar push event ingestion with payloads",
    "raw_sportradar.game_snapshots": "Sportradar game snapshot JSON payloads",
    "raw_mlb.play_by_play_snapshots": "MLB play-by-play endpoint raw snapshots",
    "raw_mlb.pitch_metrics_snapshots": "MLB pitch metrics endpoint raw snapshots",
    "raw_mlb.win_probability_snapshots": "MLB win probability endpoint raw snapshots",
    "raw_mlb.boxscore_snapshots": "MLB boxscore endpoint raw snapshots",
    # Maintenance
    "test_embeddings": "Test table for pgvector embedding storage",
    "metadata.table_dictionary": "Data dictionary of all warehouse tables",
    "metadata.column_dictionary": "Data dictionary of all warehouse columns",
    # Optimization
    "analysis.query_performance_log": "Query performance tracking log",
    "analysis.slow_query_alerts": "Slow query alert tracking",
}


def generate_comment(table_name: str, filepath: Path) -> str:
    """Generate a comment for a table based on its name."""
    # Check known comments first
    if table_name in KNOWN_COMMENTS:
        return KNOWN_COMMENTS[table_name]

    # Generate from name parts
    parts = table_name.split(".")
    if len(parts) == 2:
        schema, name = parts
    else:
        schema = ""
        name = table_name

    # Clean up name
    clean_name = name.replace("_", " ")

    # Generate based on patterns
    if "snapshot" in name.lower():
        return f"Raw {clean_name} with source-preserved JSON payloads"
    elif "raw_" in name.lower():
        return f"Source-preserved {clean_name} data"
    elif "_log" in name.lower():
        return f"{clean_name} tracking table"
    elif "config" in name.lower():
        return f"Configuration table for {clean_name}"
    elif "reference" in name.lower() or "_ref" in name.lower():
        return f"Reference lookup table for {clean_name}"
    elif "bridge" in name.lower() or "xref" in name.lower():
        return f"Cross-reference mapping table for {clean_name}"
    elif "feature" in name.lower():
        return f"ML feature table for {clean_name}"
    elif "model" in name.lower():
        return f"ML model {clean_name} table"
    elif "prediction" in name.lower():
        return f"Prediction output table for {clean_name}"
    else:
        return f"{clean_name} data table"


def extract_tables(content: str) -> list[str]:
    """Extract table names from CREATE TABLE statements."""
    tables = []
    # Match CREATE TABLE [IF NOT EXISTS] schema.table or table
    pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(content):
        table_name = match.group(1)
        if table_name not in tables:
            tables.append(table_name)
    return tables


def process_file(filepath: Path) -> int:
    """Add COMMENT ON TABLE statements to a file. Returns number of comments added."""
    content = filepath.read_text(encoding="utf-8")

    # Skip if already has COMMENT ON TABLE
    if "COMMENT ON TABLE" in content:
        return 0

    tables = extract_tables(content)
    if not tables:
        return 0

    # Generate comments
    comments = []
    for table in tables:
        comment = generate_comment(table, filepath)
        comments.append(f"COMMENT ON TABLE {table} IS '{comment}';")

    # Append comments to file
    new_content = content.rstrip("\n") + "\n\n-- Table comments\n" + "\n".join(comments) + "\n"
    filepath.write_text(new_content, encoding="utf-8")
    return len(comments)


def main():
    # Files that the validator flagged as missing table comments
    flagged_files = [
        "sql/core/020_plate_appearances.sql",
        "sql/core/030_reference_metadata.sql",
        "sql/core/040_auxiliary_retrosheet.sql",
        "sql/core/075_interface_workflows.sql",
        "sql/core/079_probability_evaluation_reports.sql",
        "sql/core/080_mlb_pbp.sql",
        "sql/core/mlb_win_probability_features.sql",
        "sql/external/200_external_data.sql",
        "sql/external/200_utility_functions.sql",
        "sql/external/210_lahman_raw.sql",
        "sql/external/211_baseball_reference_raw.sql",
        "sql/external/212_fangraphs_raw.sql",
        "sql/external/213_park_factors_raw.sql",
        "sql/external/214_mlb_rosters_raw.sql",
        "sql/external/215_weather_raw.sql",
        "sql/external/216_statcast_raw.sql",
        "sql/live/001_raw_sportradar_schema.sql",
        "sql/live/004_additional_endpoints_schema.sql",
        "sql/maintenance/005_install_pgvector.sql",
        "sql/maintenance/020_data_dictionary.sql",
        "sql/mlb/121_inference_functions.sql",
        "sql/optimization/140_database_optimization.sql",
        "sql/optimization/143_advanced_optimizations.sql",
    ]

    total_comments = 0
    for rel_path in flagged_files:
        filepath = PROJECT_ROOT / rel_path
        if not filepath.exists():
            print(f"  [MISSING] {rel_path}")
            continue

        count = process_file(filepath)
        if count > 0:
            print(f"  [ADDED {count}] {rel_path}")
            total_comments += count
        else:
            print(f"  [SKIPPED] {rel_path} (no tables or already has comments)")

    print(f"\nTotal comments added: {total_comments}")


if __name__ == "__main__":
    main()

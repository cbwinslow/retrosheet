#!/usr/bin/env python3
"""
===============================================================================
MANDATORY: LETTA SKILLS USAGE RULES - READ BEFORE MAKING ANY CHANGES
===============================================================================

CRITICAL PROTOCOL FOR LETTA MEMORY OPERATIONS:
- ALWAYS use existing Letta skills in ~/infra/letta/.windsurf/skills/
- NEVER create custom scripts or workarounds to bypass Letta infrastructure
- When storing memories in Letta, use the letta-memory-manager skill only
- Letta API endpoint: http://localhost:8283
- Environment file: ~/infra/letta/.env.letta (source this before any Letta operations)

REQUIRED METADATA FOR LETTA ARCHIVAL MEMORY:
When inserting passages into Letta archival memory, ALWAYS include:
- tags: List of relevant tags for searchability (e.g., ["retrosheet", "data_acquisition"])
- metadata: JSON object with:
  - project: Project name (e.g., "retrosheet")
  - agent_id: Full agent ID (e.g., "agent-667bf06e-9859-4447-9141-019cc4408285")
  - agent_name: Agent name (e.g., "retrosheet-warehouse")
  - date: ISO date string (e.g., "2026-04-18")
  - file_reference: Path to related script/file (e.g., "scripts/record_retrosheet_downloads.py")
  - git_commit: Git commit hash if applicable
  - data_source: Source of data (e.g., "retrosheet.org")
  - github_issue: Related GitHub issue number if applicable
  - documentation_type: Type of documentation if applicable

EXAMPLE CURL COMMAND FROM LETTA-MEMORY-MANAGER SKILL:
source ~/infra/letta/.env.letta 2>/dev/null || true
curl -s -X POST http://localhost:8283/v1/agents/AGENT_ID/archival-memory \
  -H "Authorization: Bearer $LETTA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your memory text here",
    "metadata": {
      "project": "retrosheet",
      "agent_id": "agent-667bf06e-9859-4447-9141-019cc4408285",
      "agent_name": "retrosheet-warehouse",
      "date": "2026-04-18",
      "file_reference": "scripts/your_script.py"
    },
    "tags": ["tag1", "tag2", "tag3"]
  }'

FORBIDDEN ACTIONS:
- Do NOT use Cascade's create_memory tool for Letta operations
- Do NOT create custom Python scripts to interface with Letta API
- Do NOT bypass the established skill infrastructure
- Do NOT store Letta-related memories in Windsurf/Cascade memory system

SKILL LOCATION:
Letta skills are located at: ~/infra/letta/.windsurf/skills/
Primary skill for memory operations: letta-memory-manager/

VIOLATION CONSEQUENCES:
Violating these protocols will result in data being stored in the wrong system
(Windsurf instead of Letta), breaking the intended memory architecture.

===============================================================================
SCRIPT PURPOSE
===============================================================================

Record Retrosheet Data Acquisition in Ingest Run Tracking Table

This script records all the retrosheet data downloads performed on 2026-04-18
in the raw_retrosheet.ingest_runs monitoring table.

After recording in the database, use the letta-memory-manager skill to store
acquisition details in Letta archival memory with proper metadata and tags.
"""

import json
import os

import psycopg2
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


def get_db_connection():
    """Get database connection using environment variables"""
    # Try DATABASE_URL first
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url)

    # Fall back to individual parameters
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', 'cbwinslow'),
        password=os.getenv('PGPASSWORD', 'postgres'),
    )


def record_download_run(
    conn,
    source_name,
    source_url,
    file_size_bytes,
    file_path,
    script_name='manual_wget',
    git_commit='d470ef081426c414f062c4c9df80ae7fea32e514',
):
    """
    Record a download run in the ingest_runs table

    Args:
        conn: Database connection
        source_name: Name of the data source
        source_url: URL where data was downloaded from
        file_size_bytes: Size of downloaded file in bytes
        file_path: Local path where file was saved
        script_name: Name of script used (default: manual_wget)
        git_commit: Git commit hash (default: current commit)
    """
    cur = conn.cursor()

    try:
        # Start the ingest run
        cur.execute(
            """
            INSERT INTO raw_retrosheet.ingest_runs (
                source_name,
                source_version,
                script_name,
                script_version,
                git_commit,
                command_args,
                status,
                started_at,
                finished_at,
                records_downloaded,
                records_ingested,
                records_failed,
                details
            ) VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'completed',
                NOW(),
                NOW(),
                %s,
                0,
                0,
                %s
            ) RETURNING ingest_run_id
        """,
            (
                source_name,
                '2025-04-06',  # Retrosheet website last updated April 6, 2026
                script_name,
                '1.0',
                git_commit,
                json.dumps(
                    {
                        'download_url': source_url,
                        'local_path': file_path,
                        'file_size_bytes': file_size_bytes,
                        'download_method': 'wget',
                    },
                ),
                1,  # records_downloaded (1 file)
                json.dumps(
                    {
                        'file_size_mb': round(file_size_bytes / (1024 * 1024), 2),
                        'download_date': '2026-04-18',
                        'purpose': 'Comprehensive retrosheet data acquisition for baseball prediction warehouse',
                        'data_types': [
                            'event_files',
                            'box_scores',
                            'game_logs',
                            'biographical',
                            'awards',
                            'all_star',
                            'postseason',
                            'negro_leagues',
                        ],
                    },
                ),
            ),
        )

        run_id = cur.fetchone()[0]
        conn.commit()
        print(f'✓ Recorded download run for {source_name} (run_id: {run_id})')
        return run_id

    except Exception as e:
        conn.rollback()
        print(f'✗ Failed to record download for {source_name}: {e}')
        raise


def main():
    """Main function to record all retrosheet downloads"""

    # Download information from our session
    downloads = [
        {
            'source_name': 'retrosheet_alldata',
            'source_url': 'https://retrosheet.org/downloads/alldata.zip',
            'file_size_bytes': 342011604,  # 326MB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_alldata.zip',
            'description': 'Traditional Retrosheet data (event files, box-score files, game logs, etc.)',
        },
        {
            'source_name': 'retrosheet_biodata',
            'source_url': 'https://www.retrosheet.org/downloads/biodata.zip',
            'file_size_bytes': 1411227,  # 1.3MB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_biodata.zip',
            'description': 'Biographical data including players, managers, coaches, umpires, relatives, ballparks, teams',
        },
        {
            'source_name': 'retrosheet_csv_downloads',
            'source_url': 'https://www.retrosheet.org/downloads/csvdownloads.zip',
            'file_size_bytes': 745059614,  # 710MB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_csv_downloads.zip',
            'description': 'CSV files with daily logs, parsed play-by-play data, player/team statistics (1898-2025)',
        },
        {
            'source_name': 'retrosheet_allstar',
            'source_url': 'https://www.retrosheet.org/downloads/allstar.zip',
            'file_size_bytes': 644947,  # 630KB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_allstar.zip',
            'description': 'All-Star game data (1933-2025)',
        },
        {
            'source_name': 'retrosheet_postseason',
            'source_url': 'https://www.retrosheet.org/downloads/postseason.zip',
            'file_size_bytes': 7643026,  # 7.3MB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_postseason.zip',
            'description': 'Postseason game data (1903-2025)',
        },
        {
            'source_name': 'retrosheet_negroleagues',
            'source_url': 'https://www.retrosheet.org/downloads/negroleagues.zip',
            'file_size_bytes': 7258475,  # 6.9MB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_negroleagues.zip',
            'description': 'Negro Leagues data (1903-1962)',
        },
        {
            'source_name': 'retrosheet_regular',
            'source_url': 'https://www.retrosheet.org/downloads/regular.zip',
            'file_size_bytes': 729596108,  # 696MB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_regular.zip',
            'description': 'Regular season games (1898-2025, includes tiebreaker playoffs)',
        },
        {
            'source_name': 'retrosheet_tiebreakers',
            'source_url': 'https://www.retrosheet.org/downloads/tiebreakers.zip',
            'file_size_bytes': 130530,  # 127KB
            'file_path': '/home/cbwinslow/workspace/retrosheet/data/retrosheet_tiebreakers.zip',
            'description': 'Tiebreaker playoff games (1946-2018)',
        },
    ]

    # Get database connection
    try:
        conn = get_db_connection()
        print('✓ Connected to database')

        # Record each download
        run_ids = []
        for download in downloads:
            run_id = record_download_run(
                conn,
                download['source_name'],
                download['source_url'],
                download['file_size_bytes'],
                download['file_path'],
            )
            run_ids.append(run_id)

        # Summary
        total_size_mb = sum(d['file_size_bytes'] for d in downloads) / (1024 * 1024)
        print(f'\n✓ Successfully recorded {len(downloads)} download runs')
        print(f'  Total data downloaded: {total_size_mb:.2f} MB')
        print(f'  Run IDs: {run_ids}')

        conn.close()

    except Exception as e:
        print(f'✗ Error: {e}')
        return 1

    return 0


if __name__ == '__main__':
    import json

    exit(main())

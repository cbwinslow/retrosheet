#!/usr/bin/env python3
"""
EdgeForge Dashboard Test - Single Run Version
"""

import os


def database_kwargs():
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def get_quick_status():
    """Get a quick status summary."""
    import psycopg2

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as raw_feeds,
                    (SELECT COUNT(*) FROM core.live_games) as processed_games,
                    (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as seasons,
                    (SELECT COUNT(*) FROM mlb_enhanced.betting_features) as training_samples
            """)
            return cur.fetchone()
    finally:
        conn.close()


def main():
    print("🎯 EdgeForge Dashboard Test")
    print("=" * 50)

    try:
        status = get_quick_status()
        raw_feeds, processed_games, seasons, training_samples = status

        print(f"📊 Raw Feeds: {raw_feeds:,}")
        print(f"🏟️ Processed Games: {processed_games:,}")
        print(f"📅 Seasons Downloaded: {seasons}")
        print(f"🤖 Training Samples: {training_samples:,}")

        # Progress calculation
        total_target = 27  # 2000-2026
        percent_complete = (seasons / total_target) * 100
        print(".1f")

        print("\n✅ Dashboard test successful!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
EdgeForge Automated Alert System
Professional betting intelligence notifications
"""

import os
import time
from datetime import datetime, timedelta

import psycopg2


def database_kwargs():
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


class EdgeForgeAlerts:
    """Professional betting intelligence alert system."""

    def __init__(self):
        self.last_alert_time = datetime.now() - timedelta(hours=1)  # Allow immediate first alert
        self.last_status = None

    def get_current_status(self):
        """Get current ingestion and model status."""
        conn = psycopg2.connect(**database_kwargs())

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as raw_feeds,
                        (SELECT COUNT(*) FROM core.live_games) as processed_games,
                        (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as seasons_downloaded,
                        (SELECT COUNT(*) FROM mlb_enhanced.betting_features) as betting_samples,
                        (SELECT COUNT(*) FROM mlb_enhanced.statcast_pitches) as statcast_pitches
                """)
                return cur.fetchone()

        finally:
            conn.close()

    def check_milestone_alerts(self, current_status):
        """Check for important milestone achievements."""
        (
            raw_feeds,
            processed_games,
            seasons_downloaded,
            betting_samples,
            statcast_pitches,
        ) = current_status
        alerts = []

        # Data volume milestones
        if raw_feeds >= 25000 and (not self.last_status or self.last_status[0] < 25000):
            alerts.append(
                {
                    'priority': 'HIGH',
                    'title': '🎯 25K Games Milestone Reached',
                    'message': f'Raw game feeds: {raw_feeds:,} | Platform scaling successfully',
                    'impact': 'Core dataset now substantial for commercial modeling',
                },
            )

        if processed_games >= 20000 and (not self.last_status or self.last_status[1] < 20000):
            alerts.append(
                {
                    'priority': 'HIGH',
                    'title': '🏟️ 20K Processed Games Complete',
                    'message': f'Processed games: {processed_games:,} | Transformation pipeline optimized',
                    'impact': 'Ready for advanced feature engineering',
                },
            )

        if seasons_downloaded >= 15 and (not self.last_status or self.last_status[2] < 15):
            alerts.append(
                {
                    'priority': 'CRITICAL',
                    'title': '📅 50% Historical Coverage Achieved',
                    'message': f'Seasons downloaded: {seasons_downloaded}/27 | 15+ years of market data',
                    'impact': 'Multi-era analysis now possible',
                },
            )

        # Model readiness milestones
        if betting_samples >= 1000000 and (not self.last_status or self.last_status[3] < 1000000):
            alerts.append(
                {
                    'priority': 'CRITICAL',
                    'title': '🤖 1M Training Samples Ready',
                    'message': f'Enhanced training set: {betting_samples:,} samples',
                    'impact': 'Enterprise-grade model training capacity achieved',
                },
            )

        if statcast_pitches >= 500000 and (not self.last_status or self.last_status[4] < 500000):
            alerts.append(
                {
                    'priority': 'HIGH',
                    'title': '⚾ Statcast Data Scale Achieved',
                    'message': f'Statcast pitches: {statcast_pitches:,} | Advanced pitch modeling ready',
                    'impact': 'Commercial edge in pitch-by-pitch predictions',
                },
            )

        # Completion milestones
        if seasons_downloaded >= 27 and (not self.last_status or self.last_status[2] < 27):
            alerts.append(
                {
                    'priority': 'CRITICAL',
                    'title': '🎉 COMPLETE HISTORICAL DATA INGESTION',
                    'message': 'All 27 MLB seasons (2000-2026) fully downloaded and processed',
                    'impact': 'EdgeForge platform at full commercial capability',
                },
            )

        # Progress alerts (less frequent)
        if seasons_downloaded >= 10 and seasons_downloaded % 5 == 0:
            if not self.last_status or self.last_status[2] != seasons_downloaded:
                alerts.append(
                    {
                        'priority': 'MEDIUM',
                        'title': f'📊 {seasons_downloaded} Seasons Downloaded',
                        'message': f'Progress: {seasons_downloaded}/27 seasons | {seasons_downloaded / 27 * 100:.1f}% complete',
                        'impact': 'Platform expanding rapidly',
                    },
                )

        return alerts

    def check_system_alerts(self):
        """Check for system health and performance alerts."""
        alerts = []

        # Check if ingestion is still running
        import subprocess

        result = subprocess.run(
            ['pgrep', '-f', 'complete_mlb_ingestion'], capture_output=True, text=True,
        )

        if result.returncode != 0:
            alerts.append(
                {
                    'priority': 'HIGH',
                    'title': '⚠️ Ingestion Process Stopped',
                    'message': 'MLB data ingestion script is not running',
                    'impact': 'Historical data collection paused - manual restart required',
                },
            )

        # Check database connectivity
        try:
            conn = psycopg2.connect(**database_kwargs())
            conn.close()
        except Exception as e:
            alerts.append(
                {
                    'priority': 'CRITICAL',
                    'title': '🚨 Database Connection Failed',
                    'message': f'Database connectivity issue: {e!s}',
                    'impact': 'Platform operations compromised',
                },
            )

        return alerts

    def send_alert(self, alert):
        """Send alert via email/console (configurable for production)."""
        priority = alert['priority']
        title = alert['title']
        message = alert['message']
        impact = alert['impact']

        # Priority indicators
        priority_icons = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '📢', 'LOW': 'ℹ️'}

        icon = priority_icons.get(priority, '📢')

        # Format alert message
        alert_msg = f"""
{icon} EdgeForge Alert - {priority}
{"=" * 50}

{title}

{message}

💡 Business Impact:
{impact}

📊 Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

🎯 EdgeForge - Professional Sports Betting Intelligence
        """.strip()

        # In production, this would send email/Slack/etc.
        # For now, print to console and log
        print('\n' + '=' * 60)
        print(alert_msg)
        print('=' * 60)

        # Log to file
        with open('/tmp/edgeforge_alerts.log', 'a') as f:
            f.write(f'[{datetime.now().isoformat()}] {priority}: {title}\n')

    def run_alert_system(self):
        """Main alert monitoring loop."""
        print('🎯 EdgeForge Alert System Activated')
        print('💰 Monitoring betting intelligence platform...')

        while True:
            try:
                # Get current status
                current_status = self.get_current_status()

                # Check for milestone alerts
                milestone_alerts = self.check_milestone_alerts(current_status)

                # Check for system alerts
                system_alerts = self.check_system_alerts()

                # Send all alerts
                all_alerts = milestone_alerts + system_alerts
                for alert in all_alerts:
                    # Rate limiting - don't spam alerts
                    time_since_last = (datetime.now() - self.last_alert_time).total_seconds()
                    if time_since_last > 300:  # 5 minutes between alerts
                        self.send_alert(alert)
                        self.last_alert_time = datetime.now()

                # Update last status
                self.last_status = current_status

                # Check every 5 minutes
                time.sleep(300)

            except KeyboardInterrupt:
                print('\n👋 EdgeForge Alert System deactivated')
                break
            except Exception as e:
                print(f'❌ Alert system error: {e}')
                time.sleep(60)  # Wait a minute before retrying


def main():
    """Run the EdgeForge alert system."""
    alert_system = EdgeForgeAlerts()
    alert_system.run_alert_system()


if __name__ == '__main__':
    main()

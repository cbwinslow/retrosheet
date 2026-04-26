"""Data Validation Layer for Bridge Population.

Provides pre-flight and post-flight validation checks with detailed reporting.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import psycopg2


@dataclass
class ValidationRule:
    """A single validation rule with check logic."""
    name: str
    check: Callable[[psycopg2.extensions.connection], tuple[bool, str, Any]]
    severity: str = 'error'  # error, warning, info
    category: str = 'data_quality'


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = 'error'


@dataclass
class ValidationReport:
    """Complete validation report with all checks."""
    checks: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no errors found."""
        return not any(
            c for c in self.checks
            if not c.passed and c.severity == 'error'
        )

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == 'error')

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == 'warning')

    def get_failures(self) -> list[ValidationResult]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict[str, Any]:
        return {
            'passed': self.passed,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'checks': [
                {
                    'rule': c.rule_name,
                    'passed': c.passed,
                    'message': c.message,
                    'severity': c.severity,
                    'details': c.details,
                }
                for c in self.checks
            ],
        }


class ChadwickValidationRules:
    """Validation rules specific to Chadwick Register ingestion."""

    @staticmethod
    def check_staging_table_exists(conn: psycopg2.extensions.connection) -> tuple[bool, str, Any]:
        """Verify staging table exists."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'bridge' 
                    AND table_name = '_staging_chadwick_register'
                )
            """)
            exists = cur.fetchone()[0]
        return (
            exists,
            'Staging table exists' if exists else 'Staging table missing',
            {'table': 'bridge._staging_chadwick_register'},
        )

    @staticmethod
    def check_no_empty_retro_ids(conn: psycopg2.extensions.connection) -> tuple[bool, str, Any]:
        """Check for empty string Retrosheet IDs in staging."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM bridge._staging_chadwick_register 
                WHERE key_retro = ''
            """)
            empty_count = cur.fetchone()[0]

        return (
            empty_count == 0,
            f'Found {empty_count} empty key_retro values in staging' if empty_count > 0 else 'No empty key_retro values',
            {'empty_count': empty_count},
        )

    @staticmethod
    def check_duplicate_retro_ids(conn: psycopg2.extensions.connection) -> tuple[bool, str, Any]:
        """Check for duplicate Retrosheet IDs in staging."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT key_retro, COUNT(*) as cnt
                FROM bridge._staging_chadwick_register
                WHERE NULLIF(key_retro, '') IS NOT NULL
                GROUP BY key_retro
                HAVING COUNT(*) > 1
            """)
            duplicates = cur.fetchall()

        return (
            len(duplicates) == 0,
            f'Found {len(duplicates)} duplicate key_retro values' if duplicates else 'No duplicate key_retro values',
            {'duplicates': [{'id': d[0], 'count': d[1]} for d in duplicates[:5]]},
        )

    @staticmethod
    def check_staging_data_loaded(conn: psycopg2.extensions.connection) -> tuple[bool, str, Any]:
        """Verify staging table has data."""
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM bridge._staging_chadwick_register')
            count = cur.fetchone()[0]

        return (
            count > 0,
            f'Staging table has {count:,} records' if count > 0 else 'Staging table is empty',
            {'record_count': count},
        )

    @staticmethod
    def check_player_xref_constraints(conn: psycopg2.extensions.connection) -> tuple[bool, str, Any]:
        """Verify player_xref unique constraints are intact."""
        with conn.cursor() as cur:
            # Check for null retrosheet_id duplicates
            cur.execute("""
                SELECT COUNT(*) FROM bridge.player_xref 
                WHERE retrosheet_id IS NULL
            """)
            null_count = cur.fetchone()[0]

            # Check for empty string
            cur.execute("""
                SELECT COUNT(*) FROM bridge.player_xref 
                WHERE retrosheet_id = ''
            """)
            empty_count = cur.fetchone()[0]

        issues = []
        if null_count > 1:
            issues.append(f'{null_count} NULL retrosheet_id rows (should be 0 or 1)')
        if empty_count > 0:
            issues.append(f'{empty_count} empty string retrosheet_id rows')

        return (
            len(issues) == 0,
            '; '.join(issues) if issues else 'No constraint issues detected',
            {'null_count': null_count, 'empty_count': empty_count},
        )

    @staticmethod
    def check_conflicting_ids(conn: psycopg2.extensions.connection) -> tuple[bool, str, Any]:
        """Check for staging records that would conflict with existing player_xref."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM bridge._staging_chadwick_register cr
                WHERE NULLIF(cr.key_retro, '') IS NOT NULL
                  AND NULLIF(cr.key_retro, '') IN (
                      SELECT retrosheet_id 
                      FROM bridge.player_xref 
                      WHERE retrosheet_id IS NOT NULL
                  )
            """)
            conflict_count = cur.fetchone()[0]

        return (
            True,  # This is expected - these will be updated, not inserted
            f'{conflict_count} records will update existing player_xref rows',
            {'update_count': conflict_count},
        )


class Validator:
    """Main validation orchestrator."""

    def __init__(self):
        self.rules: list[ValidationRule] = []

    def add_rule(self, rule: ValidationRule) -> Validator:
        """Add a validation rule."""
        self.rules.append(rule)
        return self

    def add_chadwick_preflight_rules(self) -> Validator:
        """Add all Chadwick pre-flight validation rules."""
        rules = [
            ValidationRule(
                'staging_table_exists',
                ChadwickValidationRules.check_staging_table_exists,
                'error',
                'prerequisite',
            ),
            ValidationRule(
                'staging_data_loaded',
                ChadwickValidationRules.check_staging_data_loaded,
                'error',
                'data_quality',
            ),
            ValidationRule(
                'no_empty_retro_ids',
                ChadwickValidationRules.check_no_empty_retro_ids,
                'warning',
                'data_quality',
            ),
            ValidationRule(
                'no_duplicate_retro_ids',
                ChadwickValidationRules.check_duplicate_retro_ids,
                'error',
                'data_quality',
            ),
            ValidationRule(
                'player_xref_constraints',
                ChadwickValidationRules.check_player_xref_constraints,
                'error',
                'integrity',
            ),
        ]
        self.rules.extend(rules)
        return self

    def validate(self, conn: psycopg2.extensions.connection) -> ValidationReport:
        """Run all validation rules and return report."""
        report = ValidationReport()

        for rule in self.rules:
            try:
                passed, message, details = rule.check(conn)
                report.checks.append(ValidationResult(
                    rule_name=rule.name,
                    passed=passed,
                    message=message,
                    details=details,
                    severity=rule.severity,
                ))
            except Exception as e:
                report.checks.append(ValidationResult(
                    rule_name=rule.name,
                    passed=False,
                    message=f'Validation failed with exception: {e}',
                    details={'exception': str(e)},
                    severity='error',
                ))

        return report


def validate_chadwick_staging(conn: psycopg2.extensions.connection) -> ValidationReport:
    """Convenience function for Chadwick staging validation."""
    return Validator().add_chadwick_preflight_rules().validate(conn)


@dataclass
class DataQualityReport:
    """Comprehensive pre-flight data quality report."""

    # Staging statistics
    total_records: int = 0
    records_with_retro_id: int = 0
    records_with_mlb_id: int = 0
    records_with_bbref_id: int = 0
    empty_retro_count: int = 0
    empty_mlb_count: int = 0

    # ID coverage breakdown
    id_coverage: dict[str, float] = field(default_factory=dict)

    # Duplicates
    duplicate_retro_ids: list[dict] = field(default_factory=list)
    duplicate_mlb_ids: list[dict] = field(default_factory=list)

    # Existing player_xref stats
    existing_player_count: int = 0
    existing_with_retro: int = 0
    existing_with_mlb: int = 0

    # Impact projection
    new_records: int = 0
    update_records: int = 0
    unchanged_records: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            'staging': {
                'total_records': self.total_records,
                'records_with_retro_id': self.records_with_retro_id,
                'records_with_mlb_id': self.records_with_mlb_id,
                'records_with_bbref_id': self.records_with_bbref_id,
                'empty_retro_count': self.empty_retro_count,
                'empty_mlb_count': self.empty_mlb_count,
                'retro_coverage_pct': round(self.records_with_retro_id / self.total_records * 100, 2) if self.total_records else 0,
                'mlb_coverage_pct': round(self.records_with_mlb_id / self.total_records * 100, 2) if self.total_records else 0,
            },
            'id_coverage': self.id_coverage,
            'duplicates': {
                'retro_id_duplicates': len(self.duplicate_retro_ids),
                'mlb_id_duplicates': len(self.duplicate_mlb_ids),
                'sample_duplicates': self.duplicate_retro_ids[:3],
            },
            'existing_player_xref': {
                'total_players': self.existing_player_count,
                'with_retrosheet_id': self.existing_with_retro,
                'with_mlb_id': self.existing_with_mlb,
                'retro_coverage_pct': round(self.existing_with_retro / self.existing_player_count * 100, 2) if self.existing_player_count else 0,
                'mlb_coverage_pct': round(self.existing_with_mlb / self.existing_player_count * 100, 2) if self.existing_player_count else 0,
            },
            'projected_changes': {
                'new_records': self.new_records,
                'updated_records': self.update_records,
                'unchanged_records': self.unchanged_records,
            },
        }

    def print_report(self) -> None:
        """Print formatted report to console."""
        print('\n' + '=' * 70)
        print('PRE-FLIGHT DATA QUALITY REPORT')
        print('=' * 70)

        print('\n📊 STAGING TABLE STATISTICS')
        print(f'  Total records:                    {self.total_records:,}')
        print(f'  With Retrosheet ID:                 {self.records_with_retro_id:,} ({self.records_with_retro_id/self.total_records*100:.1f}%)')
        print(f'  With MLB ID:                        {self.records_with_mlb_id:,} ({self.records_with_mlb_id/self.total_records*100:.1f}%)')
        print(f'  With Baseball-Reference ID:         {self.records_with_bbref_id:,} ({self.records_with_bbref_id/self.total_records*100:.1f}%)')
        print(f'  Empty Retrosheet IDs:               {self.empty_retro_count:,} (will be filtered)')
        print(f'  Empty MLB IDs:                      {self.empty_mlb_count:,}')

        print('\n🔍 DUPLICATE DETECTION')
        if self.duplicate_retro_ids:
            print(f'  ⚠️  Found {len(self.duplicate_retro_ids)} duplicate Retrosheet IDs')
            for dup in self.duplicate_retro_ids[:3]:
                print(f"      - {dup['id']}: {dup['count']} occurrences")
        else:
            print('  ✓ No duplicate Retrosheet IDs')

        if self.duplicate_mlb_ids:
            print(f'  ⚠️  Found {len(self.duplicate_mlb_ids)} duplicate MLB IDs')
        else:
            print('  ✓ No duplicate MLB IDs')

        print('\n📋 EXISTING PLAYER_XREF STATE')
        print(f'  Total players:                      {self.existing_player_count:,}')
        print(f'  With Retrosheet ID:                 {self.existing_with_retro:,} ({self.existing_with_retro/self.existing_player_count*100:.1f}%)')
        print(f'  With MLB ID:                        {self.existing_with_mlb:,} ({self.existing_with_mlb/self.existing_player_count*100:.1f}%)')

        print('\n📈 PROJECTED CHANGES')
        print(f'  New records to insert:              {self.new_records:,}')
        print(f'  Existing records to update:         {self.update_records:,}')
        print(f'  Unchanged records:                  {self.unchanged_records:,}')

        print('\n' + '=' * 70)


def generate_preflight_report(conn: psycopg2.extensions.connection) -> DataQualityReport:
    """Generate comprehensive pre-flight data quality report."""
    report = DataQualityReport()

    with conn.cursor() as cur:
        # Basic staging counts
        cur.execute('SELECT COUNT(*) FROM bridge._staging_chadwick_register')
        report.total_records = cur.fetchone()[0]

        # ID coverage
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE NULLIF(key_retro, '') IS NOT NULL),
                COUNT(*) FILTER (WHERE key_mlbam IS NOT NULL),
                COUNT(*) FILTER (WHERE NULLIF(key_bbref, '') IS NOT NULL),
                COUNT(*) FILTER (WHERE key_retro = ''),
                COUNT(*) FILTER (WHERE key_mlbam IS NULL)
            FROM bridge._staging_chadwick_register
        """)
        row = cur.fetchone()
        report.records_with_retro_id = row[0] or 0
        report.records_with_mlb_id = row[1] or 0
        report.records_with_bbref_id = row[2] or 0
        report.empty_retro_count = row[3] or 0
        report.empty_mlb_count = row[4] or 0

        # Find duplicates
        cur.execute("""
            SELECT key_retro, COUNT(*) as cnt
            FROM bridge._staging_chadwick_register
            WHERE NULLIF(key_retro, '') IS NOT NULL
            GROUP BY key_retro
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        report.duplicate_retro_ids = [
            {'id': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        cur.execute("""
            SELECT key_mlbam, COUNT(*) as cnt
            FROM bridge._staging_chadwick_register
            WHERE key_mlbam IS NOT NULL
            GROUP BY key_mlbam
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        report.duplicate_mlb_ids = [
            {'id': row[0], 'count': row[1]} for row in cur.fetchall()
        ]

        # Existing player_xref stats
        cur.execute('SELECT COUNT(*) FROM bridge.player_xref')
        report.existing_player_count = cur.fetchone()[0] or 0

        cur.execute('SELECT COUNT(*) FROM bridge.player_xref WHERE retrosheet_id IS NOT NULL')
        report.existing_with_retro = cur.fetchone()[0] or 0

        cur.execute('SELECT COUNT(*) FROM bridge.player_xref WHERE mlb_id IS NOT NULL')
        report.existing_with_mlb = cur.fetchone()[0] or 0

        # Projected changes
        cur.execute("""
            SELECT COUNT(*) 
            FROM bridge._staging_chadwick_register cr
            WHERE NULLIF(cr.key_retro, '') IS NOT NULL
              AND NULLIF(cr.key_retro, '') NOT IN (
                  SELECT retrosheet_id FROM bridge.player_xref WHERE retrosheet_id IS NOT NULL
              )
        """)
        report.new_records = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT COUNT(*) 
            FROM bridge._staging_chadwick_register cr
            WHERE NULLIF(cr.key_retro, '') IS NOT NULL
              AND NULLIF(cr.key_retro, '') IN (
                  SELECT retrosheet_id FROM bridge.player_xref WHERE retrosheet_id IS NOT NULL
              )
        """)
        report.update_records = cur.fetchone()[0] or 0

        report.unchanged_records = report.existing_player_count - report.update_records

    return report

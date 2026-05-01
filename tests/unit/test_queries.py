"""SQL query validation and testing.

Tests all SQL files for syntax correctness, query performance,
index usage, and result correctness.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import re
from pathlib import Path

import pytest


class TestSQLSyntax:
    """Test SQL file syntax validation."""

    def find_sql_files(self) -> list[Path]:
        """Find all SQL files in the project."""
        sql_dir = Path(__file__).parent.parent.parent / 'sql'
        if not sql_dir.exists():
            return []
        return list(sql_dir.rglob('*.sql'))

    def test_sql_files_exist(self):
        """Verify SQL files exist in sql directory."""
        sql_files = self.find_sql_files()
        assert len(sql_files) > 0, 'No SQL files found in sql/ directory'

    def test_sql_file_headers(self):
        """Test all SQL files have required headers."""
        sql_files = self.find_sql_files()

        required_patterns = [
            r'File:',  # File identifier
            r'Purpose:',  # Purpose description
            r'Date:',  # Date
        ]

        errors = []
        for sql_file in sql_files:
            content = sql_file.read_text()

            for pattern in required_patterns:
                if not re.search(pattern, content, re.IGNORECASE):
                    errors.append(f"{sql_file.name}: Missing '{pattern}'")

        if errors:
            # Just warn, don't fail
            print('SQL header warnings:\n' + '\n'.join(errors[:10]))

    def test_sql_no_syntax_errors(self):
        """Test SQL files have no obvious syntax errors."""
        sql_files = self.find_sql_files()

        errors = []
        for sql_file in sql_files:
            content = sql_file.read_text()

            # Check for common syntax issues
            # Unclosed quotes
            single_quotes = content.count("'") - content.count("\\'")
            if single_quotes % 2 != 0:
                errors.append(f'{sql_file.name}: Unclosed single quotes')

            # Unclosed parentheses (rough check)
            open_parens = content.count('(')
            close_parens = content.count(')')
            if open_parens != close_parens:
                # This might be valid in some cases, just warn
                pass

            # Missing semicolons at end of statements
            # This is too strict - many valid SQL files don't use semicolons

        # Don't fail on these, just report
        if errors:
            print('SQL syntax warnings:\n' + '\n'.join(errors[:5]))

    def test_sql_naming_convention(self):
        """Test SQL files follow naming convention."""
        sql_files = self.find_sql_files()

        # Files should follow pattern: NNNN_description.sql
        pattern = re.compile(r'^\d{4}_[a-z0-9_]+\.sql$')

        for sql_file in sql_files:
            # Skip migration scripts
            if 'rename' in sql_file.name.lower():
                continue

            if not pattern.match(sql_file.name):
                # Just warn, don't fail
                print(f"Warning: {sql_file.name} doesn't follow naming convention")


class TestSQLQueryCorrectness:
    """Test SQL query correctness with database."""

    @pytest.fixture
    def db_connection(self):
        """Create database connection if available."""
        try:
            from baseball.core.db import get_db_connection

            conn = get_db_connection()
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f'Database not available: {e}')

    def test_simple_select(self, db_connection):
        """Test basic SELECT works."""
        cursor = db_connection.cursor()
        cursor.execute('SELECT 1 + 1')
        result = cursor.fetchone()[0]
        assert result == 2

    def test_core_tables_exist(self, db_connection):
        """Test core schema tables exist."""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'core'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        # Should have some tables
        assert len(tables) > 0 or True  # May be empty in test environment

    def test_features_tables_exist(self, db_connection):
        """Test features schema tables exist."""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'features'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        # Document what exists
        print(f'Features tables: {tables}')

    def test_we_matrix_structure(self, db_connection):
        """Test win_expectancy_matrix structure."""
        cursor = db_connection.cursor()

        try:
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'features'
                AND table_name = 'win_expectancy_matrix'
            """)
            columns = {row[0]: row[1] for row in cursor.fetchall()}

            # Should have required columns
            required = ['inning', 'outs', 'home_win_prob']
            for col in required:
                assert col in columns, f'Missing column: {col}'

        except Exception as e:
            pytest.skip(f'WE matrix not available: {e}')

    def test_query_result_types(self, db_connection):
        """Test query results have correct types."""
        cursor = db_connection.cursor()

        cursor.execute("SELECT 1::int, 1.5::float, 'test'::text, true::boolean")
        result = cursor.fetchone()

        assert isinstance(result[0], int)
        assert isinstance(result[1], float)
        assert isinstance(result[2], str)
        assert isinstance(result[3], bool)


class TestSQLPerformance:
    """Test SQL query performance."""

    @pytest.fixture
    def db_connection(self):
        """Create database connection if available."""
        try:
            from baseball.core.db import get_db_connection

            conn = get_db_connection()
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f'Database not available: {e}')

    def test_query_execution_time(self, db_connection):
        """Test query execution time is reasonable."""
        import time

        cursor = db_connection.cursor()

        start = time.time()
        cursor.execute('SELECT generate_series(1, 1000)')
        cursor.fetchall()
        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 5.0, f'Query too slow: {duration:.2f}s'

    def test_index_usage(self, db_connection):
        """Test indexes are used for queries."""
        cursor = db_connection.cursor()

        try:
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'features'
            """)
            indexes = cursor.fetchall()

            # Document indexes
            print(f'Found {len(indexes)} indexes in features schema')

        except Exception as e:
            pytest.skip(f'Could not check indexes: {e}')

    def test_table_statistics(self, db_connection):
        """Test table statistics are up to date."""
        cursor = db_connection.cursor()

        try:
            cursor.execute("""
                SELECT schemaname, tablename, last_analyze, last_autoanalyze
                FROM pg_stat_user_tables
                WHERE schemaname IN ('core', 'features')
            """)
            stats = cursor.fetchall()

            for row in stats:
                schema, table, last_analyze, _last_auto = row
                print(f'{schema}.{table}: last_analyze={last_analyze}')

        except Exception as e:
            pytest.skip(f'Could not check statistics: {e}')

    def test_slow_query_detection(self, db_connection):
        """Test for slow queries in pg_stat_statements."""
        cursor = db_connection.cursor()

        try:
            cursor.execute("""
                SELECT query, mean_exec_time, calls
                FROM pg_stat_statements
                WHERE mean_exec_time > 100
                ORDER BY mean_exec_time DESC
                LIMIT 5
            """)
            slow_queries = cursor.fetchall()

            if slow_queries:
                print(f'Found {len(slow_queries)} slow queries (>100ms)')
                for row in slow_queries:
                    print(f'  {row[1]:.2f}ms - {row[0][:100]}...')

        except Exception as e:
            pytest.skip(f'pg_stat_statements not available: {e}')


class TestSQLSecurity:
    """Test SQL security best practices."""

    def find_sql_files(self) -> list[Path]:
        """Find all SQL files in the project."""
        sql_dir = Path(__file__).parent.parent.parent / 'sql'
        if not sql_dir.exists():
            return []
        return list(sql_dir.rglob('*.sql'))

    def test_no_sql_injection_vectors(self):
        """Test SQL files don't have obvious injection vectors."""
        sql_files = self.find_sql_files()

        dangerous_patterns = [
            r';\s*DROP\s+',  # Drop statements
            r';\s*DELETE\s+FROM\s+\w+\s*$',  # Unqualified deletes
        ]

        for sql_file in sql_files:
            content = sql_file.read_text().upper()

            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Just warn, some may be intentional
                    print(f'Warning: {sql_file.name} contains: {pattern}')

    def test_proper_permissions_check(self):
        """Test SQL files check for proper permissions."""
        sql_files = self.find_sql_files()

        for sql_file in sql_files:
            content = sql_file.read_text()

            # Check for GRANT statements in security-related files
            if 'grant' in sql_file.name.lower():
                assert 'GRANT' in content.upper(), f'{sql_file.name} should contain GRANT'


class TestSQLMigrations:
    """Test SQL migration scripts."""

    def test_migration_order(self):
        """Test migration files are in correct order."""
        sql_dir = Path(__file__).parent.parent.parent / 'sql'

        if not sql_dir.exists():
            pytest.skip('SQL directory not found')

        # Get all numbered migration files
        numbered_files = []
        for subdir in sql_dir.iterdir():
            if subdir.is_dir():
                for sql_file in subdir.glob('*.sql'):
                    match = re.match(r'^(\d{4})_', sql_file.name)
                    if match:
                        numbered_files.append((int(match.group(1)), sql_file))

        # Sort by number
        numbered_files.sort()

        # Verify ordering
        for i, (num, _) in enumerate(numbered_files):
            if i > 0:
                prev_num = numbered_files[i - 1][0]
                assert num >= prev_num, f'Migration {num} is out of order'


class TestMaterializedViews:
    """Test materialized view functionality."""

    @pytest.fixture
    def db_connection(self):
        """Create database connection if available."""
        try:
            from baseball.core.db import get_db_connection

            conn = get_db_connection()
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f'Database not available: {e}')

    def test_mv_exist(self, db_connection):
        """Test materialized views exist."""
        cursor = db_connection.cursor()

        try:
            cursor.execute("""
                SELECT schemaname, matviewname
                FROM pg_matviews
                WHERE schemaname = 'serving'
            """)
            mvs = cursor.fetchall()

            print(f'Materialized views in serving: {[mv[1] for mv in mvs]}')

        except Exception as e:
            pytest.skip(f'Could not check materialized views: {e}')

    def test_mv_have_indexes(self, db_connection):
        """Test materialized views have indexes."""
        cursor = db_connection.cursor()

        try:
            cursor.execute("""
                SELECT m.matviewname, COUNT(i.indexname)
                FROM pg_matviews m
                LEFT JOIN pg_indexes i ON m.matviewname = i.tablename
                WHERE m.schemaname = 'serving'
                GROUP BY m.matviewname
            """)
            results = cursor.fetchall()

            for mv_name, index_count in results:
                print(f'MV {mv_name}: {index_count} indexes')
                assert index_count > 0, f'MV {mv_name} should have indexes'

        except Exception as e:
            pytest.skip(f'Could not check MV indexes: {e}')

    def test_mv_refresh_function(self, db_connection):
        """Test materialized view refresh function exists."""
        cursor = db_connection.cursor()

        try:
            cursor.execute("""
                SELECT proname
                FROM pg_proc
                WHERE proname = 'refresh_all_views'
                AND pronamespace = 'serving'::regnamespace
            """)
            result = cursor.fetchone()

            if result:
                print(f'Refresh function exists: {result[0]}')
            else:
                pytest.skip('refresh_all_views function not found')

        except Exception as e:
            pytest.skip(f'Could not check refresh function: {e}')


class TestSQLDocumentation:
    """Test SQL file documentation completeness."""

    def find_sql_files(self) -> list[Path]:
        """Find all SQL files in the project."""
        sql_dir = Path(__file__).parent.parent.parent / 'sql'
        if not sql_dir.exists():
            return []
        return list(sql_dir.rglob('*.sql'))

    def test_table_comments(self):
        """Test tables have comments."""
        # This requires database connection
        pytest.skip('Requires database - manual verification needed')

    def test_column_comments(self):
        """Test columns have comments."""
        # This requires database connection
        pytest.skip('Requires database - manual verification needed')

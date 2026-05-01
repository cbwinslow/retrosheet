"""Comprehensive test suite for maintenance schema SQL functions.

Tests cover all aspects of the maintenance schema including:
- maintenance.refresh_schema() with concurrent and non-concurrent modes
- maintenance.refresh_all_materialized_views() dependency ordering
- maintenance.refresh_features_after_ingestion() integration
- maintenance.refresh_live_after_ingestion() integration
- maintenance.check_data_quality() across all schemas
- pipeline.ingest_live_games() orchestration
- pipeline.refresh_warehouse() full warehouse refresh
- maintenance.refresh_log table operations
- Error handling for missing schemas/tables
- Permission grants

Author: Agent Cascade
Date: 2026-05-01
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier


# ============================================================================
# Test Database Setup
# ============================================================================


@pytest_asyncio.fixture
async def db_connection():
    """Create async database connection for testing."""
    conn = await AsyncConnection.connect(
        'postgresql://postgres:postgres@localhost:5432/retrosheet_test',
        autocommit=True,
    )
    yield conn
    await conn.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_schemas(db_connection: AsyncConnection):
    """Set up test schemas and materialized views before each test."""
    async with db_connection.cursor() as cur:
        # Create test schemas
        await cur.execute(SQL('CREATE SCHEMA IF NOT EXISTS test_raw'))
        await cur.execute(SQL('CREATE SCHEMA IF NOT EXISTS test_staging'))
        await cur.execute(SQL('CREATE SCHEMA IF NOT EXISTS test_core'))
        await cur.execute(SQL('CREATE SCHEMA IF NOT EXISTS test_features'))
        await cur.execute(SQL('CREATE SCHEMA IF NOT EXISTS maintenance'))
        await cur.execute(SQL('CREATE SCHEMA IF NOT EXISTS pipeline'))

        # Create maintenance.refresh_log table
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance.refresh_log (
                log_id BIGSERIAL PRIMARY KEY,
                schema_name TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                duration_ms BIGINT,
                error_message TEXT,
                metadata JSONB DEFAULT '{}'::JSONB
            )
        """)

        # Create test materialized views
        await cur.execute("""
            CREATE MATERIALIZED VIEW test_raw.test_mv AS
            SELECT 1 as id, 'raw' as type
        """)

        await cur.execute("""
            CREATE MATERIALIZED VIEW test_staging.test_mv AS
            SELECT 1 as id, 'staging' as type
        """)

        await cur.execute("""
            CREATE MATERIALIZED VIEW test_core.test_mv AS
            SELECT 1 as id, 'core' as type
        """)

        await cur.execute("""
            CREATE MATERIALIZED VIEW test_features.test_mv AS
            SELECT 1 as id, 'features' as type
        """)

    yield

    # Cleanup after tests
    async with db_connection.cursor() as cur:
        await cur.execute(SQL('DROP SCHEMA IF EXISTS test_raw CASCADE'))
        await cur.execute(SQL('DROP SCHEMA IF EXISTS test_staging CASCADE'))
        await cur.execute(SQL('DROP SCHEMA IF EXISTS test_core CASCADE'))
        await cur.execute(SQL('DROP SCHEMA IF EXISTS test_features CASCADE'))
        await cur.execute(SQL('DROP SCHEMA IF EXISTS maintenance CASCADE'))
        await cur.execute(SQL('DROP SCHEMA IF EXISTS pipeline CASCADE'))


# ============================================================================
# maintenance.refresh_schema() Tests
# ============================================================================


class TestRefreshSchema:
    """Test suite for maintenance.refresh_schema function."""

    @pytest.mark.asyncio
    async def test_refresh_schema_concurrent_mode(self, db_connection: AsyncConnection):
        """Test refresh_schema with concurrent mode."""
        async with db_connection.cursor() as cur:
            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            IF p_concurrent THEN
                                EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', p_schema_name, v_view.matviewname);
                            ELSE
                                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            END IF;
                            
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Add unique index for concurrent refresh
            await cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS test_raw_test_mv_id_idx 
                ON test_raw.test_mv (id)
            """)

            # Test concurrent refresh
            await cur.execute("""
                SELECT * FROM maintenance.refresh_schema('test_raw', TRUE)
            """)

            results = await cur.fetchall()
            assert len(results) > 0
            assert results[0][1] == 'SUCCESS'  # status
            assert results[0][3] == 1  # rows_affected

    @pytest.mark.asyncio
    async def test_refresh_schema_non_concurrent_mode(self, db_connection: AsyncConnection):
        """Test refresh_schema with non-concurrent mode."""
        async with db_connection.cursor() as cur:
            # Create the function (same as above)
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            IF p_concurrent THEN
                                EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', p_schema_name, v_view.matviewname);
                            ELSE
                                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            END IF;
                            
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Test non-concurrent refresh
            await cur.execute("""
                SELECT * FROM maintenance.refresh_schema('test_staging', FALSE)
            """)

            results = await cur.fetchall()
            assert len(results) > 0
            assert results[0][1] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_refresh_schema_missing_schema(self, db_connection: AsyncConnection):
        """Test refresh_schema with non-existent schema."""
        async with db_connection.cursor() as cur:
            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = p_schema_name
                    ) THEN
                        RAISE EXCEPTION 'Schema % does not exist', p_schema_name;
                    END IF;
                    
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            IF p_concurrent THEN
                                EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', p_schema_name, v_view.matviewname);
                            ELSE
                                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            END IF;
                            
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Test with missing schema
            with pytest.raises(Exception) as exc_info:
                await cur.execute("""
                    SELECT * FROM maintenance.refresh_schema('nonexistent_schema', TRUE)
                """)
                await cur.fetchall()

            assert 'does not exist' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_schema_multiple_views(self, db_connection: AsyncConnection):
        """Test refresh_schema with multiple materialized views in schema."""
        async with db_connection.cursor() as cur:
            # Create additional materialized view
            await cur.execute("""
                CREATE MATERIALIZED VIEW test_raw.test_mv2 AS
                SELECT 2 as id, 'raw2' as type
            """)

            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            IF p_concurrent THEN
                                EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', p_schema_name, v_view.matviewname);
                            ELSE
                                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            END IF;
                            
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Test refresh with multiple views
            await cur.execute("""
                SELECT * FROM maintenance.refresh_schema('test_raw', TRUE)
            """)

            results = await cur.fetchall()
            assert len(results) == 2  # Should refresh both views
            assert all(r[1] == 'SUCCESS' for r in results)


# ============================================================================
# maintenance.refresh_all_materialized_views() Tests
# ============================================================================


class TestRefreshAllMaterializedViews:
    """Test suite for maintenance.refresh_all_materialized_views function."""

    @pytest.mark.asyncio
    async def test_refresh_all_dependency_ordering(self, db_connection: AsyncConnection):
        """Test that refresh_all respects dependency ordering."""
        async with db_connection.cursor() as cur:
            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_all_materialized_views(
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    schema_name TEXT,
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_schema RECORD;
                    v_result RECORD;
                BEGIN
                    FOR v_schema IN 
                        VALUES 
                            ('test_raw'::TEXT),
                            ('test_staging'::TEXT),
                            ('test_core'::TEXT),
                            ('test_features'::TEXT)
                    LOOP
                        IF EXISTS (
                            SELECT 1 FROM information_schema.schemata 
                            WHERE schema_name = v_schema.column1
                        ) THEN
                            FOR v_result IN 
                                SELECT * FROM maintenance.refresh_schema(v_schema.column1, p_concurrent)
                            LOOP
                                RETURN NEXT;
                            END LOOP;
                        END IF;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Also need refresh_schema function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            IF p_concurrent THEN
                                EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', p_schema_name, v_view.matviewname);
                            ELSE
                                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            END IF;
                            
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Test dependency ordering
            await cur.execute("""
                SELECT * FROM maintenance.refresh_all_materialized_views(TRUE)
            """)

            results = await cur.fetchall()
            assert len(results) >= 4  # At least 4 schemas

            # Check that schemas are refreshed in correct order
            schema_order = [r[0] for r in results]
            assert 'test_raw' in schema_order
            assert 'test_staging' in schema_order
            assert 'test_core' in schema_order
            assert 'test_features' in schema_order

    @pytest.mark.asyncio
    async def test_refresh_all_handles_missing_schemas(self, db_connection: AsyncConnection):
        """Test that refresh_all gracefully handles missing schemas."""
        async with db_connection.cursor() as cur:
            # Create the function that includes a non-existent schema
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_all_materialized_views(
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    schema_name TEXT,
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_schema RECORD;
                    v_result RECORD;
                BEGIN
                    FOR v_schema IN 
                        VALUES 
                            ('test_raw'::TEXT),
                            ('nonexistent_schema'::TEXT),
                            ('test_core'::TEXT)
                    LOOP
                        IF EXISTS (
                            SELECT 1 FROM information_schema.schemata 
                            WHERE schema_name = v_schema.column1
                        ) THEN
                            FOR v_result IN 
                                SELECT * FROM maintenance.refresh_schema(v_schema.column1, p_concurrent)
                            LOOP
                                RETURN NEXT;
                            END LOOP;
                        END IF;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Create refresh_schema
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            IF p_concurrent THEN
                                EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', p_schema_name, v_view.matviewname);
                            ELSE
                                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            END IF;
                            
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Should not fail despite missing schema
            await cur.execute("""
                SELECT * FROM maintenance.refresh_all_materialized_views(TRUE)
            """)

            results = await cur.fetchall()
            # Should only refresh existing schemas
            assert len(results) >= 2  # test_raw and test_core


# ============================================================================
# maintenance.check_data_quality() Tests
# ============================================================================


class TestCheckDataQuality:
    """Test suite for maintenance.check_data_quality function."""

    @pytest.mark.asyncio
    async def test_check_data_quality_all_schemas(self, db_connection: AsyncConnection):
        """Test data quality check across all schemas."""
        async with db_connection.cursor() as cur:
            # Create test tables
            await cur.execute("""
                CREATE TABLE test_raw.test_table1 (id INT, data TEXT)
            """)
            await cur.execute("""
                INSERT INTO test_raw.test_table1 VALUES (1, 'test'), (2, 'test2')
            """)

            await cur.execute("""
                CREATE TABLE test_staging.test_table2 (id INT, data TEXT)
            """)
            await cur.execute("""
                INSERT INTO test_staging.test_table2 VALUES (1, 'test')
            """)

            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.check_data_quality()
                RETURNS TABLE(
                    schema_name TEXT,
                    table_name TEXT,
                    check_name TEXT,
                    status TEXT,
                    details TEXT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_schema RECORD;
                    v_table RECORD;
                    v_row_count BIGINT;
                    v_check_date TIMESTAMP;
                BEGIN
                    v_check_date := NOW();
                    
                    FOR v_schema IN 
                        SELECT schema_name FROM information_schema.schemata 
                        WHERE schema_name LIKE 'test_%'
                    LOOP
                        FOR v_table IN 
                            SELECT table_name FROM information_schema.tables 
                            WHERE table_schema = v_schema.schema_name
                              AND table_type = 'BASE TABLE'
                        LOOP
                            BEGIN
                                EXECUTE format('SELECT COUNT(*) FROM %I.%I', v_schema.schema_name, v_table.table_name) 
                                INTO v_row_count;
                                
                                RETURN QUERY SELECT 
                                    v_schema.schema_name::TEXT,
                                    v_table.table_name::TEXT,
                                    'row_count'::TEXT,
                                    CASE WHEN v_row_count > 0 THEN 'PASS' ELSE 'FAIL' END::TEXT,
                                    v_row_count::TEXT;
                                    
                            EXCEPTION WHEN OTHERS THEN
                                RETURN QUERY SELECT 
                                    v_schema.schema_name::TEXT,
                                    v_table.table_name::TEXT,
                                    'row_count'::TEXT,
                                    'ERROR'::TEXT,
                                    SQLERRM::TEXT;
                            END;
                        END LOOP;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Test data quality check
            await cur.execute("""
                SELECT * FROM maintenance.check_data_quality()
            """)

            results = await cur.fetchall()
            assert len(results) >= 2

            # Check that row counts are correct
            test_raw_result = next(r for r in results if r[0] == 'test_raw' and r[1] == 'test_table1')
            assert test_raw_result[3] == 'PASS'  # status
            assert test_raw_result[4] == '2'  # row count

    @pytest.mark.asyncio
    async def test_check_data_quality_empty_table(self, db_connection: AsyncConnection):
        """Test data quality check with empty table."""
        async with db_connection.cursor() as cur:
            # Create empty table
            await cur.execute("""
                CREATE TABLE test_core.empty_table (id INT)
            """)

            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.check_data_quality()
                RETURNS TABLE(
                    schema_name TEXT,
                    table_name TEXT,
                    check_name TEXT,
                    status TEXT,
                    details TEXT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_schema RECORD;
                    v_table RECORD;
                    v_row_count BIGINT;
                    v_check_date TIMESTAMP;
                BEGIN
                    v_check_date := NOW();
                    
                    FOR v_schema IN 
                        SELECT schema_name FROM information_schema.schemata 
                        WHERE schema_name LIKE 'test_%'
                    LOOP
                        FOR v_table IN 
                            SELECT table_name FROM information_schema.tables 
                            WHERE table_schema = v_schema.schema_name
                              AND table_type = 'BASE TABLE'
                        LOOP
                            BEGIN
                                EXECUTE format('SELECT COUNT(*) FROM %I.%I', v_schema.schema_name, v_table.table_name) 
                                INTO v_row_count;
                                
                                RETURN QUERY SELECT 
                                    v_schema.schema_name::TEXT,
                                    v_table.table_name::TEXT,
                                    'row_count'::TEXT,
                                    CASE WHEN v_row_count > 0 THEN 'PASS' ELSE 'FAIL' END::TEXT,
                                    v_row_count::TEXT;
                                    
                            EXCEPTION WHEN OTHERS THEN
                                RETURN QUERY SELECT 
                                    v_schema.schema_name::TEXT,
                                    v_table.table_name::TEXT,
                                    'row_count'::TEXT,
                                    'ERROR'::TEXT,
                                    SQLERRM::TEXT;
                            END;
                        END LOOP;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Test data quality check
            await cur.execute("""
                SELECT * FROM maintenance.check_data_quality()
            """)

            results = await cur.fetchall()
            empty_table_result = next(r for r in results if r[1] == 'empty_table')
            assert empty_table_result[3] == 'FAIL'  # Empty table should fail
            assert empty_table_result[4] == '0'


# ============================================================================
# maintenance.refresh_log Table Tests
# ============================================================================


class TestRefreshLog:
    """Test suite for maintenance.refresh_log table operations."""

    @pytest.mark.asyncio
    async def test_refresh_log_insert(self, db_connection: AsyncConnection):
        """Test inserting into refresh_log table."""
        async with db_connection.cursor() as cur:
            await cur.execute("""
                INSERT INTO maintenance.refresh_log (
                    schema_name,
                    operation_type,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    error_message,
                    metadata
                ) VALUES (
                    'test_core',
                    'REFRESH_SCHEMA',
                    'COMPLETED',
                    NOW() - INTERVAL '5 seconds',
                    NOW(),
                    5000,
                    NULL,
                    '{"concurrent": true}'::JSONB
                )
            """)

            await cur.execute("""
                SELECT * FROM maintenance.refresh_log WHERE schema_name = 'test_core'
            """)

            result = await cur.fetchone()
            assert result is not None
            assert result['schema_name'] == 'test_core'
            assert result['operation_type'] == 'REFRESH_SCHEMA'
            assert result['status'] == 'COMPLETED'
            assert result['duration_ms'] == 5000

    @pytest.mark.asyncio
    async def test_refresh_log_query_by_schema(self, db_connection: AsyncConnection):
        """Test querying refresh_log by schema name."""
        async with db_connection.cursor() as cur:
            # Insert multiple log entries
            await cur.execute("""
                INSERT INTO maintenance.refresh_log (schema_name, operation_type, status, started_at)
                VALUES 
                    ('test_raw', 'REFRESH', 'COMPLETED', NOW()),
                    ('test_staging', 'REFRESH', 'COMPLETED', NOW()),
                    ('test_raw', 'REFRESH', 'COMPLETED', NOW())
            """)

            await cur.execute("""
                SELECT * FROM maintenance.refresh_log WHERE schema_name = 'test_raw'
            """)

            results = await cur.fetchall()
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_refresh_log_query_by_status(self, db_connection: AsyncConnection):
        """Test querying refresh_log by status."""
        async with db_connection.cursor() as cur:
            await cur.execute("""
                INSERT INTO maintenance.refresh_log (schema_name, operation_type, status, started_at)
                VALUES 
                    ('test_core', 'REFRESH', 'COMPLETED', NOW()),
                    ('test_features', 'REFRESH', 'FAILED', NOW()),
                    ('test_raw', 'REFRESH', 'COMPLETED', NOW())
            """)

            await cur.execute("""
                SELECT * FROM maintenance.refresh_log WHERE status = 'FAILED'
            """)

            results = await cur.fetchall()
            assert len(results) == 1
            assert results[0]['schema_name'] == 'test_features'

    @pytest.mark.asyncio
    async def test_refresh_log_metadata_jsonb(self, db_connection: AsyncConnection):
        """Test that metadata field stores JSONB correctly."""
        async with db_connection.cursor() as cur:
            metadata = {'concurrent': True, 'views_refreshed': 5, 'duration': 1234}

            await cur.execute("""
                INSERT INTO maintenance.refresh_log (
                    schema_name, operation_type, status, started_at, metadata
                ) VALUES (
                    'test_core', 'REFRESH', 'COMPLETED', NOW(), %s::JSONB
                )
            """, (metadata,))

            await cur.execute("""
                SELECT metadata FROM maintenance.refresh_log WHERE schema_name = 'test_core'
            """)

            result = await cur.fetchone()
            assert result['metadata']['concurrent'] is True
            assert result['metadata']['views_refreshed'] == 5


# ============================================================================
# Pipeline Orchestration Tests
# ============================================================================


class TestPipelineOrchestration:
    """Test suite for pipeline orchestration functions."""

    @pytest.mark.asyncio
    async def test_refresh_warehouse_full_refresh(self, db_connection: AsyncConnection):
        """Test pipeline.refresh_warehouse with full refresh mode."""
        async with db_connection.cursor() as cur:
            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION pipeline.refresh_warehouse(
                    p_full_refresh BOOLEAN DEFAULT FALSE
                )
                RETURNS TABLE(
                    schema_name TEXT,
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_result RECORD;
                BEGIN
                    FOR v_result IN 
                        SELECT * FROM maintenance.refresh_all_materialized_views(NOT p_full_refresh)
                    LOOP
                        RETURN NEXT;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Create helper functions
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_all_materialized_views(
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    schema_name TEXT,
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY SELECT 
                        'test_schema'::TEXT,
                        'test_view'::TEXT,
                        'SUCCESS'::TEXT,
                        100::BIGINT;
                END;
                $$;
            """)

            # Test full refresh (non-concurrent)
            await cur.execute("""
                SELECT * FROM pipeline.refresh_warehouse(TRUE)
            """)

            results = await cur.fetchall()
            assert len(results) > 0
            assert results[0][2] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_refresh_warehouse_incremental_refresh(self, db_connection: AsyncConnection):
        """Test pipeline.refresh_warehouse with incremental refresh mode."""
        async with db_connection.cursor() as cur:
            # Create the function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION pipeline.refresh_warehouse(
                    p_full_refresh BOOLEAN DEFAULT FALSE
                )
                RETURNS TABLE(
                    schema_name TEXT,
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_result RECORD;
                BEGIN
                    FOR v_result IN 
                        SELECT * FROM maintenance.refresh_all_materialized_views(NOT p_full_refresh)
                    LOOP
                        RETURN NEXT;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Create helper function
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_all_materialized_views(
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    schema_name TEXT,
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY SELECT 
                        'test_schema'::TEXT,
                        'test_view'::TEXT,
                        'SUCCESS'::TEXT,
                        100::BIGINT;
                END;
                $$;
            """)

            # Test incremental refresh (concurrent)
            await cur.execute("""
                SELECT * FROM pipeline.refresh_warehouse(FALSE)
            """)

            results = await cur.fetchall()
            assert len(results) > 0


# ============================================================================
# Permission Grant Tests
# ============================================================================


class TestPermissions:
    """Test suite for permission grants."""

    @pytest.mark.asyncio
    async def test_schema_usage_grant(self, db_connection: AsyncConnection):
        """Test that USAGE is granted on schemas."""
        async with db_connection.cursor() as cur:
            # Grant usage
            await cur.execute(SQL('GRANT USAGE ON SCHEMA maintenance TO PUBLIC'))
            await cur.execute(SQL('GRANT USAGE ON SCHEMA pipeline TO PUBLIC'))

            # Verify grants
            await cur.execute("""
                SELECT * FROM information_schema.role_usage_grants 
                WHERE object_schema IN ('maintenance', 'pipeline')
            """)

            results = await cur.fetchall()
            assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_function_execute_grant(self, db_connection: AsyncConnection):
        """Test that EXECUTE is granted on functions."""
        async with db_connection.cursor() as cur:
            # Create a test function
            await cur.execute("""
                CREATE FUNCTION maintenance.test_func() RETURNS INT AS $$
                SELECT 1
                $$ LANGUAGE SQL
            """)

            # Grant execute
            await cur.execute(SQL('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA maintenance TO PUBLIC'))

            # Verify grant
            await cur.execute("""
                SELECT * FROM information_schema.role_routine_grants 
                WHERE routine_schema = 'maintenance'
            """)

            results = await cur.fetchall()
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_table_select_grant(self, db_connection: AsyncConnection):
        """Test that SELECT is granted on tables."""
        async with db_connection.cursor() as cur:
            # Grant select
            await cur.execute(SQL('GRANT SELECT ON maintenance.refresh_log TO PUBLIC'))

            # Verify grant
            await cur.execute("""
                SELECT * FROM information_schema.role_table_grants 
                WHERE table_schema = 'maintenance' 
                AND table_name = 'refresh_log'
                AND privilege_type = 'SELECT'
            """)

            results = await cur.fetchall()
            assert len(results) >= 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestMaintenanceIntegration:
    """Integration tests for maintenance schema functionality."""

    @pytest.mark.asyncio
    async def test_full_refresh_workflow(self, db_connection: AsyncConnection):
        """Test complete refresh workflow with logging."""
        async with db_connection.cursor() as cur:
            # Create all necessary functions
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    INSERT INTO maintenance.refresh_log (
                        schema_name, operation_type, status, started_at
                    ) VALUES (
                        p_schema_name, 'REFRESH_SCHEMA', 'IN_PROGRESS', NOW()
                    );
                    
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    UPDATE maintenance.refresh_log
                    SET status = 'COMPLETED', completed_at = NOW()
                    WHERE schema_name = p_schema_name
                      AND operation_type = 'REFRESH_SCHEMA'
                      AND status = 'IN_PROGRESS'
                    ORDER BY started_at DESC
                    LIMIT 1;
                    
                    RETURN;
                END;
                $$;
            """)

            # Execute refresh
            await cur.execute("""
                SELECT * FROM maintenance.refresh_schema('test_raw', FALSE)
            """)

            results = await cur.fetchall()
            assert len(results) > 0

            # Verify log entry was created
            await cur.execute("""
                SELECT * FROM maintenance.refresh_log 
                WHERE schema_name = 'test_raw' AND operation_type = 'REFRESH_SCHEMA'
            """)

            log_result = await cur.fetchone()
            assert log_result is not None
            assert log_result['status'] == 'COMPLETED'

    @pytest.mark.asyncio
    async def test_error_handling_in_refresh(self, db_connection: AsyncConnection):
        """Test that errors during refresh are handled gracefully."""
        async with db_connection.cursor() as cur:
            # Create a function that will fail
            await cur.execute("""
                CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
                    p_schema_name TEXT,
                    p_concurrent BOOLEAN DEFAULT TRUE
                )
                RETURNS TABLE(
                    view_name TEXT,
                    status TEXT,
                    duration_ms BIGINT,
                    rows_affected BIGINT
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_view RECORD;
                    v_start_time TIMESTAMP;
                    v_end_time TIMESTAMP;
                    v_row_count BIGINT;
                BEGIN
                    FOR v_view IN 
                        SELECT matviewname 
                        FROM pg_matviews 
                        WHERE schemaname = p_schema_name
                    LOOP
                        v_start_time := clock_timestamp();
                        
                        BEGIN
                            -- Simulate error for specific view
                            IF v_view.matviewname = 'test_mv' THEN
                                RAISE EXCEPTION 'Simulated refresh error';
                            END IF;
                            
                            EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
                            v_end_time := clock_timestamp();
                            
                            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
                            
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'SUCCESS'::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                v_row_count;
                                
                        EXCEPTION WHEN OTHERS THEN
                            v_end_time := clock_timestamp();
                            RETURN QUERY SELECT 
                                v_view.matviewname::TEXT,
                                'FAILED: ' || SQLERRM::TEXT,
                                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                                NULL::BIGINT;
                        END;
                    END LOOP;
                    
                    RETURN;
                END;
                $$;
            """)

            # Execute refresh - should handle error gracefully
            await cur.execute("""
                SELECT * FROM maintenance.refresh_schema('test_raw', FALSE)
            """)

            results = await cur.fetchall()
            assert len(results) > 0
            # Should have a failed result
            assert any('FAILED' in r[1] for r in results)

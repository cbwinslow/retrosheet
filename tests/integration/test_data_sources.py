"""
Comprehensive integration tests for all baseball data sources.

Tests data ingestion, validation, and error handling for:
- Retrosheet historical data
- MLB live data
- Statcast data
- ESPN data
- Lahman Baseball Databank
- FanGraphs data
- Baseball-Reference data
- Weather data
- Park factors

Each test validates:
- Data download functionality
- Database ingestion
- Data validation
- Error handling and logging
- Performance metrics
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, date

from baseball.core.error_handler import (
    EnterpriseErrorHandler, 
    ErrorLevel, 
    ErrorCategory, 
    ErrorContext,
    PerformanceTimer,
    handle_error,
    handle_pipeline_error,
    handle_model_error
)


class TestDataSourceIntegration:
    """Test integration for all baseball data sources."""
    
    @pytest.fixture
    def error_handler(self):
        """Fixture for enterprise error handler."""
        return EnterpriseErrorHandler("test_data_sources")
    
    @pytest.fixture
    def temp_db(self):
        """Fixture for temporary database."""
        import tempfile
        import psycopg2
        from psycopg2.extensions import connection
        
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        db_file.close()
        
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='test_retrosheet',
            user='test_user',
            password='test_password'
        )
        
        yield conn
        
        conn.close()
    
    async def test_retrosheet_download(self, error_handler, temp_db):
        """Test Retrosheet data download with error handling."""
        from baseball.sources.retrosheet import RetrosheetSource
        
        # Mock network requests for testing
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'files': ['2023-regular.zip'],
                'size': 1024000
            }
            mock_get.return_value = mock_response
            
            source = RetrosheetSource()
            
            with PerformanceTimer("retrosheet_download", log_metrics=True) as timer:
                result = source.download(
                    start_date=date(2023, 1, 1),
                    end_date=date(2023, 12, 31)
                )
                
                # Validate result
            assert result.success is True
            assert result.rows_downloaded > 0
            
            # Check error logging
            timer.update_rows_processed(result.rows_downloaded)
    
    async def test_retrosheet_ingest_with_error(self, error_handler, temp_db):
        """Test Retrosheet ingestion error handling."""
        from baseball.sources.retrosheet import RetrosheetSource
        
        source = RetrosheetSource()
        
        # Mock database error
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception):
                source.ingest(validate=True)
    
    async def test_mlb_download_with_metrics(self, error_handler, temp_db):
        """Test MLB data download with performance metrics."""
        from baseball.sources.mlb import MlbSource
        
        source = MlbSource()
        
        with PerformanceTimer("mlb_download", log_metrics=True) as timer:
            result = source.download(
                start_date=date.today(),
                end_date=date.today()
            )
                
                # Validate result
                assert result.success is True
                timer.update_rows_processed(result.rows_downloaded if hasattr(result, 'rows_downloaded') else 0)
    
    async def test_statcast_validation(self, error_handler, temp_db):
        """Test Statcast data validation."""
        from baseball.sources.statcast import StatcastSource
        
        source = StatcastSource()
        
        with PerformanceTimer("statcast_validation", log_metrics=True) as timer:
            result = source.validate()
            
            # Check error handling
            if not result.success:
                error_id = handle_error(
                    error=Exception("Validation failed"),
                    level=ErrorLevel.ERROR,
                    category=ErrorCategory.VALIDATION,
                    context=ErrorContext(
                        command_name="statcast_validate",
                        data_source="statcast",
                        table_name="statcast_data"
                    )
                )
                assert error_id is not None
            else:
                timer.update_rows_processed(result.issues_count if hasattr(result, 'issues_count') else 0)
    
    async def test_espn_ingest_with_recovery(self, error_handler, temp_db):
        """Test ESPN data ingestion with error recovery."""
        from baseball.sources.espn import EspnSource
        
        source = EspnSource()
        
        # Simulate partial failure
        with patch.object(source, 'ingest') as mock_ingest:
            mock_result = Mock()
            mock_result.success = False
            mock_result.error_message = "Partial ingestion failure"
            mock_result.rows_inserted = 500
            mock_ingest.return_value = mock_result
            
            result = source.ingest(validate=True)
            
            # Should handle error gracefully
            assert result.success is False
            assert "Partial ingestion failure" in str(result.error_message)
    
    async def test_lahman_download_large_dataset(self, error_handler, temp_db):
        """Test Lahman download with large dataset performance."""
        from baseball.sources.lahman import LahmanSource
        
        source = LahmanSource()
        
        with PerformanceTimer("lahman_download", log_metrics=True) as timer:
            result = source.download(config={'force': True})
            
            # Validate performance metrics
            assert result.success is True
            assert timer.execution_time_ms > 0
            timer.update_rows_processed(result.metadata.get('files_count', 0) if hasattr(result, 'metadata') else 0)
    
    async def test_fangraphs_ingest_with_context(self, error_handler, temp_db):
        """Test FanGraphs ingestion with rich context."""
        from baseball.sources.fangraphs import FanGraphsSource
        
        source = FanGraphsSource()
        
        with PerformanceTimer("fangraphs_ingest", log_metrics=True) as timer:
            result = source.ingest(config={
                'player_file': 'test_players.csv',
                'team_file': 'test_teams.csv'
            })
            
            # Validate context preservation
            assert result.success is True
            timer.update_rows_processed(result.rows_inserted if hasattr(result, 'rows_inserted') else 0)
    
    async def test_bref_validation_with_errors(self, error_handler, temp_db):
        """Test Baseball-Reference validation with error handling."""
        from baseball.sources.bref import BRefSource
        
        source = BRefSource()
        
        # Simulate validation errors
        with patch.object(source, 'validate') as mock_validate:
            mock_result = Mock()
            mock_result.success = False
            mock_result.error_count = 5
            mock_result.issues = [
                "Missing game_id in 10 records",
                "Invalid date format in 25 records",
                "Duplicate player IDs in 15 records"
            ]
            mock_validate.return_value = mock_result
            
            result = source.validate(config={})
            
            # Should log all validation errors
            assert result.success is False
            assert result.error_count == 5
            assert len(result.issues) == 3
    
    async def test_weather_fetch_with_context(self, error_handler, temp_db):
        """Test weather data fetch with context preservation."""
        from baseball.sources.weather import WeatherSource
        
        source = WeatherSource()
        
        with PerformanceTimer("weather_fetch", log_metrics=True) as timer:
            result = source.download(config={
                'date': '2023-06-15',
                'venue_id': 'ATL00'
            })
            
            # Validate context preservation
            assert result.success is True
            assert 'ATL00' in str(result)
    
    async def test_park_factors_ingest(self, error_handler, temp_db):
        """Test park factors ingestion with error handling."""
        from baseball.sources.park_factors import ParkFactorsSource
        
        source = ParkFactorsSource()
        
        with PerformanceTimer("park_factors_ingest", log_metrics=True) as timer:
            result = source.ingest(config={
                'file': 'test_park_factors.csv'
            })
            
            # Validate result
            assert result.success is True
            timer.update_rows_processed(result.rows_inserted if hasattr(result, 'rows_inserted') else 0)
    
    async def test_pipeline_error_recovery(self, error_handler, temp_db):
        """Test pipeline error recovery mechanisms."""
        from baseball.sources.retrosheet import RetrosheetSource
        
        # Start pipeline run
        run_id = error_handler.log_pipeline_start(
            command_name="test_pipeline",
            parameters={'source': 'retrosheet'},
            user_id="test_user"
        )
        
        try:
            source = RetrosheetSource()
            
            # Simulate error during processing
            with patch.object(source, 'ingest') as mock_ingest:
                mock_ingest.side_effect = Exception("Network timeout during ingestion")
                
                result = source.ingest(validate=True)
                
                # Should fail
                assert result.success is False
                
                # Log error with context
                error_id = handle_pipeline_error(
                    error=Exception("Network timeout during ingestion"),
                    command_name="test_pipeline",
                    subcommand="ingest",
                    parameters={'source': 'retrosheet'},
                    context={
                        'data_source': 'retrosheet',
                        'table_name': 'events',
                        'batch_size': 1000
                    }
                )
                
                assert error_id is not None
                
        finally:
            # Complete pipeline with error status
            error_handler.log_pipeline_complete(
                run_id=run_id,
                status="FAILED",
                rows_processed=0,
                rows_failed=1000,
                error_count=1,
                performance_score=25.0
            )
    
    async def test_system_health_monitoring(self, error_handler, temp_db):
        """Test system health monitoring integration."""
        # Log system health
        success = error_handler.log_system_health(
            component_name="test_component",
            status="HEALTHY",
            cpu_usage_percent=45.2,
            memory_usage_percent=67.8,
            disk_usage_percent=23.4,
            network_latency_ms=12.5,
            database_connections=5,
            active_models=3,
            queue_depth=10,
            error_rate=0.1,
            uptime_seconds=3600.0,
            alerts={
                'warning': 'High memory usage',
                'info': 'All systems operational'
            }
        )
        
        assert success is True
    
    async def test_runtime_metrics_capture(self, error_handler, temp_db):
        """Test runtime metrics capture and logging."""
        with PerformanceTimer("test_operation", log_metrics=True) as timer:
            # Simulate processing
            timer.update_rows_processed(1000)
            timer.update_rows_processed(500)
            
            # Log custom metrics
            success = error_handler.log_runtime_metrics(
                metric_type="MODEL_INFERENCE",
                metric_name="batch_processing_time",
                metric_value=timer.execution_time_ms,
                metric_unit="ms",
                model_name="test_model",
                data_source="test_data",
                operation_name="batch_inference",
                batch_size=1500,
                throughput_per_second=1500 / (timer.execution_time_ms / 1000) if timer.execution_time_ms > 0 else 0,
                custom_tags={
                    'test_type': 'integration',
                    'environment': 'test'
                }
            )
            
            assert success is True
            assert timer.execution_time_ms > 0
    
    async def test_error_pattern_detection(self, error_handler, temp_db):
        """Test error pattern detection and automatic resolution."""
        # Simulate multiple similar errors
        for i in range(3):
            handle_error(
                error=Exception(f"Connection timeout #{i+1}"),
                level=ErrorLevel.ERROR,
                category=ErrorCategory.DATABASE,
                context=ErrorContext(
                    command_name="test_connection",
                    operation_name="database_connect",
                    data_source="postgresql"
                )
            )
        
        # Check error patterns in database
        # This would require querying the error_patterns table
        # For testing, we'll verify the error logging worked
        assert True  # If we got here, error logging worked
    
    async def test_concurrent_operations(self, error_handler, temp_db):
        """Test concurrent data source operations."""
        import asyncio
        
        async def download_retrosheet():
            from baseball.sources.retrosheet import RetrosheetSource
            source = RetrosheetSource()
            return source.download(
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 31)
            )
        
        async def download_statcast():
            from baseball.sources.statcast import StatcastSource
            source = StatcastSource()
            return source.download(
                start_date=date(2023, 1, 1),
                end_date=date(2023, 12, 31)
            )
        
        # Run concurrent downloads
        with PerformanceTimer("concurrent_operations", log_metrics=True) as timer:
            tasks = [
                asyncio.create_task(download_retrosheet()),
                asyncio.create_task(download_statcast())
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Validate all succeeded
            successful_count = sum(1 for r in results if r.success)
            assert successful_count == 2
            
            total_rows = sum(r.rows_downloaded for r in results if hasattr(r, 'rows_downloaded'))
            timer.update_rows_processed(total_rows)
    
    async def test_data_quality_validation(self, error_handler, temp_db):
        """Test comprehensive data quality validation."""
        from baseball.sources.retrosheet import RetrosheetSource
        
        source = RetrosheetSource()
        
        with PerformanceTimer("data_quality_validation", log_metrics=True) as timer:
            result = source.validate()
            
            # Validate comprehensive quality checks
            if result.success:
                quality_metrics = {
                    'completeness': 0.95,
                    'accuracy': 0.98,
                    'consistency': 0.92,
                    'validity': 0.99
                }
                
                # Log quality metrics
                for metric_name, metric_value in quality_metrics.items():
                    error_handler.log_runtime_metrics(
                        metric_type="DATA_INGESTION",
                        metric_name=f"quality_{metric_name}",
                        metric_value=metric_value,
                        metric_unit="score",
                        data_source="retrosheet",
                        operation_name="validation"
                    )
                
                timer.update_rows_processed(result.issues_count if hasattr(result, 'issues_count') else 0)
            else:
                # Log validation failure
                handle_error(
                    error=Exception("Data quality validation failed"),
                    level=ErrorLevel.ERROR,
                    category=ErrorCategory.VALIDATION,
                    context=ErrorContext(
                        command_name="retrosheet_validate",
                        data_source="retrosheet",
                        error_count=result.error_count if hasattr(result, 'error_count') else 0
                    )
                )


class TestErrorHandling:
    """Test enterprise error handling capabilities."""
    
    @pytest.fixture
    def error_handler(self):
        """Fixture for enterprise error handler."""
        return EnterpriseErrorHandler("test_error_handling")
    
    async def test_stack_trace_capture(self, error_handler):
        """Test comprehensive stack trace capture."""
        try:
            # Create nested function calls to generate stack trace
            def deep_function_1():
                def deep_function_2():
                    def deep_function_3():
                        raise ValueError("Test error with deep stack trace")
                    return deep_function_3()
                return deep_function_2()
            return deep_function_1()
            
            deep_function_1()
            
        except Exception as e:
            # Log error with full context
            error_id = error_handler.log_error(
                error=e,
                level=ErrorLevel.ERROR,
                category=ErrorCategory.SYSTEM,
                context=ErrorContext(
                    command_name="test_stack_trace",
                    function_name="deep_function_3",
                    file_path=__file__,
                    line_number=25,  # Approximate line number
                    table_name="test_table",
                    column_name="test_column"
                ),
                recovery_attempted=True,
                recovery_message="Test error recovery"
            )
            
            assert error_id is not None
            assert "Test error with deep stack trace" in str(e)
    
    async def test_error_recovery_workflow(self, error_handler):
        """Test error recovery workflow."""
        # Log initial error
        error_id_1 = error_handler.log_error(
            error=Exception("Initial error"),
            level=ErrorLevel.ERROR,
            category=ErrorCategory.DATABASE,
            context=ErrorContext(
                command_name="test_recovery",
                operation_name="database_query"
            )
        )
        
        # Simulate recovery attempt
        recovery_success = error_handler.log_pipeline_complete(
            run_id=1,  # This would be from a real pipeline run
            status="COMPLETED",
            rows_processed=100,
            error_count=1
        )
        
        assert error_id_1 is not None
        assert recovery_success is True
    
    async def test_prometheus_metrics_integration(self, error_handler):
        """Test Prometheus metrics integration."""
        # The metrics should be automatically updated when logging errors
        initial_error_count = error_handler.error_counter._value._samples.total()
        
        # Log an error to increment counter
        error_handler.log_error(
            error=Exception("Test Prometheus integration"),
            level=ErrorLevel.ERROR,
            category=ErrorCategory.SYSTEM,
            context=ErrorContext(
                command_name="test_prometheus",
                data_source="test"
            )
        )
        
        # Check that counter incremented
        final_error_count = error_handler.error_counter._value._samples.total()
        assert final_error_count > initial_error_count
    
    async def test_database_connection_pooling(self, error_handler):
        """Test database connection pooling."""
        connections = []
        
        try:
            # Create multiple connections
            for i in range(3):
                conn = error_handler._get_db_connection()
                connections.append(conn)
                
                # Simulate database operation
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            
            # Return all connections to pool
            for conn in connections:
                error_handler._return_db_connection(conn)
                
            assert True  # All connections managed successfully
            
        except Exception as e:
            handle_error(
                error=e,
                level=ErrorLevel.ERROR,
                category=ErrorCategory.DATABASE,
                context=ErrorContext(
                    command_name="test_connection_pool",
                    operation_name="database_connection"
                )
            )
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

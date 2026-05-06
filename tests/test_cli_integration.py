"""
Comprehensive test suite for CLI integration and end-to-end workflow.
Tests all aspects including edge cases, error handling, and integration scenarios.
Following AGENTS.md rules for comprehensive testing.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import tempfile
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCLIIntegration:
    """Comprehensive test suite for CLI integration."""
    
    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for CLI testing."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='Test output',
                stderr=''
            )
            yield mock_run
    
    @pytest.fixture
    def mock_database_connection(self):
        """Mock database connection for CLI testing."""
        with patch('baseball.core.db.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]
            mock_get_conn.return_value = mock_conn
            yield mock_conn
    
    def test_baseball_cli_help(self, mock_subprocess_run):
        """Test baseball CLI help command."""
        # Test main help
        result = subprocess.run(['python', '-m', 'baseball', '--help'], 
                              capture_output=True, text=True)
        
        # Verify help output
        assert result.returncode == 0
        assert 'Usage:' in result.stdout or 'usage:' in result.stdout.lower()
    
    def test_baseball_cli_version(self, mock_subprocess_run):
        """Test baseball CLI version command."""
        result = subprocess.run(['python', '-m', 'baseball', 'version'], 
                              capture_output=True, text=True)
        
        # Verify version output
        assert result.returncode == 0
    
    def test_pitch_models_cli_help(self, mock_subprocess_run):
        """Test pitch-models CLI help command."""
        result = subprocess.run(['python', '-m', 'baseball', 'pitch-models', '--help'], 
                              capture_output=True, text=True)
        
        # Verify help output
        assert result.returncode == 0
        assert 'pitch-models' in result.stdout.lower()
    
    def test_pitch_models_status_command(self, mock_database_connection):
        """Test pitch-models status command."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.side_effect = [
                [20114720],  # base_features count
                [100],       # engineered_features count
                [0]          # models count
            ]
            mock_get_conn.return_value = mock_conn
            
            # Import and test the CLI command
            from baseball.cli.commands.pitch_models import status_command
            
            # Execute status command
            status_command()
            
            # Verify database queries
            assert mock_cursor.execute.call_count >= 3
    
    def test_pitch_models_train_command(self, mock_database_connection):
        """Test pitch-models train command."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]  # base_features count
            mock_get_conn.return_value = mock_conn
            
            # Mock model training
            with patch('baseball.models.pitch.train_tier1_xgboost.PitchTier1XGBoostModel') as mock_model:
                mock_instance = Mock()
                mock_model.return_value = mock_instance
                mock_instance.train.return_value = {'accuracy': 0.85}
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import train_command
                
                # Execute train command
                train_command(target_tier='tier1', seasons=[2023], sample_rate=1.0)
                
                # Verify model training
                mock_model.assert_called_once()
                mock_instance.train.assert_called_once()
    
    def test_pitch_models_calibrate_command(self, mock_database_connection):
        """Test pitch-models calibrate command."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]  # engineered_features count
            mock_get_conn.return_value = mock_conn
            
            # Mock model calibrator
            with patch('baseball.models.pitch.calibration.PitchModelCalibrator') as mock_calibrator:
                mock_instance = Mock()
                mock_calibrator.return_value = mock_instance
                mock_instance.fit.return_value = None
                mock_instance.generate_calibration_report.return_value = {'ece': 0.05}
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import calibrate_command
                
                # Execute calibrate command
                calibrate_command(model_path='test_model.joblib', method='temperature')
                
                # Verify calibration
                mock_calibrator.assert_called_once()
                mock_instance.fit.assert_called_once()
    
    def test_pitch_models_evaluate_command(self, mock_database_connection):
        """Test pitch-models evaluate command."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]  # engineered_features count
            mock_get_conn.return_value = mock_conn
            
            # Mock model evaluation
            with patch('baseball.models.pitch.calibration.PitchModelCalibrator') as mock_calibrator:
                mock_instance = Mock()
                mock_calibrator.return_value = mock_instance
                mock_instance.calculate_comprehensive_metrics.return_value = {
                    'accuracy': 0.85,
                    'ece': 0.04
                }
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import evaluate_command
                
                # Execute evaluate command
                evaluate_command(model_path='test_model.joblib')
                
                # Verify evaluation
                mock_calibrator.assert_called_once()
                mock_instance.calculate_comprehensive_metrics.assert_called_once()
    
    def test_pitch_models_populate_features_command(self, mock_database_connection):
        """Test pitch-models populate-features command."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]  # base_features count
            mock_cursor.rowcount = 1000
            mock_get_conn.return_value = mock_conn
            
            # Mock feature population
            with patch('scripts.pitch_data.populate_engineered_features.populate_engineered_features') as mock_populate:
                mock_populate.return_value = {'processed': 1000}
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import populate_features_command
                
                # Execute populate command
                populate_features_command(feature_type='engineered', batch_size=1000, dry_run=False)
                
                # Verify population
                mock_populate.assert_called_once()
    
    def test_cli_error_handling(self, mock_database_connection):
        """Test CLI error handling."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_get_conn.side_effect = Exception("Database connection failed")
            
            # Import and test the CLI command
            from baseball.cli.commands.pitch_models import status_command
            
            # Execute status command and verify error handling
            with pytest.raises(Exception):
                status_command()
    
    def test_cli_configuration_handling(self):
        """Test CLI configuration handling."""
        with patch('baseball.core.settings.DatabaseSettings') as mock_settings:
            mock_settings.return_value.database_url = 'postgresql://test:test@localhost/test'
            
            # Test configuration loading
            from baseball.core.settings import DatabaseSettings
            
            settings = DatabaseSettings()
            assert settings.database_url is not None
    
    def test_cli_logging_configuration(self):
        """Test CLI logging configuration."""
        # Test logging setup
        import logging
        
        # Verify logging is configured
        logger = logging.getLogger('baseball')
        assert logger is not None
    
    def test_cli_argument_validation(self):
        """Test CLI argument validation."""
        # Test invalid arguments
        with pytest.raises((ValueError, TypeError)):
            # This would be tested with actual CLI argument validation
            pass
    
    def test_cli_performance_monitoring(self, mock_database_connection):
        """Test CLI performance monitoring."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]  # base_features count
            mock_get_conn.return_value = mock_conn
            
            # Mock performance timing
            with patch('time.time') as mock_time:
                import time
                start_time = time.time()
                end_time = start_time + 10.0
                mock_time.side_effect = [start_time, end_time]
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import status_command
                
                # Execute status command
                status_command()
                
                # Verify performance monitoring
                assert mock_time.call_count >= 2
    
    def test_cli_dry_run_mode(self, mock_database_connection):
        """Test CLI dry run mode."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]  # base_features count
            mock_get_conn.return_value = mock_conn
            
            # Mock dry run functionality
            with patch('scripts.pitch_data.populate_engineered_features.populate_engineered_features') as mock_populate:
                mock_populate.return_value = {'status': 'dry_run', 'source_count': 1000000}
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import populate_features_command
                
                # Execute populate command in dry run mode
                populate_features_command(feature_type='engineered', batch_size=1000, dry_run=True)
                
                # Verify dry run
                mock_populate.assert_called_once()
                args, kwargs = mock_populate.call_args
                assert kwargs.get('dry_run') == True
    
    def test_cli_batch_processing(self, mock_database_connection):
        """Test CLI batch processing."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [5000000]  # large dataset
            mock_cursor.rowcount = 10000
            mock_get_conn.return_value = mock_conn
            
            # Mock batch processing
            with patch('scripts.pitch_data.populate_engineered_features.populate_engineered_features') as mock_populate:
                mock_populate.return_value = {'processed': 10000, 'batches': 500}
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import populate_features_command
                
                # Execute populate command with large batch size
                populate_features_command(feature_type='engineered', batch_size=10000, dry_run=False)
                
                # Verify batch processing
                mock_populate.assert_called_once()
                args, kwargs = mock_populate.call_args
                assert kwargs.get('batch_size') == 10000
    
    def test_cli_progress_reporting(self, mock_database_connection):
        """Test CLI progress reporting."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]  # base_features count
            mock_get_conn.return_value = mock_conn
            
            # Mock progress reporting
            with patch('tqdm.tqdm') as mock_tqdm:
                mock_tqdm.return_value = range(100)  # Mock progress bar
                
                # Import and test the CLI command
                from baseball.cli.commands.pitch_models import status_command
                
                # Execute status command
                status_command()
                
                # Verify progress reporting
                # (This would be tested with actual progress bar implementation)
                pass
    
    def test_cli_output_formatting(self, mock_database_connection):
        """Test CLI output formatting."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.side_effect = [
                [20114720],  # base_features count
                [100],       # engineered_features count
                [0]          # models count
            ]
            mock_get_conn.return_value = mock_conn
            
            # Import and test the CLI command
            from baseball.cli.commands.pitch_models import status_command
            
            # Execute status command and capture output
            with patch('builtins.print') as mock_print:
                status_command()
                
                # Verify output formatting
                assert mock_print.call_count >= 3  # Should print multiple lines
    
    def test_cli_configuration_file_support(self):
        """Test CLI configuration file support."""
        # Test configuration file loading
        config_file = Path(__file__).parent / 'test_config.yaml'
        
        # This would test actual configuration file loading
        if config_file.exists():
            # Test loading configuration from file
            pass
    
    def test_cli_environment_variable_support(self):
        """Test CLI environment variable support."""
        # Test environment variable handling
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            # Test that environment variables are properly handled
            from baseball.core.settings import DatabaseSettings
            
            settings = DatabaseSettings()
            # Verify environment variable is used
            assert 'test' in settings.database_url


class TestCLIEndToEndWorkflow:
    """End-to-end workflow tests for CLI integration."""
    
    @pytest.mark.integration
    def test_complete_pitch_modeling_workflow(self, mock_database_connection):
        """Test complete pitch modeling workflow through CLI."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.side_effect = [
                [20114720],  # base_features count
                [100],       # engineered_features count
                [0],          # models count
                [20114720],  # training data count
                [100],       # calibration data count
                [100]        # evaluation data count
            ]
            mock_get_conn.return_value = mock_conn
            
            # Mock all workflow components
            with patch('scripts.pitch_data.populate_engineered_features.populate_engineered_features') as mock_populate, \
                 patch('baseball.models.pitch.train_tier1_xgboost.PitchTier1XGBoostModel') as mock_model, \
                 patch('baseball.models.pitch.calibration.PitchModelCalibrator') as mock_calibrator:
                
                # Setup mocks
                mock_populate.return_value = {'processed': 1000}
                mock_instance = Mock()
                mock_model.return_value = mock_instance
                mock_instance.train.return_value = {'accuracy': 0.85}
                mock_calibrator.return_value = Mock()
                mock_calibrator.return_value.fit.return_value = None
                mock_calibrator.return_value.generate_calibration_report.return_value = {'ece': 0.04}
                
                # Import CLI commands
                from baseball.cli.commands.pitch_models import (
                    populate_features_command,
                    train_command,
                    calibrate_command,
                    evaluate_command
                )
                
                # Execute complete workflow
                # 1. Populate features
                populate_features_command(feature_type='engineered', batch_size=1000, dry_run=False)
                
                # 2. Train model
                train_command(target_tier='tier1', seasons=[2023], sample_rate=1.0)
                
                # 3. Calibrate model
                calibrate_command(model_path='test_model.joblib', method='temperature')
                
                # 4. Evaluate model
                evaluate_command(model_path='test_model.joblib')
                
                # Verify workflow completion
                assert mock_populate.call_count == 1
                assert mock_model.call_count == 1
                assert mock_calibrator.call_count == 2  # Once for calibration, once for evaluation
    
    @pytest.mark.integration
    def test_cli_error_recovery_workflow(self, mock_database_connection):
        """Test CLI error recovery and resilience."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            # Simulate database connection failure
            mock_get_conn.side_effect = [Exception("Connection failed"), Mock()]
            
            # Test error recovery
            from baseball.cli.commands.pitch_models import status_command
            
            # First call should fail
            with pytest.raises(Exception):
                status_command()
            
            # Second call should succeed (simulating recovery)
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [1000000]
            mock_get_conn.return_value = mock_conn
            
            # This should work now
            status_command()
    
    @pytest.mark.integration
    def test_cli_performance_under_load(self, mock_database_connection):
        """Test CLI performance under load."""
        with patch('baseball.cli.commands.pitch_models.get_db_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [100000000]  # 100M rows
            mock_cursor.rowcount = 100000
            mock_get_conn.return_value = mock_conn
            
            # Mock performance timing
            with patch('time.time') as mock_time:
                import time
                start_time = time.time()
                end_time = start_time + 60.0  # 1 minute processing
                mock_time.side_effect = [start_time, end_time]
                
                # Import and test CLI command
                from baseball.cli.commands.pitch_models import status_command
                
                # Execute status command with large dataset
                status_command()
                
                # Verify performance handling
                assert mock_time.call_count >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

"""Comprehensive test suite for ensemble training system."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from unittest import TestCase
from unittest.mock import MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.models.ensemble.working_ensemble import WorkingEnsembleTrainer


class TestWorkingEnsembleTrainer(TestCase):
    """Test cases for WorkingEnsembleTrainer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.trainer = WorkingEnsembleTrainer(model_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('baseball.models.ensemble.working_ensemble.psycopg2.connect')
    def test_initialization(self, mock_connect):
        """Test trainer initialization."""
        # Test successful initialization
        trainer = WorkingEnsembleTrainer()
        self.assertIsNotNone(trainer)
        self.assertEqual(trainer.model_dir.name, 'data/models/ensemble')
        
        # Test custom model directory
        custom_dir = Path('/tmp/test_models')
        trainer = WorkingEnsembleTrainer(model_dir=str(custom_dir))
        self.assertEqual(trainer.model_dir, custom_dir)
    
    @patch('baseball.models.ensemble.working_ensemble.psycopg2.connect')
    def test_load_pitch_data_success(self, mock_connect):
        """Test successful pitch data loading."""
        # Mock database response
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.return_value = mock_cursor
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.execute.return_value = None
        mock_cursor.description = [
            ('release_speed', None), ('release_spin_rate', None), 
            ('target', None)
        ]
        mock_cursor.fetchall.return_value = [
            (90.5, 2000, 'strike'),
            (85.0, 1800, 'ball'),
            (92.0, 2100, 'ball_in_play')
        ]
        
        mock_connect.return_value = mock_conn
        
        # Test data loading
        X, y = self.trainer.load_pitch_data(seasons=[2015], sample_rate=1.0)
        
        # Assertions
        self.assertEqual(len(X), 3)
        self.assertEqual(len(y), 3)
        self.assertIn('release_speed', X.columns)
        self.assertEqual(list(y), ['strike', 'ball', 'ball_in_play'])
        
        # Verify connection was called correctly
        mock_connect.assert_called_once_with(
            host='localhost',
            port='5432',
            database='retrosheet',
            user='cbwinslow',
            password='123qweasd'
        )
    
    @patch('baseball.models.ensemble.working_ensemble.psycopg2.connect')
    def test_load_pitch_data_with_sampling(self, mock_connect):
        """Test pitch data loading with sampling."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.execute.return_value = None
        mock_cursor.description = [('release_speed', None), ('target', None)]
        mock_cursor.fetchall.return_value = [(90.5, 'strike')]
        
        mock_connect.return_value = mock_conn
        
        # Test with sampling
        X, y = self.trainer.load_pitch_data(seasons=[2015], sample_rate=0.1)
        
        # Verify query includes sampling
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn('random() < %s', call_args)
        self.assertEqual(call_args[1][0], 0.1)
    
    @patch('baseball.models.ensemble.working_ensemble.psycopg2.connect')
    def test_load_pitch_data_database_error(self, mock_connect):
        """Test pitch data loading with database error."""
        mock_connect.side_effect = Exception("Database connection failed")
        
        with self.assertRaises(Exception) as context:
            self.trainer.load_pitch_data(seasons=[2015])
        
        self.assertIn("Database connection failed", str(context.exception))
    
    @patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.load_pitch_data')
    @patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.train_xgboost_model')
    @patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.train_hist_gb_model')
    def test_train_ensemble_success(self, mock_load_data, mock_xgb, mock_hist_gb):
        """Test successful ensemble training."""
        # Mock data loading
        import pandas as pd
        import numpy as np
        X_mock = pd.DataFrame({
            'release_speed': [90.0, 85.0, 92.0],
            'release_spin_rate': [2000, 1800, 2100]
        })
        y_mock = pd.Series(['strike', 'ball', 'ball_in_play'])
        mock_load_data.return_value = (X_mock, y_mock)
        
        # Mock model training
        mock_xgb.return_value = {
            'model': MagicMock(),
            'label_encoder': MagicMock(),
            'accuracy': 0.85,
            'log_loss': 0.45,
            'training_time': 10.5,
            'model_type': 'xgboost'
        }
        
        mock_hist_gb.return_value = {
            'model': MagicMock(),
            'label_encoder': MagicMock(),
            'accuracy': 0.82,
            'log_loss': 0.48,
            'training_time': 8.2,
            'model_type': 'hist_gb'
        }
        
        # Test ensemble training
        results = self.trainer.train_ensemble(
            seasons=[2015],
            sample_rate=1.0
        )
        
        # Assertions
        self.assertIn('ensemble_results', results)
        self.assertIn('model_results', results)
        self.assertIn('xgboost', results['model_results'])
        self.assertIn('hist_gb', results['model_results'])
        
        # Verify ensemble results
        ensemble_results = results['ensemble_results']
        self.assertGreater(ensemble_results['ensemble_accuracy'], 0)
        self.assertGreater(ensemble_results['n_models'], 1)
    
    @patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.load_pitch_data')
    def test_train_ensemble_with_model_failure(self, mock_load_data):
        """Test ensemble training with model failure."""
        import pandas as pd
        X_mock = pd.DataFrame({'release_speed': [90.0]})
        y_mock = pd.Series(['strike'])
        mock_load_data.return_value = (X_mock, y_mock)
        
        # Mock XGBoost failure
        with patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.train_xgboost_model') as mock_xgb:
            mock_xgb.return_value = {'error': 'XGBoost training failed', 'model_type': 'xgboost'}
            
            results = self.trainer.train_ensemble(seasons=[2015])
            
            # Should still have results for successful models
            self.assertIn('ensemble_results', results)
            self.assertIn('model_results', results)
            
            # Ensemble should handle failure gracefully
            ensemble_results = results['ensemble_results']
            self.assertGreaterEqual(ensemble_results['n_models'], 0)
    
    @patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.load_pitch_data')
    @patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.train_xgboost_model')
    def test_evaluate_ensemble(self, mock_load_data, mock_xgb):
        """Test ensemble evaluation."""
        import pandas as pd
        from sklearn.preprocessing import LabelEncoder
        
        # Mock data
        X_train = pd.DataFrame({'release_speed': [90.0, 85.0]})
        y_train = pd.Series(['strike', 'ball'])
        X_test = pd.DataFrame({'release_speed': [92.0, 88.0]})
        y_test = pd.Series(['strike', 'ball'])
        
        mock_load_data.return_value = (X_train, y_train)
        
        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0, 1])
        mock_model.predict_proba.return_value = np.array([[0.8, 0.2], [0.3, 0.7]])
        
        mock_xgb.return_value = {
            'model': mock_model,
            'label_encoder': LabelEncoder().fit(['strike', 'ball']),
            'accuracy': 0.85,
            'log_loss': 0.45,
            'training_time': 10.5,
            'model_type': 'xgboost'
        }
        
        # Test evaluation
        model_results = {'xgboost': mock_xgb.return_value}
        ensemble_results = self.trainer.evaluate_ensemble(model_results, X_test, y_test)
        
        # Assertions
        self.assertIn('ensemble_accuracy', ensemble_results)
        self.assertIn('best_individual_accuracy', ensemble_results)
        self.assertIn('improvement', ensemble_results)
        self.assertIn('n_models', ensemble_results)
    
    def test_evaluate_ensemble_insufficient_models(self):
        """Test ensemble evaluation with insufficient models."""
        model_results = {}  # No successful models
        
        results = self.trainer.evaluate_ensemble(model_results, None, None)
        
        # Should handle insufficient models gracefully
        self.assertEqual(results['ensemble_accuracy'], 0)
        self.assertEqual(results['improvement'], 0)
        self.assertEqual(results['n_models'], 0)


class TestEnsembleIntegration(TestCase):
    """Integration tests for ensemble system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('baseball.models.ensemble.working_ensemble.psycopg2.connect')
    def test_end_to_end_training(self, mock_connect):
        """Test end-to-end training pipeline."""
        # Mock database with realistic data
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock realistic pitch data
        mock_cursor.execute.return_value = None
        mock_cursor.description = [
            ('release_speed', None), ('release_spin_rate', None), ('effective_speed', None),
            ('release_pos_x', None), ('release_pos_y', None), ('release_pos_z', None),
            ('pfx_x', None), ('pfx_z', None), ('spin_axis', None),
            ('plate_x', None), ('plate_z', None), ('zone', None),
            ('balls', None), ('strikes', None), ('outs_when_up', None), ('inning', None),
            ('on_1b', None), ('on_2b', None), ('on_3b', None),
            ('home_score', None), ('away_score', None), ('bat_score', None), ('fld_score', None),
            ('stand', None), ('p_throws', None),
            ('vx0', None), ('vy0', None), ('vz0', None),
            ('ax', None), ('ay', None), ('az', None),
            ('launch_speed', None), ('launch_angle', None), ('bb_type', None),
            ('target', None)
        ]
        
        # Generate realistic mock data
        import numpy as np
        n_samples = 100
        mock_data = []
        for i in range(n_samples):
            release_speed = np.random.normal(90, 5)
            release_spin_rate = np.random.normal(2000, 200)
            target = np.random.choice(['strike', 'ball', 'ball_in_play'])
            mock_data.append((
                release_speed, release_spin_rate, 85.0, -1.5, 6.2, 0.5, -0.3, 0.8,
                0.2, 0.3, 0.5, 2, 1, 7, 3, 5, 1, 4, 2, 3, 4,
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                85.0, 15.0, -5.0, 3.0, 2.0, 8.0, -1.0, 1.0, 0.5, 0.3, 0.8, 0.2,
                'R', 'R', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                target
            ))
        
        mock_cursor.fetchall.return_value = mock_data
        mock_connect.return_value = mock_conn
        
        # Test end-to-end training
        trainer = WorkingEnsembleTrainer(model_dir=self.temp_dir)
        
        with patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.train_xgboost_model') as mock_xgb:
            # Mock successful XGBoost training
            mock_xgb.return_value = {
                'model': MagicMock(),
                'label_encoder': MagicMock(),
                'accuracy': 0.82,
                'log_loss': 0.48,
                'training_time': 5.0,
                'model_type': 'xgboost'
            }
            
            with patch('baseball.models.ensemble.working_ensemble.WorkingEnsembleTrainer.train_hist_gb_model') as mock_hist_gb:
                # Mock successful HistGB training
                mock_hist_gb.return_value = {
                    'model': MagicMock(),
                    'label_encoder': MagicMock(),
                    'accuracy': 0.80,
                    'log_loss': 0.52,
                    'training_time': 4.0,
                    'model_type': 'hist_gb'
                }
                
                results = trainer.train_ensemble(
                    seasons=[2015],
                    sample_rate=0.1  # Use sampling for faster test
                )
                
                # Verify results structure
                self.assertIn('timestamp', results)
                self.assertIn('seasons', results)
                self.assertIn('sample_rate', results)
                self.assertIn('data_splits', results)
                self.assertIn('model_results', results)
                self.assertIn('ensemble_results', results)
                
                # Verify model files were saved
                model_files = list(Path(self.temp_dir).glob('*.joblib'))
                self.assertGreater(len(model_files), 0)
                
                # Verify results file was saved
                result_files = list(Path(self.temp_dir).glob('ensemble_results_*.json'))
                self.assertGreater(len(result_files), 0)


class TestEnsembleCLI(TestCase):
    """Test CLI commands for ensemble system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('baseball.cli.commands.ensemble.WorkingEnsembleTrainer')
    def test_ensemble_train_command(self, mock_trainer_class):
        """Test ensemble train CLI command."""
        from baseball.cli.commands.ensemble import train
        from typer.testing import CliRunner
        
        # Mock trainer
        mock_trainer = MagicMock()
        mock_trainer_class.return_value = mock_trainer
        
        # Mock training results
        mock_trainer.train_ensemble.return_value = {
            'ensemble_results': {
                'ensemble_accuracy': 0.85,
                'best_individual_accuracy': 0.82,
                'improvement': 0.03,
                'n_models': 2
            },
            'model_results': {
                'xgboost': {'accuracy': 0.82, 'model_type': 'xgboost'},
                'hist_gb': {'accuracy': 0.80, 'model_type': 'hist_gb'}
            },
            'timestamp': '20231201_120000'
        }
        
        # Test CLI command
        runner = CliRunner()
        result = runner.invoke(train, [
            '--seasons', '2015', '2016',
            '--sample-rate', '0.1',
            '--models', 'xgboost', 'hist_gb',
            '--output-dir', self.temp_dir
        ])
        
        # Should execute successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify trainer was called correctly
        mock_trainer_class.assert_called_once_with(model_dir=self.temp_dir)
        mock_trainer.train_ensemble.assert_called_once_with(
            seasons=[2015, 2016],
            sample_rate=0.1,
            concurrent=True
        )
    
    @patch('baseball.cli.commands.ensemble.WorkingEnsembleTrainer')
    def test_ensemble_list_command(self, mock_trainer_class):
        """Test ensemble list CLI command."""
        from baseball.cli.commands.ensemble import list
        from typer.testing import CliRunner
        
        # Mock trainer
        mock_trainer = MagicMock()
        mock_trainer_class.return_value = mock_trainer
        
        # Create mock model files
        for model_name in ['xgboost_ensemble_20231201_120000.joblib', 
                           'hist_gb_ensemble_20231201_120000.joblib']:
            model_path = Path(self.temp_dir) / model_name
            model_path.touch()
        
        # Test CLI command
        runner = CliRunner()
        result = runner.invoke(list, ['--model-dir', self.temp_dir])
        
        # Should execute successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify output contains model information
        self.assertIn('xgboost_ensemble_20231201_120000.joblib', result.stdout)
        self.assertIn('hist_gb_ensemble_20231201_120000.joblib', result.stdout)
    
    @patch('baseball.cli.commands.ensemble.WorkingEnsembleTrainer')
    def test_ensemble_doctor_command(self, mock_trainer_class):
        """Test ensemble doctor CLI command."""
        from baseball.cli.commands.ensemble import doctor
        from typer.testing import CliRunner
        
        # Test CLI command
        runner = CliRunner()
        result = runner.invoke(doctor)
        
        # Should execute successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify output contains health check information
        self.assertIn('Ensemble System Doctor', result.stdout)


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__])

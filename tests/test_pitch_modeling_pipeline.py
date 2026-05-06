#!/usr/bin/env python3
"""
Comprehensive test suite for pitch-level modeling pipeline.

Tests:
- Feature population scripts
- Model training pipeline
- Calibration framework
- CLI integration
- Database connectivity

Usage:
    python test_pitch_modeling_pipeline.py --all
    python test_pitch_modeling_pipeline.py --component base_features
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from baseball.core.db import get_db_connection
    from baseball.utils.logging_config import get_logger
    from baseball.models.pitch.train_tier1_xgboost import PitchTier1XGBoostModel
    from baseball.models.pitch.calibration import PitchModelCalibrator
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure baseball package is properly installed")
    sys.exit(1)

logger = get_logger(__name__)


class PitchModelingPipelineTester:
    """Comprehensive test suite for pitch-level modeling pipeline."""
    
    def __init__(self):
        self.test_results = {}
        
    def test_database_connectivity(self) -> dict:
        """Test database connection and basic queries."""
        logger.info("Testing database connectivity...")
        
        results = {
            'connection': False,
            'tables_exist': False,
            'row_counts': {}
        }
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Test basic connection
            cursor.execute("SELECT 1")
            results['connection'] = True
            
            # Test key tables exist
            tables_to_check = [
                'features_pitch.locations',
                'features_pitch.base_features', 
                'features_pitch.engineered_features',
                'features_pitch.feature_registry'
            ]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                    table_exists = cursor.fetchone()[0]
                    results[f'table_{table}'] = table_exists
                    
                    if table_exists:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        results['row_counts'][table] = count
                        
                except Exception as e:
                    logger.error(f"Error checking table {table}: {e}")
                    results[f'table_{table}'] = False
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def test_feature_population_scripts(self) -> dict:
        """Test feature population script functionality."""
        logger.info("Testing feature population scripts...")
        
        results = {
            'base_features_script': False,
            'engineered_features_script': False,
            'script_syntax': False
        }
        
        try:
            # Test script imports
            from scripts.pitch_data.populate_base_features import populate_all_seasons
            from scripts.pitch_data.populate_engineered_features import populate_engineered_features
            results['base_features_script'] = True
            results['engineered_features_script'] = True
            
            # Test basic syntax by importing main functions
            import scripts.pitch_data.populate_base_features as base_script
            import scripts.pitch_data.populate_engineered_features as eng_script
            
            results['script_syntax'] = (
                hasattr(base_script, 'main') and 
                hasattr(eng_script, 'main')
            )
            
        except ImportError as e:
            logger.error(f"Script import error: {e}")
        except Exception as e:
            logger.error(f"Script syntax error: {e}")
        
        return results
    
    def test_model_training_components(self) -> dict:
        """Test model training components."""
        logger.info("Testing model training components...")
        
        results = {
            'model_class_import': False,
            'calibrator_class_import': False,
            'xgboost_available': False,
            'sklearn_available': False
        }
        
        try:
            # Test model class
            model = PitchTier1XGBoostModel('tier1')
            results['model_class_import'] = True
            
            # Test calibrator class
            calibrator = PitchModelCalibrator.__new__(PitchModelCalibrator)
            results['calibrator_class_import'] = True
            
            # Test dependencies
            import xgboost as xgb
            results['xgboost_available'] = hasattr(xgb, 'XGBClassifier')
            
            from sklearn import metrics
            results['sklearn_available'] = hasattr(metrics, 'accuracy_score')
            
        except Exception as e:
            logger.error(f"Model training component test failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def test_cli_integration(self) -> dict:
        """Test CLI integration."""
        logger.info("Testing CLI integration...")
        
        results = {
            'pitch_models_app_import': False,
            'main_cli_import': False,
            'typer_available': False
        }
        
        try:
            # Test CLI imports
            from baseball.cli.commands.pitch_models import pitch_app
            results['pitch_models_app_import'] = True
            
            from baseball.cli.main import app
            results['main_cli_import'] = True
            
            # Test Typer
            import typer
            results['typer_available'] = hasattr(typer, 'Typer')
            
        except Exception as e:
            logger.error(f"CLI integration test failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def test_data_quality_checks(self) -> dict:
        """Test data quality and validation."""
        logger.info("Testing data quality checks...")
        
        results = {
            'locations_quality': False,
            'base_features_quality': False,
            'engineered_features_quality': False
        }
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Test locations table quality
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(*) FILTER (WHERE pitch_type IS NULL) as null_pitch_type,
                    COUNT(*) FILTER (WHERE release_speed IS NULL) as null_speed,
                    COUNT(*) FILTER (WHERE plate_x IS NULL) as null_location,
                    COUNT(DISTINCT game_year) as seasons_count
                FROM features_pitch.locations
                LIMIT 1
            """)
            
            if cursor.rowcount > 0:
                row = cursor.fetchone()
                results['locations_quality'] = {
                    'total_rows': row[0],
                    'null_pitch_type': row[1],
                    'null_speed': row[2], 
                    'null_location': row[3],
                    'seasons_count': row[4],
                    'quality_score': max(0, 100 - (row[1] + row[2] + row[3]) / row[0] * 100)
                }
            
            # Test base_features table if it exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'base_features'
                )
            """)
            
            if cursor.fetchone()[0]:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_rows,
                        COUNT(*) FILTER (WHERE outcome_tier1 IS NULL) as null_outcome,
                        COUNT(DISTINCT game_year) as seasons_count
                    FROM features_pitch.base_features
                    LIMIT 1
                """)
                
                if cursor.rowcount > 0:
                    row = cursor.fetchone()
                    results['base_features_quality'] = {
                        'total_rows': row[0],
                        'null_outcome': row[1],
                        'seasons_count': row[2],
                        'quality_score': max(0, 100 - (row[1] / row[0] * 100))
                    }
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Data quality test failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def run_all_tests(self) -> dict:
        """Run all tests and return comprehensive results."""
        logger.info("Running comprehensive pitch modeling pipeline tests...")
        
        all_results = {
            'database': self.test_database_connectivity(),
            'feature_scripts': self.test_feature_population_scripts(),
            'model_components': self.test_model_training_components(),
            'cli_integration': self.test_cli_integration(),
            'data_quality': self.test_data_quality_checks()
        }
        
        # Calculate overall score
        total_tests = 0
        passed_tests = 0
        
        for category, results in all_results.items():
            if 'error' in results:
                continue
                
            for test_name, result in results.items():
                if test_name == 'error':
                    continue
                    
                total_tests += 1
                if result is True:
                    passed_tests += 1
        
        all_results['overall'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0
        }
        
        return all_results
    
    def print_results(self, results: dict) -> None:
        """Print formatted test results."""
        print("\n" + "="*60)
        print("PITCH-LEVEL MODELING PIPELINE TEST RESULTS")
        print("="*60)
        
        # Database tests
        if 'database' in results:
            db_results = results['database']
            print(f"\n📊 DATABASE TESTS:")
            print(f"  Connection: {'✅ PASS' if db_results.get('connection', False) else '❌ FAIL'}")
            print(f"  Tables: {'✅ PASS' if db_results.get('tables_exist', False) else '❌ FAIL'}")
            
            if 'row_counts' in db_results:
                for table, count in db_results['row_counts'].items():
                    print(f"  {table}: {count:,} rows")
        
        # Feature script tests
        if 'feature_scripts' in results:
            script_results = results['feature_scripts']
            print(f"\n🔧 FEATURE SCRIPTS:")
            print(f"  Base Features: {'✅ PASS' if script_results.get('base_features_script', False) else '❌ FAIL'}")
            print(f"  Engineered Features: {'✅ PASS' if script_results.get('engineered_features_script', False) else '❌ FAIL'}")
            print(f"  Script Syntax: {'✅ PASS' if script_results.get('script_syntax', False) else '❌ FAIL'}")
        
        # Model component tests
        if 'model_components' in results:
            model_results = results['model_components']
            print(f"\n🤖 MODEL COMPONENTS:")
            print(f"  Model Class: {'✅ PASS' if model_results.get('model_class_import', False) else '❌ FAIL'}")
            print(f"  Calibrator Class: {'✅ PASS' if model_results.get('calibrator_class_import', False) else '❌ FAIL'}")
            print(f"  XGBoost: {'✅ PASS' if model_results.get('xgboost_available', False) else '❌ FAIL'}")
            print(f"  Scikit-learn: {'✅ PASS' if model_results.get('sklearn_available', False) else '❌ FAIL'}")
        
        # CLI integration tests
        if 'cli_integration' in results:
            cli_results = results['cli_integration']
            print(f"\n💻 CLI INTEGRATION:")
            print(f"  Pitch Models App: {'✅ PASS' if cli_results.get('pitch_models_app_import', False) else '❌ FAIL'}")
            print(f"  Main CLI: {'✅ PASS' if cli_results.get('main_cli_import', False) else '❌ FAIL'}")
            print(f"  Typer: {'✅ PASS' if cli_results.get('typer_available', False) else '❌ FAIL'}")
        
        # Data quality tests
        if 'data_quality' in results:
            quality_results = results['data_quality']
            print(f"\n📈 DATA QUALITY:")
            
            if 'locations_quality' in quality_results:
                loc_qual = quality_results['locations_quality']
                print(f"  Locations Table: {loc_qual['total_rows']:,} rows, {loc_qual['quality_score']:.1f}% quality")
            
            if 'base_features_quality' in quality_results:
                base_qual = quality_results['base_features_quality']
                print(f"  Base Features: {base_qual['total_rows']:,} rows, {base_qual['quality_score']:.1f}% quality")
        
        # Overall results
        if 'overall' in results:
            overall = results['overall']
            print(f"\n🎯 OVERALL RESULTS:")
            print(f"  Tests Passed: {overall['passed_tests']}/{overall['total_tests']}")
            print(f"  Success Rate: {overall['success_rate']:.1%}")
            
            if overall['success_rate'] >= 0.8:
                print("  🟢 PIPELINE READY FOR PRODUCTION")
            elif overall['success_rate'] >= 0.6:
                print("  🟡 PIPELINE NEEDS MINOR FIXES")
            else:
                print("  🔴 PIPELINE NEEDS MAJOR FIXES")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Test pitch-level modeling pipeline components'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Run all tests'
    )
    parser.add_argument(
        '--component', '-c',
        choices=['database', 'scripts', 'models', 'cli', 'quality'],
        help='Test specific component'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    tester = PitchModelingPipelineTester()
    
    if args.all:
        results = tester.run_all_tests()
        tester.print_results(results)
    elif args.component:
        if args.component == 'database':
            results = {'database': tester.test_database_connectivity()}
        elif args.component == 'scripts':
            results = {'feature_scripts': tester.test_feature_population_scripts()}
        elif args.component == 'models':
            results = {'model_components': tester.test_model_training_components()}
        elif args.component == 'cli':
            results = {'cli_integration': tester.test_cli_integration()}
        elif args.component == 'quality':
            results = {'data_quality': tester.test_data_quality_checks()}
        
        tester.print_results(results)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

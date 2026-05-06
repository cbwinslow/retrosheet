"""Ensemble training and management commands."""

import json
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from baseball.models.ensemble.working_ensemble import WorkingEnsembleTrainer

console = Console()
ensemble_app = typer.Typer(help='Ensemble model training and management')


@ensemble_app.command()
def train(
    seasons: Optional[List[int]] = typer.Option(
        None, 
        '--seasons', 
        '-s', 
        help='Seasons to include in training (default: 2015-2023)'
    ),
    sample_rate: float = typer.Option(
        0.1, 
        '--sample-rate', 
        '-r', 
        help='Sample rate for faster training (0.0-1.0)'
    ),
    model_types: Optional[List[str]] = typer.Option(
        None, 
        '--models', 
        '-m', 
        help='Model types to train (xgboost, hist_gb)'
    ),
    concurrent: bool = typer.Option(
        True, 
        '--concurrent/--no-concurrent', 
        help='Enable concurrent training'
    ),
    output_dir: str = typer.Option(
        'data/models/ensemble', 
        '--output-dir', 
        '-o', 
        help='Output directory for trained models'
    )
):
    """Train ensemble of baseball prediction models."""
    
    console.print('\n[bold blue]🚀 Starting Ensemble Training[/bold blue]\n')
    
    # Set defaults
    if seasons is None:
        seasons = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]
        console.print(f'[dim]Using default seasons: {seasons}[/dim]')
    
    if model_types is None:
        model_types = ['xgboost', 'hist_gb']
        console.print(f'[dim]Using default model types: {model_types}[/dim]')
    
    try:
        # Initialize trainer
        trainer = WorkingEnsembleTrainer(model_dir=output_dir)
        
        # Show training configuration
        config_table = Table(title='Training Configuration')
        config_table.add_column('Parameter')
        config_table.add_column('Value')
        
        config_table.add_row('Seasons', ', '.join(map(str, seasons)))
        config_table.add_row('Sample Rate', f'{sample_rate:.1%}')
        config_table.add_row('Model Types', ', '.join(model_types))
        config_table.add_row('Concurrent', 'Yes' if concurrent else 'No')
        config_table.add_row('Output Directory', output_dir)
        
        console.print(config_table)
        console.print()
        
        # Train ensemble with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console
        ) as progress:
            task = progress.add_task('Training ensemble models...', total=None)
            
            results = trainer.train_ensemble(
                seasons=seasons,
                sample_rate=sample_rate,
                concurrent=concurrent
            )
        
        # Display results
        console.print('\n[bold green]✅ Ensemble Training Completed![/bold green]\n')
        
        # Results table
        results_table = Table(title='Training Results')
        results_table.add_column('Metric')
        results_table.add_column('Value')
        
        ensemble_results = results.get('ensemble_results', {})
        model_results = results.get('model_results', {})
        
        results_table.add_row('Target Level', results.get('target_level', 'N/A'))
        results_table.add_row('Total Samples', f"{results.get('data_splits', {}).get('train', 0) + results.get('data_splits', {}).get('val', 0) + results.get('data_splits', {}).get('test', 0):,}")
        results_table.add_row('Ensemble Accuracy', f"{ensemble_results.get('ensemble_accuracy', 0):.3f}")
        results_table.add_row('Best Individual Accuracy', f"{ensemble_results.get('best_individual_accuracy', 0):.3f}")
        results_table.add_row('Ensemble Improvement', f"{ensemble_results.get('improvement', 0):+3f}")
        results_table.add_row('Models in Ensemble', str(ensemble_results.get('n_models', 0)))
        
        console.print(results_table)
        
        # Individual model results
        if model_results:
            console.print('\n[bold]Individual Model Results:[/bold]')
            model_table = Table()
            model_table.add_column('Model Type')
            model_table.add_column('Accuracy')
            model_table.add_column('Log Loss')
            model_table.add_column('Training Time (s)')
            model_table.add_column('Status')
            
            for model_name, result in model_results.items():
                if 'error' in result:
                    model_table.add_row(
                        model_name,
                        'N/A',
                        'N/A', 
                        'N/A',
                        f'[red]Failed: {result["error"]}[/red]'
                    )
                else:
                    model_table.add_row(
                        model_name,
                        f"{result.get('accuracy', 0):.3f}",
                        f"{result.get('log_loss', 0):.3f}",
                        f"{result.get('training_time', 0):.2f}",
                        '[green]Success[/green]'
                    )
            
            console.print(model_table)
        
        # Save results summary
        timestamp = results.get('timestamp', 'unknown')
        console.print(f'\n[dim]Results saved with timestamp: {timestamp}[/dim]')
        console.print(f'[dim]Models saved to: {output_dir}[/dim]')
        
    except Exception as e:
        console.print(f'\n[red]❌ Training failed: {e}[/red]')
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


@ensemble_app.command()
def list(
    model_dir: str = typer.Option(
        'data/models/ensemble', 
        '--model-dir', 
        '-d', 
        help='Directory containing trained models'
    )
):
    """List available trained ensemble models."""
    
    console.print('\n[bold blue]📋 Available Ensemble Models[/bold blue]\n')
    
    try:
        model_path = Path(model_dir)
        
        if not model_path.exists():
            console.print(f'[yellow]⚠️  Model directory does not exist: {model_dir}[/yellow]')
            return
        
        # Find model files
        model_files = list(model_path.glob('*.joblib'))
        result_files = list(model_path.glob('ensemble_results_*.json'))
        
        if not model_files:
            console.print('[dim]No trained models found[/dim]')
            return
        
        # Model files table
        models_table = Table(title='Trained Model Files')
        models_table.add_column('Model File')
        models_table.add_column('Size')
        models_table.add_column('Modified')
        
        for model_file in sorted(model_files):
            stat = model_file.stat()
            models_table.add_row(
                model_file.name,
                f"{stat.st_size / 1024 / 1024:.1f} MB",
                f"{stat.st_mtime}"
            )
        
        console.print(models_table)
        
        # Results files table
        if result_files:
            console.print('\n[bold]Training Results:[/bold]')
            results_table = Table()
            results_table.add_column('Results File')
            results_table.add_column('Size')
            results_table.add_column('Modified')
            
            for result_file in sorted(result_files):
                stat = result_file.stat()
                results_table.add_row(
                    result_file.name,
                    f"{stat.st_size / 1024:.1f} KB",
                    f"{stat.st_mtime}"
                )
            
            console.print(results_table)
        
        # Show detailed results for latest
        if result_files:
            latest_result = max(result_files, key=lambda x: x.stat().st_mtime)
            console.print(f'\n[bold]Latest Results: {latest_result.name}[/bold]')
            
            try:
                with open(latest_result, 'r') as f:
                    results_data = json.load(f)
                
                ensemble_results = results_data.get('ensemble_results', {})
                console.print(f'Ensemble Accuracy: {ensemble_results.get("ensemble_accuracy", "N/A")}')
                console.print(f'Improvement: {ensemble_results.get("improvement", "N/A")}')
                
            except Exception as e:
                console.print(f'[yellow]Could not read results file: {e}[/yellow]')
        
    except Exception as e:
        console.print(f'\n[red]❌ Error listing models: {e}[/red]')
        raise typer.Exit(1)


@ensemble_app.command()
def evaluate(
    model_path: str = typer.Option(
        ..., 
        '--model-path', 
        '-m', 
        help='Path to trained model file'
    ),
    test_data: Optional[str] = typer.Option(
        None, 
        '--test-data', 
        '-t', 
        help='Path to test data file'
    ),
    seasons: Optional[List[int]] = typer.Option(
        [2023], 
        '--seasons', 
        '-s', 
        help='Seasons to evaluate on'
    )
):
    """Evaluate trained ensemble model performance."""
    
    console.print('\n[bold blue]🔍 Evaluating Ensemble Model[/bold blue]\n')
    
    try:
        import joblib
        
        # Load model
        model_data = joblib.load(model_path)
        console.print(f'✅ Loaded model: {model_path}')
        console.print(f'   Model type: {model_data.get("model_type", "Unknown")}')
        console.print(f'   Training accuracy: {model_data.get("accuracy", "Unknown")}')
        
        # TODO: Implement evaluation on test data
        console.print('\n[dim]Evaluation on test data not yet implemented[/dim]')
        console.print('[dim]Use --test-data to specify custom test data[/dim]')
        
    except Exception as e:
        console.print(f'\n[red]❌ Evaluation failed: {e}[/red]')
        raise typer.Exit(1)


@ensemble_app.command()
def info(
    model_path: str = typer.Argument(..., help='Path to model file')
):
    """Show detailed information about a trained model."""
    
    console.print('\n[bold blue]ℹ️  Model Information[/bold blue]\n')
    
    try:
        import joblib
        
        # Load model
        model_data = joblib.load(model_path)
        
        # Info table
        info_table = Table(title='Model Details')
        info_table.add_column('Property')
        info_table.add_column('Value')
        
        info_table.add_row('Model File', str(Path(model_path).name))
        info_table.add_row('Model Type', model_data.get('model_type', 'Unknown'))
        info_table.add_row('Target Level', model_data.get('target_level', 'Unknown'))
        info_table.add_row('Training Accuracy', f"{model_data.get('accuracy', 'Unknown')}")
        info_table.add_row('Training Log Loss', f"{model_data.get('log_loss', 'Unknown')}")
        info_table.add_row('Training Time', f"{model_data.get('training_time', 'Unknown')}s")
        
        # Feature information
        if 'feature_names' in model_data:
            feature_names = model_data['feature_names']
            info_table.add_row('Number of Features', str(len(feature_names)))
            info_table.add_row('Feature Names', ', '.join(feature_names[:10]) + ('...' if len(feature_names) > 10 else ''))
        
        # Timestamp
        if 'timestamp' in model_data:
            info_table.add_row('Training Timestamp', model_data['timestamp'])
        
        console.print(info_table)
        
    except Exception as e:
        console.print(f'\n[red]❌ Could not load model: {e}[/red]')
        raise typer.Exit(1)


@ensemble_app.command()
def doctor():
    """Check ensemble training system health."""
    
    console.print('\n[bold blue]🏥 Ensemble System Doctor[/bold blue]\n')
    
    checks = []
    
    # Check dependencies
    try:
        import joblib
        import sklearn
        import xgboost as xgb
        checks.append(('XGBoost', '✅ Available', 'green'))
    except ImportError as e:
        checks.append(('XGBoost', f'❌ Missing: {e}', 'red'))
    
    try:
        import scipy
        checks.append(('SciPy', '✅ Available', 'green'))
    except ImportError as e:
        checks.append(('SciPy', f'❌ Missing: {e}', 'red'))
    
    # Check database connection
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            database='retrosheet',
            user='cbwinslow',
            password='123qweasd'
        )
        checks.append(('Database Connection', '✅ Connected', 'green'))
        conn.close()
    except Exception as e:
        checks.append(('Database Connection', f'❌ Failed: {e}', 'red'))
    
    # Check directories
    model_dir = Path('data/models/ensemble')
    if model_dir.exists():
        checks.append(('Model Directory', f'✅ Exists ({model_dir})', 'green'))
    else:
        checks.append(('Model Directory', f'⚠️  Missing ({model_dir})', 'yellow'))
    
    # Check data availability
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            database='retrosheet',
            user='cbwinslow',
            password='123qweasd'
        )
        
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM features_pitch.base_features LIMIT 1')
            count = cur.fetchone()[0]
            checks.append(('Pitch Features Data', f'✅ Available ({count:,} rows)', 'green'))
        
        conn.close()
    except Exception as e:
        checks.append(('Pitch Features Data', f'❌ Error: {e}', 'red'))
    
    # Display results
    table = Table(show_header=True, header_style='bold magenta')
    table.add_column('Component')
    table.add_column('Status')
    
    for component, status, color in checks:
        table.add_row(component, f'[{color}]{status}[/{color}]')
    
    console.print(table)
    
    # Overall status
    failed = [c for c in checks if '❌' in c[1]]
    if failed:
        console.print(f'\n[red]❌ {len(failed)} check(s) failed[/red]')
        raise typer.Exit(1)
    else:
        console.print('\n[green]✅ All checks passed[/green]')

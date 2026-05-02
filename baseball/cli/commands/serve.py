"""
CLI commands for model serving and inference.

Usage:
    baseball serve start --model pitch_level --port 8000
    baseball serve predict --model pitch_level --features "[1.2, 3.4, ...]"
    baseball serve batch --model pitch_level --input data.csv
    baseball serve status
    baseball serve ab-test --model-a tier1_production --model-b tier1_experiment
"""

from typing import Optional
import json

import typer
from rich.console import Console
from rich.table import Table

serve_app = typer.Typer()
console = Console()


@serve_app.command(name='start')
def start_server(
    model: str = typer.Option(
        'pitch_level',
        '--model', '-m',
        help='Model name to serve'
    ),
    version: str = typer.Option(
        'production',
        '--version', '-v',
        help='Model version (production, staging, or specific)'
    ),
    port: int = typer.Option(
        8000,
        '--port', '-p',
        help='Server port'
    ),
    cache_size: int = typer.Option(
        5,
        '--cache-size', '-c',
        help='Model cache size'
    )
):
    """Start the model serving API (placeholder for future FastAPI server)."""
    from baseball.models import ModelServer
    
    console.print(f'[bold green]Starting model server...[/bold green]')
    console.print(f'  Model: [cyan]{model}[/cyan] ({version})')
    console.print(f'  Port: [cyan]{port}[/cyan]')
    console.print(f'  Cache: [cyan]{cache_size}[/cyan] models')
    
    # Initialize server and load model
    server = ModelServer(cache_size=cache_size)
    
    if server.load_model(model, version):
        console.print(f'  [green]✓[/green] Model loaded successfully')
        
        # Show model info
        stats = server.get_performance_stats()
        console.print(f'\n[dim]Server ready. Use:[/dim]')
        console.print(f'  [cyan]baseball serve predict --model {model} --features "[...]"[/cyan]')
        console.print(f'  [cyan]baseball serve batch --model {model} --input data.csv[/cyan]')
        console.print(f'\n[yellow]Note:[/yellow] Full REST API server is planned for future release.')
        console.print(f'      Use Python API for now: [cyan]ModelServer()[/cyan]')
    else:
        console.print(f'  [red]✗[/red] Failed to load model')
        raise typer.Exit(code=1)


@serve_app.command(name='predict')
def predict_single(
    model: str = typer.Option(
        'pitch_level',
        '--model', '-m',
        help='Model name'
    ),
    version: str = typer.Option(
        'production',
        '--version', '-v',
        help='Model version'
    ),
    features: str = typer.Option(
        ...,
        '--features', '-f',
        help='Feature vector as JSON array (e.g., "[1.0, 2.0, 3.0]")'
    )
):
    """Make a single prediction with a model."""
    import numpy as np
    from baseball.models import ModelServer
    
    # Parse features
    try:
        feature_list = json.loads(features)
        feature_array = np.array(feature_list)
    except json.JSONDecodeError:
        console.print('[red]Error: Invalid JSON in features[/red]')
        raise typer.Exit(code=1)
    
    # Load model and predict
    console.print(f'[dim]Loading model {model} ({version})...[/dim]')
    server = ModelServer()
    
    if not server.load_model(model, version):
        console.print(f'[red]Error: Could not load model {model}[/red]')
        raise typer.Exit(code=1)
    
    # Make prediction
    result = server.predict(feature_array)
    
    # Display result
    console.print(f'\n[bold]Prediction Result:[/bold]')
    console.print(f'  Prediction: [cyan]{result.prediction}[/cyan]')
    
    if result.confidence:
        console.print(f'  Confidence: [cyan]{result.confidence:.2%}[/cyan]')
    
    if result.probabilities:
        console.print(f'\n  Probabilities:')
        for cls, prob in sorted(result.probabilities.items(), key=lambda x: -x[1])[:5]:
            bar = '█' * int(prob * 20)
            console.print(f'    {cls:12} {bar:<20} {prob:.2%}')
    
    console.print(f'\n  [dim]Inference time: {result.inference_time_ms:.2f} ms[/dim]')
    console.print(f'  [dim]Model version: {result.model_version}[/dim]')


@serve_app.command(name='batch')
def predict_batch(
    model: str = typer.Option(
        'pitch_level',
        '--model', '-m',
        help='Model name'
    ),
    input_file: str = typer.Option(
        ...,
        '--input', '-i',
        help='Input CSV file with features'
    ),
    output: Optional[str] = typer.Option(
        None,
        '--output', '-o',
        help='Output file for predictions (default: stdout)'
    ),
    batch_size: int = typer.Option(
        32,
        '--batch-size', '-b',
        help='Batch size for processing'
    )
):
    """Make batch predictions on a CSV file."""
    import pandas as pd
    from baseball.models import ModelServer
    
    console.print(f'[dim]Loading data from {input_file}...[/dim]')
    
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        console.print(f'[red]Error loading file: {e}[/red]')
        raise typer.Exit(code=1)
    
    # Load model
    server = ModelServer()
    if not server.load_model(model):
        console.print(f'[red]Error: Could not load model {model}[/red]')
        raise typer.Exit(code=1)
    
    console.print(f'  [green]✓[/green] Loaded {len(df)} rows')
    
    # Extract features (all columns except target if exists)
    feature_cols = [c for c in df.columns if c not in ['target', 'outcome', 'label']]
    features = df[feature_cols].values
    
    # Make predictions
    result = server.predict_batch(features, batch_size=batch_size)
    
    # Add predictions to dataframe
    df['prediction'] = result.predictions
    df['inference_time_ms'] = result.inference_time_ms / len(df)  # per-row time
    
    console.print(f'\n[bold]Batch Prediction Results:[/bold]')
    console.print(f'  Predictions: [cyan]{len(result.predictions)}[/cyan]')
    console.print(f'  Total time: [cyan]{result.inference_time_ms:.2f} ms[/cyan]')
    console.print(f'  Throughput: [cyan]{result.throughput:.1f}[/cyan] predictions/sec')
    
    # Save or display
    if output:
        df.to_csv(output, index=False)
        console.print(f'  [green]✓[/green] Saved to {output}')
    else:
        console.print(f'\n  First 5 predictions:')
        for i, pred in enumerate(result.predictions[:5]):
            console.print(f'    Row {i}: [cyan]{pred}[/cyan]')


@serve_app.command(name='status')
def server_status():
    """Check model server status and loaded models."""
    from baseball.models import ModelRegistry
    
    registry = ModelRegistry()
    models = registry.list_models()
    
    table = Table(title='Registered Models')
    table.add_column('Model Name', style='cyan')
    table.add_column('Version', style='green')
    table.add_column('Status', style='yellow')
    table.add_column('Accuracy', style='magenta')
    table.add_column('Path', style='dim')
    
    for entry in models:
        status_icon = '🟢' if entry.status == 'production' else '🟡' if entry.status == 'staging' else '⚪'
        table.add_row(
            entry.model_name,
            entry.version,
            f'{status_icon} {entry.status}',
            f'{entry.accuracy:.3f}' if entry.accuracy else '-',
            entry.artifact_path[:40] + '...' if len(entry.artifact_path) > 40 else entry.artifact_path
        )
    
    console.print(table)


@serve_app.command(name='ab-test')
def setup_ab_test(
    model_a: str = typer.Option(
        ...,
        '--model-a', '-a',
        help='Model A (control) name:version'
    ),
    model_b: str = typer.Option(
        ...,
        '--model-b', '-b',
        help='Model B (treatment) name:version'
    ),
    split: float = typer.Option(
        0.5,
        '--split', '-s',
        help='Traffic split to model A (0.5 = 50/50)'
    ),
    features: str = typer.Option(
        ...,
        '--features', '-f',
        help='Test feature vector as JSON array'
    ),
    iterations: int = typer.Option(
        100,
        '--iterations', '-n',
        help='Number of test predictions'
    )
):
    """Run A/B test between two models."""
    import numpy as np
    from baseball.models import ModelServer
    
    # Parse features
    try:
        feature_list = json.loads(features)
        feature_array = np.array(feature_list)
    except json.JSONDecodeError:
        console.print('[red]Error: Invalid JSON in features[/red]')
        raise typer.Exit(code=1)
    
    console.print(f'[bold]A/B Test Setup[/bold]')
    console.print(f'  Model A: [cyan]{model_a}[/cyan] ({split*100:.0f}% traffic)')
    console.print(f'  Model B: [cyan]{model_b}[/cyan] ({(1-split)*100:.0f}% traffic)')
    console.print(f'  Iterations: [cyan]{iterations}[/cyan]\n')
    
    # Run test
    server = ModelServer()
    server.setup_ab_test(model_a, model_b, split)
    
    a_count = 0
    b_count = 0
    a_times = []
    b_times = []
    
    for i in range(iterations):
        result = server.predict_with_ab(feature_array)
        
        if result.model_version.startswith('A:'):
            a_count += 1
            a_times.append(result.inference_time_ms)
        else:
            b_count += 1
            b_times.append(result.inference_time_ms)
    
    # Show results
    console.print(f'[bold]Results:[/bold]')
    console.print(f'  Model A traffic: [cyan]{a_count}[/cyan] ({a_count/iterations*100:.1f}%)')
    console.print(f'  Model B traffic: [cyan]{b_count}[/cyan] ({b_count/iterations*100:.1f}%)')
    
    if a_times:
        console.print(f'  Avg inference (A): [cyan]{np.mean(a_times):.2f}[/cyan] ms')
    if b_times:
        console.print(f'  Avg inference (B): [cyan]{np.mean(b_times):.2f}[/cyan] ms')
    
    console.print(f'\n[dim]A/B test configuration saved. Use in production:[/dim]')
    console.print(f'  [cyan]server.setup_ab_test("{model_a}", "{model_b}", {split})[/cyan]')

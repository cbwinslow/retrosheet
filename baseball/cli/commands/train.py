"""
Training CLI Commands

Commands for running training experiments and managing models.
"""

import typer
from rich.console import Console
from rich.table import Table
from typing import List, Optional

from baseball.training import (
    TrainingOrchestrator,
    ExperimentConfig,
    ModelType,
    TrainingConfig,
)

console = Console()
train_app = typer.Typer(help="Training commands for baseball models")


@train_app.command(name='run')
def train_run(
    model_type: str = typer.Option(..., '--model', '-m', help='Model type to train'),
    seasons: str = typer.Option(..., '--seasons', '-s', help='Seasons to train on (e.g., 2020-2024)'),
    experiment_name: str = typer.Option(..., '--name', '-n', help='Experiment name'),
    description: str = typer.Option('', '--description', '-d', help='Experiment description'),
    promote: bool = typer.Option(False, '--promote', '-p', help='Promote best model to production'),
    tags: Optional[str] = typer.Option(None, '--tags', '-t', help='Comma-separated tags'),
):
    """Run a training experiment."""
    # Parse model type
    try:
        model_enum = ModelType(model_type.lower())
    except ValueError:
        console.print(f'[red]Invalid model type: {model_type}[/red]')
        console.print(f'Valid types: {[t.value for t in ModelType]}')
        raise typer.Exit(1)
    
    # Parse seasons
    if '-' in seasons:
        start, end = map(int, seasons.split('-'))
        season_list = list(range(start, end + 1))
    else:
        season_list = [int(s.strip()) for s in seasons.split(',')]
    
    # Parse tags
    tag_list = tags.split(',') if tags else []
    
    console.print(f'[bold]Starting training experiment:[/bold] {experiment_name}')
    console.print(f'  Model type: {model_enum.value}')
    console.print(f'  Seasons: {season_list}')
    console.print(f'  Promote best: {promote}')
    console.print()
    
    # Run experiment
    orchestrator = TrainingOrchestrator()
    
    result = orchestrator.run_experiment(
        model_type=model_enum,
        seasons=season_list,
        experiment_name=experiment_name,
        description=description,
        tags=tag_list,
        promote_best=promote
    )
    
    # Display results
    console.print(f'\n[bold]Experiment Complete:[/bold] {result.experiment_id}')
    console.print(f'  Status: {result.status}')
    console.print(f'  Duration: {result.duration_seconds:.1f}s')
    
    if result.best_model_id:
        console.print(f'\n[green]Best Model: {result.best_model_id}[/green]')
        console.print(f'  Accuracy: {result.best_metric:.3f}')
        
        if result.vs_baseline_improvement is not None:
            sign = '+' if result.vs_baseline_improvement >= 0 else ''
            color = 'green' if result.vs_baseline_improvement >= 0 else 'red'
            console.print(f'  vs Baseline: [{color}]{sign}{result.vs_baseline_improvement:.3f}[/{color}]')
    
    if result.training_results:
        console.print(f'\n[dim]Completed {len(result.training_results)} training runs[/dim]')


@train_app.command(name='list')
def train_list(
    model_type: Optional[str] = typer.Option(None, '--model', '-m', help='Filter by model type'),
    status: Optional[str] = typer.Option(None, '--status', help='Filter by status'),
    limit: int = typer.Option(20, '--limit', '-l', help='Max experiments to show'),
):
    """List recent training experiments."""
    orchestrator = TrainingOrchestrator()
    
    # Parse model type filter
    model_enum = None
    if model_type:
        try:
            model_enum = ModelType(model_type.lower())
        except ValueError:
            console.print(f'[red]Invalid model type: {model_type}[/red]')
            raise typer.Exit(1)
    
    experiments = orchestrator.list_experiments(
        model_type=model_enum,
        status=status,
        limit=limit
    )
    
    if not experiments:
        console.print('[yellow]No experiments found[/yellow]')
        return
    
    table = Table()
    table.add_column('Experiment ID', style='cyan')
    table.add_column('Name')
    table.add_column('Model Type')
    table.add_column('Status')
    table.add_column('Best Metric')
    table.add_column('Started')
    
    for exp in experiments:
        metrics = exp.get('metrics', {})
        accuracy = metrics.get('accuracy', 0)
        
        status_color = {
            'completed': 'green',
            'running': 'yellow',
            'failed': 'red'
        }.get(exp.get('status'), 'white')
        
        table.add_row(
            exp.get('experiment_id', 'N/A')[:20],
            exp.get('experiment_name', 'N/A'),
            exp.get('model_type', 'N/A'),
            f'[{status_color}]{exp.get("status", "unknown")}[/{status_color}]',
            f'{accuracy:.3f}' if accuracy else 'N/A',
            exp.get('started_at', 'N/A')[:10]
        )
    
    console.print(table)
    console.print(f'\n[dim]Showing {len(experiments)} experiments[/dim]')


@train_app.command(name='show')
def train_show(
    experiment_id: str = typer.Option(..., '--id', '-i', help='Experiment ID'),
):
    """Show details of a specific experiment."""
    orchestrator = TrainingOrchestrator()
    
    exp = orchestrator.get_experiment(experiment_id)
    
    if not exp:
        console.print(f'[red]Experiment not found: {experiment_id}[/red]')
        raise typer.Exit(1)
    
    console.print(f'[bold]Experiment: {exp.get("experiment_name")}[/bold]')
    console.print(f'  ID: {exp.get("experiment_id")}')
    console.print(f'  Model Type: {exp.get("model_type")}')
    console.print(f'  Status: {exp.get("status")}')
    console.print(f'  Started: {exp.get("started_at")}')
    if exp.get('completed_at'):
        console.print(f'  Completed: {exp.get("completed_at")}')
    
    console.print(f'\n[bold]Configuration:[/bold]')
    config = exp.get('config', {})
    console.print(f'  Description: {config.get("description", "N/A")}')
    console.print(f'  Tags: {", ".join(config.get("tags", [])) or "None"}')
    
    console.print(f'\n[bold]Results:[/bold]')
    metrics = exp.get('metrics', {})
    for metric, value in metrics.items():
        console.print(f'  {metric}: {value:.4f}')
    
    if exp.get('best_model_id'):
        console.print(f'\n[green]Best Model: {exp.get("best_model_id")}[/green]')
    
    # Show training runs
    runs = exp.get('training_runs', [])
    if runs:
        console.print(f'\n[bold]Training Runs ({len(runs)}):[/bold]')
        for run in runs:
            run_metrics = run.get('metrics', {})
            acc = run_metrics.get('accuracy', 0)
            console.print(f'  Run {run.get("run_id")}: accuracy={acc:.3f}')


@train_app.command(name='compare')
def train_compare(
    experiment_ids: List[str] = typer.Argument(..., help='Experiment IDs to compare'),
    metric: str = typer.Option('accuracy', '--metric', '-m', help='Metric to compare'),
):
    """Compare multiple experiments."""
    if len(experiment_ids) < 2:
        console.print('[red]Need at least 2 experiments to compare[/red]')
        raise typer.Exit(1)
    
    orchestrator = TrainingOrchestrator()
    comparison = orchestrator.compare_experiments(experiment_ids, metric)
    
    console.print(f'[bold]Experiment Comparison ({metric})[/bold]\n')
    
    table = Table()
    table.add_column('Experiment', style='cyan')
    table.add_column('Model Type')
    table.add_column('Status')
    table.add_column(metric.capitalize(), justify='right')
    table.add_column('Best Model')
    
    for exp in comparison.get('experiments', []):
        is_best = exp['experiment_id'] == comparison.get('best_experiment')
        metric_value = exp.get(metric, 0)
        
        table.add_row(
            f'[bold]{exp["experiment_id"]}[/bold]' if is_best else exp['experiment_id'],
            exp.get('model_type', 'N/A'),
            exp.get('status', 'unknown'),
            f'{metric_value:.4f}' if metric_value else 'N/A',
            str(exp.get('best_model_id', 'N/A'))
        )
    
    console.print(table)
    
    if comparison.get('best_experiment'):
        console.print(f'\n[green]Best: {comparison["best_experiment"]} ({comparison["best_value"]:.4f})[/green]')


@train_app.command(name='promote')
def train_promote(
    experiment_id: str = typer.Option(..., '--experiment', '-e', help='Experiment ID'),
):
    """Promote the best model from an experiment to production."""
    from baseball.models import ModelRegistry
    
    orchestrator = TrainingOrchestrator()
    registry = ModelRegistry()
    
    exp = orchestrator.get_experiment(experiment_id)
    if not exp:
        console.print(f'[red]Experiment not found: {experiment_id}[/red]')
        raise typer.Exit(1)
    
    best_model_id = exp.get('best_model_id')
    if not best_model_id:
        console.print('[red]No best model found for this experiment[/red]')
        raise typer.Exit(1)
    
    console.print(f'Promoting model {best_model_id} to production...')
    
    try:
        registry.promote_to_production(best_model_id)
        console.print(f'[green]Successfully promoted model {best_model_id}[/green]')
    except Exception as e:
        console.print(f'[red]Failed to promote: {e}[/red]')
        raise typer.Exit(1)

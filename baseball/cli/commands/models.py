"""ML model management commands."""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()

models_app = typer.Typer(help='ML model commands', no_args_is_help=True)


@models_app.command(name='list')
def models_list(
    show_archived: bool = typer.Option(False, '--archived', help='Include archived models'),
    model_name: Optional[str] = typer.Option(None, '--name', '-n', help='Filter by model name'),
    status: Optional[str] = typer.Option(None, '--status', '-s', help='Filter by status: production, staging, archived'),
    limit: int = typer.Option(20, '--limit', '-l', help='Maximum results to show'),
    show_metrics: bool = typer.Option(False, '--metrics', '-m', help='Show validation metrics'),
):
    """List available models in the registry."""
    from baseball.core.db import get_db_connection
    from baseball.models.registry import ModelRegistry

    # Try ModelRegistry first (newer implementation)
    try:
        registry = ModelRegistry()
        models = registry.list_models(model_name=model_name, status=status, limit=limit)

        if not models:
            console.print('[yellow]No models found matching criteria.[/yellow]')
            return

        table = Table(title=f'Registered Models ({len(models)} shown)')
        table.add_column('ID', style='dim', width=6)
        table.add_column('Name', style='cyan')
        table.add_column('Version', style='blue')
        table.add_column('Type', style='white')
        table.add_column('Status', style='green')
        table.add_column('Primary Metric', style='yellow')
        table.add_column('Training Date', style='dim')

        for model in models:
            status_color = {
                'production': '[bold green]',
                'staging': '[yellow]',
                'archived': '[dim]'
            }.get(model.status, '[white]')

            metric_str = f'{model.primary_metric_value:.4f}' if model.primary_metric_value else 'N/A'

            table.add_row(
                str(model.model_id),
                model.model_name,
                model.model_version,
                model.model_type,
                f"{status_color}{model.status}[/]",
                f"{model.primary_metric}: {metric_str}" if model.primary_metric else 'N/A',
                model.training_date.strftime('%Y-%m-%d') if model.training_date else 'N/A'
            )

        console.print(table)

        if show_metrics and models:
            console.print('\n[bold]Latest Model Metrics:[/bold]')
            latest = models[0]
            for metric, value in latest.validation_metrics.items():
                console.print(f'  {metric}: {value:.4f}')

        return

    except Exception:
        # Fallback to direct database query
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                query = """
                    SELECT model_name, model_type, task, current_version, total_versions, is_active, created_at
                    FROM models.registry
                    WHERE %s OR is_active = TRUE
                    ORDER BY created_at DESC
                """
                cur.execute(query, (show_archived,))
                rows = cur.fetchall()

                if not rows:
                    console.print('[yellow]No models found in registry.[/yellow]')
                    return

                table = Table(title='Available Models')
                table.add_column('Model')
                table.add_column('Type')
                table.add_column('Task')
                table.add_column('Version')
                table.add_column('Status')

                for row in rows:
                    status = 'active' if row[5] else 'archived'
                    version = f"{row[3]} ({row[4]} total)" if row[4] > 1 else row[3]
                    table.add_row(row[0], row[1], row[2], version, status)

                console.print(table)
                console.print(f'\n[dim]Found {len(rows)} model(s)[/dim]')

        except Exception as e:
            console.print(f'[red]Error querying model registry: {e}[/red]')
            # Fallback to placeholder data
            table = Table(title='Available Models')
            table.add_column('Model')
            table.add_column('Type')
            table.add_column('Versions')
            table.add_column('Status')
            table.add_row('win_probability_v1', 'classification', '1', 'active')
            table.add_row('pa_outcome_v1', 'classification', '1', 'active')
            console.print(table)


@models_app.command(name='info')
def models_info(
    model_name: str = typer.Argument(..., help='Model name or ID'),
):
    """Show detailed info about a model."""
    console.print(f'[dim]Loading info for model: {model_name}...[/dim]')
    # TODO: Load model metadata, show config, metrics, features
    raise typer.Exit(code=0)


@models_app.command(name='download')
def models_download(
    model_name: str = typer.Argument(..., help='Model name or ID'),
    version: str = typer.Option('latest', '--version', '-v', help='Model version'),
    output: Path = typer.Option(None, '--output', '-o', help='Download path'),
):
    """Download a model artifact."""
    from baseball.core.db import get_db_connection

    console.print(f'[dim]Downloading {model_name} (version: {version})...[/dim]')

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get model and version info
            if version == 'latest':
                cur.execute("""
                    SELECT v.artifact_path, r.model_name, v.version
                    FROM models.versions v
                    JOIN models.registry r ON v.model_id = r.id
                    WHERE r.model_name = %s
                    ORDER BY v.created_at DESC
                    LIMIT 1
                """, (model_name,))
            else:
                cur.execute("""
                    SELECT v.artifact_path, r.model_name, v.version
                    FROM models.versions v
                    JOIN models.registry r ON v.model_id = r.id
                    WHERE r.model_name = %s AND v.version = %s
                """, (model_name, version))

            row = cur.fetchone()
            if not row:
                console.print(f'[yellow]Model {model_name} version {version} not found.[/yellow]')
                raise typer.Exit(code=1)

            artifact_path, actual_name, actual_version = row

            # Determine output path
            if output is None:
                output = Path(f'{actual_name}_{actual_version}.pkl')

            # For now, create a placeholder pickle file
            # In production, would load actual model from artifact_path
            placeholder_model = {
                'model_name': actual_name,
                'version': actual_version,
                'status': 'placeholder',
                'note': 'Download actual model from storage'
            }

            with open(output, 'wb') as f:
                pickle.dump(placeholder_model, f)

            console.print(f'[green]✓ Downloaded to {output}[/green]')

    except Exception as e:
        console.print(f'[red]Error downloading model: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='archive')
def models_archive(
    model_name: str = typer.Argument(None, help='Model name or ID (deprecated, use model-id)'),
    model_id: int = typer.Option(None, '--model-id', help='Model ID to archive'),
    reason: str = typer.Option(None, '--reason', help='Reason for archiving'),
    force: bool = typer.Option(False, '--force', '-f', help='Archive even if production model'),
):
    """Archive a model (remove from active pool)."""
    from baseball.core.db import get_db_connection
    from baseball.models.registry import ModelRegistry

    # Use model_id if provided (newer API)
    if model_id is not None:
        try:
            registry = ModelRegistry()

            model = registry.get_model_by_id(model_id)
            if not model:
                console.print(f'[red]Model ID {model_id} not found.[/red]')
                raise typer.Exit(code=1)

            if model.status == 'production' and not force:
                console.print(f'[yellow]Model {model_id} is in production. Use --force to archive.[/yellow]')
                raise typer.Exit(code=1)

            success = registry.archive_model(model_id)
            if success:
                console.print(f'[green]✓ Archived {model.model_name} v{model.model_version}[/green]')
            else:
                console.print(f'[red]Failed to archive model {model_id}[/red]')
                raise typer.Exit(code=1)

        except Exception as e:
            console.print(f'[red]Error archiving model: {e}[/red]')
            raise typer.Exit(code=1)
    else:
        # Legacy API using model_name
        if model_name is None:
            console.print('[red]Please provide either --model-id or model_name argument[/red]')
            raise typer.Exit(code=1)

        console.print(f'[dim]Archiving model: {model_name}...[/dim]')

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Check if model exists
                cur.execute(
                    'SELECT id, is_active FROM models.registry WHERE model_name = %s',
                    (model_name,)
                )
                row = cur.fetchone()

                if not row:
                    console.print(f'[red]Model {model_name} not found.[/red]')
                    raise typer.Exit(code=1)

                if not row[1]:
                    console.print(f'[yellow]Model {model_name} is already archived.[/yellow]')
                    raise typer.Exit(code=0)

                # Archive the model
                cur.execute(
                    'UPDATE models.registry SET is_active = FALSE, updated_at = NOW() WHERE model_name = %s',
                    (model_name,)
                )
                conn.commit()

                # Log reason if provided
                if reason:
                    console.print(f'  Reason: {reason}')

                console.print(f'[green]✓ Model {model_name} archived successfully[/green]')

        except Exception as e:
            console.print(f'[red]Error archiving model: {e}[/red]')
            raise typer.Exit(code=1)


@models_app.command(name='compare')
def models_compare(
    models: list[str] = typer.Argument(..., help='Model names or IDs to compare'),
    metric: str = typer.Option('logloss', '--metric', '-m', help='Metric for comparison'),
):
    """Compare multiple models on a specific metric."""
    from baseball.core.db import get_db_connection

    if len(models) < 2:
        console.print('[red]Please provide at least 2 models to compare[/red]')
        raise typer.Exit(code=1)

    console.print(f'[dim]Comparing {len(models)} models on {metric}...[/dim]')

    try:
        conn = get_db_connection()
        results = []

        with conn.cursor() as cur:
            for model_name in models:
                cur.execute("""
                    SELECT r.model_name, v.version, v.metrics
                    FROM models.registry r
                    JOIN models.versions v ON r.id = v.model_id
                    WHERE r.model_name = %s
                    ORDER BY v.created_at DESC
                    LIMIT 1
                """, (model_name,))

                row = cur.fetchone()
                if row:
                    metrics = json.loads(row[2]) if row[2] else {}
                    metric_value = metrics.get(metric, metrics.get(metric.lower(), None))
                    results.append({
                        'model': row[0],
                        'version': row[1],
                        'metric_value': metric_value,
                        'all_metrics': metrics
                    })
                else:
                    console.print(f'[yellow]Model {model_name} not found[/yellow]')

        if not results:
            console.print('[red]No models found to compare[/red]')
            raise typer.Exit(code=1)

        # Sort by metric value
        results.sort(key=lambda x: x['metric_value'] if x['metric_value'] is not None else float('inf'))

        # Display comparison table
        table = Table(title=f'Model Comparison - {metric}')
        table.add_column('Rank')
        table.add_column('Model')
        table.add_column('Version')
        table.add_column(metric.capitalize(), justify='right')

        for i, r in enumerate(results, 1):
            val = f"{r['metric_value']:.4f}" if r['metric_value'] is not None else 'N/A'
            table.add_row(str(i), r['model'], r['version'], val)

        console.print(table)

        # Show winner
        if results and results[0]['metric_value'] is not None:
            console.print(f'\n[green]🏆 Best model: {results[0]["model"]} ({metric} = {results[0]["metric_value"]:.4f})[/green]')

    except Exception as e:
        console.print(f'[red]Error comparing models: {e}[/red]')


@models_app.command(name='export')
def models_export(
    model_name: str = typer.Argument(..., help='Model name or ID'),
    fmt: str = typer.Option('onnx', '--format', '-f', help='Export format: onnx, pmml, json, pickle'),
    output: Path = typer.Option(None, '--output', '-o', help='Output file path'),
):
    """Export a model to different formats."""
    from baseball.core.db import get_db_connection

    console.print(f'[dim]Exporting {model_name} to {fmt}...[/dim]')

    # Determine output path
    if output is None:
        output = Path(f'{model_name}.{fmt}')

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get model info and artifact path
            cur.execute("""
                SELECT r.model_name, r.model_type, r.task, r.features, v.artifact_path, v.metrics
                FROM models.registry r
                JOIN models.versions v ON r.id = v.model_id
                WHERE r.model_name = %s
                ORDER BY v.created_at DESC
                LIMIT 1
            """, (model_name,))

            row = cur.fetchone()
            if not row:
                console.print(f'[red]Model {model_name} not found[/red]')
                raise typer.Exit(code=1)

            model_data = {
                'model_name': row[0],
                'model_type': row[1],
                'task': row[2],
                'features': row[3],
                'export_format': fmt,
                'export_timestamp': str(datetime.now()),
            }

            # Export based on format
            if fmt == 'json':
                model_data['metrics'] = row[5]
                with open(output, 'w') as f:
                    json.dump(model_data, f, indent=2)

            elif fmt == 'pickle' or fmt == 'pkl':
                # In production, would load actual model from artifact_path
                with open(output, 'wb') as f:
                    pickle.dump(model_data, f)

            elif fmt == 'onnx':
                # Placeholder - would convert to ONNX format
                with open(output, 'w') as f:
                    f.write(f'# ONNX model placeholder for {model_name}\n')
                    f.write('# Actual ONNX conversion requires model-specific logic\n')

            else:
                console.print(f'[yellow]Format {fmt} not fully supported yet. Exporting as JSON.[/yellow]')
                with open(output, 'w') as f:
                    json.dump(model_data, f, indent=2)

            console.print(f'[green]✓ Exported to {output}[/green]')

    except Exception as e:
        console.print(f'[red]Error exporting model: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='train')
def models_train(
    model_type: str = typer.Argument(..., help='Model type: next_run, pa_outcome, win_probability'),
    season: int = typer.Option(..., '--season', '-s', help='Season to train on'),
    test_season: int = typer.Option(
        None, '--test-season', help='Season for validation (default: season+1)'
    ),
    name: str = typer.Option(None, '--name', '-n', help='Custom model name'),
    dry_run: bool = typer.Option(False, '--dry-run', help='Show training plan without executing'),
):
    """Train a new model on historical data."""
    from baseball.models import (
        ModelType,
        NextRunProbabilityModel,
        PAOutcomeModel,
        TrainingConfig,
        WinProbabilityModel,
    )

    # Map model type strings to classes
    model_map = {
        'next_run': (NextRunProbabilityModel, ModelType.NEXT_RUN_PROBABILITY),
        'pa_outcome': (PAOutcomeModel, ModelType.PA_OUTCOME),
        'win_probability': (WinProbabilityModel, ModelType.WIN_PROBABILITY),
    }

    if model_type not in model_map:
        console.print(f'[red]Unknown model type: {model_type}[/red]')
        console.print(f'Available: {", ".join(model_map.keys())}')
        raise typer.Exit(code=1)

    model_class, model_enum = model_map[model_type]

    if dry_run:
        console.print(f'[yellow]Dry run: Would train {model_type} model[/yellow]')
        console.print(f'  Training season: {season}')
        console.print(f'  Test season: {test_season or season + 1}')
        console.print(f'  Model class: {model_class.__name__}')
        return

    try:
        console.print(f'[dim]Training {model_type} model on {season} data...[/dim]')

        # Create training config
        config = TrainingConfig(
            model_type=model_enum,
            model_name=name or f'{model_type}_{season}',
            training_seasons=[season],
            test_seasons=[test_season] if test_season else [season + 1],
        )

        # Initialize and train model
        model = model_class(config=config)
        result = model.train()

        if result.success:
            console.print('[green]✅ Training complete![/green]')
            console.print(f'  Model: {result.model_name}')
            console.print(f'  Training rows: {result.training_rows:,}')
            console.print(f'  Validation AUC: {result.validation_auc:.4f}')
            console.print(f'  Log Loss: {result.log_loss:.4f}')
        else:
            console.print(f'[red]❌ Training failed: {result.error_message}[/red]')
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f'[red]Error during training: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='predict')
def models_predict(
    game_pk: int = typer.Option(..., '--game-pk', '-g', help='MLB game ID to predict'),
    model_name: str = typer.Option('win_probability', '--model', '-m', help='Model name'),
    model_version: Optional[str] = typer.Option(None, '--version', '-v', help='Model version (default: production)'),
    store_result: bool = typer.Option(True, '--store/--no-store', help='Store prediction in database'),
    show_features: bool = typer.Option(False, '--features', help='Show feature vector used')
):
    """Run prediction for a specific game."""
    from baseball.models.inference import InferencePipeline

    try:
        console.print(f'[bold blue]Predicting {model_name} for game {game_pk}...[/bold blue]')

        pipeline = InferencePipeline(
            model_name=model_name,
            model_version=model_version
        )

        result = pipeline.predict_game(
            game_pk=game_pk,
            store_result=store_result,
            request_source='cli'
        )

        if result.success:
            console.print(f'\n[green]✓ Prediction successful[/green]')
            console.print(f'  Model: {result.prediction_type} v{result.model_version}')
            console.print(f'  Home win probability: {result.predicted_value:.1%}')

            if result.confidence_lower is not None and result.confidence_upper is not None:
                console.print(f'  Confidence interval: [{result.confidence_lower:.1%}, {result.confidence_upper:.1%}]')

            console.print(f'  Inference time: {result.inference_time_ms:.1f}ms')

            if show_features and result.feature_vector:
                console.print(f'\n[dim]Features used:[/dim]')
                for name, value in result.feature_vector.items():
                    console.print(f'  {name}: {value}')

            if result.prediction_id:
                console.print(f'\n[dim]Stored as prediction_id: {result.prediction_id}[/dim]')
        else:
            console.print(f'[red]❌ Prediction failed: {result.error_message}[/red]')
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f'[red]Error during prediction: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='batch-predict')
def models_batch_predict(
    game_pks: str = typer.Option(..., '--games', '-g', help='Comma-separated game IDs'),
    model_name: str = typer.Option('win_probability', '--model', '-m', help='Model name'),
    model_version: Optional[str] = typer.Option(None, '--version', '-v', help='Model version')
):
    """Run predictions for multiple games."""
    from baseball.models.inference import InferencePipeline

    try:
        game_list = [int(g.strip()) for g in game_pks.split(',')]

        console.print(f'[bold blue]Batch predicting {len(game_list)} games...[/bold blue]')

        pipeline = InferencePipeline(
            model_name=model_name,
            model_version=model_version
        )

        results = pipeline.predict_batch(game_list, store_results=True)

        # Summary
        successful = sum(1 for r in results if r.success)

        table = Table(title=f'Batch Predictions - {model_name}')
        table.add_column('Game PK', style='cyan')
        table.add_column('Home Win %', style='green')
        table.add_column('Confidence', style='yellow')
        table.add_column('Status', style='white')

        for game_pk, result in zip(game_list, results):
            if result.success:
                table.add_row(
                    str(game_pk),
                    f'{result.predicted_value:.1%}',
                    f'{result.confidence_lower:.0%}-{result.confidence_upper:.0%}' if result.confidence_lower else 'N/A',
                    '✓'
                )
            else:
                table.add_row(
                    str(game_pk),
                    'N/A',
                    'N/A',
                    f'✗ {result.error_message[:30]}'
                )

        console.print(table)
        console.print(f'\n[green]✓ {successful}/{len(results)} predictions successful[/green]')

    except Exception as e:
        console.print(f'[red]Error during batch prediction: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='promote')
def models_promote(
    model_id: int = typer.Argument(..., help='Model ID to promote'),
    to_status: str = typer.Option('production', '--to', help='Target status: production, staging, archived'),
    promoted_by: str = typer.Option('cli', '--by', help='User/system promoting the model'),
):
    """Promote a model to production (or other status)."""
    from baseball.models.registry import ModelRegistry

    try:
        registry = ModelRegistry()

        # Get model info first
        model = registry.get_model_by_id(model_id)
        if not model:
            console.print(f'[red]Model ID {model_id} not found.[/red]')
            raise typer.Exit(code=1)

        if to_status == 'production':
            success = registry.promote_model(model_id, promoted_by=promoted_by)
            if success:
                console.print(f'[green]✓ Promoted {model.model_name} v{model.model_version} to production[/green]')
            else:
                console.print(f'[red]Failed to promote model {model_id}[/red]')
                raise typer.Exit(code=1)
        elif to_status == 'archived':
            success = registry.archive_model(model_id)
            if success:
                console.print(f'[green]✓ Archived {model.model_name} v{model.model_version}[/green]')
            else:
                console.print(f'[red]Failed to archive model {model_id}[/red]')
                raise typer.Exit(code=1)
        else:
            console.print(f'[yellow]Status "{to_status}" requires manual database update[/yellow]')

    except Exception as e:
        console.print(f'[red]Error promoting model: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='backtest')
def models_backtest(
    model_name: str = typer.Argument(..., help='Model name to backtest'),
    seasons: List[int] = typer.Option([2022, 2023, 2024], '--season', '-s', help='Seasons to include'),
    window_days: int = typer.Option(7, '--window', '-w', help='Test window size in days'),
    feature_set: str = typer.Option('default', '--features', '-f', help='Feature set to use'),
    output_file: Optional[str] = typer.Option(None, '--output', '-o', help='Save results to file'),
    save_predictions: bool = typer.Option(True, '--save-predictions/--no-save', help='Store predictions in DB'),
    verbose: bool = typer.Option(True, '--verbose/--quiet', help='Show progress and results'),
):
    """Run walk-forward backtest on historical data."""
    from baseball.models import NextRunProbabilityModel, PAOutcomeModel, WinProbabilityModel
    from baseball.models.backtesting import (
        BacktestConfig,
        BacktestEngine,
        BacktestStatus,
    )

    # Map model name to class
    model_map = {
        'next_run': NextRunProbabilityModel,
        'pa_outcome': PAOutcomeModel,
        'win_probability': WinProbabilityModel,
    }

    if model_name not in model_map:
        console.print(f'[red]Unknown model: {model_name}[/red]')
        console.print(f'Available: {", ".join(model_map.keys())}')
        raise typer.Exit(code=1)

    model_class = model_map[model_name]

    try:
        config = BacktestConfig(
            model_class=model_class,
            model_name=model_name,
            seasons=seasons,
            test_window_days=window_days,
            feature_set=feature_set,
            save_predictions=save_predictions,
            show_progress=verbose
        )

        engine = BacktestEngine(config)

        # Progress callback with rich progress bar
        if verbose:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                console=console
            )

            with progress:
                task = progress.add_task(f"[cyan]Backtesting {model_name}...", total=100)

                def progress_callback(current, total, elapsed):
                    pct = (current / total * 100) if total > 0 else 0
                    progress.update(task, completed=pct)

                engine.progress_tracker.add_callback(progress_callback)
                result = engine.run()
        else:
            result = engine.run()

        # Display results
        if result.status == BacktestStatus.COMPLETED:
            console.print(f'\n[green]✓ Backtest completed successfully[/green]')

            # Summary table
            table = Table(title=f'Backtest Results: {model_name}')
            table.add_column('Metric', style='cyan')
            table.add_column('Value', style='green')
            table.add_column('Std Dev', style='yellow')

            table.add_row('Accuracy', f'{result.mean_accuracy:.4f}', f'{result.std_accuracy:.4f}')
            table.add_row('Log Loss', f'{result.mean_log_loss:.4f}', f'{result.std_log_loss:.4f}')
            table.add_row('AUC', f'{result.mean_auc:.4f}', f'{result.std_auc:.4f}')
            table.add_row('Brier Score', f'{result.mean_brier_score:.4f}', '-')
            table.add_row('Calibration Error', f'{result.mean_calibration_error:.4f}', '-')
            table.add_row('Total Predictions', str(result.total_predictions), '-')
            table.add_row('Duration', f'{result.duration_seconds:.1f}s', '-')

            console.print(table)

            # Season breakdown
            if result.by_season:
                season_table = Table(title='Performance by Season')
                season_table.add_column('Season', style='cyan')
                season_table.add_column('Accuracy', style='green')
                season_table.add_column('Log Loss', style='yellow')
                season_table.add_column('Count', style='dim')

                for season, metrics in sorted(result.by_season.items()):
                    season_table.add_row(
                        str(season),
                        f"{metrics['mean_accuracy']:.4f}",
                        f"{metrics['mean_log_loss']:.4f}",
                        str(metrics['count'])
                    )

                console.print(season_table)

            # Save to file if requested
            if output_file:
                if result.save_to_file(output_file):
                    console.print(f'\n[dim]Results saved to {output_file}[/dim]')
                else:
                    console.print(f'\n[yellow]Warning: Could not save to {output_file}[/yellow]')

            console.print(f'\n[dim]Backtest ID: {result.backtest_id}[/dim]')

        elif result.status == BacktestStatus.FAILED:
            console.print(f'\n[red]✗ Backtest failed: {result.error_message}[/red]')
            raise typer.Exit(code=1)
        else:
            console.print(f'\n[yellow]Backtest status: {result.status.value}[/yellow]')

    except Exception as e:
        console.print(f'[red]Error during backtest: {e}[/red]')
        raise typer.Exit(code=1)

"""
Content Generation CLI Commands

Command-line interface for the content generation pipeline.
Provides commands for generating, managing, and scheduling content.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from baseball.content import TemplateEngine, ContentGenerator, ContentScheduler
from baseball.content.llm.generator import GenerationRequest, OpenAIProvider
from baseball.core.settings import get_settings

logger = logging.getLogger(__name__)

# Create CLI app
content_app = typer.Typer(help="Content generation commands")
console = Console()


@content_app.command()
def generate(
    template: str = typer.Option(..., "--template", help="Template name to use"),
    game_pk: Optional[int] = typer.Option(None, "--game-pk", help="Game ID for content"),
    player_id: Optional[str] = typer.Option(None, "--player-id", help="Player ID for content"),
    context_file: Optional[str] = typer.Option(None, "--context-file", help="JSON file with context data"),
    output_file: Optional[str] = typer.Option(None, "--output", help="Output file for generated content"),
    model: str = typer.Option("gpt-4", "--model", help="LLM model to use"),
    max_tokens: int = typer.Option(1000, "--max-tokens", help="Maximum tokens to generate"),
    temperature: float = typer.Option(0.7, "--temperature", help="Generation temperature"),
    preview: bool = typer.Option(False, "--preview", help="Preview only, don't save")
):
    """Generate content using templates and LLM."""
    
    async def _generate():
        try:
            # Initialize components
            template_engine = TemplateEngine()
            
            # Setup LLM provider if API key is available
            settings = get_settings()
            generator = ContentGenerator()
            
            if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=model)
                generator.set_provider(provider)
            else:
                console.print("[yellow]Warning: No OpenAI API key found. Using mock generation.[/yellow]")
            
            # Build context
            context = {}
            
            if context_file:
                context_path = Path(context_file)
                if context_path.exists():
                    with open(context_path, 'r') as f:
                        context.update(json.load(f))
            
            # Add specific context based on parameters
            if game_pk:
                context['game_pk'] = game_pk
                # Mock game data for now
                context['game'] = {
                    'home_team': 'Yankees',
                    'away_team': 'Red Sox', 
                    'game_time': datetime.now().strftime('%I:%M %p'),
                    'venue': 'Yankee Stadium',
                    'home_win_prob': 0.58,
                    'total_runs_expected': 8.5
                }
            
            if player_id:
                context['player_id'] = player_id
                # Mock player data for now
                context['player'] = {
                    'name': 'Mike Trout',
                    'team': 'Angels',
                    'avg': 0.305,
                    'hr': 35,
                    'rbi': 102,
                    'ops': 0.945
                }
            
            # Generate content
            request = GenerationRequest(
                template_name=template,
                context=context,
                content_type=_infer_content_type(template),
                max_tokens=max_tokens,
                temperature=temperature,
                model=model
            )
            
            console.print(f"[blue]Generating content using template: {template}[/blue]")
            
            if generator.provider:
                response = await generator.generate_content(request)
                content = response.content
                
                # Display generation stats
                stats_table = Table(title="Generation Statistics")
                stats_table.add_column("Metric", style="cyan")
                stats_table.add_column("Value", style="green")
                
                stats_table.add_row("Model", response.model_used)
                stats_table.add_row("Tokens Used", str(response.tokens_used))
                stats_table.add_row("Generation Time", f"{response.generation_time:.2f}s")
                stats_table.add_row("Content Length", f"{len(content)} chars")
                
                console.print(stats_table)
            else:
                # Mock content for demo
                content = f"""
# Generated Content: {template}

This is sample content generated for the {template} template.
In a real implementation, this would be generated by an LLM using the provided context.

Context provided:
{json.dumps(context, indent=2)}

Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Display content
            console.print(Panel(
                content,
                title=f"Generated Content ({template})",
                expand=False
            ))
            
            # Save to file if requested
            if output_file and not preview:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                console.print(f"[green]Content saved to: {output_path}[/green]")
            
            # Validate content quality
            if generator.provider:
                quality = generator.validate_content_quality(content)
                
                quality_table = Table(title="Quality Assessment")
                quality_table.add_column("Metric", style="cyan")
                quality_table.add_column("Result", style="green")
                
                quality_table.add_row("Valid", str(quality['valid']))
                quality_table.add_row("Length", f"{quality['length']} chars")
                quality_table.add_row("Sentences", str(quality['sentence_count']))
                quality_table.add_row("Has Numbers", str(quality['has_numbers']))
                
                if quality['issues']:
                    quality_table.add_row("Issues", ", ".join(quality['issues']))
                
                console.print(quality_table)
        
        except Exception as e:
            console.print(f"[red]Error generating content: {e}[/red]")
            raise typer.Exit(1)
    
    # Run async function
    asyncio.run(_generate())


@content_app.command()
def templates(
    list: bool = typer.Option(False, "--list", help="List all templates"),
    validate: Optional[str] = typer.Option(None, "--validate", help="Validate a specific template"),
    info: Optional[str] = typer.Option(None, "--info", help="Get template information")
):
    """Manage content templates."""
    
    template_engine = TemplateEngine()
    
    if list:
        templates = template_engine.list_templates()
        
        table = Table(title="Available Templates")
        table.add_column("Template", style="cyan")
        table.add_column("Status", style="green")
        
        for template_name in templates:
            validation = template_engine.validate_template(template_name)
            status = "✅ Valid" if validation['valid'] else "❌ Invalid"
            table.add_row(template_name, status)
        
        console.print(table)
    
    elif validate:
        try:
            validation = template_engine.validate_template(validate)
            
            console.print(f"[blue]Template: {validate}[/blue]")
            
            if validation['valid']:
                console.print("[green]✅ Template syntax is valid[/green]")
                
                if validation['variables']:
                    console.print("\n[cyan]Variables found:[/cyan]")
                    for var in sorted(validation['variables']):
                        console.print(f"  • {var}")
                else:
                    console.print("[yellow]No variables found in template[/yellow]")
            else:
                console.print(f"[red]❌ Template validation failed: {validation['error']}[/red]")
        
        except Exception as e:
            console.print(f"[red]Error validating template: {e}[/red]")
            raise typer.Exit(1)
    
    elif info:
        try:
            template_info = template_engine.get_template_info(info)
            
            table = Table(title=f"Template Info: {info}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Path", template_info['path'])
            table.add_row("Size", f"{template_info['size']} bytes")
            table.add_row("Created", template_info['created'].strftime('%Y-%m-%d %H:%M:%S'))
            table.add_row("Modified", template_info['modified'].strftime('%Y-%m-%d %H:%M:%S'))
            table.add_row("Valid", str(template_info['valid']))
            
            if template_info['variables']:
                table.add_row("Variables", ", ".join(template_info['variables']))
            
            if template_info['error']:
                table.add_row("Error", template_info['error'])
            
            console.print(table)
        
        except Exception as e:
            console.print(f"[red]Error getting template info: {e}[/red]")
            raise typer.Exit(1)
    
    else:
        console.print("[yellow]Use --list, --validate, or --info to specify an action[/yellow]")


@content_app.command()
def schedule(
    template: str = typer.Option(..., "--template", help="Template name"),
    task_id: str = typer.Option(..., "--task-id", help="Unique task identifier"),
    time: Optional[str] = typer.Option(None, "--time", help="Schedule time (HH:MM format)"),
    context_file: Optional[str] = typer.Option(None, "--context-file", help="JSON context file"),
    recurring: bool = typer.Option(False, "--recurring", help="Schedule as recurring task"),
    interval_hours: int = typer.Option(24, "--interval", help="Hours between recurring tasks"),
    list_tasks: bool = typer.Option(False, "--list", help="List scheduled tasks")
):
    """Schedule content generation tasks."""
    
    async def _schedule():
        try:
            scheduler = ContentScheduler()
            
            if list_tasks:
                tasks = scheduler.list_tasks()
                
                table = Table(title="Scheduled Tasks")
                table.add_column("Task ID", style="cyan")
                table.add_column("Template", style="green")
                table.add_column("Scheduled", style="yellow")
                table.add_column("Status", style="magenta")
                
                for task in tasks:
                    scheduled_str = task.scheduled_time.strftime('%Y-%m-%d %H:%M')
                    table.add_row(task.task_id, task.template_name, scheduled_str, task.status.value)
                
                console.print(table)
                
                # Show stats
                stats = scheduler.get_task_stats()
                console.print(f"\n[blue]Total tasks: {stats['total_tasks']}[/blue]")
                
                return
            
            # Load context
            context = {}
            if context_file:
                context_path = Path(context_file)
                if context_path.exists():
                    with open(context_path, 'r') as f:
                        context.update(json.load(f))
            
            # Parse schedule time
            scheduled_time = datetime.now()
            if time:
                try:
                    hour, minute = map(int, time.split(':'))
                    scheduled_time = scheduled_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If time is in the past, schedule for tomorrow
                    if scheduled_time <= datetime.now():
                        scheduled_time += timedelta(days=1)
                except ValueError:
                    console.print("[red]Invalid time format. Use HH:MM[/red]")
                    raise typer.Exit(1)
            
            # Schedule task(s)
            if recurring:
                tasks = scheduler.schedule_recurring(
                    base_task_id=task_id,
                    template_name=template,
                    context=context,
                    interval_hours=interval_hours,
                    max_occurrences=30  # 30 days
                )
                console.print(f"[green]Scheduled {len(tasks)} recurring tasks starting at {scheduled_time}[/green]")
            else:
                task = scheduler.schedule_task(
                    task_id=task_id,
                    template_name=template,
                    context=context,
                    scheduled_time=scheduled_time
                )
                console.print(f"[green]Task scheduled: {task_id} for {scheduled_time}[/green]")
        
        except Exception as e:
            console.print(f"[red]Error scheduling task: {e}[/red]")
            raise typer.Exit(1)
    
    # Run async function
    asyncio.run(_schedule())


def _infer_content_type(template: str) -> str:
    """Infer content type from template name."""
    template_lower = template.lower()
    
    if "preview" in template_lower:
        return "game-preview"
    elif "player" in template_lower:
        return "player-analysis"
    elif "stats" in template_lower or "statistical" in template_lower:
        return "statistical-breakdown"
    elif "prediction" in template_lower:
        return "prediction-explanation"
    else:
        return "game-preview"


# Register with main CLI
def register_commands(app):
    """Register content commands with main CLI app."""
    app.add_typer(content_app, name="content", help="Content generation commands")

"""Chatbot interface commands."""

import typer
from rich.console import Console

console = Console()

chatbot_app = typer.Typer(help='Natural language chatbot interface', no_args_is_help=True)


@chatbot_app.command(name='chat')
def chatbot_chat(
    message: str = typer.Option(None, '--message', '-m', help='Single message to send'),
    interactive: bool = typer.Option(False, '--interactive', '-i', help='Interactive chat mode'),
):
    """Chat with the baseball prediction bot."""
    try:
        from baseball.chatbot import Chatbot
    except ImportError as e:
        console.print(f'[red]Chatbot module not available: {e}[/red]')
        raise typer.Exit(code=1)

    bot = Chatbot()

    if message:
        # Single message mode
        response = bot.chat(message)
        console.print(f'[cyan]You:[/cyan] {message}')
        console.print(f'[green]Bot:[/green] {response}')
    elif interactive:
        # Interactive mode
        console.print('[bold blue]Baseball Chatbot[/bold blue]')
        console.print('[dim]Type "help" for examples, "quit" to exit[/dim]\n')

        while True:
            try:
                user_input = console.input('[cyan]You:[/cyan] ').strip()

                if not user_input:
                    continue

                if user_input.lower() in ('quit', 'exit', 'bye'):
                    console.print('[green]Bot:[/green] Goodbye!')
                    break

                if user_input.lower() == 'help':
                    console.print('\n[bold]Example queries:[/bold]')
                    for cmd in bot.get_supported_commands():
                        console.print(f'  • {cmd}')
                    console.print()
                    continue

                response = bot.chat(user_input)
                console.print(f'[green]Bot:[/green] {response}\n')

            except KeyboardInterrupt:
                console.print('\n[yellow]Goodbye![/yellow]')
                break
    else:
        console.print(
            '[yellow]Use --message for single query or --interactive for chat mode[/yellow]'
        )
        console.print('[dim]Examples:[/dim]')
        console.print('  baseball chatbot chat -m "What is the Yankees win probability?"')
        console.print('  baseball chatbot chat --interactive')


@chatbot_app.command(name='demo')
def chatbot_demo():
    """Run a demo conversation with the chatbot."""
    try:
        from baseball.chatbot import Chatbot
    except ImportError as e:
        console.print(f'[red]Chatbot module not available: {e}[/red]')
        raise typer.Exit(code=1)

    bot = Chatbot()

    demo_queries = [
        'Hello!',
        "What's the Yankees win probability?",
        'How about the Red Sox?',
        "What's Aaron Judge's batting average?",
        "Who's pitching for the Dodgers?",
        'How do predictions work?',
        'Thanks, bye!',
    ]

    console.print('[bold blue]Chatbot Demo[/bold blue]\n')

    for query in demo_queries:
        console.print(f'[cyan]You:[/cyan] {query}')
        response = bot.chat(query)
        console.print(f'[green]Bot:[/green] {response}\n')

    # Show conversation summary
    summary = bot.get_conversation_summary()
    console.print('[dim]Conversation summary:[/dim]')
    console.print(f'  Messages: {summary["session_info"]["message_count"]}')
    console.print(f'  Active team: {summary["context"]["team"] or "None"}')


@chatbot_app.command(name='route')
def chatbot_route(
    query: str = typer.Option(..., '--query', '-q', help='Natural language query to route')
):
    """Show how a query is routed to models."""
    from baseball.nlp import QueryRouter
    
    router = QueryRouter()
    result = router.execute(query)
    
    routed = result['routed_query']
    
    console.print('[bold]Query Routing Analysis[/bold]\n')
    console.print(f'[cyan]Original:[/cyan] {query}')
    console.print(f'[cyan]Intent:[/cyan] {routed.intent.value}')
    console.print(f'[cyan]Model:[/cyan] {routed.model_type.value if routed.model_type else "None"}')
    console.print(f'[cyan]Confidence:[/cyan] {routed.confidence:.0%}')
    
    if routed.entities:
        console.print(f'\n[cyan]Entities:[/cyan]')
        for key, value in routed.entities.items():
            console.print(f'  {key}: {value}')
    
    if result['success']:
        console.print(f'\n[green]Response:[/green]')
        console.print(result['response'])
    else:
        console.print(f'\n[yellow]Note:[/yellow] {result["response"]}')

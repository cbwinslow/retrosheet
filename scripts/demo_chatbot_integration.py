"""Demo script for chatbot + model serving integration.

Shows how the chatbot can connect to the model server
for live predictions and natural language responses.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.chatbot import Chatbot
from baseball.serving import ModelServer


def demo_with_mock_predictions():
    """Demo chatbot with mock prediction data."""
    print("=" * 60)
    print("Baseball Chatbot Demo (Mock Predictions)")
    print("=" * 60)
    print()
    
    # Create chatbot
    bot = Chatbot()
    
    # Demo conversation
    queries = [
        "Hello!",
        "What's the Yankees win probability?",
        "How about the Red Sox?",
        "What's Aaron Judge's batting average?",
        "How about his home runs?",
        "Who's pitching for the Dodgers?",
        "How do predictions work?",
        "Compare Judge and Ohtani",
        "Where are the Cubs in the standings?",
        "Thanks, bye!",
    ]
    
    for query in queries:
        print(f"You: {query}")
        response = bot.chat(query)
        print(f"Bot: {response}")
        print()
    
    # Show conversation summary
    summary = bot.get_conversation_summary()
    print("-" * 60)
    print("Conversation Summary:")
    print(f"  Messages: {summary['session_info']['message_count']}")
    print(f"  Active team: {summary['context']['team'] or 'None'}")
    print(f"  Active player: {summary['context']['player'] or 'None'}")
    print()


def demo_with_model_server():
    """Demo chatbot connected to model server."""
    print("=" * 60)
    print("Baseball Chatbot Demo (With Model Server)")
    print("=" * 60)
    print()
    
    # Create model server
    server = ModelServer(model_dir='models')
    
    # Try to load models (may fail if no models trained yet)
    models_loaded = []
    for model_name in ['next_run', 'pa_outcome']:
        if server.load_model(model_name, 'latest'):
            models_loaded.append(model_name)
    
    if models_loaded:
        print(f"Loaded models: {', '.join(models_loaded)}")
    else:
        print("No trained models found. Using placeholder predictions.")
    
    # Create chatbot with model server
    bot = Chatbot(model_server=server)
    
    # Demo with prediction queries
    prediction_queries = [
        "What's the win probability?",
        "Will the Yankees win?",
        "Run probability in this situation?",
    ]
    
    for query in prediction_queries:
        print(f"You: {query}")
        response = bot.chat(query)
        print(f"Bot: {response}")
        print()
    
    # Show server stats
    print("-" * 60)
    print("Server Stats:")
    stats = server.get_stats()
    print(f"  Models loaded: {stats['models_loaded']}")
    print(f"  Predictions served: {stats['predictions_served']}")
    print()


def interactive_demo():
    """Interactive demo with user input."""
    print("=" * 60)
    print("Baseball Chatbot - Interactive Demo")
    print("=" * 60)
    print("Type 'help' for examples, 'quit' to exit")
    print()
    
    bot = Chatbot()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ('quit', 'exit', 'bye'):
                print("Bot: Goodbye!")
                break
            
            if user_input.lower() == 'help':
                print("\nExample queries:")
                for cmd in bot.get_supported_commands():
                    print(f"  • {cmd}")
                print()
                continue
            
            if user_input.lower() == 'summary':
                summary = bot.get_conversation_summary()
                print("\nConversation Summary:")
                print(f"  Messages: {summary['session_info']['message_count']}")
                print(f"  Active team: {summary['context']['team'] or 'None'}")
                print(f"  Active player: {summary['context']['player'] or 'None'}")
                print()
                continue
            
            response = bot.chat(user_input)
            print(f"Bot: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Chatbot Integration Demo')
    parser.add_argument(
        '--mode', '-m',
        choices=['mock', 'server', 'interactive'],
        default='mock',
        help='Demo mode'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'mock':
        demo_with_mock_predictions()
    elif args.mode == 'server':
        demo_with_model_server()
    elif args.mode == 'interactive':
        interactive_demo()


if __name__ == '__main__':
    main()

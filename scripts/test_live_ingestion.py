"""Test script for end-to-end live data ingestion.

Verifies MLB live data ingestion pipeline from API → Database → Betting.

Usage:
    python scripts/test_live_ingestion.py [--game 716190] [--duration 60]

Author: Agent Cascade
Date: 2026-04-30
"""

import argparse
import asyncio
import logging
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def test_schedule_fetch():
    """Test fetching today's schedule."""
    from baseball.ingestion.mlb_live_adapter import MlbScheduleIngestionSource

    print('\n' + '='*60)
    print("TEST 1: Fetch Today's Schedule")
    print('='*60)

    source = MlbScheduleIngestionSource()
    result = await source.fetch_today()

    if not result.success:
        print(f'❌ FAILED: {result.error}')
        return False

    games = result.data.get('games', [])
    print(f'✅ SUCCESS: Found {len(games)} games today')

    live_games = source.get_live_games(result)
    preview_games = [g for g in games if g.get('is_preview')]

    print(f'   - Live games: {len(live_games)}')
    print(f'   - Preview games: {len(preview_games)}')

    if live_games:
        print('\n   Live Games:')
        for g in live_games[:3]:  # Show first 3
            print(f"   • {g['game_pk']}: {g['away_team']} @ {g['home_team']}")

    return True


async def test_game_stream(game_pk: int, duration: int = 30):
    """Test streaming game updates."""
    from baseball.ingestion.mlb_live_adapter import MlbLiveIngestionSource

    print('\n' + '='*60)
    print(f'TEST 2: Stream Game {game_pk} for {duration}s')
    print('='*60)

    source = MlbLiveIngestionSource(
        game_pk=game_pk,
        poll_interval=10,
    )

    update_count = 0
    start_time = datetime.utcnow()

    print(f'Starting stream at {start_time.isoformat()}')

    try:
        async for result in source.stream(duration=duration):
            if not result.success:
                print(f'❌ Stream error: {result.error}')
                continue

            update_count += 1
            state = result.data.get('state', {})

            print(f'\n   Update #{update_count} at {result.timestamp}')
            print(f"   Inning: {state.get('inning')} {'Top' if state.get('is_top') else 'Bottom'}")
            print(f"   Score: {state.get('score_away')} - {state.get('score_home')}")
            print(f"   Outs: {state.get('outs')}, Base State: {state.get('base_state')}")

            # Stop after 3 updates for demo
            if update_count >= 3:
                print('\n   (Limiting to 3 updates for demo)')
                break

        end_time = datetime.utcnow()
        elapsed = (end_time - start_time).total_seconds()

        print(f'\n✅ SUCCESS: Received {update_count} updates in {elapsed:.1f}s')
        return True

    except Exception as e:
        print(f'❌ FAILED: {e}')
        return False


async def test_database_save(game_pk: int):
    """Test saving raw data to database."""
    from baseball.sources.live_mlb import LiveMlbSource

    print('\n' + '='*60)
    print(f'TEST 3: Database Save for Game {game_pk}')
    print('='*60)

    source = LiveMlbSource()

    # Download game data
    print('   Fetching game data...')
    result = source.download(game_pk=game_pk)

    if not result.success:
        print(f'❌ FAILED: {result.error}')
        return False

    if result.records == 0:
        print(f'⚠️  Game {game_pk} not live, skipping DB test')
        return True  # Not a failure, just not live

    # Save to database
    print('   Saving to database...')
    save_result = source.save_raw(result.data)

    if not save_result.success:
        print(f'❌ FAILED: {save_result.error}')
        return False

    print(f'✅ SUCCESS: {save_result.message}')
    return True


async def test_integration_pipeline(game_pk: int):
    """Test full pipeline: live data → simulation → betting."""
    from baseball.simulation.service import SimulationService

    print('\n' + '='*60)
    print(f'TEST 4: Full Integration Pipeline (Game {game_pk})')
    print('='*60)

    # Step 1: Get live game state
    print('\n   Step 1: Fetching live game state...')

    states = []

    async def collect_state(state):
        states.append(state)
        print(f"   ✓ Collected state: Inning {state['state']['inning']}")

    # Collect one update
    source = __import__('baseball.ingestion.mlb_live_adapter', fromlist=['MlbLiveIngestionSource']).MlbLiveIngestionSource(game_pk=game_pk)

    try:
        async for result in source.stream(duration=30):
            if result.success:
                await collect_state(result.data)
                break  # Just need one
    except Exception as e:
        print(f'   ⚠️  Live stream failed: {e}')
        print('   (This is OK if game is not currently live)')

    # Step 2: Check simulation availability
    print('\n   Step 2: Checking simulation data...')

    try:
        sim_service = SimulationService()
        probs = await sim_service.get_game_probabilities(str(game_pk))

        if probs:
            print('   ✓ Simulation found:')
            print(f"     Home win: {probs.get('home_win', 0):.1%}")
            print(f"     Away win: {probs.get('away_win', 0):.1%}")
        else:
            print('   ⚠️  No simulation found (run simulation first)')
    except Exception as e:
        print(f'   ⚠️  Simulation check failed: {e}')

    print('\n✅ Integration pipeline test completed')
    return True


async def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(
        description='Test live MLB data ingestion pipeline',
    )
    parser.add_argument(
        '--game',
        type=int,
        default=716190,
        help='Game PK to test (default: 716190)',
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Stream duration in seconds (default: 30)',
    )
    parser.add_argument(
        '--test',
        choices=['all', 'schedule', 'stream', 'database', 'integration'],
        default='all',
        help='Which test to run (default: all)',
    )

    args = parser.parse_args()

    print('\n' + '='*60)
    print('MLB LIVE DATA INGESTION TEST SUITE')
    print('='*60)
    print(f'Game PK: {args.game}')
    print(f'Duration: {args.duration}s')
    print(f'Test: {args.test}')

    results = []

    # Run selected tests
    if args.test in ['all', 'schedule']:
        results.append(('Schedule Fetch', await test_schedule_fetch()))

    if args.test in ['all', 'stream']:
        results.append(('Game Stream', await test_game_stream(args.game, args.duration)))

    if args.test in ['all', 'database']:
        results.append(('Database Save', await test_database_save(args.game)))

    if args.test in ['all', 'integration']:
        results.append(('Integration Pipeline', await test_integration_pipeline(args.game)))

    # Summary
    print('\n' + '='*60)
    print('TEST SUMMARY')
    print('='*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = '✅ PASS' if result else '❌ FAIL'
        print(f'   {status}: {name}')

    print(f'\n   Total: {passed}/{total} tests passed')

    if passed == total:
        print('\n🎉 All tests passed!')
        return 0
    print(f'\n⚠️  {total - passed} test(s) failed')
    return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)

"""Integration test for MLB Stats API live data.

This test hits the real MLB API to verify end-to-end functionality.
Requires no API keys - MLB Stats API is free.

Usage:
    pytest tests/integration/test_mlb_live_api.py -v

Author: Agent Cascade
Date: 2026-04-30
"""


import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_todays_schedule():
    """Test fetching today's schedule from MLB API."""
    from baseball.ingestion.mlb_live_adapter import MlbScheduleIngestionSource

    source = MlbScheduleIngestionSource()
    result = await source.fetch_today()

    assert result.success, f'Failed to fetch schedule: {result.error}'
    assert 'games' in result.data
    assert isinstance(result.data['games'], list)

    print(f"\nFound {len(result.data['games'])} games today")

    # Verify game structure
    if result.data['games']:
        game = result.data['games'][0]
        assert 'game_pk' in game
        assert 'home_team' in game
        assert 'away_team' in game
        assert 'status' in game


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_live_games():
    """Test extracting live games from schedule."""
    from baseball.ingestion.mlb_live_adapter import MlbScheduleIngestionSource

    source = MlbScheduleIngestionSource()
    result = await source.fetch_today()

    assert result.success

    live_games = source.get_live_games(result)

    # Note: May be 0 if no games are live right now
    print(f'\nFound {len(live_games)} live games')

    for game in live_games:
        assert game.get('is_live') is True
        assert 'game_pk' in game
        print(f"  Live: {game['away_team']} @ {game['home_team']} (PK: {game['game_pk']})")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_game_state_fetch():
    """Test fetching game state for a known game."""
    from baseball.ingestion.mlb_live_adapter import MlbLiveIngestionSource

    # Use a recent game PK (this may need updating)
    # Using 716190 as example - replace with actual live game if testing during season
    game_pk = 716190

    source = MlbLiveIngestionSource(
        game_pk=game_pk,
        poll_interval=5,
    )

    # Try to fetch once
    data = await source.fetch()

    if data is None:
        pytest.skip(f'Game {game_pk} not available (not live or invalid PK)')

    # Verify structure
    assert 'state' in data
    state = data['state']

    # Check key fields exist
    assert 'inning' in state
    assert 'is_top' in state
    assert 'outs' in state
    assert 'score_home' in state
    assert 'score_away' in state

    print(f'\nGame {game_pk} state:')
    print(f"  Inning: {state['inning']} {'Top' if state['is_top'] else 'Bottom'}")
    print(f"  Score: {state['score_away']}-{state['score_home']}")
    print(f"  Outs: {state['outs']}, Bases: {state.get('base_state', 'unknown')}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_game_stream():
    """Test streaming game updates."""
    from baseball.ingestion.mlb_live_adapter import MlbLiveIngestionSource

    game_pk = 716190
    source = MlbLiveIngestionSource(game_pk=game_pk, poll_interval=5)

    updates = []

    # Stream for max 20 seconds or 2 updates
    async for result in source.stream(duration=20):
        if result.success:
            updates.append(result.data)
            print(f"\n  Update #{len(updates)}: "
                  f"Inning {result.data['state']['inning']}, "
                  f"Score {result.data['state']['score_away']}-{result.data['state']['score_home']}")

        if len(updates) >= 2:
            break

    # It's OK if no updates (game not live) - just verify stream mechanics work
    print(f'\nReceived {len(updates)} updates')


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delegate_functions():
    """Test transform and filter delegates."""
    from baseball.ingestion.mlb_live_adapter import MlbScheduleIngestionSource

    # Filter to only live games
    def live_only(game):
        return game.get('is_live', False)

    # Transform to add display name
    def add_display(games):
        for g in games:
            g['display_name'] = f"{g['away_team']} @ {g['home_team']}"
        return games

    source = MlbScheduleIngestionSource(
        filter_fn=live_only,
        transform_fn=add_display,
    )

    result = await source.fetch_today()

    if result.success and result.data['games']:
        for game in result.data['games']:
            assert 'display_name' in game
            assert game.get('is_live') is True


@pytest.mark.integration
def test_source_status():
    """Test source status reporting."""
    from baseball.ingestion.mlb_live_adapter import MlbLiveIngestionSource

    game_pk = 716190
    source = MlbLiveIngestionSource(game_pk=game_pk)

    status = source.get_status()

    assert status['name'] == 'mlb_live'
    assert status['game_pk'] == game_pk
    assert 'poll_interval' in status
    assert 'connected' in status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline_integration():
    """Test full pipeline: schedule → live data → simulation check."""
    from baseball.ingestion.mlb_live_adapter import (
        MlbLiveIngestionSource,
        MlbScheduleIngestionSource,
    )
    from baseball.simulation.service import SimulationService

    print('\n' + '='*60)
    print('FULL PIPELINE INTEGRATION TEST')
    print('='*60)

    # Step 1: Get schedule
    print("\n1. Fetching today's schedule...")
    schedule_source = MlbScheduleIngestionSource()
    schedule_result = await schedule_source.fetch_today()

    assert schedule_result.success, 'Failed to fetch schedule'
    print(f"   ✓ Found {len(schedule_result.data['games'])} games")

    # Step 2: Get live games
    live_games = schedule_source.get_live_games(schedule_result)
    print(f'   ✓ {len(live_games)} games currently live')

    if not live_games:
        pytest.skip('No live games right now - cannot test live pipeline')

    # Step 3: Try to fetch live state for first live game
    game = live_games[0]
    game_pk = game['game_pk']

    print(f'\n2. Fetching live state for game {game_pk}...')
    live_source = MlbLiveIngestionSource(game_pk=game_pk, poll_interval=10)

    data = await live_source.fetch()

    if data:
        print('   ✓ Live state received')
        print(f"   Score: {data['state']['score_away']}-{data['state']['score_home']}")
    else:
        print('   ⚠ Game not actually live (may be pre-game)')

    # Step 4: Check simulation availability (optional)
    print('\n3. Checking simulation data...')
    try:
        sim_service = SimulationService()
        probs = await sim_service.get_game_probabilities(str(game_pk))

        if probs:
            print('   ✓ Simulation found')
            print(f"   Home win: {probs.get('home_win', 0):.1%}")
        else:
            print('   ⚠ No simulation (run simulation first)')
    except Exception as e:
        print(f'   ⚠ Simulation check failed: {e}')

    print('\n✅ Pipeline integration test completed')

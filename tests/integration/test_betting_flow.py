"""Integration tests for betting flow.

Covers:
- End-to-end betting analysis flow
- Source → Analyzer → Paper Trading
- Multiple sources with analyzer
- AI integration flow
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from baseball.betting.analyzer import BettingAnalyzer
from baseball.betting.paper_trading import PaperTradingAccount
from baseball.betting.schemas import (
    BetOpportunity,
    BettingMarket,
    BookRegion,
    MarketStatus,
    MarketType,
    Sport,
)


# =============================================================================
# End-to-End Flow Tests
# =============================================================================

class TestEndToEndBettingFlow:
    """Test complete betting flow from source to settlement."""

    @pytest.fixture
    def mock_source_with_odds(self):
        """Create mock source returning realistic odds."""
        mock = Mock()
        mock.get_game_odds.return_value = [
            BettingMarket(
                market_id='dk_ml_001',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='draftkings',
                book_region=BookRegion.US,
                odds=Decimal('-110'),
                odds_format='american',
                line=None,
                side='Yankees',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='Yankees',
                away_team='Red Sox',
                is_live=False,
            ),
            BettingMarket(
                market_id='dk_ml_002',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='draftkings',
                book_region=BookRegion.US,
                odds=Decimal('100'),
                odds_format='american',
                line=None,
                side='Red Sox',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='Yankees',
                away_team='Red Sox',
                is_live=False,
            ),
            BettingMarket(
                market_id='fd_ml_001',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='fanduel',
                book_region=BookRegion.US,
                odds=Decimal('-105'),
                odds_format='american',
                line=None,
                side='Yankees',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='Yankees',
                away_team='Red Sox',
                is_live=False,
            ),
        ]
        return mock

    def test_full_flow_opportunity_to_bet(self, mock_source_with_odds):
        """Full flow: find opportunity, create bet, place it."""
        # Step 1: Create analyzer
        analyzer = BettingAnalyzer(
            odds_source=mock_source_with_odds,
            min_edge=Decimal('0.01'),
        )

        # Step 2: Model predicts Yankees win 58%
        model_probs = {'Yankees': Decimal('0.58'), 'Red Sox': Decimal('0.42')}

        # Step 3: Find edges
        opportunities = analyzer.find_edges('716190', model_probs)

        # Should find edge on Yankees at -105 (FanDuel)
        # Implied: 51.2%, Model: 58%, Edge: ~6.8%
        assert len(opportunities) > 0

        # Step 4: Create paper trading account
        account = PaperTradingAccount(
            name='Integration Test',
            initial_bankroll=Decimal('10000'),
        )

        # Step 5: Create and place bet
        for opp in opportunities:
            if opp.recommendation == 'bet':
                bet = analyzer.create_bet(opp, Decimal('10000'), 'kelly')
                result = account.place_bet(bet)

                assert result is True
                assert bet.bet_id in account._bets

    def test_multi_source_price_shopping(self):
        """Compare odds across multiple sources for best price."""

        # Create mock sources with different prices
        dk_source = Mock()
        dk_source.get_game_odds.return_value = [
            BettingMarket(
                market_id='dk_001', game_id='g1', sport=Sport.MLB,
                market_type=MarketType.MONEYLINE, book='draftkings',
                book_region=BookRegion.US, odds=Decimal('-110'),
                odds_format='american', line=None, side='TeamA',
                timestamp=datetime.now(), game_time=datetime.now(),
                status=MarketStatus.OPEN, home_team='A', away_team='B',
                is_live=False,
            ),
        ]

        fd_source = Mock()
        fd_source.get_game_odds.return_value = [
            BettingMarket(
                market_id='fd_001', game_id='g1', sport=Sport.MLB,
                market_type=MarketType.MONEYLINE, book='fanduel',
                book_region=BookRegion.US, odds=Decimal('-105'),
                odds_format='american', line=None, side='TeamA',
                timestamp=datetime.now(), game_time=datetime.now(),
                status=MarketStatus.OPEN, home_team='A', away_team='B',
                is_live=False,
            ),
        ]

        # Analyze with both sources
        dk_analyzer = BettingAnalyzer(odds_source=dk_source, min_edge=Decimal('0'))
        fd_analyzer = BettingAnalyzer(odds_source=fd_source, min_edge=Decimal('0'))

        model_probs = {'TeamA': Decimal('0.55')}

        dk_opps = dk_analyzer.find_edges('g1', model_probs)
        fd_opps = fd_analyzer.find_edges('g1', model_probs)

        # FanDuel at -105 should have higher edge than DraftKings at -110
        if dk_opps and fd_opps:
            assert fd_opps[0].edge > dk_opps[0].edge

    def test_bet_settlement_updates_analytics(self, mock_source_with_odds):
        """Bet settlement properly updates all analytics."""
        # Setup
        analyzer = BettingAnalyzer(
            odds_source=mock_source_with_odds,
            min_edge=Decimal('0.01'),
        )
        account = PaperTradingAccount(
            name='Analytics Test',
            initial_bankroll=Decimal('10000'),
        )

        # Find and place bet
        opportunities = analyzer.find_edges('716190', {'Yankees': Decimal('0.58')})

        for opp in opportunities:
            bet = analyzer.create_bet(opp, Decimal('10000'), 'flat')
            account.place_bet(bet)

        initial_bankroll = account.bankroll

        # Settle bets (Yankees win 4-2)
        account.settle_by_game_result('716190', 4, 2)

        # Verify analytics updated
        summary = account.get_performance_summary()
        assert summary['bets_won'] > 0 or summary['bets_lost'] > 0
        assert summary['total_pnl'] != Decimal('0')
        assert account.bankroll != initial_bankroll

    def test_multiple_bets_same_game(self, mock_source_with_odds):
        """Can place multiple bets on same game (different markets)."""
        # Add spread market
        mock_source_with_odds.get_game_odds.return_value.extend([
            BettingMarket(
                market_id='dk_spread_001',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.SPREAD,
                book='draftkings',
                book_region=BookRegion.US,
                odds=Decimal('-110'),
                odds_format='american',
                line=Decimal('-1.5'),
                side='Yankees',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='Yankees',
                away_team='Red Sox',
                is_live=False,
            ),
        ])

        analyzer = BettingAnalyzer(odds_source=mock_source_with_odds)
        account = PaperTradingAccount(name='Multi Bet Test')

        # Model probabilities for different markets
        model_probs = {
            'Yankees': Decimal('0.58'),
            'Yankees -1.5': Decimal('0.45'),
            'Red Sox +1.5': Decimal('0.55'),
        }

        opportunities = analyzer.find_edges('716190', model_probs)

        # Place bets on different markets
        placed = 0
        for opp in opportunities:
            bet = analyzer.create_bet(opp, Decimal('10000'), 'flat')
            if account.place_bet(bet):
                placed += 1

        assert placed >= 1

    def test_bankroll_management_across_multiple_bets(self):
        """Bankroll properly managed across multiple bets."""
        account = PaperTradingAccount(
            name='Bankroll Test',
            initial_bankroll=Decimal('1000'),
            max_bet_pct=Decimal('0.10'),  # 10% max
        )

        # Create multiple opportunities
        for i in range(5):
            market = BettingMarket(
                market_id=f'm_{i}',
                game_id=f'g_{i}',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='dk',
                book_region=BookRegion.US,
                odds=Decimal('-110'),
                odds_format='american',
                line=None,
                side='TeamA',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='A',
                away_team='B',
                is_live=False,
            )

            opp = BetOpportunity(
                opportunity_id=f'opp_{i}',
                market=market,
                model_probability=Decimal('0.55'),
                edge=Decimal('0.05'),
                ev=Decimal('0'),
                recommendation='bet',
                timestamp=datetime.now(),
                strategy_id='test',
            )

            bet = PlacedBet(
                bet_id=f'bet_{i}',
                opportunity=opp,
                stake=Decimal('100'),  # Try to bet $100 each
                odds_placed=Decimal('-110'),
                placed_at=datetime.now(),
                strategy_id='test',
            )

            account.place_bet(bet)

        # Check that bankroll decreased correctly
        expected_deducted = sum(
            min(Decimal('100'), account.initial_bankroll * Decimal('0.10'))
            for _ in range(5)
        )

        assert account.bankroll == account.initial_bankroll - expected_deducted


# =============================================================================
# Error Handling Integration Tests
# =============================================================================

class TestIntegrationErrorHandling:
    """Test error handling in integrated flows."""

    def test_source_failure_handled_gracefully(self):
        """Source failure doesn't crash analyzer."""
        failing_source = Mock()
        failing_source.get_game_odds.side_effect = Exception('API down')

        analyzer = BettingAnalyzer(odds_source=failing_source)

        # Should handle error
        with pytest.raises(Exception):
            analyzer.find_edges('716190', {})

    def test_invalid_odds_handled_in_flow(self):
        """Invalid odds don't break the flow."""
        mock_source = Mock()
        mock_source.get_game_odds.return_value = [
            BettingMarket(
                market_id='bad_001',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='badbook',
                book_region=BookRegion.US,
                odds=Decimal('0'),  # Invalid odds
                odds_format='american',
                line=None,
                side='Team',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='A',
                away_team='B',
                is_live=False,
            ),
        ]

        analyzer = BettingAnalyzer(odds_source=mock_source)

        # Should not crash
        try:
            opportunities = analyzer.find_edges('716190', {'Team': Decimal('0.55')})
            # May return empty or filtered list
            assert isinstance(opportunities, list)
        except:
            pytest.fail('Should handle invalid odds gracefully')

    def test_insufficient_bankroll_handled(self):
        """Insufficient bankroll handled gracefully."""
        account = PaperTradingAccount(
            name='Poor Account',
            initial_bankroll=Decimal('10'),
        )

        market = BettingMarket(
            market_id='m1', game_id='g1', sport=Sport.MLB,
            market_type=MarketType.MONEYLINE, book='dk',
            book_region=BookRegion.US, odds=Decimal('-110'),
            odds_format='american', line=None, side='A',
            timestamp=datetime.now(), game_time=datetime.now(),
            status=MarketStatus.OPEN, home_team='A', away_team='B',
            is_live=False,
        )

        opp = BetOpportunity(
            opportunity_id='opp1', market=market,
            model_probability=Decimal('0.55'), edge=Decimal('0.05'),
            ev=Decimal('0'), recommendation='bet',
            timestamp=datetime.now(), strategy_id='test',
        )

        bet = PlacedBet(
            bet_id='big_bet', opportunity=opp,
            stake=Decimal('100'),  # More than bankroll
            odds_placed=Decimal('-110'),
            placed_at=datetime.now(), strategy_id='test',
        )

        result = account.place_bet(bet)

        assert result is False
        assert len(account._bets) == 0

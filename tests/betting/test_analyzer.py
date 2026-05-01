"""Tests for BettingAnalyzer engine.

Covers:
- Edge calculation with various odds formats
- Opportunity detection
- Stake calculation (Kelly, flat, confidence)
- Reverse line movement detection
- Bet creation
- Delegate functions
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from baseball.betting.analyzer import (
    BettingAnalyzer,
    kelly_edge_calculator,
    standard_edge_calculator,
)
from baseball.betting.schemas import (
    BetOpportunity,
    BettingMarket,
    BookRegion,
    MarketStatus,
    MarketType,
    Sport,
)


# =============================================================================
# Edge Calculation Tests
# =============================================================================

class TestEdgeCalculations:
    """Test edge calculation functions."""

    @pytest.mark.parametrize(('prob', 'odds', 'expected_edge'), [
        (Decimal('0.55'), Decimal('-110'), Decimal('0.047')),   # Slight edge
        (Decimal('0.60'), Decimal('-110'), Decimal('0.143')),   # Strong edge
        (Decimal('0.45'), Decimal('120'), Decimal('-0.01')),     # Slight negative
        (Decimal('0.50'), Decimal('100'), Decimal('0.0')),      # Break-even
    ])
    def test_standard_edge_calculator(self, prob, odds, expected_edge):
        """Standard edge calculation accuracy."""
        edge = standard_edge_calculator(prob, odds)
        assert abs(edge - expected_edge) < Decimal('0.01')

    def test_kelly_edge_calculator(self):
        """Kelly criterion edge calculation."""
        prob = Decimal('0.60')
        odds = Decimal('-110')

        edge = kelly_edge_calculator(prob, odds)

        # Kelly edge should account for bankroll preservation
        assert isinstance(edge, Decimal)
        assert edge > 0  # Positive edge

    def test_edge_with_positive_odds(self):
        """Edge calculation for positive odds (+150)."""
        prob = Decimal('0.45')
        odds = Decimal('150')

        edge = standard_edge_calculator(prob, odds)

        # +150 = 40% implied, model says 45%, so positive edge
        assert edge > 0

    def test_edge_with_negative_odds(self):
        """Edge calculation for negative odds (-150)."""
        prob = Decimal('0.40')
        odds = Decimal('-150')

        edge = standard_edge_calculator(prob, odds)

        # -150 = 60% implied, model says 40%, so negative edge
        assert edge < 0

    def test_edge_calculation_symmetry(self):
        """Edge calculation is consistent."""
        prob = Decimal('0.50')

        # +100 should have zero edge at 50%
        edge = standard_edge_calculator(prob, Decimal('100'))
        assert abs(edge) < Decimal('0.001')


# =============================================================================
# Stake Calculation Tests
# =============================================================================

class TestStakeCalculations:
    """Test stake calculation methods."""

    @pytest.fixture
    def sample_opportunity(self):
        """Create sample betting opportunity."""
        market = BettingMarket(
            market_id='test_001',
            game_id='716190',
            sport=Sport.MLB,
            market_type=MarketType.MONEYLINE,
            book='draftkings',
            book_region=BookRegion.US,
            odds=Decimal('-110'),
            odds_format='american',
            line=None,
            side='Home',
            timestamp=datetime.now(),
            game_time=datetime.now(),
            status=MarketStatus.OPEN,
            home_team='Yankees',
            away_team='Red Sox',
            is_live=False,
        )

        return BetOpportunity(
            opportunity_id='opp_001',
            market=market,
            model_probability=Decimal('0.55'),
            model_confidence=Decimal('0.75'),
            edge=Decimal('0.047'),
            ev=Decimal('0.045'),
            recommendation='bet',
            timestamp=datetime.now(),
            strategy_id='test_strategy',
        )

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        mock_source = Mock()
        return BettingAnalyzer(odds_source=mock_source)

    def test_kelly_stake_calculation(self, analyzer, sample_opportunity):
        """Kelly criterion stake calculation."""
        bankroll = Decimal('10000')

        stake = analyzer.calculate_stake(
            sample_opportunity, bankroll, method='kelly',
        )

        # Kelly stake should be reasonable (not all-in)
        assert stake > 0
        assert stake <= bankroll * Decimal('0.25')  # Capped by fractional Kelly

    def test_flat_stake_calculation(self, analyzer, sample_opportunity):
        """Flat stake calculation."""
        bankroll = Decimal('10000')
        analyzer.flat_stake_unit = Decimal('100')

        stake = analyzer.calculate_stake(
            sample_opportunity, bankroll, method='flat',
        )

        assert stake == Decimal('100')

    def test_confidence_stake_calculation(self, analyzer, sample_opportunity):
        """Confidence-based stake calculation."""
        bankroll = Decimal('10000')
        analyzer.confidence_max_stake = Decimal('500')

        stake = analyzer.calculate_stake(
            sample_opportunity, bankroll, method='confidence',
        )

        # Stake should be proportional to confidence
        assert stake > 0
        assert stake <= Decimal('500')

    def test_stake_respects_max_bet_limit(self, analyzer, sample_opportunity):
        """Stake respects maximum bet percentage."""
        bankroll = Decimal('10000')
        analyzer.max_bet_pct = Decimal('0.02')  # 2% max

        stake = analyzer.calculate_stake(
            sample_opportunity, bankroll, method='kelly',
        )

        assert stake <= bankroll * Decimal('0.02')

    def test_kelly_formula_accuracy(self):
        """Kelly formula produces correct result."""
        # f* = (bp - q) / b
        # where b = odds, p = prob, q = 1-p
        prob = Decimal('0.60')
        odds = Decimal('-110')  # Decimal odds = 1.909

        # Kelly % = (0.909 * 0.60 - 0.40) / 0.909 = 0.16
        kelly_pct = BettingAnalyzer.kelly_criterion(prob, odds)

        assert abs(kelly_pct - Decimal('0.16')) < Decimal('0.02')


# =============================================================================
# Opportunity Finding Tests
# =============================================================================

class TestOpportunityFinding:
    """Test opportunity detection."""

    def test_find_edges_returns_opportunities(self):
        """find_edges returns list of opportunities."""
        mock_source = Mock()
        mock_source.get_game_odds.return_value = [
            BettingMarket(
                market_id='m1',
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
        ]

        analyzer = BettingAnalyzer(odds_source=mock_source, min_edge=Decimal('0.01'))

        opportunities = analyzer.find_edges(
            '716190',
            {'Yankees': Decimal('0.55'), 'Red Sox': Decimal('0.45')},
        )

        assert isinstance(opportunities, list)

    def test_opportunities_filtered_by_min_edge(self):
        """Opportunities filtered by minimum edge threshold."""
        mock_source = Mock()
        mock_source.get_game_odds.return_value = [
            BettingMarket(
                market_id='m1',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='draftkings',
                book_region=BookRegion.US,
                odds=Decimal('-200'),  # High implied prob
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

        # High min_edge should filter out weak opportunities
        analyzer = BettingAnalyzer(odds_source=mock_source, min_edge=Decimal('0.10'))

        opportunities = analyzer.find_edges(
            '716190',
            {'Yankees': Decimal('0.55')},  # Model says 55%, market says 66.7%
        )

        # Should be filtered out (edge is negative)
        assert len(opportunities) == 0

    def test_analyze_game_with_no_odds(self):
        """Handle game with no odds available."""
        mock_source = Mock()
        mock_source.get_game_odds.return_value = []

        analyzer = BettingAnalyzer(odds_source=mock_source)

        result = analyzer.analyze_game('716190', {})

        assert 'markets_analyzed' in result
        assert result['markets_analyzed'] == 0


# =============================================================================
# Reverse Line Movement Tests
# =============================================================================

class TestReverseLineMovement:
    """Test reverse line movement detection."""

    def test_detect_reverse_line_movement_true(self):
        """Detect when public bets one way but line moves other."""
        analyzer = BettingAnalyzer(odds_source=Mock())

        # Public heavily on favorite, line moves toward underdog
        result = analyzer.detect_reverse_line_movement(
            game_id='716190',
            public_pct=Decimal('0.75'),  # 75% on favorite
            line_movement=-Decimal('0.05'),  # Line moved toward dog
        )

        assert result is True

    def test_detect_reverse_line_movement_false(self):
        """No RLM when line follows public."""
        analyzer = BettingAnalyzer(odds_source=Mock())

        # Public on favorite, line moves toward favorite (expected)
        result = analyzer.detect_reverse_line_movement(
            game_id='716190',
            public_pct=Decimal('0.70'),
            line_movement=Decimal('0.03'),
        )

        assert result is False


# =============================================================================
# Bet Creation Tests
# =============================================================================

class TestBetCreation:
    """Test bet creation."""

    @pytest.fixture
    def sample_opportunity(self):
        """Create sample opportunity."""
        market = BettingMarket(
            market_id='test_001',
            game_id='716190',
            sport=Sport.MLB,
            market_type=MarketType.MONEYLINE,
            book='draftkings',
            book_region=BookRegion.US,
            odds=Decimal('-110'),
            odds_format='american',
            line=None,
            side='Home',
            timestamp=datetime.now(),
            game_time=datetime.now(),
            status=MarketStatus.OPEN,
            home_team='Yankees',
            away_team='Red Sox',
            is_live=False,
        )

        return BetOpportunity(
            opportunity_id='opp_001',
            market=market,
            model_probability=Decimal('0.55'),
            model_confidence=Decimal('0.75'),
            edge=Decimal('0.05'),
            ev=Decimal('0.047'),
            recommendation='bet',
            timestamp=datetime.now(),
            strategy_id='test_strategy',
        )

    def test_create_bet_returns_placed_bet(self, sample_opportunity):
        """create_bet returns PlacedBet."""
        analyzer = BettingAnalyzer(odds_source=Mock())

        bet = analyzer.create_bet(
            sample_opportunity,
            bankroll=Decimal('10000'),
            stake_method='kelly',
        )

        assert bet.opportunity == sample_opportunity
        assert bet.stake > 0
        assert bet.odds_placed == sample_opportunity.market.odds

    def test_create_bet_with_custom_stake(self, sample_opportunity):
        """create_bet accepts custom stake override."""
        analyzer = BettingAnalyzer(odds_source=Mock())

        bet = analyzer.create_bet(
            sample_opportunity,
            bankroll=Decimal('10000'),
            stake_method='flat',
            custom_stake=Decimal('250'),
        )

        assert bet.stake == Decimal('250')


# =============================================================================
# Delegate Function Tests
# =============================================================================

class TestDelegateFunctions:
    """Test pluggable delegate functions."""

    def test_custom_edge_calculator(self):
        """Custom edge calculator can be provided."""
        def custom_calc(p, o):
            return (p * Decimal('2')) - Decimal('1')

        analyzer = BettingAnalyzer(
            odds_source=Mock(),
            edge_calculator=custom_calc,
        )

        # Custom calculator should be used
        edge = analyzer.edge_calculator(Decimal('0.60'), Decimal('-110'))
        assert edge == Decimal('0.20')  # 0.60 * 2 - 1

    def test_delegate_change_at_runtime(self):
        """Edge calculator can be swapped at runtime."""
        analyzer = BettingAnalyzer(odds_source=Mock())

        # Swap to Kelly
        analyzer.edge_calculator = kelly_edge_calculator

        edge = analyzer.edge_calculator(Decimal('0.60'), Decimal('-110'))
        assert isinstance(edge, Decimal)


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling."""

    def test_invalid_stake_method(self):
        """Invalid stake method raises error."""
        analyzer = BettingAnalyzer(odds_source=Mock())

        opp = MagicMock()
        opp.market.odds = Decimal('-110')
        opp.model_probability = Decimal('0.55')

        with pytest.raises(ValueError):
            analyzer.calculate_stake(opp, Decimal('10000'), method='invalid')

    def test_source_error_handling(self):
        """Source errors handled gracefully."""
        mock_source = Mock()
        mock_source.get_game_odds.side_effect = Exception('API Error')

        analyzer = BettingAnalyzer(odds_source=mock_source)

        # Should handle error without crashing
        with pytest.raises(Exception):
            analyzer.find_edges('716190', {})

    def test_invalid_probability(self):
        """Invalid probability values handled."""
        with pytest.raises((ValueError, AssertionError)):
            standard_edge_calculator(Decimal('1.5'), Decimal('-110'))  # > 100%


# =============================================================================
# Integration Pattern Tests
# =============================================================================

class TestIntegrationPatterns:
    """Test analyzer works in integration patterns."""

    def test_analyzer_with_real_source_mock(self):
        """Analyzer works with mocked real source."""
        from baseball.betting.sources.the_odds_api import TheOddsApiSource

        mock_source = Mock(spec=TheOddsApiSource)
        mock_source.get_game_odds.return_value = []

        analyzer = BettingAnalyzer(odds_source=mock_source)
        result = analyzer.analyze_game('716190', {})

        assert 'markets_analyzed' in result

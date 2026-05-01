"""Tests for PaperTradingAccount and PaperTradingManager.

Covers:
- Bet placement and tracking
- Bet settlement (win, loss, push)
- Bankroll management
- ROI calculation
- Win rate tracking
- Event hooks
- Auto-settlement by game result
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

from baseball.betting.paper_trading import PaperTradingAccount, PaperTradingManager
from baseball.betting.schemas import (
    PlacedBet, BetOpportunity, BettingMarket, 
    MarketType, Sport, BookRegion, MarketStatus
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_market():
    """Create sample betting market."""
    return BettingMarket(
        market_id="m_001",
        game_id="716190",
        sport=Sport.MLB,
        market_type=MarketType.MONEYLINE,
        book="draftkings",
        book_region=BookRegion.US,
        odds=Decimal("-110"),
        odds_format="american",
        line=None,
        side="Yankees",
        timestamp=datetime.now(),
        game_time=datetime.now(),
        status=MarketStatus.OPEN,
        home_team="Yankees",
        away_team="Red Sox",
        is_live=False
    )


@pytest.fixture
def sample_opportunity(sample_market):
    """Create sample bet opportunity."""
    return BetOpportunity(
        opportunity_id="opp_001",
        market=sample_market,
        model_probability=Decimal("0.55"),
        model_confidence=Decimal("0.75"),
        edge=Decimal("0.05"),
        ev=Decimal("0.047"),
        recommendation="bet",
        timestamp=datetime.now(),
        strategy_id="test_strategy"
    )


@pytest.fixture
def sample_bet(sample_opportunity):
    """Create sample placed bet."""
    return PlacedBet(
        bet_id="bet_001",
        opportunity=sample_opportunity,
        stake=Decimal("100"),
        odds_placed=Decimal("-110"),
        placed_at=datetime.now(),
        strategy_id="test_strategy",
        notes=[]
    )


@pytest.fixture
def fresh_account():
    """Create fresh paper trading account."""
    return PaperTradingAccount(
        name="Test Account",
        initial_bankroll=Decimal("10000"),
        max_bet_pct=Decimal("0.05")
    )


# =============================================================================
# Account Initialization Tests
# =============================================================================

class TestAccountInitialization:
    """Test account setup."""
    
    def test_initial_bankroll_set(self):
        """Initial bankroll is set correctly."""
        account = PaperTradingAccount(
            name="Test",
            initial_bankroll=Decimal("5000")
        )
        
        assert account.initial_bankroll == Decimal("5000")
        assert account.bankroll == Decimal("5000")
    
    def test_default_max_bet_pct(self):
        """Default max bet percentage is 5%."""
        account = PaperTradingAccount(name="Test")
        
        assert account.max_bet_pct == Decimal("0.05")
    
    def test_strategy_id_optional(self):
        """Strategy ID is optional."""
        account = PaperTradingAccount(name="Test")
        
        assert account.strategy_id is None
    
    def test_initial_snapshot_recorded(self):
        """Initial state is recorded in history."""
        account = PaperTradingAccount(name="Test", initial_bankroll=Decimal("10000"))
        
        assert len(account._history) == 1
        assert account._history[0]['bankroll'] == Decimal("10000")


# =============================================================================
# Bet Placement Tests
# =============================================================================

class TestBetPlacement:
    """Test placing bets."""
    
    def test_place_bet_deducts_stake(self, fresh_account, sample_bet):
        """Placing bet deducts stake from bankroll."""
        initial = fresh_account.bankroll
        
        fresh_account.place_bet(sample_bet)
        
        assert fresh_account.bankroll == initial - sample_bet.stake
    
    def test_place_bet_increments_counters(self, fresh_account, sample_bet):
        """Bet counters incremented."""
        fresh_account.place_bet(sample_bet)
        
        assert fresh_account._stats['bets_placed'] == 1
        assert fresh_account._stats['bets_pending'] == 1
        assert fresh_account._stats['total_staked'] == sample_bet.stake
    
    def test_place_bet_enforces_max_bet_limit(self, fresh_account, sample_opportunity):
        """Max bet limit enforced."""
        # Try to place bet exceeding max (5% of 10000 = 500)
        big_bet = PlacedBet(
            bet_id="big_bet",
            opportunity=sample_opportunity,
            stake=Decimal("1000"),  # Exceeds 5%
            odds_placed=Decimal("-110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        result = fresh_account.place_bet(big_bet)
        
        # Should still place but at max
        assert result is True
        placed_bet = fresh_account._bets["big_bet"]
        assert placed_bet.stake <= Decimal("500")
    
    def test_place_bet_insufficient_bankroll(self, fresh_account, sample_opportunity):
        """Cannot place bet with insufficient bankroll."""
        huge_bet = PlacedBet(
            bet_id="huge",
            opportunity=sample_opportunity,
            stake=Decimal("20000"),  # More than bankroll
            odds_placed=Decimal("-110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        result = fresh_account.place_bet(huge_bet)
        
        assert result is False
    
    def test_duplicate_bet_rejected(self, fresh_account, sample_bet):
        """Duplicate bet ID rejected."""
        fresh_account.place_bet(sample_bet)
        
        result = fresh_account.place_bet(sample_bet)
        
        assert result is False
    
    def test_event_hook_fired(self, sample_bet):
        """on_bet_placed hook is called."""
        events = []
        
        account = PaperTradingAccount(
            name="Test",
            on_bet_placed=lambda b: events.append(b.bet_id)
        )
        
        account.place_bet(sample_bet)
        
        assert sample_bet.bet_id in events


# =============================================================================
# Bet Settlement Tests
# =============================================================================

class TestBetSettlement:
    """Test settling bets."""
    
    def test_settle_win_returns_stake_plus_winnings(self, fresh_account, sample_bet):
        """Win returns stake plus winnings."""
        fresh_account.place_bet(sample_bet)
        
        initial_bankroll = fresh_account.bankroll
        
        pnl = fresh_account.settle_bet(sample_bet.bet_id, "win")
        
        # PnL should be positive
        assert pnl > 0
        
        # Bankroll should increase
        assert fresh_account.bankroll > initial_bankroll
    
    def test_settle_loss_keeps_stake(self, fresh_account, sample_bet):
        """Loss keeps stake (already deducted)."""
        fresh_account.place_bet(sample_bet)
        initial_bankroll = fresh_account.bankroll
        
        pnl = fresh_account.settle_bet(sample_bet.bet_id, "loss")
        
        # PnL should be negative (lost stake)
        assert pnl == -sample_bet.stake
        
        # Bankroll unchanged (stake already deducted)
        assert fresh_account.bankroll == initial_bankroll
    
    def test_settle_push_returns_stake(self, fresh_account, sample_bet):
        """Push returns stake."""
        fresh_account.place_bet(sample_bet)
        initial_bankroll = fresh_account.bankroll
        
        pnl = fresh_account.settle_bet(sample_bet.bet_id, "push")
        
        # PnL should be zero
        assert pnl == Decimal("0")
        
        # Bankroll should return to initial (stake refunded)
        assert fresh_account.bankroll == initial_bankroll + sample_bet.stake
    
    def test_settle_win_calculates_winnings_correctly(self, fresh_account, sample_opportunity):
        """Winnings calculated correctly for -110 odds."""
        bet = PlacedBet(
            bet_id="win_bet",
            opportunity=sample_opportunity,
            stake=Decimal("110"),
            odds_placed=Decimal("-110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        fresh_account.place_bet(bet)
        pnl = fresh_account.settle_bet("win_bet", "win")
        
        # -110 means win $100 on $110 stake
        assert pnl == Decimal("100")
    
    def test_settle_win_positive_odds(self, fresh_account, sample_opportunity):
        """Winnings calculated correctly for +150 odds."""
        market = sample_opportunity.market
        market.odds = Decimal("150")
        
        bet = PlacedBet(
            bet_id="pos_bet",
            opportunity=sample_opportunity,
            stake=Decimal("100"),
            odds_placed=Decimal("150"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        fresh_account.place_bet(bet)
        pnl = fresh_account.settle_bet("pos_bet", "win")
        
        # +150 means win $150 on $100 stake
        assert pnl == Decimal("150")
    
    def test_settle_updates_stats(self, fresh_account, sample_bet):
        """Settlement updates statistics."""
        fresh_account.place_bet(sample_bet)
        
        fresh_account.settle_bet(sample_bet.bet_id, "win")
        
        assert fresh_account._stats['bets_won'] == 1
        assert fresh_account._stats['bets_pending'] == 0
    
    def test_double_settle_prevented(self, fresh_account, sample_bet):
        """Cannot settle same bet twice."""
        fresh_account.place_bet(sample_bet)
        fresh_account.settle_bet(sample_bet.bet_id, "win")
        
        pnl = fresh_account.settle_bet(sample_bet.bet_id, "win")
        
        # Second settle should return 0
        assert pnl == Decimal("0")
    
    def test_event_hook_fired_on_settle(self, sample_bet):
        """on_bet_settled hook is called."""
        events = []
        
        account = PaperTradingAccount(
            name="Test",
            on_bet_settled=lambda b: events.append(b.bet_id)
        )
        
        account.place_bet(sample_bet)
        account.settle_bet(sample_bet.bet_id, "win")
        
        assert sample_bet.bet_id in events


# =============================================================================
# Auto-Settlement Tests
# =============================================================================

class TestAutoSettlement:
    """Test auto-settlement by game result."""
    
    def test_auto_settle_moneyline_home_win(self, fresh_account, sample_market):
        """Auto-settle moneyline when home team wins."""
        bet = PlacedBet(
            bet_id="ml_bet",
            opportunity=BetOpportunity(
                opportunity_id="opp",
                market=sample_market,
                model_probability=Decimal("0.55"),
                edge=Decimal("0.05"),
                ev=Decimal("0"),
                recommendation="bet",
                timestamp=datetime.now(),
                strategy_id="test"
            ),
            stake=Decimal("100"),
            odds_placed=Decimal("-110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        fresh_account.place_bet(bet)
        
        # Home team (Yankees) wins 5-3
        settled = fresh_account.settle_by_game_result("716190", 5, 3)
        
        assert "ml_bet" in settled
        assert fresh_account._stats['bets_won'] == 1
    
    def test_auto_settle_moneyline_away_win(self, fresh_account, sample_market):
        """Auto-settle moneyline when away team wins."""
        # Bet on away team
        sample_market.side = "Red Sox"
        
        bet = PlacedBet(
            bet_id="away_bet",
            opportunity=BetOpportunity(
                opportunity_id="opp",
                market=sample_market,
                model_probability=Decimal("0.45"),
                edge=Decimal("0.05"),
                ev=Decimal("0"),
                recommendation="bet",
                timestamp=datetime.now(),
                strategy_id="test"
            ),
            stake=Decimal("100"),
            odds_placed=Decimal("110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        fresh_account.place_bet(bet)
        
        # Away team (Red Sox) wins 4-2
        settled = fresh_account.settle_by_game_result("716190", 2, 4)
        
        assert "away_bet" in settled
        assert fresh_account._stats['bets_won'] == 1
    
    def test_auto_settle_spread(self, fresh_account):
        """Auto-settle spread bet."""
        market = BettingMarket(
            market_id="spread_m",
            game_id="716190",
            sport=Sport.MLB,
            market_type=MarketType.SPREAD,
            book="dk",
            book_region=BookRegion.US,
            odds=Decimal("-110"),
            odds_format="american",
            line=Decimal("-1.5"),
            side="Yankees",
            timestamp=datetime.now(),
            game_time=datetime.now(),
            status=MarketStatus.OPEN,
            home_team="Yankees",
            away_team="Red Sox",
            is_live=False
        )
        
        bet = PlacedBet(
            bet_id="spread_bet",
            opportunity=BetOpportunity(
                opportunity_id="opp",
                market=market,
                model_probability=Decimal("0.55"),
                edge=Decimal("0.05"),
                ev=Decimal("0"),
                recommendation="bet",
                timestamp=datetime.now(),
                strategy_id="test"
            ),
            stake=Decimal("100"),
            odds_placed=Decimal("-110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        fresh_account.place_bet(bet)
        
        # Yankees win by 3 (5-2), covering -1.5
        settled = fresh_account.settle_by_game_result("716190", 5, 2)
        
        assert "spread_bet" in settled
        assert fresh_account._stats['bets_won'] == 1
    
    def test_auto_settle_total(self, fresh_account):
        """Auto-settle total bet."""
        market = BettingMarket(
            market_id="total_m",
            game_id="716190",
            sport=Sport.MLB,
            market_type=MarketType.TOTAL,
            book="dk",
            book_region=BookRegion.US,
            odds=Decimal("-110"),
            odds_format="american",
            line=Decimal("8.5"),
            side="Over",
            timestamp=datetime.now(),
            game_time=datetime.now(),
            status=MarketStatus.OPEN,
            home_team="Yankees",
            away_team="Red Sox",
            is_live=False
        )
        
        bet = PlacedBet(
            bet_id="over_bet",
            opportunity=BetOpportunity(
                opportunity_id="opp",
                market=market,
                model_probability=Decimal("0.52"),
                edge=Decimal("0.02"),
                ev=Decimal("0"),
                recommendation="bet",
                timestamp=datetime.now(),
                strategy_id="test"
            ),
            stake=Decimal("100"),
            odds_placed=Decimal("-110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        
        fresh_account.place_bet(bet)
        
        # Total runs = 10 (5-5), over 8.5 hits
        settled = fresh_account.settle_by_game_result("716190", 5, 5)
        
        assert "over_bet" in settled
        assert fresh_account._stats['bets_won'] == 1


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Test statistics calculations."""
    
    def test_roi_calculation(self, fresh_account, sample_bet):
        """ROI calculated correctly."""
        fresh_account.place_bet(sample_bet)
        fresh_account.settle_bet(sample_bet.bet_id, "win")
        
        roi = fresh_account.get_roi()
        
        assert isinstance(roi, Decimal)
        assert roi > 0  # Won, so positive ROI
    
    def test_win_rate_calculation(self, fresh_account, sample_opportunity):
        """Win rate calculated correctly."""
        # Place 3 bets: 2 wins, 1 loss
        for i, outcome in enumerate(["win", "win", "loss"]):
            bet = PlacedBet(
                bet_id=f"bet_{i}",
                opportunity=sample_opportunity,
                stake=Decimal("100"),
                odds_placed=Decimal("-110"),
                placed_at=datetime.now(),
                strategy_id="test"
            )
            fresh_account.place_bet(bet)
            fresh_account.settle_bet(bet.bet_id, outcome)
        
        win_rate = fresh_account.get_win_rate()
        
        assert win_rate == Decimal("0.667")  # 2/3
    
    def test_average_odds_calculation(self, fresh_account, sample_opportunity):
        """Average odds calculated correctly."""
        odds_values = [Decimal("-110"), Decimal("120"), Decimal("-105")]
        
        for i, odds in enumerate(odds_values):
            opp = sample_opportunity.model_copy()
            opp.market = sample_opportunity.market.model_copy()
            opp.market.odds = odds
            
            bet = PlacedBet(
                bet_id=f"bet_{i}",
                opportunity=opp,
                stake=Decimal("100"),
                odds_placed=odds,
                placed_at=datetime.now(),
                strategy_id="test"
            )
            fresh_account.place_bet(bet)
        
        avg = fresh_account.get_average_odds()
        
        assert avg == sum(odds_values) / len(odds_values)
    
    def test_drawdown_tracking(self, fresh_account, sample_opportunity):
        """Max drawdown tracked."""
        initial = fresh_account.bankroll
        
        # Place large losing bet
        bet = PlacedBet(
            bet_id="loss_bet",
            opportunity=sample_opportunity,
            stake=Decimal("500"),
            odds_placed=Decimal("-110"),
            placed_at=datetime.now(),
            strategy_id="test"
        )
        fresh_account.place_bet(bet)
        fresh_account.settle_bet("loss_bet", "loss")
        
        drawdown = fresh_account._stats['max_drawdown']
        
        assert drawdown == Decimal("500")
    
    def test_performance_summary(self, fresh_account, sample_bet):
        """Performance summary contains all metrics."""
        fresh_account.place_bet(sample_bet)
        fresh_account.settle_bet(sample_bet.bet_id, "win")
        
        summary = fresh_account.get_performance_summary()
        
        required_keys = [
            'name', 'initial_bankroll', 'current_bankroll', 'total_pnl',
            'roi', 'win_rate', 'bets_placed', 'bets_won', 'bets_lost',
            'bets_pending', 'avg_odds', 'max_drawdown', 'drawdown_pct'
        ]
        
        for key in required_keys:
            assert key in summary


# =============================================================================
# Query Tests
# =============================================================================

class TestQueries:
    """Test bet queries."""
    
    def test_get_open_bets(self, fresh_account, sample_opportunity):
        """get_open_bets returns pending bets."""
        bet1 = PlacedBet(
            bet_id="open_1", opportunity=sample_opportunity,
            stake=Decimal("100"), odds_placed=Decimal("-110"),
            placed_at=datetime.now(), strategy_id="test"
        )
        bet2 = PlacedBet(
            bet_id="open_2", opportunity=sample_opportunity,
            stake=Decimal("100"), odds_placed=Decimal("-110"),
            placed_at=datetime.now(), strategy_id="test"
        )
        
        fresh_account.place_bet(bet1)
        fresh_account.place_bet(bet2)
        fresh_account.settle_bet("open_1", "win")
        
        open_bets = fresh_account.get_open_bets()
        
        assert len(open_bets) == 1
        assert open_bets[0].bet_id == "open_2"
    
    def test_get_settled_bets(self, fresh_account, sample_opportunity):
        """get_settled_bets returns completed bets."""
        bet1 = PlacedBet(
            bet_id="bet_1", opportunity=sample_opportunity,
            stake=Decimal("100"), odds_placed=Decimal("-110"),
            placed_at=datetime.now(), strategy_id="test"
        )
        bet2 = PlacedBet(
            bet_id="bet_2", opportunity=sample_opportunity,
            stake=Decimal("100"), odds_placed=Decimal("-110"),
            placed_at=datetime.now(), strategy_id="test"
        )
        
        fresh_account.place_bet(bet1)
        fresh_account.place_bet(bet2)
        fresh_account.settle_bet("bet_1", "win")
        
        settled = fresh_account.get_settled_bets()
        
        assert len(settled) == 1
        assert settled[0].bet_id == "bet_1"


# =============================================================================
# Manager Tests
# =============================================================================

class TestPaperTradingManager:
    """Test PaperTradingManager."""
    
    def test_create_account(self):
        """Manager creates accounts."""
        manager = PaperTradingManager()
        
        account = manager.create_account(
            name="Strategy A",
            initial_bankroll=Decimal("5000")
        )
        
        assert account.name == "Strategy A"
        assert manager.get_account("Strategy A") == account
    
    def test_get_all_accounts(self):
        """Manager returns all accounts."""
        manager = PaperTradingManager()
        
        manager.create_account("A", Decimal("1000"))
        manager.create_account("B", Decimal("2000"))
        
        accounts = manager.get_all_accounts()
        
        assert len(accounts) == 2
        assert "A" in accounts
        assert "B" in accounts
    
    def test_consolidated_report(self):
        """Manager generates consolidated report."""
        manager = PaperTradingManager()
        
        acc1 = manager.create_account("A", Decimal("10000"))
        acc2 = manager.create_account("B", Decimal("10000"))
        
        # Modify bankrolls
        acc1.bankroll = Decimal("11000")
        acc2.bankroll = Decimal("9000")
        
        report = manager.get_consolidated_report()
        
        assert report['accounts'] == 2
        assert report['total_initial_bankroll'] == Decimal("20000")
        assert report['total_current_bankroll'] == Decimal("20000")
        assert report['total_pnl'] == Decimal("0")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error conditions."""
    
    def test_settle_nonexistent_bet(self, fresh_account):
        """Settling nonexistent bet returns 0."""
        pnl = fresh_account.settle_bet("nonexistent", "win")
        
        assert pnl == Decimal("0")
    
    def test_invalid_outcome(self, fresh_account, sample_bet):
        """Invalid outcome handled gracefully."""
        fresh_account.place_bet(sample_bet)
        
        # Should not crash, but behavior is undefined
        # Test that it doesn't raise
        try:
            fresh_account.settle_bet(sample_bet.bet_id, "invalid")
        except:
            pytest.fail("Should handle invalid outcome gracefully")

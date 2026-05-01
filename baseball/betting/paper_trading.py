"""Paper trading system for bet tracking without real money risk.

Provides:
- Simulated bet placement
- Bankroll tracking
- Performance analytics
- ROI calculation

Author: Agent Cascade
Date: 2026-04-30
"""

import logging
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

from baseball.betting.schemas import PlacedBet


logger = logging.getLogger(__name__)


class PaperTradingAccount:
    """Paper trading account for testing strategies without real money.

    Tracks simulated bets with full performance analytics:
    - Bankroll curve over time
    - Win/loss record by strategy
    - ROI and Sharpe ratio
    - Drawdown analysis

    Example:
        >>> account = PaperTradingAccount(
        ...     name="Test Strategy",
        ...     initial_bankroll=Decimal("10000")
        ... )
        >>>
        >>> # Place simulated bets
        >>> bet = analyzer.create_bet(opportunity, bankroll=account.bankroll)
        >>> account.place_bet(bet)
        >>>
        >>> # Later, when game completes
        >>> account.settle_bet(bet.bet_id, outcome="win", actual_odds=bet.odds_placed)
        >>>
        >>> # Check performance
        >>> print(f"ROI: {account.get_roi():.1%}")
    """

    def __init__(
        self,
        name: str,
        initial_bankroll: Decimal = Decimal('10000'),
        max_bet_pct: Decimal = Decimal('0.05'),
        strategy_id: str | None = None,
        on_bet_placed: Callable | None = None,
        on_bet_settled: Callable | None = None,
    ) -> None:
        """Initialize paper trading account.

        Args:
            name: Account identifier
            initial_bankroll: Starting bankroll
            max_bet_pct: Maximum bet as % of bankroll (risk management)
            strategy_id: Associated strategy
            on_bet_placed: Hook called when bet placed (Event Pattern)
            on_bet_settled: Hook called when bet settled (Event Pattern)
        """
        self.name = name
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.max_bet_pct = max_bet_pct
        self.strategy_id = strategy_id

        # Event hooks (Event Pattern)
        self._on_bet_placed = on_bet_placed or (lambda b: None)
        self._on_bet_settled = on_bet_settled or (lambda b: None)

        # Bet storage
        self._bets: dict[str, PlacedBet] = {}
        self._history: list[dict] = []  # Bankroll snapshots

        # Statistics
        self._stats = {
            'bets_placed': 0,
            'bets_won': 0,
            'bets_lost': 0,
            'bets_pending': 0,
            'total_staked': Decimal('0'),
            'total_won': Decimal('0'),
            'total_lost': Decimal('0'),
            'peak_bankroll': initial_bankroll,
            'max_drawdown': Decimal('0'),
        }

        # Record initial state
        self._record_snapshot()

        logger.info(f'Paper trading account created: {name} (${initial_bankroll})')

    def place_bet(self, bet: PlacedBet) -> bool:
        """Place a paper bet (simulated).

        Args:
            bet: The bet to place

        Returns:
            True if bet was placed successfully
        """
        # Validate bet
        if bet.bet_id in self._bets:
            logger.warning(f'Bet {bet.bet_id} already exists')
            return False

        # Check bankroll
        if bet.stake > self.bankroll:
            logger.error(f'Insufficient bankroll for bet {bet.bet_id}')
            return False

        # Check max bet limit
        max_bet = self.bankroll * self.max_bet_pct
        if bet.stake > max_bet:
            logger.warning(f'Bet {bet.bet_id} exceeds max bet limit, capping')
            bet = bet.model_copy(update={'stake': max_bet})

        # Deduct stake from bankroll
        self.bankroll -= bet.stake

        # Store bet
        self._bets[bet.bet_id] = bet

        # Update stats
        self._stats['bets_placed'] += 1
        self._stats['bets_pending'] += 1
        self._stats['total_staked'] += bet.stake

        # Record snapshot
        self._record_snapshot()

        # Emit event (Event Pattern)
        self._on_bet_placed(bet)

        logger.info(f'Paper bet placed: {bet.bet_id} ${bet.stake} on {bet.opportunity.market.side}')
        return True

    def settle_bet(
        self,
        bet_id: str,
        outcome: str,  # 'win', 'loss', 'push'
        actual_odds: Decimal | None = None,
        settlement_price: Decimal | None = None,
    ) -> Decimal:
        """Settle a paper bet and update bankroll.

        Args:
            bet_id: Bet to settle
            outcome: win, loss, or push
            actual_odds: Actual odds at settlement (if different)
            settlement_price: Cash out price (optional)

        Returns:
            P&L from this bet
        """
        if bet_id not in self._bets:
            logger.error(f'Bet {bet_id} not found')
            return Decimal('0')

        bet = self._bets[bet_id]

        # Skip if already settled
        if bet.opportunity.market.status.value != 'open':
            logger.warning(f'Bet {bet_id} already settled')
            return Decimal('0')

        pnl = Decimal('0')

        if outcome == 'win':
            # Calculate winnings
            odds = actual_odds or bet.odds_placed
            if odds > 0:
                winnings = bet.stake * (odds / Decimal('100'))
            else:
                winnings = bet.stake * (Decimal('100') / abs(odds))

            pnl = winnings
            self.bankroll += bet.stake + winnings  # Return stake + winnings
            self._stats['bets_won'] += 1
            self._stats['total_won'] += winnings

        elif outcome == 'loss':
            pnl = -bet.stake
            self._stats['bets_lost'] += 1
            self._stats['total_lost'] += bet.stake
            # Stake already deducted

        elif outcome == 'push':
            # Return stake
            self.bankroll += bet.stake
            pnl = Decimal('0')

        # Update bet status
        settled_bet = bet.model_copy(update={
            'opportunity': bet.opportunity.model_copy(update={
                'market': bet.opportunity.market.model_copy(update={
                    'status': 'settled',
                }),
            }),
        })
        self._bets[bet_id] = settled_bet

        # Update stats
        self._stats['bets_pending'] -= 1

        # Update peak/drawdown
        if self.bankroll > self._stats['peak_bankroll']:
            self._stats['peak_bankroll'] = self.bankroll

        drawdown = self._stats['peak_bankroll'] - self.bankroll
        if drawdown > self._stats['max_drawdown']:
            self._stats['max_drawdown'] = drawdown

        # Record snapshot
        self._record_snapshot()

        # Emit event (Event Pattern)
        self._on_bet_settled(settled_bet)

        logger.info(f'Paper bet settled: {bet_id} {outcome} P&L: ${pnl:.2f}')
        return pnl

    def settle_by_game_result(
        self,
        game_id: str,
        home_score: int,
        away_score: int,
    ) -> list[str]:
        """Auto-settle all bets for a game based on final score.

        Args:
            game_id: Game to settle
            home_score: Final home score
            away_score: Final away score

        Returns:
            List of settled bet IDs
        """
        settled_bets = []

        for bet_id, bet in self._bets.items():
            if bet.opportunity.market.game_id != game_id:
                continue

            if bet.opportunity.market.status.value != 'open':
                continue

            market = bet.opportunity.market
            side = bet.opportunity.market.side

            # Determine outcome
            outcome = None

            if market.market_type.value == 'moneyline':
                # Moneyline
                home_won = home_score > away_score
                if side == market.home_team:
                    outcome = 'win' if home_won else 'loss'
                else:
                    outcome = 'win' if not home_won else 'loss'

            elif market.market_type.value == 'spread':
                # Spread
                if market.line is None:
                    continue

                adjusted_home = home_score + float(market.line)
                if side == market.home_team:
                    outcome = 'win' if adjusted_home > away_score else 'loss'
                else:
                    outcome = 'win' if adjusted_home < away_score else 'loss'

            elif market.market_type.value == 'total':
                # Total
                if market.line is None:
                    continue

                total_runs = home_score + away_score
                if side.lower() == 'over':
                    outcome = 'win' if total_runs > float(market.line) else 'loss'
                else:
                    outcome = 'win' if total_runs < float(market.line) else 'loss'

            if outcome:
                self.settle_bet(bet_id, outcome)
                settled_bets.append(bet_id)

        return settled_bets

    def _record_snapshot(self) -> None:
        """Record bankroll snapshot."""
        self._history.append({
            'timestamp': datetime.now(),
            'bankroll': self.bankroll,
            'bets_pending': self._stats['bets_pending'],
        })

    # ===================================================================
    # Analytics
    # ===================================================================

    def get_roi(self) -> Decimal:
        """Calculate return on investment."""
        if self._stats['total_staked'] == 0:
            return Decimal('0')

        total_pnl = self._stats['total_won'] - self._stats['total_lost']
        return total_pnl / self._stats['total_staked']

    def get_win_rate(self) -> Decimal:
        """Calculate win rate."""
        decided = self._stats['bets_won'] + self._stats['bets_lost']
        if decided == 0:
            return Decimal('0')
        return Decimal(self._stats['bets_won']) / decided

    def get_average_odds(self) -> Decimal:
        """Calculate average odds of placed bets."""
        if not self._bets:
            return Decimal('0')

        total_odds = sum(b.odds_placed for b in self._bets.values())
        return total_odds / len(self._bets)

    def get_clv(self) -> Decimal:
        """Calculate closing line value (beat the closing line)."""
        # Would compare placed odds to closing odds
        # Placeholder implementation
        return Decimal('0')

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            'name': self.name,
            'initial_bankroll': self.initial_bankroll,
            'current_bankroll': self.bankroll,
            'total_pnl': self.bankroll - self.initial_bankroll,
            'roi': self.get_roi(),
            'win_rate': self.get_win_rate(),
            'bets_placed': self._stats['bets_placed'],
            'bets_won': self._stats['bets_won'],
            'bets_lost': self._stats['bets_lost'],
            'bets_pending': self._stats['bets_pending'],
            'avg_odds': self.get_average_odds(),
            'max_drawdown': self._stats['max_drawdown'],
            'drawdown_pct': self._stats['max_drawdown'] / self.initial_bankroll if self.initial_bankroll else 0,
            'bankroll_history': self._history[-10:],  # Last 10 snapshots
        }

    def get_open_bets(self) -> list[PlacedBet]:
        """Get list of pending bets."""
        return [
            bet for bet in self._bets.values()
            if bet.opportunity.market.status.value == 'open'
        ]

    def get_settled_bets(self) -> list[PlacedBet]:
        """Get list of settled bets."""
        return [
            bet for bet in self._bets.values()
            if bet.opportunity.market.status.value == 'settled'
        ]


class PaperTradingManager:
    """Manager for multiple paper trading accounts.

    Handles multiple strategies/accounts with consolidated reporting.
    """

    def __init__(self) -> None:
        self._accounts: dict[str, PaperTradingAccount] = {}

    def create_account(
        self,
        name: str,
        initial_bankroll: Decimal = Decimal('10000'),
        **kwargs,
    ) -> PaperTradingAccount:
        """Create new paper trading account."""
        account = PaperTradingAccount(
            name=name,
            initial_bankroll=initial_bankroll,
            **kwargs,
        )
        self._accounts[name] = account
        return account

    def get_account(self, name: str) -> PaperTradingAccount | None:
        """Get account by name."""
        return self._accounts.get(name)

    def get_all_accounts(self) -> dict[str, PaperTradingAccount]:
        """Get all accounts."""
        return self._accounts.copy()

    def get_consolidated_report(self) -> dict[str, Any]:
        """Get consolidated performance across all accounts."""
        if not self._accounts:
            return {}

        total_bankroll = sum(a.bankroll for a in self._accounts.values())
        total_initial = sum(a.initial_bankroll for a in self._accounts.values())

        return {
            'accounts': len(self._accounts),
            'total_initial_bankroll': total_initial,
            'total_current_bankroll': total_bankroll,
            'total_pnl': total_bankroll - total_initial,
            'account_summaries': {
                name: acc.get_performance_summary()
                for name, acc in self._accounts.items()
            },
        }

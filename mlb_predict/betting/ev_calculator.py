"""Expected Value (EV) Betting Calculator for Baseball

Converts model probabilities to expected value calculations
and identifies profitable betting opportunities.

Author: Agent Cascade
Date: April 24, 2026
"""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================================
# ODDS CONVERSION
# ============================================================================

def american_to_implied_prob(odds: float) -> float:
    """Convert American odds to implied probability.
    
    Parameters:
    -----------
    odds : float
        American odds (e.g., +150, -200)
    
    Returns:
    --------
    float : Implied probability (0-1)
    """
    if odds > 0:
        return 100 / (odds + 100)
    return -odds / (-odds + 100)


def implied_prob_to_american(prob: float) -> float:
    """Convert implied probability to American odds.
    
    Parameters:
    -----------
    prob : float
        Implied probability (0-1)
    
    Returns:
    --------
    float : American odds
    """
    if prob >= 0.5:
        return -100 * prob / (1 - prob)
    return 100 * (1 - prob) / prob


def decimal_to_implied_prob(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    return 1 / odds


def implied_prob_to_decimal(prob: float) -> float:
    """Convert implied probability to decimal odds."""
    return 1 / prob


# ============================================================================
# VIG CALCULATIONS
# ============================================================================

def calculate_vig(
    prob_home: float,
    prob_away: float,
) -> float:
    """Calculate bookmaker vig (overround).
    
    vig = (1/prob_home + 1/prob_away) - 1
    """
    return (1/prob_home + 1/prob_away) - 1


def remove_vig(prob_home: float, prob_away: float) -> tuple[float, float]:
    """Remove vig to get true probabilities.
    
    Uses the proportional method:
    true_prob = implied_prob / (sum of implied_probs)
    """
    total = prob_home + prob_away
    return prob_home / total, prob_away / total


# ============================================================================
# EXPECTED VALUE
# ============================================================================

def calculate_ev(
    model_prob: float,
    odds: float,
    stake: float = 100.0,
) -> float:
    """Calculate expected value of a bet.
    
    Formula:
    EV = (p * payout) - (1 - p) * stake
    
    Parameters:
    -----------
    model_prob : float
        Model's estimated probability of winning (0-1)
    odds : float
        American odds
    stake : float
        Amount wagered
    
    Returns:
    --------
    float : Expected value in dollars
    """
    # Calculate payout
    if odds > 0:
        profit = stake * odds / 100
    else:
        profit = stake * 100 / abs(odds)

    payout = profit + stake

    # EV calculation
    ev = (model_prob * payout) - stake

    return ev


def calculate_ev_percent(
    model_prob: float,
    odds: float,
) -> float:
    """Calculate EV as percentage of stake.
    
    Returns:
    --------
    float : EV percentage (e.g., 0.05 = +5%)
    """
    implied = american_to_implied_prob(odds)
    edge = model_prob - implied
    return edge / implied if implied > 0 else 0


# ============================================================================
# KELLY CRITERION
# ============================================================================

def kelly_criterion(
    model_prob: float,
    odds: float,
    fraction: float = 0.25,  # Conservative Kelly (1/4 Kelly)
) -> float:
    """Calculate Kelly Criterion bet size.
    
    Full Kelly: f* = (bp - q) / b
    Where:
    - b = net odds received (decimal odds - 1)
    - p = probability of win
    - q = probability of loss (1 - p)
    
    Parameters:
    -----------
    model_prob : float
        Model's win probability
    odds : float
        American odds
    fraction : float
        Kelly fraction (0.25 = quarter Kelly, safer)
    
    Returns:
    --------
    float : Recommended bet size as fraction of bankroll
    """
    # Convert American to decimal odds
    if odds > 0:
        decimal = 1 + odds / 100
    else:
        decimal = 1 + 100 / abs(odds)

    # Net odds
    b = decimal - 1
    p = model_prob
    q = 1 - p

    # Full Kelly
    kelly = (b * p - q) / b if b > 0 else 0

    # Apply fraction
    kelly = kelly * fraction

    # Clamp to valid range
    return max(0, min(kelly, 1))


# ============================================================================
# BET TYPES
# ============================================================================

@dataclass
class MoneylineBet:
    """Moneyline bet (who wins)."""
    team: str  # 'home' or 'away'
    odds: float  # American odds
    model_prob: float  # Model win probability

    def ev(self, stake: float = 100) -> float:
        """Calculate expected value."""
        return calculate_ev(self.model_prob, self.odds, stake)

    def kelly(self, fraction: float = 0.25) -> float:
        """Calculate Kelly bet size."""
        return kelly_criterion(self.model_prob, self.odds, fraction)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'type': 'moneyline',
            'team': self.team,
            'odds': self.odds,
            'implied_prob': american_to_implied_prob(self.odds),
            'model_prob': self.model_prob,
            'edge': self.model_prob - american_to_implied_prob(self.odds),
            'ev': self.ev(),
            'kelly': self.kelly(),
        }


@dataclass
class RunLineBet:
    """Run line bet (spread bet, typically +/- 1.5 runs)."""
    team: str
    runs: float  # Usually -1.5 or +1.5
    odds: float
    model_prob: float

    def ev(self, stake: float = 100) -> float:
        return calculate_ev(self.model_prob, self.odds, stake)

    def to_dict(self) -> dict:
        return {
            'type': 'run_line',
            'team': self.team,
            'runs': self.runs,
            'odds': self.odds,
            'model_prob': self.model_prob,
            'ev': self.ev(),
        }


@dataclass
class TotalBet:
    """Over/Under total runs bet."""
    over_under: str  # 'over' or 'under'
    total: float  # Line (e.g., 8.5)
    odds: float
    model_prob: float

    def ev(self, stake: float = 100) -> float:
        return calculate_ev(self.model_prob, self.odds, stake)

    def to_dict(self) -> dict:
        return {
            'type': 'total',
            'over_under': self.over_under,
            'total': self.total,
            'odds': self.odds,
            'model_prob': self.model_prob,
            'ev': self.ev(),
        }


# ============================================================================
# BETTING OPPORTUNITY FINDER
# ============================================================================

@dataclass
class BettingOpportunity:
    """Represents a profitable betting opportunity."""
    bet_type: str
    description: str
    model_prob: float
    market_prob: float
    edge: float
    ev_dollars: float
    ev_percent: float
    kelly_fraction: float
    confidence: str  # 'high', 'medium', 'low'

    def to_dict(self) -> dict:
        return {
            'type': self.bet_type,
            'description': self.description,
            'model_prob': self.model_prob,
            'market_prob': self.market_prob,
            'edge': self.edge,
            'ev_dollars': self.ev_dollars,
            'ev_percent': self.ev_percent,
            'kelly_fraction': self.kelly_fraction,
            'confidence': self.confidence,
        }


class EVCalculator:
    """Expected Value calculator for baseball betting.
    
    Identifies profitable bets by comparing model probabilities
    to market implied probabilities.
    """

    def __init__(
        self,
        min_edge: float = 0.02,  # 2% minimum edge
        min_ev_percent: float = 0.05,  # 5% minimum EV
    ):
        self.min_edge = min_edge
        self.min_ev_percent = min_ev_percent

    def find_opportunities(
        self,
        model_probs: dict[str, float],
        market_odds: dict[str, float],
    ) -> list[BettingOpportunity]:
        """Find all profitable betting opportunities.
        
        Parameters:
        -----------
        model_probs : dict
            {bet_key: model_probability}
        market_odds : dict
            {bet_key: american_odds}
        
        Returns:
        --------
        List of BettingOpportunity
        """
        opportunities = []

        for key, model_prob in model_probs.items():
            if key not in market_odds:
                continue

            odds = market_odds[key]
            market_prob = american_to_implied_prob(odds)
            edge = model_prob - market_prob

            # Check if meets criteria
            if edge < self.min_edge:
                continue

            ev_dollars = calculate_ev(model_prob, odds, stake=100)
            ev_percent = calculate_ev_percent(model_prob, odds)
            kelly = kelly_criterion(model_prob, odds)

            if ev_percent < self.min_ev_percent:
                continue

            # Determine confidence
            if edge > 0.05 and ev_percent > 0.10:
                confidence = 'high'
            elif edge > 0.03 and ev_percent > 0.07:
                confidence = 'medium'
            else:
                confidence = 'low'

            opp = BettingOpportunity(
                bet_type=key.split('_')[0],
                description=key,
                model_prob=model_prob,
                market_prob=market_prob,
                edge=edge,
                ev_dollars=ev_dollars,
                ev_percent=ev_percent,
                kelly_fraction=kelly,
                confidence=confidence,
            )
            opportunities.append(opp)

        # Sort by EV
        opportunities.sort(key=lambda x: x.ev_percent, reverse=True)
        return opportunities

    def analyze_game(
        self,
        home_win_prob: float,
        away_win_prob: float,
        home_odds: float,
        away_odds: float,
        over_under_line: float = 8.5,
        over_prob: float | None = None,
        under_prob: float | None = None,
        over_odds: float | None = None,
        under_odds: float | None = None,
    ) -> dict:
        """Comprehensive analysis of a single game.
        
        Returns:
        --------
        Dict with all betting analysis
        """
        # Calculate market implied probs
        home_implied = american_to_implied_prob(home_odds)
        away_implied = american_to_implied_prob(away_odds)

        # Remove vig
        home_fair, away_fair = remove_vig(home_implied, away_implied)
        vig = calculate_vig(home_implied, away_implied)

        # Find moneyline opportunities
        model_probs = {
            'home_ml': home_win_prob,
            'away_ml': away_win_prob,
        }
        market_odds = {
            'home_ml': home_odds,
            'away_ml': away_odds,
        }

        if over_prob is not None and over_odds is not None:
            model_probs['over'] = over_prob
            model_probs['under'] = under_prob
            market_odds['over'] = over_odds
            market_odds['under'] = under_odds

        opportunities = self.find_opportunities(model_probs, market_odds)

        return {
            'model_probs': {
                'home_win': home_win_prob,
                'away_win': away_win_prob,
            },
            'market_implied': {
                'home': home_implied,
                'away': away_implied,
            },
            'fair_probs': {
                'home': home_fair,
                'away': away_fair,
            },
            'vig': vig,
            'opportunities': [opp.to_dict() for opp in opportunities],
            'recommendation': 'bet' if opportunities else 'pass',
            'best_bet': opportunities[0].to_dict() if opportunities else None,
        }


# ============================================================================
# PORTFOLIO MANAGEMENT
# ============================================================================

def calculate_portfolio_ev(
    bets: list[tuple[float, float, float]],
) -> tuple[float, float]:
    """Calculate expected value of a betting portfolio.
    
    Parameters:
    -----------
    bets : list of (stake, model_prob, odds)
    
    Returns:
    --------
    (total_ev, total_stake)
    """
    total_ev = 0
    total_stake = 0

    for stake, model_prob, odds in bets:
        ev = calculate_ev(model_prob, odds, stake)
        total_ev += ev
        total_stake += stake

    return total_ev, total_stake


def optimal_portfolio_allocation(
    opportunities: list[BettingOpportunity],
    bankroll: float,
    max_kelly_fraction: float = 0.025,  # Max 2.5% per bet
) -> list[tuple[str, float]]:
    """Calculate optimal bet sizes for a portfolio of opportunities.
    
    Uses fractional Kelly with maximum allocation constraints.
    
    Returns:
    --------
    List of (bet_key, stake_amount)
    """
    allocations = []

    for opp in opportunities:
        # Kelly fraction
        kelly = opp.kelly_fraction

        # Apply maximum constraint
        kelly = min(kelly, max_kelly_fraction)

        # Calculate stake
        stake = bankroll * kelly

        allocations.append((opp.description, stake))

    return allocations


# ============================================================================
# BACKTESTING
# ============================================================================

def backtest_betting_strategy(
    predictions: list[tuple[float, float, bool]],
    initial_bankroll: float = 1000,
    kelly_fraction: float = 0.25,
) -> dict:
    """Backtest a betting strategy.
    
    Parameters:
    -----------
    predictions : list of (model_prob, odds, did_win)
    initial_bankroll : float
    kelly_fraction : float
    
    Returns:
    --------
    Dict with backtest results
    """
    bankroll = initial_bankroll
    bankroll_history = [bankroll]
    bets_won = 0
    bets_lost = 0
    total_staked = 0

    for model_prob, odds, did_win in predictions:
        # Calculate stake using Kelly
        kelly = kelly_criterion(model_prob, odds, kelly_fraction)
        stake = bankroll * kelly

        if stake < 1:  # Skip tiny bets
            continue

        total_staked += stake

        # Update bankroll
        if did_win:
            # Calculate profit
            if odds > 0:
                profit = stake * odds / 100
            else:
                profit = stake * 100 / abs(odds)
            bankroll += profit
            bets_won += 1
        else:
            bankroll -= stake
            bets_lost += 1

        bankroll_history.append(bankroll)

    total_bets = bets_won + bets_lost

    return {
        'initial_bankroll': initial_bankroll,
        'final_bankroll': bankroll,
        'profit': bankroll - initial_bankroll,
        'roi': (bankroll - initial_bankroll) / initial_bankroll * 100,
        'total_bets': total_bets,
        'bets_won': bets_won,
        'bets_lost': bets_lost,
        'win_rate': bets_won / total_bets if total_bets > 0 else 0,
        'avg_bet_size': total_staked / total_bets if total_bets > 0 else 0,
        'bankroll_history': bankroll_history,
    }

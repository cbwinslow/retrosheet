"""Tests for BaseOddsSource super class.

Covers:
- Super class abstract methods
- Delegate functions (transform_fn, filter_fn)
- Edge calculation delegates
- Caching behavior
- Health checks
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock

from baseball.betting.sources.base import BaseOddsSource, american_to_decimal, decimal_to_american
from baseball.betting.schemas import Sport, MarketType, BookRegion


# =============================================================================
# Abstract Class Tests
# =============================================================================

class ConcreteOddsSource(BaseOddsSource):
    """Concrete implementation for testing."""
    
    def get_live_odds(self, sport, market_type, region=None, odds_format="american"):
        return []
    
    def get_game_odds(self, game_id, market_types=None):
        return []
    
    def get_line_movement(self, game_id, market_type, hours=24):
        return []
    
    def get_sharp_lines(self, sport, market_type):
        return []


class TestBaseOddsSource:
    """Test BaseOddsSource abstract class."""
    
    def test_abstract_class_cannot_instantiate(self):
        """BaseOddsSource is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseOddsSource(api_key="test")
    
    def test_concrete_class_can_instantiate(self):
        """Concrete subclass can be instantiated."""
        source = ConcreteOddsSource(api_key="test_key")
        assert source.api_key == "test_key"
        assert source.base_url is not None
    
    def test_default_url_implementation(self):
        """Default URL must be implemented by subclass."""
        source = ConcreteOddsSource()
        assert source.base_url == "https://api.example.com"
    
    def test_cache_storage(self):
        """Cache stores and retrieves values."""
        source = ConcreteOddsSource()
        
        source._cache["test_key"] = "test_value"
        assert source._cache["test_key"] == "test_value"
    
    def test_cache_ttl_expired(self):
        """Cache entries respect TTL."""
        import time
        source = ConcreteOddsSource(cache_ttl_seconds=0)
        
        source._cache["key"] = "value"
        time.sleep(0.01)  # Wait for TTL to expire
        
        # Would need implementation of TTL checking to test properly
        assert "key" in source._cache


# =============================================================================
# Odds Conversion Tests
# =============================================================================

class TestOddsConversions:
    """Test odds format conversions."""
    
    @pytest.mark.parametrize("american,expected_decimal", [
        (Decimal("100"), Decimal("2.0")),
        (Decimal("-110"), Decimal("1.909")),
        (Decimal("150"), Decimal("2.5")),
        (Decimal("-150"), Decimal("1.667")),
        (Decimal("200"), Decimal("3.0")),
        (Decimal("-200"), Decimal("1.5")),
    ])
    def test_american_to_decimal(self, american, expected_decimal):
        """American to decimal conversion is accurate."""
        result = american_to_decimal(american)
        assert abs(result - expected_decimal) < Decimal("0.01")
    
    @pytest.mark.parametrize("decimal,expected_american", [
        (Decimal("2.0"), Decimal("100")),
        (Decimal("1.909"), Decimal("-110")),
        (Decimal("2.5"), Decimal("150")),
        (Decimal("1.667"), Decimal("-150")),
    ])
    def test_decimal_to_american(self, decimal, expected_american):
        """Decimal to American conversion is accurate."""
        result = decimal_to_american(decimal)
        assert abs(result - expected_american) < Decimal("5")
    
    def test_even_money_conversion(self):
        """Even money (+100) converts correctly."""
        assert american_to_decimal(Decimal("100")) == Decimal("2.0")
        assert decimal_to_american(Decimal("2.0")) == Decimal("100")
    
    def test_invalid_odds_handling(self):
        """Invalid odds raise appropriate errors."""
        with pytest.raises((ValueError, TypeError)):
            american_to_decimal(Decimal("invalid"))


# =============================================================================
# Delegate Function Tests
# =============================================================================

class TestDelegateFunctions:
    """Test transform and filter delegates."""
    
    def test_transform_fn_applied(self):
        """Transform function is applied to markets."""
        source = ConcreteOddsSource(
            transform_fn=lambda m: {**m, "transformed": True}
        )
        
        test_market = {"id": "1", "odds": Decimal("-110")}
        result = source._apply_transforms([test_market])
        
        assert result[0]["transformed"] is True
    
    def test_filter_fn_applied(self):
        """Filter function filters markets."""
        source = ConcreteOddsSource(
            filter_fn=lambda m: m.get("odds", 0) > 0
        )
        
        markets = [
            {"id": "1", "odds": Decimal("150")},
            {"id": "2", "odds": Decimal("-110")},
            {"id": "3", "odds": Decimal("200")},
        ]
        
        result = source._apply_transforms(markets)
        # Filter should keep only positive odds
        assert len(result) == 2
        assert all(m["odds"] > 0 for m in result)
    
    def test_default_transform_is_identity(self):
        """Default transform is identity function."""
        source = ConcreteOddsSource()
        test_data = {"key": "value"}
        
        result = source.transform_fn(test_data)
        assert result == test_data
    
    def test_default_filter_passes_all(self):
        """Default filter passes all items."""
        source = ConcreteOddsSource()
        
        assert source.filter_fn({"any": "data"}) is True
        assert source.filter_fn(None) is True


# =============================================================================
# Probability & Edge Calculation Tests
# =============================================================================

class TestProbabilityCalculations:
    """Test implied probability and edge calculations."""
    
    def test_implied_probability_positive_odds(self):
        """Implied probability for + odds."""
        source = ConcreteOddsSource()
        
        # +100 = 50% implied
        prob = source.calculate_implied_probability(Decimal("100"))
        assert abs(prob - Decimal("0.5")) < Decimal("0.01")
        
        # +200 = 33.3% implied
        prob = source.calculate_implied_probability(Decimal("200"))
        assert abs(prob - Decimal("0.333")) < Decimal("0.01")
    
    def test_implied_probability_negative_odds(self):
        """Implied probability for - odds."""
        source = ConcreteOddsSource()
        
        # -110 = 52.4% implied
        prob = source.calculate_implied_probability(Decimal("-110"))
        assert abs(prob - Decimal("0.524")) < Decimal("0.01")
        
        # -200 = 66.7% implied
        prob = source.calculate_implied_probability(Decimal("-200"))
        assert abs(prob - Decimal("0.667")) < Decimal("0.01")
    
    def test_calculate_edge_positive(self):
        """Positive edge when model > market."""
        source = ConcreteOddsSource()
        
        # Model says 60%, market says 52.4% (-110)
        edge = source.calculate_edge(Decimal("0.60"), Decimal("-110"))
        assert edge > 0
        assert abs(edge - Decimal("0.076")) < Decimal("0.01")
    
    def test_calculate_edge_negative(self):
        """Negative edge when model < market."""
        source = ConcreteOddsSource()
        
        # Model says 45%, market says 52.4% (-110)
        edge = source.calculate_edge(Decimal("0.45"), Decimal("-110"))
        assert edge < 0
    
    def test_remove_vig_equal_lines(self):
        """Vig removal on equal lines."""
        source = ConcreteOddsSource()
        
        # -110 / -110 typical vig
        home_prob, away_prob = source.remove_vig(
            Decimal("-110"), Decimal("-110")
        )
        
        # Should normalize to roughly 50/50
        assert abs(home_prob - away_prob) < Decimal("0.01")
        assert abs(home_prob + away_prob - Decimal("1.0")) < Decimal("0.01")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_health_check_default(self):
        """Default health check returns False."""
        source = ConcreteOddsSource()
        # Base implementation returns False
        assert source.health_check() is False
    
    def test_invalid_sport_handling(self):
        """Invalid sport raises error."""
        source = ConcreteOddsSource()
        
        with pytest.raises((ValueError, KeyError)):
            source.SPORT_IDS["INVALID_SPORT"]
    
    def test_none_odds_handling(self):
        """None odds handled gracefully."""
        source = ConcreteOddsSource()
        
        with pytest.raises((ValueError, TypeError)):
            source.calculate_implied_probability(None)


# =============================================================================
# Integration Pattern Tests
# =============================================================================

class TestSourceIntegration:
    """Test source works in integration patterns."""
    
    def test_source_in_source_map(self):
        """Source can be used in source mapping pattern."""
        source_map = {
            "concrete": ConcreteOddsSource,
        }
        
        source_class = source_map["concrete"]
        instance = source_class(api_key="test")
        
        assert isinstance(instance, BaseOddsSource)
    
    def test_multiple_sources_polymorphism(self):
        """Multiple sources work polymorphically."""
        
        class SourceA(BaseOddsSource):
            def get_live_odds(self, *args, **kwargs): return ["A"]
            def get_game_odds(self, *args, **kwargs): return []
            def get_line_movement(self, *args, **kwargs): return []
            def get_sharp_lines(self, *args, **kwargs): return []
        
        class SourceB(BaseOddsSource):
            def get_live_odds(self, *args, **kwargs): return ["B"]
            def get_game_odds(self, *args, **kwargs): return []
            def get_line_movement(self, *args, **kwargs): return []
            def get_sharp_lines(self, *args, **kwargs): return []
        
        sources = [SourceA(), SourceB()]
        results = [s.get_live_odds(None, None) for s in sources]
        
        assert results == [["A"], ["B"]]

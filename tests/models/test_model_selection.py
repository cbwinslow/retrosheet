"""
Comprehensive test suite for Model Selection Framework (#161)
Tests context-aware model selection, scoring, and recommendation logic.
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np
from datetime import datetime

from baseball.models.model_selection import (
    ModelSelector, PredictionType, ModelFamily, PredictionContext,
    ModelRecommendation, ModelCapability,
    select_model_for_pa_outcome, select_model_for_win_probability,
    select_model_for_strikeout_rate
)


class TestModelSelector:
    """Comprehensive tests for ModelSelector functionality."""
    
    @pytest.fixture
    def selector(self):
        """Create ModelSelector instance for testing."""
        return ModelSelector()
    
    @pytest.fixture
    def basic_context(self):
        """Create basic prediction context."""
        return PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=["velocity", "zone_x", "zone_y"],
            feature_types={"velocity": "numeric", "zone_x": "numeric", "zone_y": "numeric"},
            sample_size=10000
        )
    
    @pytest.fixture
    def rich_context(self):
        """Create rich prediction context with many features."""
        return PredictionContext(
            prediction_type=PredictionType.WIN_PROBABILITY,
            available_features=["velocity", "zone_x", "zone_y", "count", "run_diff", "inning"],
            feature_types={
                "velocity": "numeric", "zone_x": "numeric", "zone_y": "numeric",
                "count": "categorical", "run_diff": "numeric", "inning": "numeric"
            },
            sample_size=50000,
            ensemble_allowed=True
        )
    
    @pytest.fixture
    def realtime_context(self):
        """Create real-time prediction context."""
        return PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=["velocity", "zone_x"],
            feature_types={"velocity": "numeric", "zone_x": "numeric"},
            sample_size=5000,
            latency_requirement_ms=50,
            real_time_prediction=True
        )
    
    def test_model_capabilities_initialization(self, selector):
        """Test model capabilities are properly initialized."""
        assert len(selector.model_capabilities) == 9
        
        # Test specific capabilities
        hgb_cap = selector.model_capabilities[ModelFamily.HIST_GRADIENT_BOOSTING]
        assert hgb_cap.supports_features is True
        assert hgb_cap.supports_multi_class is True
        assert hgb_cap.interpretability == "low"
        
        empirical_cap = selector.model_capabilities[ModelFamily.EMPIRICAL_BASELINE]
        assert empirical_cap.supports_features is False
        assert empirical_cap.requires_features is False
        assert empirical_cap.interpretability == "high"
    
    def test_prediction_mappings_initialization(self, selector):
        """Test prediction type mappings are properly initialized."""
        assert len(selector.prediction_mappings) == 7
        
        # Test specific mappings
        pa_models = selector.prediction_mappings[PredictionType.PA_OUTCOME]
        assert ModelFamily.HIST_GRADIENT_BOOSTING in pa_models
        assert ModelFamily.SOFTMAX_REGRESSION in pa_models
        
        win_models = selector.prediction_mappings[PredictionType.WIN_PROBABILITY]
        assert ModelFamily.ENSEMBLE in win_models
        assert ModelFamily.LIGHTGBM in win_models
    
    @pytest.mark.asyncio
    async def test_basic_model_recommendation(self, selector, basic_context):
        """Test basic model recommendation functionality."""
        
        recommendation = selector.recommend_model(basic_context)
        
        # Verify recommendation structure
        assert isinstance(recommendation, ModelRecommendation)
        assert isinstance(recommendation.model_family, ModelFamily)
        assert 0 <= recommendation.confidence_score <= 1
        assert len(recommendation.reasoning) > 0
        assert len(recommendation.strengths) > 0
        assert len(recommendation.weaknesses) >= 0
        assert len(recommendation.requirements) > 0
        assert isinstance(recommendation.alternatives, list)
        
        # Should recommend a model that supports features
        assert recommendation.model_family != ModelFamily.EMPIRICAL_BASELINE
    
    def test_pa_outcome_with_features(self, selector, basic_context):
        """Test PA outcome prediction with features available."""
        
        recommendation = selector.recommend_model(basic_context)
        
        # Should recommend HGB or Softmax for PA outcome with features
        assert recommendation.model_family in [
            ModelFamily.HIST_GRADIENT_BOOSTING,
            ModelFamily.SOFTMAX_REGRESSION,
            ModelFamily.ENSEMBLE
        ]
        
        # Should mention features in reasoning
        assert any(keyword in recommendation.reasoning.lower() 
                  for keyword in ["feature", "leverag", "availabl"])
    
    def test_win_probability_ensemble_preference(self, selector, rich_context):
        """Test win probability prediction prefers ensemble."""
        
        recommendation = selector.recommend_model(rich_context)
        
        # Should prefer ensemble for win probability with rich features
        assert recommendation.model_family in [
            ModelFamily.ENSEMBLE,
            ModelFamily.LIGHTGBM,
            ModelFamily.HIST_GRADIENT_BOOSTING
        ]
        
        # Should have high confidence with rich features
        assert recommendation.confidence_score > 0.5
    
    def test_real_time_latency_constraints(self, selector, realtime_context):
        """Test real-time prediction with latency constraints."""
        
        recommendation = selector.recommend_model(realtime_context)
        
        # Should prefer fast models for real-time requirements
        capability = selector.model_capabilities[recommendation.model_family]
        assert capability.speed in ["fast", "medium"]
        
        # Should not recommend slow models
        assert recommendation.model_family != ModelFamily.BAYESIAN_HIERARCHICAL
        assert recommendation.model_family != ModelFamily.ENSEMBLE
    
    def test_no_features_fallback(self, selector):
        """Test fallback to empirical baseline when no features available."""
        
        context = PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=[],
            feature_types={},
            sample_size=1000
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should fallback to empirical baseline
        assert recommendation.model_family == ModelFamily.EMPIRICAL_BASELINE
        
        # Should mention no features in reasoning
        assert "no features" in recommendation.reasoning.lower() or "minimal" in recommendation.reasoning.lower()
    
    def test_interpretability_requirements(self, selector):
        """Test interpretability constraints affect model selection."""
        
        # High interpretability requirement
        context = PredictionContext(
            prediction_type=PredictionType.STRIKEOUT_RATE,
            available_features=["velocity", "k_rate"],
            feature_types={"velocity": "numeric", "k_rate": "numeric"},
            sample_size=5000,
            interpretability_requirement="high"
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should prefer interpretable models
        capability = selector.model_capabilities[recommendation.model_family]
        assert capability.interpretability == "high"
        
        # Should mention interpretability in reasoning
        assert "interpret" in recommendation.reasoning.lower()
    
    def test_uncertainty_estimation_preference(self, selector):
        """Test uncertainty estimation affects model selection."""
        
        context = PredictionContext(
            prediction_type=PredictionType.WIN_PROBABILITY,
            available_features=["velocity", "run_diff"],
            feature_types={"velocity": "numeric", "run_diff": "numeric"},
            sample_size=10000,
            uncertainty_estimation=True
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should prefer models that support uncertainty
        assert recommendation.model_family in [
            ModelFamily.BAYESIAN_HIERARCHICAL,
            ModelFamily.ENSEMBLE,
            ModelFamily.SOFTMAX_REGRESSION
        ]
    
    def test_ensemble_disallowed(self, selector, rich_context):
        """Test ensemble constraint affects model selection."""
        
        # Disallow ensemble
        rich_context.ensemble_allowed = False
        
        recommendation = selector.recommend_model(rich_context)
        
        # Should not recommend ensemble
        assert recommendation.model_family != ModelFamily.ENSEMBLE
        
        # Should recommend alternative
        assert recommendation.model_family in [
            ModelFamily.LIGHTGBM,
            ModelFamily.HIST_GRADIENT_BOOSTING
        ]
    
    def test_small_sample_size_preference(self, selector):
        """Test small sample size affects model selection."""
        
        context = PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=["velocity"],
            feature_types={"velocity": "numeric"},
            sample_size=500  # Small sample
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should prefer simpler models for small samples
        capability = selector.model_capabilities[recommendation.model_family]
        assert capability.data_requirements in ["minimal", "moderate"]
        
        # Should mention sample size in reasoning
        assert "sample" in recommendation.reasoning.lower() or "data" in recommendation.reasoning.lower()
    
    def test_large_sample_size_complexity(self, selector):
        """Test large sample size allows complex models."""
        
        context = PredictionContext(
            prediction_type=PredictionType.WIN_PROBABILITY,
            available_features=["velocity", "zone_x", "zone_y", "count", "run_diff", "inning", "outs"],
            feature_types={f"feature_{i}": "numeric" for i in range(7)},
            sample_size=100000  # Large sample
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should allow complex models for large samples
        capability = selector.model_capabilities[recommendation.model_family]
        assert capability.data_requirements in ["moderate", "extensive"]
    
    def test_scoring_function(self, selector, basic_context):
        """Test model scoring function works correctly."""
        
        # Test scoring of different models
        hgb_score = selector._score_candidate(ModelFamily.HIST_GRADIENT_BOOSTING, basic_context)
        empirical_score = selector._score_candidate(ModelFamily.EMPIRICAL_BASELINE, basic_context)
        
        # Scores should be in valid range
        assert 0 <= hgb_score <= 1
        assert 0 <= empirical_score <= 1
        
        # HGB should score higher with features available
        assert hgb_score > empirical_score
    
    def test_reasoning_generation(self, selector, basic_context):
        """Test reasoning generation provides useful information."""
        
        recommendation = selector.recommend_model(basic_context)
        
        reasoning = recommendation.reasoning
        
        # Should contain prediction type information
        assert any(keyword in reasoning.lower() 
                  for keyword in ["pa_outcome", "prediction", "model"])
        
        # Should be well-formed
        assert len(reasoning) > 20  # Reasonable length
        assert reasoning.count(";") >= 1  # Multiple points
    
    def test_strengths_weaknesses_extraction(self, selector):
        """Test strengths and weaknesses are properly extracted."""
        
        # Test HGB
        strengths, weaknesses = selector._get_strengths_weaknesses(ModelFamily.HIST_GRADIENT_BOOSTING)
        
        assert len(strengths) > 0
        assert len(weaknesses) > 0
        assert any("feature" in s.lower() for s in strengths)
        assert any("black box" in w.lower() or "interpret" in w.lower() for w in weaknesses)
        
        # Test Empirical Baseline
        strengths, weaknesses = selector._get_strengths_weaknesses(ModelFamily.EMPIRICAL_BASELINE)
        
        assert any("fast" in s.lower() or "no training" in s.lower() for s in strengths)
        assert any("personalization" in w.lower() for w in weaknesses)
    
    def test_requirements_extraction(self, selector, basic_context):
        """Test requirements are properly extracted."""
        
        recommendation = selector.recommend_model(basic_context)
        requirements = recommendation.requirements
        
        # Should contain required fields
        assert "features" in requirements
        assert "sample_size" in requirements
        assert "speed_class" in requirements
        assert "interpretability" in requirements
        
        # Feature requirements should match context
        if requirements["features"]:
            assert set(requirements["features"]) <= set(basic_context.available_features)
    
    def test_get_all_recommendations(self, selector, basic_context):
        """Test getting all recommendations ranked by score."""
        
        recommendations = selector.get_all_recommendations(basic_context)
        
        # Should return multiple recommendations
        assert len(recommendations) >= 2
        
        # Should be sorted by confidence score
        scores = [r.confidence_score for r in recommendations]
        assert scores == sorted(scores, reverse=True)
        
        # First recommendation should match single recommendation
        single_rec = selector.recommend_model(basic_context)
        assert recommendations[0].model_family == single_rec.model_family
        assert abs(recommendations[0].confidence_score - single_rec.confidence_score) < 0.01
        
        # Should have alternatives for non-last recommendations
        for i, rec in enumerate(recommendations[:-1]):
            assert len(rec.alternatives) >= 1
    
    def test_markov_chain_selection(self, selector):
        """Test Markov chain selection for appropriate prediction types."""
        
        # Test inning runs prediction
        context = PredictionContext(
            prediction_type=PredictionType.INNING_RUNS,
            available_features=[],
            feature_types={},
            sample_size=1000
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should prefer Markov for inning runs without features
        assert recommendation.model_family in [
            ModelFamily.MARKOV_UNINFORMED,
            ModelFamily.MARKOV_INFORMED
        ]
    
    def test_base_out_state_selection(self, selector):
        """Test base-out state prediction selection."""
        
        context = PredictionContext(
            prediction_type=PredictionType.BASE_OUT_STATE,
            available_features=["count", "outs"],
            feature_types={"count": "categorical", "outs": "numeric"},
            sample_size=5000
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should prefer softmax or Markov for base-out states
        assert recommendation.model_family in [
            ModelFamily.SOFTMAX_REGRESSION,
            ModelFamily.MARKOV_INFORMED,
            ModelFamily.HIST_GRADIENT_BOOSTING
        ]


class TestConvenienceFunctions:
    """Test convenience functions for common prediction types."""
    
    def test_select_model_for_pa_outcome(self):
        """Test PA outcome convenience function."""
        
        recommendation = select_model_for_pa_outcome(
            available_features=["velocity", "zone_x"],
            feature_types={"velocity": "numeric", "zone_x": "numeric"},
            sample_size=10000,
            latency_requirement_ms=100,
            real_time=False
        )
        
        assert isinstance(recommendation, ModelRecommendation)
        assert recommendation.model_family in [
            ModelFamily.HIST_GRADIENT_BOOSTING,
            ModelFamily.SOFTMAX_REGRESSION,
            ModelFamily.ENSEMBLE
        ]
    
    def test_select_model_for_win_probability(self):
        """Test win probability convenience function."""
        
        recommendation = select_model_for_win_probability(
            available_features=["run_diff", "outs", "inning"],
            feature_types={"run_diff": "numeric", "outs": "numeric", "inning": "numeric"},
            sample_size=50000,
            ensemble_allowed=True
        )
        
        assert isinstance(recommendation, ModelRecommendation)
        assert recommendation.model_family in [
            ModelFamily.ENSEMBLE,
            ModelFamily.LIGHTGBM,
            ModelFamily.HIST_GRADIENT_BOOSTING
        ]
    
    def test_select_model_for_strikeout_rate(self):
        """Test strikeout rate convenience function."""
        
        recommendation = select_model_for_strikeout_rate(
            available_features=["k_rate", "velocity"],
            feature_types={"k_rate": "numeric", "velocity": "numeric"},
            sample_size=25000,
            interpretability="medium"
        )
        
        assert isinstance(recommendation, ModelRecommendation)
        assert recommendation.model_family in [
            ModelFamily.HIST_GRADIENT_BOOSTING,
            ModelFamily.LOGISTIC_REGRESSION,
            ModelFamily.MARKOV_INFORMED
        ]


class TestModelSelectionEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def selector(self):
        return ModelSelector()
    
    def test_unknown_prediction_type(self, selector):
        """Test handling of unknown prediction types."""
        
        # Create context with prediction type not in mappings
        context = PredictionContext(
            prediction_type=PredictionType.PITCHER_PERFORMANCE,  # Less common type
            available_features=["velocity"],
            feature_types={"velocity": "numeric"},
            sample_size=1000
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should still provide a recommendation
        assert isinstance(recommendation, ModelRecommendation)
        assert isinstance(recommendation.model_family, ModelFamily)
    
    def test_empty_feature_types(self, selector):
        """Test handling of empty feature types."""
        
        context = PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=["velocity", "zone_x"],
            feature_types={},  # Empty feature types
            sample_size=1000
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should still work
        assert isinstance(recommendation, ModelRecommendation)
    
    def test_extremely_low_latency_requirement(self, selector):
        """Test extremely low latency requirements."""
        
        context = PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=["velocity"],
            feature_types={"velocity": "numeric"},
            sample_size=1000,
            latency_requirement_ms=10  # Very low latency
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should prefer fastest models
        capability = selector.model_capabilities[recommendation.model_family]
        assert capability.speed == "fast"
    
    def test_zero_sample_size(self, selector):
        """Test zero sample size handling."""
        
        context = PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=[],
            feature_types={},
            sample_size=0  # No data
        )
        
        recommendation = selector.recommend_model(context)
        
        # Should fallback to empirical baseline
        assert recommendation.model_family == ModelFamily.EMPIRICAL_BASELINE
    
    def test_all_model_families_coverage(self, selector):
        """Test that all model families can be recommended in some context."""
        
        recommended_families = set()
        
        # Try various contexts to hit all model families
        contexts = [
            # Empirical baseline
            PredictionContext(PredictionType.PA_OUTCOME, [], {}, 100),
            # Markov uninformed
            PredictionContext(PredictionType.INNING_RUNS, [], {}, 1000),
            # Markov informed
            PredictionContext(PredictionType.BASE_OUT_STATE, ["count"], {"count": "categorical"}, 5000),
            # Softmax
            PredictionContext(PredictionType.BASE_OUT_STATE, ["zone_x"], {"zone_x": "numeric"}, 10000),
            # HGB
            PredictionContext(PredictionType.PA_OUTCOME, ["velocity"], {"velocity": "numeric"}, 50000),
            # LightGBM
            PredictionContext(PredictionType.WIN_PROBABILITY, ["run_diff"], {"run_diff": "numeric"}, 100000),
            # Logistic
            PredictionContext(PredictionType.STRIKEOUT_RATE, ["k_rate"], {"k_rate": "numeric"}, 25000, interpretability_requirement="high"),
            # Ensemble
            PredictionContext(PredictionType.WIN_PROBABILITY, ["run_diff"], {"run_diff": "numeric"}, 50000, ensemble_allowed=True),
            # Bayesian
            PredictionContext(PredictionType.WIN_PROBABILITY, ["run_diff"], {"run_diff": "numeric"}, 50000, uncertainty_estimation=True),
        ]
        
        for context in contexts:
            recommendation = selector.recommend_model(context)
            recommended_families.add(recommendation.model_family)
        
        # Should have recommended most model families
        assert len(recommended_families) >= 7  # At least 7 out of 9


class TestModelSelectionPerformance:
    """Test performance of model selection framework."""
    
    @pytest.fixture
    def selector(self):
        return ModelSelector()
    
    def test_recommendation_performance(self, selector):
        """Test recommendation performance is acceptable."""
        import time
        
        context = PredictionContext(
            prediction_type=PredictionType.PA_OUTCOME,
            available_features=["velocity", "zone_x", "zone_y", "count"],
            feature_types={"velocity": "numeric", "zone_x": "numeric", "zone_y": "numeric", "count": "categorical"},
            sample_size=10000
        )
        
        # Measure recommendation time
        start_time = time.time()
        recommendation = selector.recommend_model(context)
        end_time = time.time()
        
        recommendation_time_ms = (end_time - start_time) * 1000
        
        # Should be fast (< 50ms)
        assert recommendation_time_ms < 50
        assert isinstance(recommendation, ModelRecommendation)
    
    def test_all_recommendations_performance(self, selector):
        """Test getting all recommendations performance."""
        import time
        
        context = PredictionContext(
            prediction_type=PredictionType.WIN_PROBABILITY,
            available_features=["run_diff", "outs", "inning", "velocity"],
            feature_types={"run_diff": "numeric", "outs": "numeric", "inning": "numeric", "velocity": "numeric"},
            sample_size=50000
        )
        
        # Measure time for all recommendations
        start_time = time.time()
        recommendations = selector.get_all_recommendations(context)
        end_time = time.time()
        
        all_recommendations_time_ms = (end_time - start_time) * 1000
        
        # Should still be reasonably fast (< 100ms)
        assert all_recommendations_time_ms < 100
        assert len(recommendations) >= 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])

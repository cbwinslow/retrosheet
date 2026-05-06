"""
Context-Aware Model Selection Framework for Baseball Predictions

Implements research-backed model selection based on prediction target,
feature availability, and context requirements. Follows the Model Selection Guide
for automated model recommendation.

Author: Agent Cascade
Date: 2026-05-06
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from abc import ABC, abstractmethod

from baseball.models.registry import ModelRegistryEntry


class PredictionType(Enum):
    """Types of baseball predictions."""
    PA_OUTCOME = "pa_outcome"  # Multi-class: Ball, Strike, BallInPlay
    INNING_RUNS = "inning_runs"  # Count: 0, 1, 2, 3+
    BASE_OUT_STATE = "base_out_state"  # Discrete: 24 possible states
    STRIKEOUT_RATE = "strikeout_rate"  # Binary probability
    WIN_PROBABILITY = "win_probability"  # Game-level probability
    HIT_PROJECTION = "hit_projection"  # Multi-class hit types
    PITCHER_PERFORMANCE = "pitcher_performance"  # ERA, K/BB, etc


class ModelFamily(Enum):
    """Model families with their characteristics."""
    EMPIRICAL_BASELINE = "empirical_baseline"
    MARKOV_UNINFORMED = "markov_uninformed"
    MARKOV_INFORMED = "markov_informed"
    SOFTMAX_REGRESSION = "softmax_regression"
    HIST_GRADIENT_BOOSTING = "hist_gradient_boosting"
    LIGHTGBM = "lightgbm"
    LOGISTIC_REGRESSION = "logistic_regression"
    ENSEMBLE = "ensemble"
    BAYESIAN_HIERARCHICAL = "bayesian_hierarchical"


@dataclass
class ModelCapability:
    """Model capability and requirements."""
    supports_features: bool
    supports_categorical: bool
    supports_multi_class: bool
    supports_binary: bool
    supports_regression: bool
    requires_features: bool
    interpretability: str  # "high", "medium", "low"
    speed: str  # "fast", "medium", "slow"
    data_requirements: str  # "minimal", "moderate", "extensive"


@dataclass
class PredictionContext:
    """Context for model selection."""
    prediction_type: PredictionType
    available_features: List[str]
    feature_types: Dict[str, str]  # feature_name -> type
    sample_size: int
    latency_requirement_ms: Optional[int] = None
    interpretability_requirement: Optional[str] = None
    uncertainty_estimation: bool = False
    real_time_prediction: bool = False
    ensemble_allowed: bool = True


@dataclass
class ModelRecommendation:
    """Model recommendation with reasoning."""
    model_family: ModelFamily
    confidence_score: float
    reasoning: str
    strengths: List[str]
    weaknesses: List[str]
    requirements: Dict[str, Any]
    alternatives: List[ModelFamily]


class ModelSelector:
    """Context-aware model selection framework.
    
    Analyzes prediction context and recommends optimal models
    based on research-backed guidelines and feature availability.
    """
    
    def __init__(self):
        self.model_capabilities = self._initialize_model_capabilities()
        self.prediction_mappings = self._initialize_prediction_mappings()
    
    def _initialize_model_capabilities(self) -> Dict[ModelFamily, ModelCapability]:
        """Initialize model capability matrix."""
        return {
            ModelFamily.EMPIRICAL_BASELINE: ModelCapability(
                supports_features=False,
                supports_categorical=False,
                supports_multi_class=False,
                supports_binary=False,
                supports_regression=False,
                requires_features=False,
                interpretability="high",
                speed="fast",
                data_requirements="minimal"
            ),
            ModelFamily.MARKOV_UNINFORMED: ModelCapability(
                supports_features=False,
                supports_categorical=True,
                supports_multi_class=True,
                supports_binary=False,
                supports_regression=False,
                requires_features=False,
                interpretability="high",
                speed="fast",
                data_requirements="minimal"
            ),
            ModelFamily.MARKOV_INFORMED: ModelCapability(
                supports_features=True,
                supports_categorical=True,
                supports_multi_class=True,
                supports_binary=False,
                supports_regression=False,
                requires_features=True,
                interpretability="medium",
                speed="medium",
                data_requirements="moderate"
            ),
            ModelFamily.SOFTMAX_REGRESSION: ModelCapability(
                supports_features=True,
                supports_categorical=True,
                supports_multi_class=True,
                supports_binary=True,
                supports_regression=False,
                requires_features=True,
                interpretability="high",
                speed="fast",
                data_requirements="moderate"
            ),
            ModelFamily.HIST_GRADIENT_BOOSTING: ModelCapability(
                supports_features=True,
                supports_categorical=True,
                supports_multi_class=True,
                supports_binary=True,
                supports_regression=True,
                requires_features=True,
                interpretability="low",
                speed="medium",
                data_requirements="extensive"
            ),
            ModelFamily.LIGHTGBM: ModelCapability(
                supports_features=True,
                supports_categorical=True,
                supports_multi_class=True,
                supports_binary=True,
                supports_regression=True,
                requires_features=True,
                interpretability="low",
                speed="fast",
                data_requirements="extensive"
            ),
            ModelFamily.LOGISTIC_REGRESSION: ModelCapability(
                supports_features=True,
                supports_categorical=True,
                supports_multi_class=False,
                supports_binary=True,
                supports_regression=False,
                requires_features=True,
                interpretability="high",
                speed="fast",
                data_requirements="moderate"
            ),
            ModelFamily.ENSEMBLE: ModelCapability(
                supports_features=True,
                supports_categorical=True,
                supports_multi_class=True,
                supports_binary=True,
                supports_regression=True,
                requires_features=True,
                interpretability="low",
                speed="slow",
                data_requirements="extensive"
            ),
            ModelFamily.BAYESIAN_HIERARCHICAL: ModelCapability(
                supports_features=True,
                supports_categorical=True,
                supports_multi_class=True,
                supports_binary=True,
                supports_regression=True,
                requires_features=True,
                interpretability="medium",
                speed="slow",
                data_requirements="extensive"
            )
        }
    
    def _initialize_prediction_mappings(self) -> Dict[PredictionType, List[ModelFamily]]:
        """Initialize prediction type to model family mappings."""
        return {
            PredictionType.PA_OUTCOME: [
                ModelFamily.HIST_GRADIENT_BOOSTING,
                ModelFamily.SOFTMAX_REGRESSION,
                ModelFamily.ENSEMBLE
            ],
            PredictionType.INNING_RUNS: [
                ModelFamily.MARKOV_UNINFORMED,
                ModelFamily.MARKOV_INFORMED,
                ModelFamily.HIST_GRADIENT_BOOSTING
            ],
            PredictionType.BASE_OUT_STATE: [
                ModelFamily.SOFTMAX_REGRESSION,
                ModelFamily.MARKOV_INFORMED,
                ModelFamily.HIST_GRADIENT_BOOSTING
            ],
            PredictionType.STRIKEOUT_RATE: [
                ModelFamily.HIST_GRADIENT_BOOSTING,
                ModelFamily.LOGISTIC_REGRESSION,
                ModelFamily.MARKOV_INFORMED
            ],
            PredictionType.WIN_PROBABILITY: [
                ModelFamily.ENSEMBLE,
                ModelFamily.LIGHTGBM,
                ModelFamily.HIST_GRADIENT_BOOSTING
            ],
            PredictionType.HIT_PROJECTION: [
                ModelFamily.SOFTMAX_REGRESSION,
                ModelFamily.EMPIRICAL_BASELINE,
                ModelFamily.HIST_GRADIENT_BOOSTING
            ],
            PredictionType.PITCHER_PERFORMANCE: [
                ModelFamily.HIST_GRADIENT_BOOSTING,
                ModelFamily.LIGHTGBM,
                ModelFamily.LOGISTIC_REGRESSION
            ]
        }
    
    def recommend_model(self, context: PredictionContext) -> ModelRecommendation:
        """Recommend optimal model for given context.
        
        Args:
            context: Prediction context with requirements and constraints
            
        Returns:
            ModelRecommendation with detailed reasoning
        """
        # Get candidate models for prediction type
        candidates = self.prediction_mappings.get(context.prediction_type, [])
        
        # Filter candidates based on context requirements
        viable_candidates = []
        for candidate in candidates:
            capability = self.model_capabilities[candidate]
            
            # Check feature requirements
            if capability.requires_features and not context.available_features:
                continue
            
            # Check latency requirements
            if context.latency_requirement_ms:
                if capability.speed == "slow" and context.latency_requirement_ms < 100:
                    continue
                elif capability.speed == "medium" and context.latency_requirement_ms < 50:
                    continue
            
            # Check interpretability requirements
            if context.interpretability_requirement:
                if context.interpretability_requirement == "high" and capability.interpretability != "high":
                    continue
                elif context.interpretability_requirement == "medium" and capability.interpretability == "low":
                    continue
            
            # Check uncertainty estimation
            if context.uncertainty_estimation and candidate != ModelFamily.BAYESIAN_HIERARCHICAL:
                if candidate not in [ModelFamily.ENSEMBLE, ModelFamily.SOFTMAX_REGRESSION]:
                    continue
            
            # Check real-time prediction
            if context.real_time_prediction and capability.speed == "slow":
                continue
            
            # Check ensemble allowance
            if not context.ensemble_allowed and candidate == ModelFamily.ENSEMBLE:
                continue
            
            viable_candidates.append(candidate)
        
        # If no viable candidates, fallback to empirical baseline
        if not viable_candidates:
            viable_candidates = [ModelFamily.EMPIRICAL_BASELINE]
        
        # Score candidates and select best
        scored_candidates = []
        for candidate in viable_candidates:
            score = self._score_candidate(candidate, context)
            scored_candidates.append((candidate, score))
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select best candidate
        best_candidate, best_score = scored_candidates[0]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(best_candidate, context, best_score)
        strengths, weaknesses = self._get_strengths_weaknesses(best_candidate)
        requirements = self._get_requirements(best_candidate, context)
        alternatives = [c[0] for c in scored_candidates[1:3]]  # Top 2 alternatives
        
        return ModelRecommendation(
            model_family=best_candidate,
            confidence_score=best_score,
            reasoning=reasoning,
            strengths=strengths,
            weaknesses=weaknesses,
            requirements=requirements,
            alternatives=alternatives
        )
    
    def _score_candidate(self, candidate: ModelFamily, context: PredictionContext) -> float:
        """Score candidate model for context."""
        capability = self.model_capabilities[candidate]
        score = 0.0
        
        # Base score for prediction type match
        if candidate in self.prediction_mappings.get(context.prediction_type, []):
            score += 0.4
        
        # Feature availability bonus
        if context.available_features and capability.supports_features:
            score += 0.2
        
        # Sample size appropriateness
        if context.sample_size > 10000 and capability.data_requirements == "extensive":
            score += 0.1
        elif context.sample_size < 1000 and capability.data_requirements == "minimal":
            score += 0.1
        
        # Speed bonus for real-time requirements
        if context.real_time_prediction:
            if capability.speed == "fast":
                score += 0.2
            elif capability.speed == "medium":
                score += 0.1
        
        # Interpretability bonus
        if context.interpretability_requirement == "high" and capability.interpretability == "high":
            score += 0.2
        elif context.interpretability_requirement == "medium" and capability.interpretability in ["high", "medium"]:
            score += 0.1
        
        # Uncertainty estimation bonus
        if context.uncertainty_estimation:
            if candidate in [ModelFamily.BAYESIAN_HIERARCHICAL, ModelFamily.ENSEMBLE]:
                score += 0.2
            elif candidate == ModelFamily.SOFTMAX_REGRESSION:
                score += 0.1
        
        # Add small randomness for tie-breaking
        score += np.random.normal(0, 0.01)
        
        return max(0.0, min(1.0, score))
    
    def _generate_reasoning(self, candidate: ModelFamily, context: PredictionContext, score: float) -> str:
        """Generate reasoning for model selection."""
        capability = self.model_capabilities[candidate]
        
        reasoning_parts = []
        
        # Prediction type match
        if candidate in self.prediction_mappings.get(context.prediction_type, []):
            reasoning_parts.append(f"{candidate.value} is research-backed for {context.prediction_type.value}")
        
        # Feature considerations
        if context.available_features:
            if capability.supports_features:
                reasoning_parts.append("Leverages available features effectively")
            else:
                reasoning_parts.append("Feature-independent approach suitable")
        else:
            if not capability.requires_features:
                reasoning_parts.append("No features required - minimal data needs")
        
        # Performance characteristics
        if context.real_time_prediction and capability.speed == "fast":
            reasoning_parts.append("Meets real-time latency requirements")
        
        if context.interpretability_requirement:
            if capability.interpretability == "high":
                reasoning_parts.append("High interpretability meets requirements")
            elif capability.interpretability == "low":
                reasoning_parts.append("Lower interpretability but higher accuracy")
        
        # Uncertainty estimation
        if context.uncertainty_estimation and candidate in [ModelFamily.BAYESIAN_HIERARCHICAL, ModelFamily.ENSEMBLE]:
            reasoning_parts.append("Provides uncertainty estimates")
        
        # Sample size considerations
        if context.sample_size > 10000 and capability.data_requirements == "extensive":
            reasoning_parts.append("Sufficient data for complex model")
        elif context.sample_size < 1000 and capability.data_requirements == "minimal":
            reasoning_parts.append("Appropriate for limited data")
        
        if not reasoning_parts:
            reasoning_parts.append(f"Selected as best match for context (score: {score:.2f})")
        
        return "; ".join(reasoning_parts)
    
    def _get_strengths_weaknesses(self, candidate: ModelFamily) -> Tuple[List[str], List[str]]:
        """Get strengths and weaknesses for model family."""
        capability = self.model_capabilities[candidate]
        
        strengths = []
        weaknesses = []
        
        # Speed
        if capability.speed == "fast":
            strengths.append("Fast prediction speed")
        elif capability.speed == "slow":
            weaknesses.append("Slower prediction speed")
        
        # Interpretability
        if capability.interpretability == "high":
            strengths.append("High interpretability")
        elif capability.interpretability == "low":
            weaknesses.append("Low interpretability (black box)")
        
        # Data requirements
        if capability.data_requirements == "minimal":
            strengths.append("Minimal data requirements")
        elif capability.data_requirements == "extensive":
            weaknesses.append("Requires extensive data")
        
        # Feature support
        if capability.supports_features:
            strengths.append("Feature-rich modeling")
        else:
            strengths.append("Simple and robust")
        
        # Model-specific strengths/weaknesses
        if candidate == ModelFamily.EMPIRICAL_BASELINE:
            strengths.extend(["No training needed", "No overfitting risk"])
            weaknesses.append("No personalization")
        elif candidate == ModelFamily.MARKOV_UNINFORMED:
            strengths.extend(["Interpretable transitions", "No features needed"])
            weaknesses.append("Assumes stationarity")
        elif candidate == ModelFamily.HIST_GRADIENT_BOOSTING:
            strengths.extend(["Handles categoricals natively", "Good defaults"])
            weaknesses.append("Black box nature")
        elif candidate == ModelFamily.ENSEMBLE:
            strengths.extend(["Robust predictions", "Worst-case protection"])
            weaknesses.extend(["Complex architecture", "Slower inference"])
        elif candidate == ModelFamily.BAYESIAN_HIERARCHICAL:
            strengths.extend(["Uncertainty quantification", "90% credible intervals"])
            weaknesses.extend(["Computationally intensive", "Complex implementation"])
        
        return strengths, weaknesses
    
    def _get_requirements(self, candidate: ModelFamily, context: PredictionContext) -> Dict[str, Any]:
        """Get requirements for model implementation."""
        capability = self.model_capabilities[candidate]
        requirements = {}
        
        # Feature requirements
        if capability.requires_features:
            requirements["features"] = context.available_features
            requirements["feature_types"] = context.feature_types
        else:
            requirements["features"] = []
        
        # Data requirements
        requirements["sample_size"] = {
            "minimal": 100,
            "moderate": 1000,
            "extensive": 10000
        }[capability.data_requirements]
        
        # Training requirements
        if candidate != ModelFamily.EMPIRICAL_BASELINE:
            requirements["training_needed"] = True
            requirements["validation_needed"] = True
        else:
            requirements["training_needed"] = False
            requirements["validation_needed"] = False
        
        # Computational requirements
        requirements["speed_class"] = capability.speed
        requirements["interpretability"] = capability.interpretability
        
        # Special requirements
        if candidate == ModelFamily.MARKOV_UNINFORMED:
            requirements["run_expectancy_matrix"] = True
        elif candidate == ModelFamily.MARKOV_INFORMED:
            requirements["run_expectancy_matrix"] = True
            requirements["feature_bins"] = True
        elif candidate == ModelFamily.BAYESIAN_HIERARCHICAL:
            requirements["mcmc_sampling"] = True
            requirements["prior_specification"] = True
        elif candidate == ModelFamily.ENSEMBLE:
            requirements["multiple_models"] = True
            requirements["ensemble_method"] = "weighted_average"
        
        return requirements
    
    def get_all_recommendations(self, context: PredictionContext) -> List[ModelRecommendation]:
        """Get all viable model recommendations ranked by score."""
        # Get candidate models for prediction type
        candidates = self.prediction_mappings.get(context.prediction_type, [])
        
        # Filter and score all candidates
        recommendations = []
        for candidate in candidates:
            capability = self.model_capabilities[candidate]
            
            # Basic filtering
            if capability.requires_features and not context.available_features:
                continue
            if not context.ensemble_allowed and candidate == ModelFamily.ENSEMBLE:
                continue
            
            score = self._score_candidate(candidate, context)
            if score > 0.1:  # Only include reasonable candidates
                reasoning = self._generate_reasoning(candidate, context, score)
                strengths, weaknesses = self._get_strengths_weaknesses(candidate)
                requirements = self._get_requirements(candidate, context)
                
                recommendations.append(ModelRecommendation(
                    model_family=candidate,
                    confidence_score=score,
                    reasoning=reasoning,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    requirements=requirements,
                    alternatives=[]
                ))
        
        # Sort by score
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Add alternatives
        for i, rec in enumerate(recommendations):
            rec.alternatives = [r.model_family for r in recommendations[i+1:i+3]]
        
        return recommendations


# Convenience functions
def select_model_for_pa_outcome(
    available_features: List[str],
    feature_types: Dict[str, str],
    sample_size: int,
    latency_requirement_ms: Optional[int] = None,
    real_time: bool = False
) -> ModelRecommendation:
    """Convenience function for PA outcome prediction."""
    context = PredictionContext(
        prediction_type=PredictionType.PA_OUTCOME,
        available_features=available_features,
        feature_types=feature_types,
        sample_size=sample_size,
        latency_requirement_ms=latency_requirement_ms,
        real_time_prediction=real_time
    )
    
    selector = ModelSelector()
    return selector.recommend_model(context)


def select_model_for_win_probability(
    available_features: List[str],
    feature_types: Dict[str, str],
    sample_size: int,
    ensemble_allowed: bool = True
) -> ModelRecommendation:
    """Convenience function for win probability prediction."""
    context = PredictionContext(
        prediction_type=PredictionType.WIN_PROBABILITY,
        available_features=available_features,
        feature_types=feature_types,
        sample_size=sample_size,
        ensemble_allowed=ensemble_allowed
    )
    
    selector = ModelSelector()
    return selector.recommend_model(context)


def select_model_for_strikeout_rate(
    available_features: List[str],
    feature_types: Dict[str, str],
    sample_size: int,
    interpretability: Optional[str] = None
) -> ModelRecommendation:
    """Convenience function for strikeout rate prediction."""
    context = PredictionContext(
        prediction_type=PredictionType.STRIKEOUT_RATE,
        available_features=available_features,
        feature_types=feature_types,
        sample_size=sample_size,
        interpretability_requirement=interpretability
    )
    
    selector = ModelSelector()
    return selector.recommend_model(context)

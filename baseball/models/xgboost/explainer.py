"""
Model Explainer for XGBoost Models

Provides model explanation capabilities using SHAP values
and feature importance analysis for interpretability.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any
import json

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class ModelExplainer:
    """
    Model explainer for XGBoost models using SHAP values.
    
    Provides feature importance, contribution analysis, and
    prediction explanations for model interpretability.
    """
    
    def __init__(self, use_shap: bool = True):
        self.use_shap = use_shap and SHAP_AVAILABLE
        self.explainer = None
        self.feature_names = []
        self.feature_importance = {}
        
    def explain(self, model, X: pd.DataFrame, feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Explain model predictions.
        
        Args:
            model: Trained XGBoost model
            X: Feature data to explain
            feature_names: List of feature names
            
        Returns:
            Dictionary with explanation results
        """
        self.feature_names = feature_names or list(X.columns)
        
        explanation = {
            'feature_importance': self._get_feature_importance(model),
            'prediction_explanation': None,
            'summary_plots': None,
            'top_features': self._get_top_features(model)
        }
        
        if self.use_shap:
            try:
                explanation['prediction_explanation'] = self._explain_predictions(model, X)
                explanation['summary_plots'] = self._create_summary_plots(model, X)
            except Exception as e:
                explanation['shap_error'] = str(e)
        
        return explanation
    
    def _get_feature_importance(self, model) -> Dict[str, float]:
        """Get feature importance from model"""
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            
            if len(importance) == len(self.feature_names):
                self.feature_importance = dict(zip(self.feature_names, importance))
                return self.feature_importance
        
        return {}
    
    def _get_top_features(self, model, n: int = 10) -> List[Dict[str, Union[str, float]]]:
        """Get top n most important features"""
        importance = self._get_feature_importance(model)
        
        if not importance:
            return []
        
        sorted_features = sorted(
            importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {'feature': name, 'importance': float(score)}
            for name, score in sorted_features[:n]
        ]
    
    def _explain_predictions(self, model, X: pd.DataFrame) -> Dict[str, Any]:
        """Explain individual predictions using SHAP"""
        if not self.use_shap:
            return {'error': 'SHAP not available'}
        
        try:
            # Create SHAP explainer
            self.explainer = shap.TreeExplainer(model)
            
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(X)
            
            # For multi-class models, get values for first class
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            # Create explanation for each prediction
            explanations = []
            
            for i in range(len(X)):
                pred_explanation = self._create_prediction_explanation(
                    shap_values[i], X.iloc[i], i
                )
                explanations.append(pred_explanation)
            
            return {
                'shap_values': shap_values.tolist(),
                'predictions': explanations,
                'base_value': float(self.explainer.expected_value) if hasattr(self.explainer, 'expected_value') else None
            }
            
        except Exception as e:
            return {'error': f'SHAP explanation failed: {str(e)}'}
    
    def _create_prediction_explanation(self, shap_values: np.ndarray, features: pd.Series, index: int) -> Dict[str, Any]:
        """Create explanation for a single prediction"""
        # Get top positive and negative contributors
        feature_contributions = []
        
        for i, (feature_name, value) in enumerate(zip(self.feature_names, features)):
            contribution = {
                'feature': feature_name,
                'value': float(value),
                'contribution': float(shap_values[i]),
                'abs_contribution': abs(float(shap_values[i]))
            }
            feature_contributions.append(contribution)
        
        # Sort by absolute contribution
        feature_contributions.sort(key=lambda x: x['abs_contribution'], reverse=True)
        
        # Separate positive and negative contributors
        positive_contributors = [f for f in feature_contributions if f['contribution'] > 0][:5]
        negative_contributors = [f for f in feature_contributions if f['contribution'] < 0][:5]
        
        return {
            'prediction_index': index,
            'total_shap_value': float(np.sum(shap_values)),
            'positive_contributors': positive_contributors,
            'negative_contributors': negative_contributors,
            'top_features': feature_contributors[:10]
        }
    
    def _create_summary_plots(self, model, X: pd.DataFrame) -> Dict[str, Any]:
        """Create summary plot data for SHAP values"""
        if not self.use_shap:
            return {'error': 'SHAP not available'}
        
        try:
            if self.explainer is None:
                self.explainer = shap.TreeExplainer(model)
            
            shap_values = self.explainer.shap_values(X)
            
            # For multi-class models, get values for first class
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            # Create summary data
            summary_data = []
            
            for i, feature_name in enumerate(self.feature_names):
                feature_shap = shap_values[:, i]
                feature_values = X.iloc[:, i].values
                
                summary_data.append({
                    'feature': feature_name,
                    'mean_shap_value': float(np.mean(feature_shap)),
                    'std_shap_value': float(np.std(feature_shap)),
                    'feature_values': feature_values.tolist(),
                    'shap_values': feature_shap.tolist()
                })
            
            # Sort by mean absolute SHAP value
            summary_data.sort(key=lambda x: abs(x['mean_shap_value']), reverse=True)
            
            return {
                'summary_data': summary_data,
                'feature_importance_by_shap': [
                    {'feature': d['feature'], 'importance': abs(d['mean_shap_value'])}
                    for d in summary_data
                ]
            }
            
        except Exception as e:
            return {'error': f'Summary plot creation failed: {str(e)}'}
    
    def explain_single_prediction(self, model, features: Dict[str, Union[int, float]], 
                                 feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Explain a single prediction.
        
        Args:
            model: Trained XGBoost model
            features: Feature values for prediction
            feature_names: List of feature names
            
        Returns:
            Dictionary with explanation for single prediction
        """
        if feature_names is None:
            feature_names = list(features.keys())
        
        # Convert to DataFrame
        X = pd.DataFrame([features])
        
        # Get prediction
        prediction = model.predict_proba(X)[0] if hasattr(model, 'predict_proba') else model.predict(X)[0]
        
        # Get SHAP explanation
        explanation = self.explain(model, X, feature_names)
        
        # Add prediction information
        explanation['prediction'] = {
            'predicted_class': int(np.argmax(prediction)) if hasattr(prediction, '__len__') else int(prediction),
            'prediction_probabilities': prediction.tolist() if hasattr(prediction, '__len__') else [float(prediction)]
        }
        
        return explanation
    
    def get_feature_interactions(self, model, X: pd.DataFrame) -> Dict[str, Any]:
        """Get feature interaction analysis"""
        if not self.use_shap:
            return {'error': 'SHAP not available'}
        
        try:
            if self.explainer is None:
                self.explainer = shap.TreeExplainer(model)
            
            # Calculate SHAP interaction values
            shap_interaction_values = self.explainer.shap_interaction_values(X)
            
            # For multi-class models, get values for first class
            if isinstance(shap_interaction_values, list):
                shap_interaction_values = shap_interaction_values[0]
            
            # Calculate interaction strengths
            interaction_strengths = []
            
            for i in range(len(self.feature_names)):
                for j in range(i + 1, len(self.feature_names)):
                    interaction_strength = np.mean(np.abs(shap_interaction_values[:, i, j]))
                    
                    interaction_strengths.append({
                        'feature1': self.feature_names[i],
                        'feature2': self.feature_names[j],
                        'interaction_strength': float(interaction_strength)
                    })
            
            # Sort by interaction strength
            interaction_strengths.sort(key=lambda x: x['interaction_strength'], reverse=True)
            
            return {
                'top_interactions': interaction_strengths[:20],
                'interaction_matrix': shap_interaction_values.tolist()
            }
            
        except Exception as e:
            return {'error': f'Interaction analysis failed: {str(e)}'}
    
    def create_explanation_report(self, model, X: pd.DataFrame, 
                                 feature_names: Optional[List[str]] = None) -> str:
        """
        Create a comprehensive explanation report.
        
        Args:
            model: Trained XGBoost model
            X: Feature data
            feature_names: List of feature names
            
        Returns:
            Formatted explanation report as string
        """
        explanation = self.explain(model, X, feature_names)
        
        report = []
        report.append("# Model Explanation Report")
        report.append("")
        
        # Feature importance
        report.append("## Feature Importance")
        report.append("")
        if 'top_features' in explanation and explanation['top_features']:
            for i, feature in enumerate(explanation['top_features'][:10]):
                report.append(f"{i+1}. {feature['feature']}: {feature['importance']:.4f}")
        else:
            report.append("No feature importance data available.")
        report.append("")
        
        # SHAP explanations
        if 'prediction_explanation' in explanation and explanation['prediction_explanation']:
            shap_data = explanation['prediction_explanation']
            
            report.append("## SHAP Analysis")
            report.append("")
            
            if 'base_value' in shap_data:
                report.append(f"Base Value: {shap_data['base_value']:.4f}")
                report.append("")
            
            # Example prediction explanation
            if 'predictions' in shap_data and shap_data['predictions']:
                pred_explanation = shap_data['predictions'][0]
                
                report.append("### Example Prediction Explanation")
                report.append("")
                report.append(f"Total SHAP Value: {pred_explanation['total_shap_value']:.4f}")
                report.append("")
                
                report.append("#### Top Positive Contributors:")
                for contributor in pred_explanation['positive_contributors']:
                    report.append(f"- {contributor['feature']}: +{contributor['contribution']:.4f} (value: {contributor['value']:.4f})")
                report.append("")
                
                report.append("#### Top Negative Contributors:")
                for contributor in pred_explanation['negative_contributors']:
                    report.append(f"- {contributor['feature']}: {contributor['contribution']:.4f} (value: {contributor['value']:.4f})")
                report.append("")
        
        # Errors
        if 'shap_error' in explanation:
            report.append("## SHAP Error")
            report.append("")
            report.append(f"SHAP analysis failed: {explanation['shap_error']}")
            report.append("")
        
        return "\n".join(report)
    
    def save_explanation(self, explanation: Dict[str, Any], filepath: str):
        """Save explanation to file"""
        # Convert numpy arrays to lists for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            return obj
        
        # Recursively convert numpy objects
        def recursive_convert(obj):
            if isinstance(obj, dict):
                return {k: recursive_convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [recursive_convert(item) for item in obj]
            else:
                return convert_numpy(obj)
        
        converted_explanation = recursive_convert(explanation)
        
        with open(filepath, 'w') as f:
            json.dump(converted_explanation, f, indent=2)
    
    def load_explanation(self, filepath: str) -> Dict[str, Any]:
        """Load explanation from file"""
        with open(filepath, 'r') as f:
            return json.load(f)

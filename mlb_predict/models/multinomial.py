"""
Multinomial Classification Models for Baseball Outcomes

Implements:
- Multinomial Logistic Regression (baseline)
- Gradient Boosting with softprob (XGBoost/LightGBM)
- Neural Network with embeddings (PyTorch)
- Calibration (Platt scaling, Isotonic regression)

Author: Agent Cascade
Date: April 24, 2026
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import softmax
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder


# ============================================================================
# OUTCOME DEFINITIONS
# ============================================================================

PA_OUTCOMES = [
    'strikeout',
    'walk',
    'single',
    'double',
    'triple',
    'home_run',
    'ball_in_play_out',
    'hit_by_pitch',
    'error',
    'sacrifice',
]

OUTCOME_INDEX = {outcome: i for i, outcome in enumerate(PA_OUTCOMES)}


# ============================================================================
# MULTINOMIAL LOGISTIC REGRESSION
# ============================================================================

class MultinomialLogisticRegression(BaseEstimator, ClassifierMixin):
    """
    Multinomial Logistic Regression for baseball outcomes.
    
    Models:
    P(y = k | X) = exp(β_k · X) / ∑_j exp(β_j · X)
    
    Parameters:
    -----------
    regularization : str
        'l1', 'l2', or 'elasticnet'
    C : float
        Inverse of regularization strength
    max_iter : int
        Maximum iterations for solver
    """
    
    def __init__(
        self,
        regularization: str = 'l2',
        C: float = 1.0,
        max_iter: int = 1000,
        random_state: Optional[int] = None,
    ):
        self.regularization = regularization
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state
        
        self.model_ = None
        self.scaler_ = None
        self.classes_ = None
        self.n_classes_ = None
        self.n_features_ = None
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'MultinomialLogisticRegression':
        """Fit multinomial logistic regression."""
        # Encode labels
        self.label_encoder_ = LabelEncoder()
        y_encoded = self.label_encoder_.fit_transform(y)
        
        self.classes_ = self.label_encoder_.classes_
        self.n_classes_ = len(self.classes_)
        self.n_features_ = X.shape[1]
        
        # Scale features
        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X)
        
        # Fit sklearn multinomial logistic regression
        self.model_ = LogisticRegression(
            multi_class='multinomial',
            solver='lbfgs',
            penalty=self.regularization if self.regularization != 'elasticnet' else 'l2',
            C=self.C,
            max_iter=self.max_iter,
            random_state=self.random_state,
        )
        self.model_.fit(X_scaled, y_encoded)
        
        return self
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        X_scaled = self.scaler_.transform(X)
        return self.model_.predict_proba(X_scaled)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels."""
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]
    
    def get_coefficients(self) -> pd.DataFrame:
        """Get coefficient matrix for interpretation."""
        if self.model_ is None:
            raise ValueError('Model not fitted')
        
        coef = self.model_.coef_
        return pd.DataFrame(
            coef,
            columns=[f'feature_{i}' for i in range(coef.shape[1])],
            index=self.classes_,
        )


# ============================================================================
# GRADIENT BOOSTING WITH SOFT PROBABILITY
# ============================================================================

class MultinomialXGBoost(BaseEstimator, ClassifierMixin):
    """
    XGBoost with softmax output for multinomial classification.
    
    Parameters:
    -----------
    n_estimators : int
    max_depth : int
    learning_rate : float
    subsample : float
    colsample_bytree : float
    """
    
    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
        n_jobs: int = -1,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state
        self.n_jobs = n_jobs
        
        self.model_ = None
        self.scaler_ = None
        self.classes_ = None
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'MultinomialXGBoost':
        """Fit XGBoost with softmax objective."""
        try:
            from xgboost import XGBClassifier
        except ImportError:
            raise ImportError('xgboost required: pip install xgboost')
        
        # Encode labels
        self.label_encoder_ = LabelEncoder()
        y_encoded = self.label_encoder_.fit_transform(y)
        self.classes_ = self.label_encoder_.classes_
        
        # Scale features
        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X)
        
        # Build model with softmax
        self.model_ = XGBClassifier(
            objective='multi:softprob',
            num_class=len(self.classes_),
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            use_label_encoder=False,
            eval_metric='mlogloss',
        )
        
        self.model_.fit(X_scaled, y_encoded)
        return self
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        X_scaled = self.scaler_.transform(X)
        return self.model_.predict_proba(X_scaled)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels."""
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance by outcome class."""
        if self.model_ is None:
            raise ValueError('Model not fitted')
        
        importance = self.model_.feature_importances_
        return pd.DataFrame({
            'feature': [f'feature_{i}' for i in range(len(importance))],
            'importance': importance,
        }).sort_values('importance', ascending=False)


class MultinomialLightGBM(BaseEstimator, ClassifierMixin):
    """LightGBM with softmax output for multinomial classification."""
    
    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
        n_jobs: int = -1,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state
        self.n_jobs = n_jobs
        
        self.model_ = None
        self.scaler_ = None
        self.classes_ = None
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'MultinomialLightGBM':
        """Fit LightGBM with softmax objective."""
        try:
            from lightgbm import LGBMClassifier
        except ImportError:
            raise ImportError('lightgbm required: pip install lightgbm')
        
        # Encode labels
        self.label_encoder_ = LabelEncoder()
        y_encoded = self.label_encoder_.fit_transform(y)
        self.classes_ = self.label_encoder_.classes_
        
        # Scale features
        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X)
        
        # Build model
        self.model_ = LGBMClassifier(
            objective='multiclass',
            num_class=len(self.classes_),
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            verbose=-1,
        )
        
        self.model_.fit(X_scaled, y_encoded)
        return self
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        X_scaled = self.scaler_.transform(X)
        return self.model_.predict_proba(X_scaled)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels."""
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]


# ============================================================================
# PROBABILITY CALIBRATION
# ============================================================================

class PlattScaler:
    """
    Platt Scaling for probability calibration.
    
    Maps raw scores to calibrated probabilities using logistic function:
    p' = 1 / (1 + exp(A * x + B))
    """
    
    def __init__(self):
        self.A_ = None
        self.B_ = None
        
    def fit(self, scores: np.ndarray, y_true: np.ndarray):
        """
        Fit Platt scaling parameters.
        
        Parameters:
        -----------
        scores : array of raw model scores (e.g., logits)
        y_true : array of true binary labels {0, 1}
        """
        # Convert to binary problem (one-vs-rest for multiclass)
        # For now, handle binary case
        y_true = np.array(y_true)
        scores = np.array(scores)
        
        # MLE optimization for Platt scaling
        def neg_log_likelihood(params):
            A, B = params
            p = 1 / (1 + np.exp(A * scores + B))
            # Avoid log(0)
            p = np.clip(p, 1e-15, 1 - 1e-15)
            return -np.sum(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))
        
        # Initial guess
        result = minimize(neg_log_likelihood, [0.0, 0.0], method='BFGS')
        self.A_, self.B_ = result.x
        
    def transform(self, scores: np.ndarray) -> np.ndarray:
        """Apply Platt scaling to raw scores."""
        if self.A_ is None or self.B_ is None:
            raise ValueError('Scaler not fitted')
        return 1 / (1 + np.exp(self.A_ * scores + self.B_))


class MulticlassCalibration:
    """
    Calibration for multiclass probabilities.
    
    Applies calibration separately for each class (one-vs-rest).
    """
    
    def __init__(self, method: str = 'isotonic'):
        """
        Parameters:
        -----------
        method : str
            'isotonic' or 'platt'
        """
        self.method = method
        self.calibrators_ = {}
        
    def fit(self, y_proba: np.ndarray, y_true: np.ndarray):
        """
        Fit calibration for each class.
        
        Parameters:
        -----------
        y_proba : array of shape (n_samples, n_classes)
            Uncalibrated probabilities
        y_true : array of shape (n_samples,)
            True class labels
        """
        n_classes = y_proba.shape[1]
        y_true = np.array(y_true)
        
        for k in range(n_classes):
            # Binary labels for class k
            y_binary = (y_true == k).astype(int)
            
            if self.method == 'isotonic':
                calibrator = IsotonicRegression(out_of_bounds='clip')
                calibrator.fit(y_proba[:, k], y_binary)
            elif self.method == 'platt':
                calibrator = PlattScaler()
                # Use logit of probability as score
                scores = np.log(np.clip(y_proba[:, k], 1e-15, 1 - 1e-15))
                calibrator.fit(scores, y_binary)
            else:
                raise ValueError(f'Unknown method: {self.method}')
            
            self.calibrators_[k] = calibrator
            
    def transform(self, y_proba: np.ndarray) -> np.ndarray:
        """Apply calibration to probabilities."""
        n_samples, n_classes = y_proba.shape
        calibrated = np.zeros_like(y_proba)
        
        for k in range(n_classes):
            calibrator = self.calibrators_[k]
            if self.method == 'isotonic':
                calibrated[:, k] = calibrator.transform(y_proba[:, k])
            elif self.method == 'platt':
                scores = np.log(np.clip(y_proba[:, k], 1e-15, 1 - 1e-15))
                calibrated[:, k] = calibrator.transform(scores)
        
        # Renormalize to sum to 1
        calibrated = calibrated / calibrated.sum(axis=1, keepdims=True)
        return calibrated


# ============================================================================
# NEURAL NETWORK (Simple MLP)
# ============================================================================

class SimpleMLP(BaseEstimator, ClassifierMixin):
    """
    Simple Multi-Layer Perceptron for baseball outcomes.
    
    Architecture:
    - Input layer
    - Hidden layer(s) with ReLU
    - Output layer with Softmax
    """
    
    def __init__(
        self,
        hidden_layers: Tuple[int, ...] = (128, 64),
        dropout: float = 0.3,
        batch_norm: bool = True,
        learning_rate: float = 0.001,
        epochs: int = 100,
        batch_size: int = 256,
        random_state: int = 42,
        verbose: bool = False,
    ):
        self.hidden_layers = hidden_layers
        self.dropout = dropout
        self.batch_norm = batch_norm
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.random_state = random_state
        self.verbose = verbose
        
        self.model_ = None
        self.scaler_ = None
        self.classes_ = None
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'SimpleMLP':
        """Fit neural network."""
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
            from torch.utils.data import DataLoader, TensorDataset
        except ImportError:
            raise ImportError('pytorch required: pip install torch')
        
        # Set random seed
        torch.manual_seed(self.random_state)
        
        # Encode labels
        self.label_encoder_ = LabelEncoder()
        y_encoded = self.label_encoder_.fit_transform(y)
        self.classes_ = self.label_encoder_.classes_
        n_classes = len(self.classes_)
        
        # Scale features
        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X)
        
        # Convert to tensors
        X_tensor = torch.FloatTensor(X_scaled)
        y_tensor = torch.LongTensor(y_encoded)
        
        # Create data loader
        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        # Build model
        layers = []
        in_features = X.shape[1]
        
        for hidden_size in self.hidden_layers:
            layers.append(nn.Linear(in_features, hidden_size))
            if self.batch_norm:
                layers.append(nn.BatchNorm1d(hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(self.dropout))
            in_features = hidden_size
        
        layers.append(nn.Linear(in_features, n_classes))
        
        self.model_ = nn.Sequential(*layers)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model_.parameters(), lr=self.learning_rate)
        
        # Training loop
        self.model_.train()
        for epoch in range(self.epochs):
            total_loss = 0
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                outputs = self.model_(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if self.verbose and (epoch + 1) % 10 == 0:
                print(f'Epoch {epoch+1}/{self.epochs}, Loss: {total_loss/len(loader):.4f}')
        
        return self
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        import torch
        
        X_scaled = self.scaler_.transform(X)
        X_tensor = torch.FloatTensor(X_scaled)
        
        self.model_.eval()
        with torch.no_grad():
            logits = self.model_(X_tensor)
            proba = torch.softmax(logits, dim=1).numpy()
        
        return proba
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels."""
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]


# ============================================================================
# MODEL COMPARISON AND SELECTION
# ============================================================================

@dataclass
class MultinomialMetrics:
    """Metrics for multinomial classification."""
    log_loss: float
    brier_score: float
    accuracy: float
    top2_accuracy: float
    calibration_error: float
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'log_loss': self.log_loss,
            'brier_score': self.brier_score,
            'accuracy': self.accuracy,
            'top2_accuracy': self.top2_accuracy,
            'calibration_error': self.calibration_error,
        }


def compute_multinomial_metrics(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    classes: List[str],
) -> MultinomialMetrics:
    """
    Compute metrics for multinomial classification.
    
    Parameters:
    -----------
    y_true : true class labels
    y_proba : predicted probabilities (n_samples, n_classes)
    classes : list of class names
    
    Returns:
    --------
    MultinomialMetrics
    """
    from sklearn.metrics import log_loss, accuracy_score, top_k_accuracy_score
    
    # Encode y_true
    y_true_encoded = np.array([classes.index(y) for y in y_true])
    
    # Log loss
    ll = log_loss(y_true_encoded, y_proba)
    
    # Brier score (multiclass adaptation)
    # One-hot encode y_true
    y_onehot = np.zeros((len(y_true), len(classes)))
    for i, y in enumerate(y_true_encoded):
        y_onehot[i, y] = 1
    brier = np.mean(np.sum((y_proba - y_onehot) ** 2, axis=1))
    
    # Accuracy
    y_pred = classes[np.argmax(y_proba, axis=1)]
    acc = accuracy_score(y_true, y_pred)
    
    # Top-2 accuracy
    top2_acc = top_k_accuracy_score(y_true_encoded, y_proba, k=2)
    
    # Expected calibration error (ECE)
    ece = compute_expected_calibration_error(y_proba, y_true_encoded)
    
    return MultinomialMetrics(
        log_loss=ll,
        brier_score=brier,
        accuracy=acc,
        top2_accuracy=top2_acc,
        calibration_error=ece,
    )


def compute_expected_calibration_error(
    y_proba: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Expected Calibration Error (ECE).
    
    ECE = ∑ (bin_size / N) * |accuracy_in_bin - avg_confidence_in_bin|
    """
    # Get predicted class and confidence
    y_pred = np.argmax(y_proba, axis=1)
    confidences = np.max(y_proba, axis=1)
    
    # Create bins
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(confidences, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    ece = 0.0
    for bin_idx in range(n_bins):
        mask = bin_indices == bin_idx
        if mask.sum() == 0:
            continue
        
        bin_acc = (y_pred[mask] == y_true[mask]).mean()
        bin_conf = confidences[mask].mean()
        bin_weight = mask.sum() / len(y_true)
        
        ece += bin_weight * abs(bin_acc - bin_conf)
    
    return ece


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def train_multinomial_model(
    model_type: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: Optional[np.ndarray] = None,
    y_val: Optional[np.ndarray] = None,
    calibrate: bool = True,
    **kwargs,
) -> Tuple[Any, Optional[MulticlassCalibration]]:
    """
    Train a multinomial model with optional calibration.
    
    Parameters:
    -----------
    model_type : 'logistic', 'xgboost', 'lightgbm', 'mlp'
    X_train, y_train : training data
    X_val, y_val : validation data for calibration
    calibrate : whether to apply probability calibration
    
    Returns:
    --------
    (model, calibrator) tuple
    """
    # Train model
    if model_type == 'logistic':
        model = MultinomialLogisticRegression(**kwargs)
    elif model_type == 'xgboost':
        model = MultinomialXGBoost(**kwargs)
    elif model_type == 'lightgbm':
        model = MultinomialLightGBM(**kwargs)
    elif model_type == 'mlp':
        model = SimpleMLP(**kwargs)
    else:
        raise ValueError(f'Unknown model type: {model_type}')
    
    print(f'[INFO] Training {model_type} model...')
    model.fit(X_train, y_train)
    
    # Calibrate if validation data provided
    calibrator = None
    if calibrate and X_val is not None and y_val is not None:
        print('[INFO] Calibrating probabilities...')
        y_proba_val = model.predict_proba(X_val)
        calibrator = MulticlassCalibration(method='isotonic')
        calibrator.fit(y_proba_val, y_val)
    
    return model, calibrator


def compare_multinomial_models(
    models: Dict[str, Any],
    X_test: np.ndarray,
    y_test: np.ndarray,
    classes: List[str],
) -> pd.DataFrame:
    """
    Compare multiple multinomial models.
    
    Parameters:
    -----------
    models : dict of {name: model}
    X_test, y_test : test data
    classes : list of class names
    
    Returns:
    --------
    DataFrame with comparison results
    """
    results = []
    
    for name, model in models.items():
        y_proba = model.predict_proba(X_test)
        metrics = compute_multinomial_metrics(y_test, y_proba, classes)
        
        results.append({
            'model': name,
            **metrics.to_dict(),
        })
    
    return pd.DataFrame(results)

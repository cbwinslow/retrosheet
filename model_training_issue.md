## 🎯 Objective
Train the Two-Tier XGBoost baseline model for pitch-level outcomes using the populated features and establish the foundation for the pitch-level prediction system.

## 📋 Task Breakdown
- [x] Two-Tier XGBoost model class implemented (baseball/models/pitch/train_tier1_xgboost.py)
- [x] Model calibration framework completed (baseball/models/pitch/calibration.py)
- [ ] Install required ML dependencies (xgboost, scikit-learn, pandas)
- [ ] Prepare training data from engineered_features table
- [ ] Train Tier-1 XGBoost model (ball/strike/ball_in_play classification)
- [ ] Implement proper data preprocessing and feature engineering
- [ ] Configure XGBoost hyperparameters for optimal performance
- [ ] Train model with cross-validation and early stopping
- [ ] Evaluate model performance and calibration
- [ ] Save trained model artifacts and metadata
- [ ] Create model serving interface for predictions

## 🔧 Technical Requirements
- Use existing model class: baseball.models.pitch.train_tier1_xGBoostModel
- Target: Tier-1 classification {ball, strike, ball_in_play}
- Data source: features_pitch.engineered_features table
- Framework: XGBoost with multi-class classification
- Evaluation: Accuracy, precision, recall, F1-score, calibration metrics
- Target performance: >80% coarse outcome accuracy

## 🎯 Success Criteria
- Two-Tier XGBoost model successfully trained
- Model achieves >80% accuracy on test set
- Proper calibration with ECE < 0.05
- Model artifacts saved and versioned
- Prediction interface functional
- Comprehensive evaluation completed
- Model ready for production deployment

## 🔗 Dependencies
- Engineered features table populated (⏳ issue #173)
- ML dependencies installed (⏳ xgboost, scikit-learn, pandas)
- Base features population completed (✓ issue #172)
- Calibration framework ready (✓)
- Model class implemented (✓)

## 📅 Timeline
Target completion: Within 72 hours

## 🚀 Implementation Strategy
1. Install ML dependencies (xgboost, scikit-learn, pandas)
2. Prepare training data from engineered_features
3. Configure XGBoost model with proper hyperparameters
4. Train model with cross-validation
5. Evaluate performance and calibration
6. Save model artifacts and create serving interface
7. Document model performance and characteristics

## 📊 Model Specifications
- **Model Type**: XGBoost Classifier (multi-class)
- **Target Variable**: outcome_tier1 {ball, strike, ball_in_play}
- **Features**: All engineered features from base_features
- **Training Data**: 20.1M pitch records
- **Validation**: 20% holdout test set
- **Cross-validation**: 5-fold stratified CV
- **Early Stopping**: 50 rounds patience
- **Learning Rate**: 0.1 (tunable)
- **Max Depth**: 6 (tunable)
- **N Estimators**: 1000 (with early stopping)

## 🔍 Data Requirements
- Source: features_pitch.engineered_features table
- Features: All engineered columns (velocity, zone, physics, context)
- Target: outcome_tier1 column
- Quality: Remove null values and outliers
- Split: 80% train, 20% test
- Sampling: Use full dataset for training

## 📈 Evaluation Metrics
- **Primary**: Accuracy (target >80%)
- **Secondary**: Precision, Recall, F1-score per class
- **Calibration**: Expected Calibration Error (ECE < 0.05)
- **Confusion Matrix**: Class-wise performance
- **Feature Importance**: Top predictive features
- **Learning Curves**: Training vs validation performance

## 🚨 Known Issues
- ML dependencies not installed (xgboost, scikit-learn, pandas)
- Environment is externally managed, needs --break-system-packages
- Need to verify data quality before training
- Large dataset (20.1M rows) requires memory optimization

## 🔧 Installation Requirements
```bash
pip install --break-system-packages xgboost scikit-learn pandas
```

## 📁 Model Artifacts
- Trained model file: data/models/pitch_level/tier1_xgboost.joblib
- Feature metadata: data/models/pitch_level/features.json
- Performance metrics: data/models/pitch_level/evaluation.json
- Calibration artifacts: data/models/pitch_level/calibration.pkl
- Model configuration: data/models/pitch_level/config.json

## 🎯 Next Steps After Completion
1. Deploy model to production serving layer
2. Integrate with live prediction pipeline
3. Implement model monitoring and retraining
4. Create Tier-2 model for fine-grained outcomes
5. Build ensemble prediction system

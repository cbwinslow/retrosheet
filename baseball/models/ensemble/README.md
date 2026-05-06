# Ensemble Training System for Baseball Prediction Models

## Overview

This directory contains a flexible, concurrent ensemble training system designed to train multiple model types simultaneously and combine their predictions using various ensemble methods.

## Architecture

### Core Components

1. **EnsembleTrainingManager** (`training_manager.py`)
   - Full-featured ensemble trainer with comprehensive model support
   - Supports XGBoost, HistGradientBoosting, and extensible model types
   - Concurrent training with ThreadPoolExecutor
   - Multiple ensemble methods (voting, averaging, stacking)

2. **SimpleEnsembleTrainer** (`simple_ensemble.py`)
   - Simplified version focused on core functionality
   - Direct database integration
   - Basic voting and probability averaging ensembles

3. **WorkingEnsembleTrainer** (`working_ensemble.py`)
   - Production-ready version with robust error handling
   - Optimized for concurrent training
   - Comprehensive model persistence and evaluation

## Key Features

### Flexible Model Support
- **XGBoost**: Gradient boosting with tree-based learning
- **HistGradientBoosting**: Fast histogram-based gradient boosting
- **Extensible**: Easy to add new model types through trainer interface

### Concurrent Training
- **ThreadPoolExecutor**: Trains multiple models simultaneously
- **Resource Management**: Configurable worker limits
- **Progress Tracking**: Real-time training progress and metrics

### Ensemble Methods
- **Voting Ensemble**: Majority vote across model predictions
- **Probability Averaging**: Average prediction probabilities
- **Adaptive Selection**: Automatically selects best performing models

### Data Pipeline
- **Database Integration**: Direct PostgreSQL connection
- **Feature Engineering**: Automatic categorical/boolean conversion
- **Data Splitting**: Train/validation/test splits with stratification
- **Sampling**: Configurable data sampling for faster training

## Usage Examples

### Basic Ensemble Training
```python
from baseball.models.ensemble import WorkingEnsembleTrainer

trainer = WorkingEnsembleTrainer()
results = trainer.train_ensemble(
    seasons=[2015, 2016, 2017],
    sample_rate=0.1,  # 10% of data
    concurrent=True
)
```

### Custom Model Types
```python
# Add new model type by implementing trainer interface
class CustomModelTrainer(ModelTrainer):
    def train(self, X_train, y_train, X_val, y_val):
        # Custom training logic
        pass
    
    def predict(self, X):
        # Custom prediction logic
        pass

# Register with ensemble manager
trainer.train_ensemble(
    model_types=['xgboost', 'hist_gb', 'custom'],
    target_level='pitch'
)
```

## Model Persistence

### Model Storage
- **Location**: `data/models/ensemble/`
- **Format**: Joblib serialized objects
- **Metadata**: Training metrics, timestamps, hyperparameters

### Model Loading
```python
import joblib
model_data = joblib.load('path/to/model.joblib')
model = model_data['model']
label_encoder = model_data['label_encoder']
metrics = model_data['training_metrics']
```

## Evaluation Metrics

### Individual Model Metrics
- **Accuracy**: Classification accuracy on validation set
- **Log Loss**: Cross-entropy loss
- **Training Time**: Model training duration
- **Feature Importance**: Model-specific feature importance

### Ensemble Metrics
- **Ensemble Accuracy**: Combined model performance
- **Individual Best**: Best single model accuracy
- **Improvement**: Ensemble improvement over best individual
- **Model Count**: Number of successful models in ensemble

## Database Schema

### Pitch-Level Features
```sql
-- Base features from features_pitch.base_features
SELECT 
    release_speed, release_spin_rate, effective_speed,
    release_pos_x, release_pos_y, release_pos_z,
    pfx_x, pfx_z, spin_axis,
    plate_x, plate_z, zone,
    balls, strikes, outs_when_up, inning,
    on_1b, on_2b, on_3b,
    home_score, away_score, bat_score, fld_score,
    stand, p_throws,
    vx0, vy0, vz0,
    ax, ay, az,
    launch_speed, launch_angle, bb_type
FROM features_pitch.base_features bf
WHERE bf.game_year IN (seasons)
```

### Target Classification
```sql
-- Simple 3-class classification
CASE 
    WHEN ef.is_strike THEN 'strike'
    WHEN ef.is_ball_in_play THEN 'ball_in_play'
    ELSE 'ball'
END as target
```

## Configuration

### Training Parameters
- **seasons**: List of seasons to include (default: [2015-2023])
- **sample_rate**: Data sampling rate (default: 1.0)
- **test_size**: Test set proportion (default: 0.2)
- **concurrent**: Enable concurrent training (default: True)
- **model_types**: List of model types to train

### Model Hyperparameters
- **XGBoost**: n_estimators=100, max_depth=6, learning_rate=0.1
- **HistGB**: max_iter=100, max_depth=6, learning_rate=0.1
- **Random State**: 42 for reproducibility

## Performance Considerations

### Concurrent Training Benefits
- **Speed**: 2-4x faster training with multiple models
- **Resource**: Efficient CPU utilization with n_jobs=-1
- **Scalability**: Linear scaling with available cores

### Memory Management
- **Sampling**: Reduce memory usage with sample_rate < 1.0
- **Batching**: Process data in chunks for large datasets
- **Cleanup**: Automatic connection and cursor cleanup

## Error Handling

### Robust Error Recovery
- **Model Failures**: Continue training if individual models fail
- **Database Errors**: Connection retry and graceful degradation
- **Data Issues**: Automatic null handling and type conversion

### Logging
- **Progress**: Real-time training progress updates
- **Metrics**: Detailed performance metrics logging
- **Errors**: Comprehensive error tracking and reporting

## Integration Points

### Model Registry Integration
```python
# Register trained models in model registry
from baseball.models.registry import ModelRegistryEntry

entry = ModelRegistryEntry(
    model_name='pitch_ensemble',
    model_version='1.0.0',
    training_date=datetime.now(),
    hyperparameters=training_params,
    feature_set=feature_names,
    primary_metric=ensemble_accuracy,
    artifact_path=model_path,
    status='active'
)
```

### CLI Integration
```bash
# Train ensemble via CLI
python -m baseball.models.ensemble.working_ensemble \
    --seasons 2015 2016 2017 \
    --sample-rate 0.1 \
    --concurrent
```

## Future Extensions

### Advanced Ensemble Methods
- **Stacking**: Meta-model to combine predictions
- **Dynamic Weighting**: Performance-based model weights
- **Cross-Validation**: K-fold ensemble evaluation

### Multi-Level Support
- **PA-Level**: Plate appearance outcome prediction
- **Game-Level**: Game result prediction
- **Real-Time**: Live prediction serving

### Model Types
- **Neural Networks**: Deep learning models
- **Linear Models**: Logistic regression, SVM
- **Time Series**: Sequential prediction models

## Troubleshooting

### Common Issues
1. **Database Connection**: Check credentials and network
2. **Memory Errors**: Reduce sample_rate or batch size
3. **Import Errors**: Verify all dependencies installed
4. **Training Failures**: Check data quality and feature types

### Performance Tuning
1. **Concurrent Workers**: Adjust based on CPU cores
2. **Model Parameters**: Optimize for specific datasets
3. **Data Sampling**: Balance speed vs. accuracy
4. **Feature Selection**: Remove irrelevant features

## Best Practices

### Development
- **Modular Design**: Separate trainers for each model type
- **Interface Consistency**: Common trainer interface
- **Error Handling**: Graceful failure recovery
- **Testing**: Comprehensive unit and integration tests

### Production
- **Model Versioning**: Track model versions and metrics
- **A/B Testing**: Compare ensemble vs. individual models
- **Monitoring**: Track prediction accuracy and drift
- **Rollback**: Maintain previous model versions

## Dependencies

### Core Requirements
- **scikit-learn**: Machine learning algorithms
- **xgboost**: Gradient boosting library
- **pandas**: Data manipulation
- **numpy**: Numerical computing
- **psycopg2**: PostgreSQL database connector
- **joblib**: Model serialization

### Optional Requirements
- **scipy**: Statistical functions (for ensemble voting)
- **matplotlib**: Visualization and plotting
- **structlog**: Structured logging

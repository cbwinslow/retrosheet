## 🎯 Objective
Install and configure all required machine learning dependencies for the pitch-level modeling pipeline to enable XGBoost model training and calibration.

## 📋 Task Breakdown
- [ ] Install XGBoost library for gradient boosting
- [ ] Install scikit-learn for preprocessing and evaluation
- [ ] Install pandas for data manipulation
- [ ] Install numpy for numerical operations
- [ ] Verify all dependencies are working correctly
- [ ] Test model class imports and functionality
- [ ] Validate calibration framework dependencies
- [ ] Document dependency versions and compatibility

## 🔧 Technical Requirements
- XGBoost: >=2.0.0 for latest features and optimizations
- scikit-learn: >=1.3.0 for preprocessing and evaluation metrics
- pandas: >=2.0.0 for data handling
- numpy: >=1.24.0 for numerical operations
- matplotlib: >=3.6.0 for calibration plots
- seaborn: >=0.12.0 for advanced visualizations

## 🎯 Success Criteria
- All ML dependencies installed successfully
- Model class imports without errors
- Calibration framework loads correctly
- Test model training runs without import errors
- Dependencies are compatible with Python 3.12
- Virtual environment or system packages properly configured

## 🔗 Dependencies
- Python 3.12 environment (✓)
- pip package manager (✓)
- System access for package installation (✓)
- Externally managed environment (⚠️ needs --break-system-packages)

## 📅 Timeline
Target completion: Within 2 hours

## 🚀 Implementation Strategy
1. Install dependencies using --break-system-packages flag
2. Verify each package installation
3. Test model class imports
4. Run basic functionality tests
5. Document installed versions
6. Update requirements.txt if needed

## 📦 Installation Commands
```bash
pip install --break-system-packages xgboost>=2.0.0
pip install --break-system-packages scikit-learn>=1.3.0
pip install --break-system-packages pandas>=2.0.0
pip install --break-system-packages numpy>=1.24.0
pip install --break-system-packages matplotlib>=3.6.0
pip install --break-system-packages seaborn>=0.12.0
```

## 🔍 Verification Steps
```python
# Test imports
import xgboost as xgb
import sklearn
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Test model class
from baseball.models.pitch.train_tier1_xgboost import PitchTier1XGBoostModel
model = PitchTier1XGBoostModel(target_tier='tier1')

# Test calibration
from baseball.models.pitch.calibration import PitchModelCalibrator
print("All dependencies working correctly!")
```

## 🚨 Known Issues
- Environment is externally managed by system
- Need to use --break-system-packages flag
- Potential conflicts with system packages
- May need virtual environment setup for production

## 📋 Alternative Approaches
1. **Virtual Environment**: Create dedicated venv for ML dependencies
2. **Conda**: Use conda environment for scientific packages
3. **Docker**: Containerize ML dependencies
4. **System Packages**: Use apt-get for system-level packages

## 🎯 Recommended Approach
Use --break-system-packages for immediate development, but plan virtual environment for production deployment to avoid conflicts.

## 📁 Files to Update
- requirements.txt (if exists)
- baseball/models/pitch/__init__.py (verify imports)
- Environment documentation
- Setup scripts for new developers

## 🔗 Related Issues
- #175: Train Two-Tier XGBoost Baseline Model (depends on this)
- #173: Complete Engineered Features Population (uses trained model)
- #172: Complete Base Features Population (upstream dependency)

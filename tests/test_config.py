"""
Tests for Pydantic Configuration Schemas

Tests cover:
- ModelConfig validation
- Enum constraint checking
- YAML/JSON serialization
- Default configurations

Author: Agent Cascade
Date: April 24, 2026
"""

import pytest


# Skip tests if pydantic not installed
pytest.importorskip('pydantic', minversion='2.0')

from mlb_predict.config.loader import (
    ConfigManager,
    load_config,
    save_config,
    substitute_env_vars,
)
from mlb_predict.config.schemas import (
    ExperimentConfig,
    FeatureSet,
    LightGBMConfig,
    ModelConfig,
    ModelFamily,
    SplitConfig,
    TargetVariable,
    ValidationStrategy,
    XGBoostConfig,
    get_default_lightgbm_config,
    get_default_xgboost_config,
    get_model_comparison_experiment,
    get_quick_test_config,
)


class TestModelFamily:
    """Test ModelFamily enum."""

    def test_enum_values(self):
        """Test that all expected values exist."""
        assert ModelFamily.XGBOOST.value == 'xgboost'
        assert ModelFamily.LIGHTGBM.value == 'lightgbm'
        assert ModelFamily.CATBOOST.value == 'catboost'
        assert ModelFamily.SKLEARN_GBM.value == 'sklearn_histgradient'
        assert ModelFamily.LOGISTIC.value == 'logistic_regression'
        assert ModelFamily.RANDOM_FOREST.value == 'random_forest'
        assert ModelFamily.CUSTOM.value == 'custom'

    def test_enum_comparison(self):
        """Test enum comparison works."""
        assert ModelFamily('xgboost') == ModelFamily.XGBOOST
        assert ModelFamily.XGBOOST != ModelFamily.LIGHTGBM


class TestTargetVariable:
    """Test TargetVariable enum."""

    def test_enum_values(self):
        """Test that all expected values exist."""
        assert TargetVariable.SWING_DECISION.value == 'swing_decision'
        assert TargetVariable.CONTACT_MADE.value == 'contact_made'
        assert TargetVariable.HIT_OUTCOME.value == 'hit_outcome'
        assert TargetVariable.PA_OUTCOME.value == 'pa_outcome'
        assert TargetVariable.WIN_PROBABILITY.value == 'win_probability'
        assert TargetVariable.RUN_EXPECTANCY.value == 'run_expectancy'


class TestFeatureSet:
    """Test FeatureSet enum."""

    def test_enum_values(self):
        """Test that all expected values exist."""
        assert FeatureSet.BASIC.value == 'basic'
        assert FeatureSet.PHYSICS.value == 'physics'
        assert FeatureSet.CONTEXT.value == 'context'
        assert FeatureSet.ADVANCED.value == 'advanced'
        assert FeatureSet.COMPLETE.value == 'complete'
        assert FeatureSet.CUSTOM.value == 'custom'


class TestValidationStrategy:
    """Test ValidationStrategy enum."""

    def test_enum_values(self):
        """Test that all expected values exist."""
        assert ValidationStrategy.TEMPORAL.value == 'temporal'
        assert ValidationStrategy.RANDOM.value == 'random'
        assert ValidationStrategy.K_FOLD.value == 'k_fold'
        assert ValidationStrategy.GROUP.value == 'group'
        assert ValidationStrategy.STRATIFIED.value == 'stratified'


class TestXGBoostConfig:
    """Test XGBoostConfig validation."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        config = XGBoostConfig()
        assert config.max_depth == 6
        assert config.n_estimators == 200
        assert config.learning_rate == 0.05
        assert config.subsample == 0.8
        assert config.tree_method == 'hist'

    def test_valid_values(self):
        """Test that valid values are accepted."""
        config = XGBoostConfig(
            max_depth=10,
            n_estimators=500,
            learning_rate=0.1,
        )
        assert config.max_depth == 10
        assert config.n_estimators == 500
        assert config.learning_rate == 0.1

    def test_invalid_max_depth(self):
        """Test that invalid max_depth raises error."""
        with pytest.raises(Exception) as exc_info:
            XGBoostConfig(max_depth=25)  # > 20
        assert (
            'max_depth' in str(exc_info.value).lower()
            or 'validation' in str(exc_info.value).lower()
        )

    def test_invalid_learning_rate(self):
        """Test that invalid learning_rate raises error."""
        with pytest.raises(Exception) as exc_info:
            XGBoostConfig(learning_rate=1.5)  # > 1.0
        assert (
            'learning_rate' in str(exc_info.value).lower()
            or 'validation' in str(exc_info.value).lower()
        )

    def test_tree_method_pattern(self):
        """Test that tree_method must be valid."""
        with pytest.raises(Exception):
            XGBoostConfig(tree_method='invalid')


class TestLightGBMConfig:
    """Test LightGBMConfig validation."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        config = LightGBMConfig()
        assert config.num_leaves == 31
        assert config.n_estimators == 200
        assert config.learning_rate == 0.05

    def test_valid_values(self):
        """Test that valid values are accepted."""
        config = LightGBMConfig(
            num_leaves=50,
            n_estimators=300,
            learning_rate=0.1,
        )
        assert config.num_leaves == 50


class TestSplitConfig:
    """Test SplitConfig validation."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        config = SplitConfig()
        assert config.strategy == ValidationStrategy.TEMPORAL
        assert config.train_ratio == 0.7
        assert config.val_ratio == 0.15
        assert config.test_ratio == 0.15

    def test_valid_ratios(self):
        """Test that valid ratios are accepted."""
        config = SplitConfig(
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )
        assert config.train_ratio == 0.6

    def test_invalid_ratios_sum(self):
        """Test that ratios that don't sum to 1.0 raise error."""
        with pytest.raises(Exception) as exc_info:
            SplitConfig(
                train_ratio=0.5,
                val_ratio=0.3,
                test_ratio=0.3,  # Sum = 1.1
            )
        assert '1.0' in str(exc_info.value) or 'sum' in str(exc_info.value).lower()


class TestModelConfig:
    """Test ModelConfig validation and methods."""

    def test_required_fields(self):
        """Test that family and target are required."""
        with pytest.raises(Exception):
            ModelConfig()  # Missing required fields

    def test_valid_config(self):
        """Test creating a valid config."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )
        assert config.family == ModelFamily.XGBOOST
        assert config.target == TargetVariable.SWING_DECISION
        assert config.features == FeatureSet.ADVANCED  # Default

    def test_xgboost_auto_config(self):
        """Test that xgboost config is auto-created."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )
        assert config.xgboost is not None
        assert isinstance(config.xgboost, XGBoostConfig)

    def test_lightgbm_auto_config(self):
        """Test that lightgbm config is auto-created."""
        config = ModelConfig(
            family=ModelFamily.LIGHTGBM,
            target=TargetVariable.SWING_DECISION,
        )
        assert config.lightgbm is not None
        assert isinstance(config.lightgbm, LightGBMConfig)

    def test_custom_features_validation(self):
        """Test that custom features must be provided for CUSTOM feature set."""
        with pytest.raises(Exception) as exc_info:
            ModelConfig(
                family=ModelFamily.XGBOOST,
                target=TargetVariable.SWING_DECISION,
                features=FeatureSet.CUSTOM,
            )
        assert 'custom_features' in str(exc_info.value).lower()

    def test_valid_custom_features(self):
        """Test that CUSTOM feature set works with custom_features provided."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
            features=FeatureSet.CUSTOM,
            custom_features=['pitch_speed', 'spin_rate', 'plate_x'],
        )
        assert config.features == FeatureSet.CUSTOM
        assert len(config.custom_features) == 3

    def test_seasons_validation(self):
        """Test that seasons must be valid."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
            seasons=[2023, 2024, 2025],
        )
        assert len(config.seasons) == 3

    def test_to_yaml_and_back(self, tmp_path):
        """Test saving to YAML and loading back."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
            xgboost=XGBoostConfig(max_depth=8, n_estimators=300),
        )

        yaml_path = tmp_path / 'test_config.yaml'
        config.to_yaml(yaml_path)

        # Check file exists
        assert yaml_path.exists()

        # Load and verify
        loaded = ModelConfig.from_yaml(yaml_path)
        assert loaded.family == ModelFamily.XGBOOST
        assert loaded.target == TargetVariable.SWING_DECISION
        assert loaded.xgboost.max_depth == 8
        assert loaded.xgboost.n_estimators == 300

    def test_to_json_and_back(self, tmp_path):
        """Test saving to JSON and loading back."""
        config = ModelConfig(
            family=ModelFamily.LIGHTGBM,
            target=TargetVariable.CONTACT_MADE,
            lightgbm=LightGBMConfig(num_leaves=50),
        )

        json_path = tmp_path / 'test_config.json'
        config.to_json(json_path)

        # Load and verify
        loaded = ModelConfig.from_json(json_path)
        assert loaded.family == ModelFamily.LIGHTGBM
        assert loaded.lightgbm.num_leaves == 50

    def test_get_model_id_string(self):
        """Test that model ID string is generated."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )
        model_id = config.get_model_id_string()
        assert 'xgboost' in model_id
        assert 'swing_decision' in model_id
        assert len(model_id) > 20  # Should have hash suffix

    def test_to_dict(self):
        """Test converting to dictionary."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )
        data = config.to_dict()
        assert isinstance(data, dict)
        assert data['family'] == 'xgboost'
        assert data['target'] == 'swing_decision'

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'family': 'xgboost',
            'target': 'swing_decision',
            'features': 'advanced',
        }
        config = ModelConfig.from_dict(data)
        assert config.family == ModelFamily.XGBOOST
        assert config.target == TargetVariable.SWING_DECISION


class TestExperimentConfig:
    """Test ExperimentConfig validation."""

    def test_required_name(self):
        """Test that experiment_name is required."""
        with pytest.raises(Exception):
            ExperimentConfig()

    def test_valid_experiment(self):
        """Test creating a valid experiment."""
        exp = ExperimentConfig(experiment_name='test_experiment')
        assert exp.experiment_name == 'test_experiment'
        assert exp.models == []

    def test_add_model(self):
        """Test adding models to experiment."""
        exp = ExperimentConfig(experiment_name='compare_models')

        config1 = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )
        exp.add_model(config1)

        config2 = ModelConfig(
            family=ModelFamily.LIGHTGBM,
            target=TargetVariable.SWING_DECISION,
        )
        exp.add_model(config2)

        assert len(exp.models) == 2

    def test_to_yaml_and_back(self, tmp_path):
        """Test saving experiment to YAML and loading."""
        exp = ExperimentConfig(
            experiment_name='model_comparison',
            description='Compare XGBoost and LightGBM',
        )

        exp.add_model(
            ModelConfig(
                family=ModelFamily.XGBOOST,
                target=TargetVariable.SWING_DECISION,
            ),
        )
        exp.add_model(
            ModelConfig(
                family=ModelFamily.LIGHTGBM,
                target=TargetVariable.SWING_DECISION,
            ),
        )

        yaml_path = tmp_path / 'experiment.yaml'
        exp.to_yaml(yaml_path)

        loaded = ExperimentConfig.from_yaml(yaml_path)
        assert loaded.experiment_name == 'model_comparison'
        assert len(loaded.models) == 2


class TestDefaultConfigs:
    """Test default configuration generators."""

    def test_get_default_xgboost_config(self):
        """Test XGBoost default config."""
        config = get_default_xgboost_config()
        assert config.family == ModelFamily.XGBOOST
        assert config.target == TargetVariable.SWING_DECISION
        assert config.xgboost is not None

    def test_get_default_lightgbm_config(self):
        """Test LightGBM default config."""
        config = get_default_lightgbm_config()
        assert config.family == ModelFamily.LIGHTGBM
        assert config.target == TargetVariable.SWING_DECISION
        assert config.lightgbm is not None

    def test_get_quick_test_config(self):
        """Test quick test config for rapid iteration."""
        config = get_quick_test_config()
        assert config.family == ModelFamily.XGBOOST
        assert config.features == FeatureSet.BASIC
        assert config.xgboost.n_estimators == 50  # Small for speed
        assert config.xgboost.max_depth == 4  # Shallow

    def test_get_model_comparison_experiment(self):
        """Test model comparison experiment generator."""
        exp = get_model_comparison_experiment()
        assert exp.experiment_name.startswith('model_comparison')
        assert len(exp.models) >= 1

    def test_get_hyperparameter_search_experiment(self):
        """Test hyperparameter search experiment generator."""
        exp = get_hyperparameter_search_experiment()
        assert 'search' in exp.experiment_name.lower()
        assert len(exp.models) > 0


class TestConfigLoader:
    """Test configuration loading utilities."""

    def test_save_and_load_yaml(self, tmp_path):
        """Test saving and loading via save_config/load_config."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )

        yaml_path = tmp_path / 'config.yaml'
        save_config(config, yaml_path, 'yaml')

        loaded = load_config(yaml_path, 'model')
        assert loaded.family == ModelFamily.XGBOOST

    def test_save_and_load_json(self, tmp_path):
        """Test saving and loading JSON format."""
        config = ModelConfig(
            family=ModelFamily.LIGHTGBM,
            target=TargetVariable.SWING_DECISION,
        )

        json_path = tmp_path / 'config.json'
        save_config(config, json_path, 'json')

        loaded = load_config(json_path, 'model')
        assert loaded.family == ModelFamily.LIGHTGBM

    def test_load_nonexistent_file(self, tmp_path):
        """Test that loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / 'nonexistent.yaml', 'model')

    def test_load_invalid_format(self, tmp_path):
        """Test that invalid format raises error."""
        bad_path = tmp_path / 'config.txt'
        bad_path.write_text('invalid')

        with pytest.raises(ValueError):
            load_config(bad_path, 'model')


class TestEnvVarSubstitution:
    """Test environment variable substitution."""

    def test_substitute_simple_var(self, monkeypatch):
        """Test simple variable substitution."""
        monkeypatch.setenv('TEST_VAR', 'test_value')
        result = substitute_env_vars('Value is ${TEST_VAR}')
        assert result == 'Value is test_value'

    def test_substitute_with_default(self, monkeypatch):
        """Test substitution with default value."""
        # Don't set the env var
        result = substitute_env_vars('Value is ${MISSING_VAR:default}')
        assert result == 'Value is default'

    def test_substitute_missing_no_default(self, monkeypatch):
        """Test that missing var without default raises error."""
        monkeypatch.delenv('MISSING_VAR', raising=False)
        with pytest.raises(ValueError) as exc_info:
            substitute_env_vars('${MISSING_VAR}')
        assert 'MISSING_VAR' in str(exc_info.value)

    def test_substitute_in_dict(self, monkeypatch):
        """Test substitution in nested dict."""
        monkeypatch.setenv('DB_HOST', 'localhost')
        data = {
            'database': {
                'host': '${DB_HOST}',
                'port': 5432,
            },
            'seasons': [2023, 2024],
        }
        result = substitute_env_vars(data)
        assert result['database']['host'] == 'localhost'
        assert result['database']['port'] == 5432


class TestConfigManager:
    """Test ConfigManager class."""

    def test_initialization(self, tmp_path):
        """Test that ConfigManager creates directories."""
        ConfigManager(tmp_path / 'configs')
        assert (tmp_path / 'configs').exists()
        assert (tmp_path / 'configs' / 'models').exists()
        assert (tmp_path / 'configs' / 'experiments').exists()

    def test_save_and_load_model_config(self, tmp_path):
        """Test saving and loading model config via manager."""
        manager = ConfigManager(tmp_path / 'configs')

        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )

        path = manager.save_model_config(config, 'my_model')
        assert path.exists()

        loaded = manager.load_model_config('my_model')
        assert loaded.family == ModelFamily.XGBOOST

    def test_save_and_load_experiment_config(self, tmp_path):
        """Test saving and loading experiment config via manager."""
        manager = ConfigManager(tmp_path / 'configs')

        exp = ExperimentConfig(experiment_name='test_exp')
        exp.add_model(
            ModelConfig(
                family=ModelFamily.XGBOOST,
                target=TargetVariable.SWING_DECISION,
            ),
        )

        path = manager.save_experiment_config(exp)
        assert path.exists()

        loaded = manager.load_experiment_config('test_exp')
        assert loaded.experiment_name == 'test_exp'

    def test_list_configs(self, tmp_path):
        """Test listing available configs."""
        manager = ConfigManager(tmp_path / 'configs')

        # Initially empty
        assert manager.list_model_configs() == []

        # Add a config
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )
        manager.save_model_config(config, 'model1')

        # Should be listed
        assert 'model1' in manager.list_model_configs()

    def test_get_default_config(self, tmp_path):
        """Test getting default configs."""
        manager = ConfigManager(tmp_path / 'configs')

        xgb_default = manager.get_default_config('xgboost')
        assert xgb_default is not None
        assert xgb_default.family == ModelFamily.XGBOOST

        lgb_default = manager.get_default_config('lightgbm')
        assert lgb_default is not None
        assert lgb_default.family == ModelFamily.LIGHTGBM

        missing = manager.get_default_config('nonexistent')
        assert missing is None


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

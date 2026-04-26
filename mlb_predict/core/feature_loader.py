"""FeatureLoader - Data access layer for ML features.

Phase 2.3: Feature Loader

Loads features from PostgreSQL feature marts for training.
Wraps existing data loading patterns from train_models.py.

Author: Agent Cascade
Date: April 24, 2026
"""

import os
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from mlb_predict.config import ModelConfig


@dataclass
class FeatureSchema:
    """Schema definition for features."""
    numeric_features: list[str]
    categorical_features: list[str]
    target_column: str

    @property
    def all_features(self) -> list[str]:
        """Get all feature columns."""
        return self.numeric_features + self.categorical_features


@dataclass
class DataSplit:
    """Container for train/val/test splits."""
    X_train: pd.DataFrame
    y_train: pd.Series
    X_val: pd.DataFrame | None = None
    y_val: pd.Series | None = None
    X_test: pd.DataFrame | None = None
    y_test: pd.Series | None = None

    @property
    def n_train(self) -> int:
        return len(self.X_train)

    @property
    def n_val(self) -> int:
        return len(self.X_val) if self.X_val is not None else 0

    @property
    def n_test(self) -> int:
        return len(self.X_test) if self.X_test is not None else 0


class FeatureLoader:
    """Load features from PostgreSQL for model training.
    
    Wraps existing feature mart queries and provides:
    - Config-driven feature selection
    - Train/val/test splitting
    - Batch loading for large datasets
    - Feature metadata tracking
    
    Example:
        config = ModelConfig(
            family='xgboost',
            target='swing_decision',
            features='advanced',
            seasons=[2020, 2021, 2022, 2023]
        )
        
        loader = FeatureLoader(config)
        data = loader.load_split(train_through=2022)
        
        # Use in training
        model.fit(data.X_train, data.y_train)
        predictions = model.predict(data.X_val)
    """

    # Feature set definitions mapping to existing feature lists
    FEATURE_SETS = {
        'basic': {
            'numeric': [
                'balls', 'strikes', 'outs_when_up',
                'inning', 'score_diff', 'runners_on',
            ],
            'categorical': [
                'stand', 'p_throws', 'inning_topbot',
            ],
        },
        'physics': {
            'numeric': [
                'balls', 'strikes', 'outs_when_up',
                'inning', 'score_diff', 'runners_on',
                'release_speed', 'release_spin_rate',
                'plate_x', 'plate_z',
            ],
            'categorical': [
                'stand', 'p_throws', 'inning_topbot',
                'pitch_type',
            ],
        },
        'advanced': {
            'numeric': [
                'balls', 'strikes', 'outs_when_up',
                'inning', 'score_diff', 'runners_on',
                'release_speed', 'release_spin_rate',
                'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
                'launch_speed', 'launch_angle',
                'home_score', 'away_score',
            ],
            'categorical': [
                'stand', 'p_throws', 'inning_topbot',
                'pitch_type', 'bb_type',
            ],
        },
        'complete': {
            'numeric': [
                'balls', 'strikes', 'outs_when_up',
                'inning', 'score_diff', 'runners_on',
                'release_speed', 'release_spin_rate',
                'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
                'launch_speed', 'launch_angle',
                'home_score', 'away_score',
                'hit_distance_sc', 'effective_speed',
                'release_extension', 'release_pos_x',
                'release_pos_z',
            ],
            'categorical': [
                'stand', 'p_throws', 'inning_topbot',
                'pitch_type', 'bb_type', 'events',
                'description', 'zone',
            ],
        },
    }

    # Target column mapping
    TARGETS = {
        'swing_decision': 'swing',
        'contact_made': 'contact',
        'hit_outcome': 'hit',
        'pa_outcome': 'events_encoded',
        'win_probability': 'home_win',
        'run_expectancy': 'runs_scored',
    }

    def __init__(self, config: ModelConfig):
        """Initialize feature loader with config.
        
        Args:
            config: ModelConfig with features, target, seasons
        """
        self.config = config
        self._engine = None
        self._feature_schema: FeatureSchema | None = None

    @property
    def engine(self):
        """Lazy-load SQLAlchemy engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self):
        """Create database engine from environment or config."""
        # Use existing connection pattern
        host = os.getenv('PGHOST', 'localhost')
        port = int(os.getenv('PGPORT', 5432))
        dbname = os.getenv('PGDATABASE', 'retrosheet')
        user = os.getenv('PGUSER', 'postgres')
        password = os.getenv('PGPASSWORD', '')

        conn_str = f'postgresql://{user}:{password}@{host}:{port}/{dbname}'
        return create_engine(conn_str)

    def get_feature_schema(self) -> FeatureSchema:
        """Get feature schema for current config.
        
        Returns:
            FeatureSchema with numeric/categorical features
        """
        if self._feature_schema is None:
            # config.features and config.target are already string values
            feature_set = self.FEATURE_SETS.get(
                self.config.features,
                self.FEATURE_SETS['advanced'],
            )

            target = self.TARGETS.get(
                self.config.target,
                'target',
            )

            self._feature_schema = FeatureSchema(
                numeric_features=feature_set['numeric'],
                categorical_features=feature_set['categorical'],
                target_column=target,
            )

        return self._feature_schema

    def load_data(
        self,
        seasons: list[int] | None = None,
        sample_rate: float = 1.0,
        where_clause: str | None = None,
    ) -> pd.DataFrame:
        """Load raw data from feature mart.
        
        Args:
            seasons: List of seasons to load (default: config.seasons)
            sample_rate: Fraction of data to sample (0.0-1.0)
            where_clause: Additional SQL WHERE conditions
            
        Returns:
            DataFrame with features and target
        """
        seasons = seasons or self.config.seasons
        schema = self.get_feature_schema()

        # Build query
        columns = schema.all_features + [schema.target_column, 'season']

        query = f"""
        SELECT {', '.join(columns)}
        FROM features_pitch.training_examples
        WHERE season = ANY(%(seasons)s)
          AND {schema.target_column} IS NOT NULL
        """

        if where_clause:
            query += f' AND {where_clause}'

        if sample_rate < 1.0:
            query += f' AND random() < {sample_rate}'

        query += ' ORDER BY game_date, game_pk, at_bat_number, pitch_number'

        # Execute query
        try:
            df = pd.read_sql(
                text(query),
                self.engine,
                params={'seasons': seasons},
            )

            print(f'[INFO] Loaded {len(df)} rows from seasons {seasons}')
            return df

        except Exception as e:
            print(f'[ERROR] Failed to load data: {e}')
            # Return empty DataFrame with expected columns for testing
            return pd.DataFrame(columns=columns)

    def load_split(
        self,
        train_through: int | None = None,
        val_seasons: list[int] | None = None,
        test_seasons: list[int] | None = None,
        sample_rate: float = 1.0,
    ) -> DataSplit:
        """Load data split into train/val/test.
        
        Args:
            train_through: Last season for training (default: max(seasons)-1)
            val_seasons: Seasons for validation (default: [train_through+1])
            test_seasons: Seasons for testing (default: remaining)
            sample_rate: Fraction of data to sample
            
        Returns:
            DataSplit with X/y for each split
        """
        # Determine splits
        seasons = self.config.seasons

        if train_through is None:
            train_through = max(seasons) - 1

        if val_seasons is None:
            val_seasons = [s for s in seasons if s == train_through + 1]

        if test_seasons is None:
            test_seasons = [s for s in seasons if s > train_through + 1]

        # Load all data
        all_data = self.load_data(seasons=seasons, sample_rate=sample_rate)

        if len(all_data) == 0:
            print('[WARNING] No data loaded, returning empty split')
            return self._create_empty_split()

        schema = self.get_feature_schema()

        # Split by season
        train_data = all_data[all_data['season'] <= train_through]
        val_data = all_data[all_data['season'].isin(val_seasons)] if val_seasons else None
        test_data = all_data[all_data['season'].isin(test_seasons)] if test_seasons else None

        # Create split
        split = DataSplit(
            X_train=train_data[schema.all_features],
            y_train=train_data[schema.target_column],
            X_val=val_data[schema.all_features] if val_data is not None and len(val_data) > 0 else None,
            y_val=val_data[schema.target_column] if val_data is not None and len(val_data) > 0 else None,
            X_test=test_data[schema.all_features] if test_data is not None and len(test_data) > 0 else None,
            y_test=test_data[schema.target_column] if test_data is not None and len(test_data) > 0 else None,
        )

        print(f'[INFO] Split: train={split.n_train}, val={split.n_val}, test={split.n_test}')
        return split

    def load_batch(
        self,
        batch_size: int = 10000,
        seasons: list[int] | None = None,
    ):
        """Generator for batch loading large datasets.
        
        Args:
            batch_size: Number of rows per batch
            seasons: Seasons to load
            
        Yields:
            Batches of (X, y) tuples
        """
        seasons = seasons or self.config.seasons
        schema = self.get_feature_schema()

        query = f"""
        SELECT {', '.join(schema.all_features + [schema.target_column])}
        FROM features_pitch.training_examples
        WHERE season = ANY(%(seasons)s)
          AND {schema.target_column} IS NOT NULL
        ORDER BY game_date, game_pk, at_bat_number, pitch_number
        """

        offset = 0
        while True:
            batch_query = query + f' LIMIT {batch_size} OFFSET {offset}'

            df = pd.read_sql(
                text(batch_query),
                self.engine,
                params={'seasons': seasons},
            )

            if len(df) == 0:
                break

            X = df[schema.all_features]
            y = df[schema.target_column]

            yield X, y
            offset += batch_size

    def _create_empty_split(self) -> DataSplit:
        """Create empty DataSplit for testing."""
        schema = self.get_feature_schema()

        empty_df = pd.DataFrame(columns=schema.all_features)
        empty_series = pd.Series([], name=schema.target_column, dtype='float64')

        return DataSplit(
            X_train=empty_df,
            y_train=empty_series,
        )

    def get_feature_info(self) -> dict[str, Any]:
        """Get information about loaded features.
        
        Returns:
            Dict with feature counts, types, etc.
        """
        schema = self.get_feature_schema()

        return {
            'n_numeric': len(schema.numeric_features),
            'n_categorical': len(schema.categorical_features),
            'n_total': len(schema.all_features),
            'target_column': schema.target_column,
            'target_variable': self.config.target,
            'feature_set': self.config.features,
        }

    def validate_features(self, df: pd.DataFrame) -> list[str]:
        """Validate that DataFrame has all required features.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            List of missing features
        """
        schema = self.get_feature_schema()
        missing = [f for f in schema.all_features if f not in df.columns]

        if missing:
            print(f'[WARNING] Missing features: {missing}')

        return missing


def load_features_for_config(
    config: ModelConfig,
    train_through: int | None = None,
) -> DataSplit:
    """Convenience function to load features for a config.
    
    Args:
        config: ModelConfig with features, target, seasons
        train_through: Last training season
        
    Returns:
        DataSplit ready for training
    """
    loader = FeatureLoader(config)
    return loader.load_split(train_through=train_through)


__all__ = [
    'DataSplit',
    'FeatureLoader',
    'FeatureSchema',
    'load_features_for_config',
]

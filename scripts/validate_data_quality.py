#!/usr/bin/env python3
"""
Data quality validation scripts for the Retrosheet Prediction Warehouse.

This script performs various data quality checks on the warehouse tables:
- Schema validation
- Null rate monitoring
- Value range validation
- Referential integrity checks
- Temporal consistency checks
"""

from __future__ import annotations

import argparse
import json
from typing import Any
from dataclasses import dataclass, asdict

import pandas as pd
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import database_url


@dataclass
class ValidationResult:
    """Data class for validation results."""
    check_name: str
    table_name: str
    check_type: str
    passed: bool
    value: float | int | str
    threshold: float | int | str
    message: str


class DataQualityValidator:
    """Data quality validator for warehouse tables."""
    
    def __init__(self, db_url: str = database_url()):
        self.engine = create_engine(db_url)
        self.results: list[ValidationResult] = []
    
    def run_all_checks(self) -> list[ValidationResult]:
        """Run all data quality checks."""
        self.results = []
        
        # Schema validation
        self.validate_schema('core.games')
        self.validate_schema('core.events')
        self.validate_schema('core.plate_appearances')
        self.validate_schema('features.plate_appearance_advanced_examples')
        
        # Null rate monitoring
        self.check_null_rates('core.games', threshold=0.05)
        self.check_null_rates('core.events', threshold=0.10)
        self.check_null_rates('core.plate_appearances', threshold=0.05)
        self.check_null_rates('features.plate_appearance_advanced_examples', threshold=0.05)
        
        # Value range validation
        self.validate_value_ranges('core.games', {
            'inning': (1, 20),
            'home_score': (0, 50),
            'away_score': (0, 50),
        })
        self.validate_value_ranges('core.events', {
            'inning': (1, 20),
            'outs_before': (0, 3),
            'balls': (0, 4),
            'strikes': (0, 3),
        })
        
        # Referential integrity checks
        self.check_referential_integrity(
            'core.events',
            'game_id',
            'core.games',
            'game_id'
        )
        self.check_referential_integrity(
            'core.plate_appearances',
            'game_id',
            'core.games',
            'game_id'
        )
        
        # Temporal consistency checks
        self.check_temporal_consistency('core.games', 'game_date', 'season')
        
        return self.results
    
    def validate_schema(self, table_name: str) -> None:
        """Validate that table schema matches expected structure."""
        query = text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = '{table_name.split('.')[0]}'
              AND table_name = '{table_name.split('.')[1]}'
            ORDER BY ordinal_position
        """)
        
        df = pd.read_sql(query, self.engine)
        
        # Check for required columns
        required_columns = self._get_required_columns(table_name)
        actual_columns = set(df['column_name'].tolist())
        
        missing_columns = required_columns - actual_columns
        if missing_columns:
            self.results.append(ValidationResult(
                check_name='schema_validation',
                table_name=table_name,
                check_type='schema',
                passed=False,
                value=len(missing_columns),
                threshold=0,
                message=f"Missing columns: {', '.join(missing_columns)}"
            ))
        else:
            self.results.append(ValidationResult(
                check_name='schema_validation',
                table_name=table_name,
                check_type='schema',
                passed=True,
                value=len(actual_columns),
                threshold=len(required_columns),
                message="Schema validation passed"
            ))
    
    def check_null_rates(self, table_name: str, threshold: float = 0.05) -> None:
        """Check null rates for all columns in a table."""
        schema, table = table_name.split('.')
        
        # Get column names first
        columns_query = text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = '{schema}'
              AND table_name = '{table}'
        """)
        
        try:
            columns_df = pd.read_sql(columns_query, self.engine)
            columns = columns_df['column_name'].tolist()
            
            # Check null rate for each column
            for column in columns:
                query = text(f"""
                    SELECT 
                        COUNT(*) FILTER (WHERE {column} IS NULL) * 100.0 / COUNT(*) AS null_rate
                    FROM {table_name}
                """)
                
                df = pd.read_sql(query, self.engine)
                null_rate = df['null_rate'].iloc[0]
                
                passed = null_rate <= threshold
                self.results.append(ValidationResult(
                    check_name='null_rate',
                    table_name=table_name,
                    check_type='null_rate',
                    passed=passed,
                    value=null_rate,
                    threshold=threshold,
                    message=f"Column {column}: {null_rate:.2f}% null rate"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name='null_rate',
                table_name=table_name,
                check_type='null_rate',
                passed=False,
                value=0,
                threshold=threshold,
                message=f"Error checking null rates: {str(e)}"
            ))
    
    def validate_value_ranges(self, table_name: str, ranges: dict[str, tuple[float, float]]) -> None:
        """Validate that numeric columns are within expected ranges."""
        for column, (min_val, max_val) in ranges.items():
            query = text(f"""
                SELECT COUNT(*) FILTER (WHERE {column} < {min_val} OR {column} > {max_val}) AS out_of_range_count,
                       COUNT(*) AS total_count
                FROM {table_name}
            """)
            
            try:
                df = pd.read_sql(query, self.engine)
                out_of_range_count = df['out_of_range_count'].iloc[0]
                total_count = df['total_count'].iloc[0]
                
                if total_count > 0:
                    out_of_range_rate = out_of_range_count / total_count
                    passed = out_of_range_rate == 0
                    
                    self.results.append(ValidationResult(
                        check_name='value_range',
                        table_name=table_name,
                        check_type='value_range',
                        passed=passed,
                        value=out_of_range_count,
                        threshold=0,
                        message=f"Column {column}: {out_of_range_count} out of {total_count} rows out of range [{min_val}, {max_val}]"
                    ))
            except Exception as e:
                self.results.append(ValidationResult(
                    check_name='value_range',
                    table_name=table_name,
                    check_type='value_range',
                    passed=False,
                    value=0,
                    threshold=0,
                    message=f"Error checking value ranges for {column}: {str(e)}"
                ))
    
    def check_referential_integrity(
        self,
        child_table: str,
        child_column: str,
        parent_table: str,
        parent_column: str
    ) -> None:
        """Check referential integrity between two tables."""
        query = text(f"""
            SELECT COUNT(*) AS orphan_count
            FROM {child_table} c
            LEFT JOIN {parent_table} p ON c.{child_column} = p.{parent_column}
            WHERE p.{parent_column} IS NULL
        """)
        
        try:
            df = pd.read_sql(query, self.engine)
            orphan_count = df['orphan_count'].iloc[0]
            
            passed = orphan_count == 0
            self.results.append(ValidationResult(
                check_name='referential_integrity',
                table_name=child_table,
                check_type='referential_integrity',
                passed=passed,
                value=orphan_count,
                threshold=0,
                message=f"{orphan_count} orphaned rows in {child_table}.{child_column} referencing {parent_table}.{parent_column}"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name='referential_integrity',
                table_name=child_table,
                check_type='referential_integrity',
                passed=False,
                value=0,
                threshold=0,
                message=f"Error checking referential integrity: {str(e)}"
            ))
    
    def check_temporal_consistency(self, table_name: str, date_column: str, season_column: str) -> None:
        """Check temporal consistency between date and season columns."""
        query = text(f"""
            SELECT COUNT(*) AS inconsistent_count
            FROM {table_name}
            WHERE EXTRACT(YEAR FROM {date_column})::integer != {season_column}
        """)
        
        try:
            df = pd.read_sql(query, self.engine)
            inconsistent_count = df['inconsistent_count'].iloc[0]
            
            passed = inconsistent_count == 0
            self.results.append(ValidationResult(
                check_name='temporal_consistency',
                table_name=table_name,
                check_type='temporal_consistency',
                passed=passed,
                value=inconsistent_count,
                threshold=0,
                message=f"{inconsistent_count} rows with inconsistent {date_column} and {season_column}"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name='temporal_consistency',
                table_name=table_name,
                check_type='temporal_consistency',
                passed=False,
                value=0,
                threshold=0,
                message=f"Error checking temporal consistency: {str(e)}"
            ))
    
    def _get_required_columns(self, table_name: str) -> set[str]:
        """Get required columns for a table."""
        required_columns = {
            'core.games': {'game_id', 'game_date', 'season', 'home_team_id', 'away_team_id'},
            'core.events': {'event_id', 'game_id', 'inning', 'outs_before', 'start_bases'},
            'core.plate_appearances': {'plate_appearance_id', 'game_id', 'batter_id', 'pitcher_id'},
            'features.plate_appearance_advanced_examples': {'plate_appearance_id', 'feature_season', 'inning', 'outs_before'},
        }
        return required_columns.get(table_name, set())
    
    def print_results(self) -> None:
        """Print validation results to console."""
        print("\n" + "="*80)
        print("DATA QUALITY VALIDATION RESULTS")
        print("="*80)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        
        print(f"\nTotal checks: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print("\n" + "-"*80)
            print("FAILED CHECKS:")
            print("-"*80)
            for result in self.results:
                if not result.passed:
                    print(f"\n{result.table_name} - {result.check_name}")
                    print(f"  Type: {result.check_type}")
                    print(f"  Message: {result.message}")
                    print(f"  Value: {result.value}")
                    print(f"  Threshold: {result.threshold}")
        
        print("\n" + "="*80)
    
    def export_results(self, output_file: str) -> None:
        """Export validation results to JSON file."""
        results_dict = [asdict(r) for r in self.results]
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        print(f"\nResults exported to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Validate data quality in the warehouse')
    parser.add_argument('--output', '-o', help='Output JSON file for results')
    parser.add_argument('--fail-on-error', action='store_true', help='Exit with error if any check fails')
    args = parser.parse_args()
    
    validator = DataQualityValidator()
    validator.run_all_checks()
    validator.print_results()
    
    if args.output:
        validator.export_results(args.output)
    
    if args.fail_on_error and any(not r.passed for r in validator.results):
        exit(1)


if __name__ == '__main__':
    main()

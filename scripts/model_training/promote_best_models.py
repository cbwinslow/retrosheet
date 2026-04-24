#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import psycopg2


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def promote_best_models(args: argparse.Namespace) -> None:
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH candidates AS (
                    SELECT
                        model_id,
                        target_id,
                        model_name,
                        (metrics->'validation'->>'roc_auc')::numeric AS roc_auc,
                        (metrics->'validation'->>'log_loss')::numeric AS log_loss,
                        COALESCE((metrics->'validation'->>'rows')::integer, 0) AS validation_rows,
                        row_number() OVER (
                            PARTITION BY target_id, model_name
                            ORDER BY
                                (metrics->'validation'->>'roc_auc')::numeric DESC,
                                (metrics->'validation'->>'log_loss')::numeric ASC NULLS LAST,
                                model_version DESC
                        ) AS rank
                    FROM models.model_registry
                    WHERE (%(target_prefix)s IS NULL OR target_id LIKE %(target_prefix)s)
                      AND (%(target_id)s IS NULL OR target_id = %(target_id)s)
                      AND COALESCE((metrics->'validation'->>'rows')::integer, 0) >= %(min_validation_rows)s
                      AND metrics->'validation' ? 'roc_auc'
                ),
                winners AS (
                    SELECT model_id, target_id, model_name
                    FROM candidates
                    WHERE rank = 1
                ),
                scoped AS (
                    SELECT registry.model_id
                    FROM models.model_registry registry
                    JOIN (
                        SELECT DISTINCT target_id, model_name
                        FROM winners
                    ) winner_groups
                      ON winner_groups.target_id = registry.target_id
                     AND winner_groups.model_name = registry.model_name
                    WHERE (%(target_prefix)s IS NULL OR registry.target_id LIKE %(target_prefix)s)
                      AND (%(target_id)s IS NULL OR registry.target_id = %(target_id)s)
                )
                UPDATE models.model_registry registry
                SET is_active = registry.model_id IN (SELECT model_id FROM winners)
                WHERE registry.model_id IN (SELECT model_id FROM scoped);
                """,
                {
                    'target_prefix': args.target_prefix,
                    'target_id': args.target_id,
                    'min_validation_rows': args.min_validation_rows,
                },
            )
            cur.execute(
                """
                SELECT
                    target_id,
                    model_name,
                    model_version,
                    feature_spec->>'feature_set' AS feature_set,
                    round(((metrics->'validation'->>'roc_auc')::numeric), 6) AS roc_auc,
                    round(((metrics->'validation'->>'log_loss')::numeric), 6) AS log_loss,
                    (metrics->'validation'->>'rows')::integer AS validation_rows
                FROM models.model_registry
                WHERE is_active
                  AND (%(target_prefix)s IS NULL OR target_id LIKE %(target_prefix)s)
                  AND (%(target_id)s IS NULL OR target_id = %(target_id)s)
                ORDER BY target_id, model_name;
                """,
                {'target_prefix': args.target_prefix, 'target_id': args.target_id},
            )
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()

    for row in rows:
        print(
            'activated '
            f'target={row[0]} model={row[1]} version={row[2]} '
            f'feature_set={row[3]} roc_auc={row[4]} log_loss={row[5]} rows={row[6]}',
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Activate the best registered model per target/model family.',
    )
    parser.add_argument(
        '--target-prefix',
        default=None,
        help="Optional SQL LIKE prefix filter, e.g. 'pa_%%'.",
    )
    parser.add_argument('--target-id', default=None, help='Optional exact target id.')
    parser.add_argument(
        '--min-validation-rows',
        type=int,
        default=1000,
        help='Ignore candidates with fewer validation rows.',
    )
    args = parser.parse_args()
    promote_best_models(args)


if __name__ == '__main__':
    main()

import { apiError, queryJson, queryOne } from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const [overview, leaderboard, sweepCandidates] = await Promise.all([
      queryOne(`
        SELECT
          count(*) AS registered_models,
          count(*) FILTER (WHERE is_active) AS active_models,
          count(*) FILTER (WHERE feature_spec->>'sweep' = 'true') AS sweep_candidates,
          round(max((metrics->'validation'->>'roc_auc')::numeric), 4) AS best_validation_roc_auc,
          max(created_at) AS latest_registered_at
        FROM models.model_registry
        WHERE target_id = 'game_home_win' OR target_id LIKE 'pa_%'
      `),
      queryJson(`
        WITH ranked AS (
          SELECT
            target_id,
            model_name,
            model_family,
            model_version,
            is_active,
            feature_spec->>'feature_set' AS feature_set,
            COALESCE(feature_spec->>'sweep', 'false') AS is_sweep,
            round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
            round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
            (metrics->'validation'->>'rows')::integer AS validation_rows,
            row_number() OVER (
              PARTITION BY target_id
              ORDER BY (metrics->'validation'->>'roc_auc')::numeric DESC NULLS LAST
            ) AS rank
          FROM models.model_registry
          WHERE target_id = 'game_home_win' OR target_id LIKE 'pa_%'
            AND metrics->'validation' ? 'roc_auc'
        )
        SELECT *
        FROM ranked
        WHERE rank <= 5
        ORDER BY target_id, rank
      `),
      queryJson(`
        SELECT
          target_id,
          model_name,
          model_version,
          feature_spec->>'feature_set' AS feature_set,
          round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
          round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
          created_at
        FROM models.model_registry
        WHERE feature_spec->>'sweep' = 'true'
        ORDER BY created_at DESC
        LIMIT 20
      `),
    ])

    return Response.json({ overview, leaderboard, sweep_candidates: sweepCandidates })
  } catch (error) {
    return apiError(error)
  }
}

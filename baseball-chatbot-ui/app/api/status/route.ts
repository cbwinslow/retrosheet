import { apiError, queryJson, queryOne } from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const [summary, activeModels, latestRuns] = await Promise.all([
      queryJson(`
        SELECT object_name, row_count
        FROM (
        SELECT * FROM core.auxiliary_validation_summary
        UNION ALL SELECT * FROM features.feature_mart_validation_summary
        UNION ALL SELECT * FROM features.advanced_feature_mart_validation_summary
        UNION ALL SELECT * FROM features.temporal_production_validation_summary
        UNION ALL SELECT * FROM features.count_state_feature_mart_validation_summary
        ) summary
        ORDER BY object_name
      `),
      queryJson(`
        SELECT
          target_id,
          model_name,
          feature_spec->>'feature_set' AS feature_set,
          round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
          round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
          (metrics->'validation'->>'rows')::integer AS validation_rows,
          created_at
        FROM models.model_registry
        WHERE is_active
        ORDER BY target_id, model_name
      `),
      queryOne(`
        SELECT
          count(*) FILTER (WHERE status = 'completed') AS completed_runs,
          count(*) FILTER (WHERE status <> 'completed') AS incomplete_runs,
          max(finished_at) AS last_finished_at
        FROM raw_retrosheet.ingest_runs
      `),
    ])

    return Response.json({
      generated_at: new Date().toISOString(),
      summary,
      active_models: activeModels,
      ingest: latestRuns,
    })
  } catch (error) {
    return apiError(error)
  }
}

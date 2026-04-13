import { apiError, queryJson, queryOne } from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const [overall, modelMetrics, batterLeaders, pitcherLeaders, targetSummary] =
      await Promise.all([
        queryOne(`
          SELECT
            count(*) AS total_active_models,
            round(avg((metrics->'validation'->>'roc_auc')::numeric), 4) AS avg_roc_auc,
            max((metrics->'validation'->>'roc_auc')::numeric) AS best_roc_auc,
            max(created_at) AS latest_model_created_at
          FROM models.model_registry
          WHERE is_active
        `),
        queryJson(`
          SELECT
            target_id,
            model_name,
            model_family,
            feature_spec->>'feature_set' AS feature_set,
            (metrics->'validation'->>'rows')::integer AS validation_rows,
            round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
            round(((metrics->'validation'->>'accuracy')::numeric), 4) AS accuracy,
            round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
            round(((metrics->'validation'->>'brier_score')::numeric), 4) AS brier_score,
            jsonb_array_length(feature_spec->'numeric_features') + jsonb_array_length(feature_spec->'categorical_features') AS feature_count,
            created_at
          FROM models.model_registry
          WHERE is_active
          ORDER BY target_id, roc_auc DESC
        `),
        queryJson(`
          SELECT
            season,
            player_id,
            player_name,
            plate_appearances,
            hits,
            home_runs,
            batting_average,
            on_base_percentage_proxy,
            slugging_percentage,
            round((COALESCE(on_base_percentage_proxy, 0) + COALESCE(slugging_percentage, 0))::numeric, 4) AS ops_proxy
          FROM features.player_production_season
          WHERE season = 2025
            AND plate_appearances >= 400
          ORDER BY ops_proxy DESC
          LIMIT 15
        `),
        queryJson(`
          SELECT
            season,
            player_id,
            player_name,
            batters_faced,
            strikeouts,
            walks_allowed,
            home_runs_allowed,
            strikeout_rate,
            walk_allowed_rate,
            command_power_score_proxy
          FROM features.pitcher_production_season
          WHERE season = 2025
            AND batters_faced >= 400
          ORDER BY command_power_score_proxy DESC
          LIMIT 15
        `),
        queryJson(`
          SELECT
            target_id,
            count(*) AS active_models,
            round(avg((metrics->'validation'->>'roc_auc')::numeric), 4) AS avg_roc_auc,
            round(max((metrics->'validation'->>'roc_auc')::numeric), 4) AS best_roc_auc
          FROM models.model_registry
          WHERE is_active
          GROUP BY target_id
          ORDER BY target_id
        `),
      ])

    return Response.json({
      generated_at: new Date().toISOString(),
      overall,
      model_metrics: modelMetrics,
      target_summary: targetSummary,
      batter_leaders: batterLeaders,
      pitcher_leaders: pitcherLeaders,
    })
  } catch (error) {
    return apiError(error)
  }
}

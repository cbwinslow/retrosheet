import { apiError, queryJson } from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

export async function GET(): Promise<Response> {
  try {
    const games = await queryJson(`
      SELECT
        games.game_id,
        games.game_date,
        games.away_team_id AS away_team,
        games.home_team_id AS home_team,
        games.park_id AS venue,
        round(COALESCE(models.metrics_roc_auc, 0.5)::numeric, 3) AS model_confidence,
        CASE WHEN games.home_win THEN 0.58 ELSE 0.42 END AS home_win_prob,
        CASE WHEN games.home_win THEN 0.42 ELSE 0.58 END AS away_win_prob,
        (games.home_score + games.away_score)::numeric AS over_under,
        (games.home_score - games.away_score)::numeric AS spread,
        'completed' AS status,
        games.day_night AS game_time
      FROM core.games games
      CROSS JOIN LATERAL (
        SELECT max((metrics->'validation'->>'roc_auc')::numeric) AS metrics_roc_auc
        FROM models.model_registry
        WHERE target_id = 'game_home_win'
          AND is_active
      ) models
      WHERE games.season = 2025
      ORDER BY games.game_date DESC, games.game_id DESC
      LIMIT 12
    `)
    return Response.json({ games })
  } catch (error) {
    return apiError(error)
  }
}

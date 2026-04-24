import {
  apiError,
  executeOne,
  jsonLiteral,
  queryJson,
  queryOne,
  sqlLiteral,
} from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

type ChatRequest = {
  message?: string
}

type Row = Record<string, unknown>

async function logChatInteraction({
  message,
  intent,
  response,
  tools,
  rowCount,
}: {
  message: string
  intent: Record<string, unknown>
  response: string
  tools: string[]
  rowCount: number
}) {
  await executeOne(`
    WITH inserted AS (
      INSERT INTO chat.query_logs (
        user_question,
        parsed_intent,
        response_summary,
        tools_used,
        result_row_count,
        metadata
      )
      VALUES (
        ${sqlLiteral(message)},
        ${jsonLiteral(intent)},
        ${sqlLiteral(response)},
        ${jsonLiteral(tools)},
        ${rowCount},
        ${jsonLiteral({ source: 'web_command_center' })}
      )
      RETURNING query_log_id
    )
    SELECT COALESCE(jsonb_agg(row_to_json(inserted)), '[]'::jsonb)::text
    FROM inserted
  `)
}

export async function POST(request: Request) {
  try {
    const { message = '' } = (await request.json()) as ChatRequest
    const lower = message.toLowerCase()

    if (lower.includes('model') || lower.includes('auc') || lower.includes('performance')) {
      const rows = await queryJson<Row[]>(`
        SELECT
          target_id,
          model_name,
          feature_spec->>'feature_set' AS feature_set,
          round(((metrics->'validation'->>'roc_auc')::numeric), 3) AS roc_auc,
          round(((metrics->'validation'->>'log_loss')::numeric), 3) AS log_loss
        FROM models.model_registry
        WHERE is_active
        ORDER BY roc_auc DESC
        LIMIT 8
      `)
      const response = 'Here are the strongest active model registrations by validation ROC AUC.'
      const tools = ['models.model_registry']
      await logChatInteraction({
        message,
        intent: { name: 'active_models' },
        response,
        tools,
        rowCount: rows.length,
      })
      return Response.json({
        response,
        tools_used: tools,
        table: rows,
      })
    }

    if (lower.includes('left') || lower.includes('inning') || lower.includes('simulate')) {
      const row = await queryOne(`
        SELECT
          count(*) AS historical_half_innings,
          round(avg(runs_scored)::numeric, 3) AS expected_runs,
          round(avg((runs_scored > 0)::integer)::numeric, 3) AS run_probability,
          round(avg(all_left_handed_batters_hit::integer)::numeric, 3) AS all_left_handed_batters_hit_probability
        FROM features.half_inning_outcome_summary
        WHERE season BETWEEN 2021 AND 2025
          AND left_handed_pa > 0
      `)
      const response =
        'Using historical half-innings from 2021-2025 where at least one left-handed batter appeared, here is the scenario baseline.'
      const tools = ['features.half_inning_outcome_summary']
      await logChatInteraction({
        message,
        intent: { name: 'left_handed_half_inning' },
        response,
        tools,
        rowCount: row ? 1 : 0,
      })
      return Response.json({
        response,
        tools_used: tools,
        table: row ? [row] : [],
      })
    }

    if (lower.includes('batter') || lower.includes('hitter') || lower.includes('player')) {
      const rows = await queryJson<Row[]>(`
        SELECT
          player_id,
          player_name,
          plate_appearances,
          hits,
          home_runs,
          batting_average,
          on_base_percentage_proxy,
          slugging_percentage,
          round((COALESCE(on_base_percentage_proxy, 0) + COALESCE(slugging_percentage, 0))::numeric, 3) AS ops_proxy
        FROM features.player_production_season
        WHERE season = 2025
          AND plate_appearances >= 400
        ORDER BY ops_proxy DESC
        LIMIT 10
      `)
      const response = 'Top 2025 hitters by our current OPS proxy.'
      const tools = ['features.player_production_season']
      await logChatInteraction({
        message,
        intent: { name: 'top_hitters' },
        response,
        tools,
        rowCount: rows.length,
      })
      return Response.json({
        response,
        tools_used: tools,
        table: rows,
      })
    }

    const status = await queryOne(`
      SELECT
        (SELECT count(*) FROM core.games) AS games,
        (SELECT count(*) FROM core.plate_appearances) AS plate_appearances,
        (SELECT count(*) FROM features.player_production_season) AS player_seasons,
        (SELECT count(*) FROM models.model_registry WHERE is_active) AS active_models
    `)

    const response =
      'I can inspect model performance, hitter/pitcher production, half-inning scenarios, and warehouse status. Try: “show active models”, “simulate left-handed batters this inning”, or “top hitters”.'
    const tools = ['warehouse_status']
    await logChatInteraction({
      message,
      intent: { name: 'warehouse_status' },
      response,
      tools,
      rowCount: status ? 1 : 0,
    })
    return Response.json({
      response,
      tools_used: tools,
      table: status ? [status] : [],
    })
  } catch (error) {
    return apiError(error)
  }
}

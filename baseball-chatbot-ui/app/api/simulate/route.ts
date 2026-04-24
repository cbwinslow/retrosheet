import {
  apiError,
  executeOne,
  jsonLiteral,
  queryJson,
  queryOne,
  sqlLiteral,
} from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

type SimulationRequest = {
  season?: number
  inning?: number
  is_bottom_inning?: boolean
  batting_team_id?: string
  fielding_team_id?: string
  left_handed_only?: boolean
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as SimulationRequest
    const filters = [
      `season BETWEEN ${Number(body.season || 2021) - 4} AND ${Number(body.season || 2025)}`,
    ]

    if (body.inning) filters.push(`inning = ${Number(body.inning)}`)
    if (typeof body.is_bottom_inning === 'boolean') {
      filters.push(`is_bottom_inning = ${body.is_bottom_inning ? 'true' : 'false'}`)
    }
    if (body.batting_team_id)
      filters.push(`batting_team_id = ${sqlLiteral(body.batting_team_id.toUpperCase())}`)
    if (body.fielding_team_id)
      filters.push(`fielding_team_id = ${sqlLiteral(body.fielding_team_id.toUpperCase())}`)
    if (body.left_handed_only) filters.push(`left_handed_pa > 0`)

    const whereClause = filters.join(' AND ')

    const [summary, runDistribution, recentExamples] = await Promise.all([
      queryOne(`
        SELECT
          count(*) AS historical_half_innings,
          round(avg(runs_scored)::numeric, 4) AS expected_runs,
          round(avg((runs_scored > 0)::integer)::numeric, 4) AS run_probability,
          round(avg(all_left_handed_batters_hit::integer)::numeric, 4) AS all_left_handed_batters_hit_probability,
          round(avg((home_runs > 0)::integer)::numeric, 4) AS home_run_in_half_inning_probability,
          round(avg(hits)::numeric, 4) AS expected_hits,
          round(avg(walks)::numeric, 4) AS expected_walks,
          round(avg(strikeouts)::numeric, 4) AS expected_strikeouts
        FROM features.half_inning_outcome_summary
        WHERE ${whereClause}
      `),
      queryJson(`
        SELECT
          runs_scored,
          count(*) AS half_innings,
          round(count(*)::numeric / sum(count(*)) OVER (), 4) AS probability
        FROM features.half_inning_outcome_summary
        WHERE ${whereClause}
        GROUP BY runs_scored
        ORDER BY runs_scored
      `),
      queryJson(`
        SELECT
          game_id,
          season,
          game_date,
          inning,
          is_bottom_inning,
          batting_team_id,
          fielding_team_id,
          plate_appearances,
          hits,
          walks,
          strikeouts,
          home_runs,
          runs_scored,
          all_left_handed_batters_hit
        FROM features.half_inning_outcome_summary
        WHERE ${whereClause}
        ORDER BY game_date DESC, game_id DESC
        LIMIT 25
      `),
    ])

    const simulationRun = await executeOne(`
      WITH inserted AS (
        INSERT INTO predictions.simulation_runs (
          run_name,
          run_mode,
          filters,
          summary,
          run_distribution,
          sample_size,
          notes
        )
        VALUES (
          ${sqlLiteral(`Historical ${body.season || 2025} inning ${body.inning || 'all'} scenario`)},
          'historical_backtest_distribution',
          ${jsonLiteral(body)},
          ${jsonLiteral(summary)},
          ${jsonLiteral(runDistribution)},
          ${(summary?.historical_half_innings as number | undefined) ?? 'NULL'},
          'Saved from the Next.js Sim Lab.'
        )
        RETURNING simulation_run_id, requested_at, run_name
      )
      SELECT COALESCE(jsonb_agg(row_to_json(inserted)), '[]'::jsonb)::text
      FROM inserted
    `)

    return Response.json({
      filters: body,
      mode: 'historical_backtest_distribution',
      simulation_run: simulationRun,
      summary,
      run_distribution: runDistribution,
      recent_examples: recentExamples,
    })
  } catch (error) {
    return apiError(error)
  }
}

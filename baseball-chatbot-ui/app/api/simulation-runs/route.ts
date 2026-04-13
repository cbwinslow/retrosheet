import { apiError, queryJson } from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const rows = await queryJson(`
      SELECT
        simulation_run_id,
        requested_at,
        run_name,
        run_mode,
        filters,
        historical_half_innings,
        round(expected_runs, 4) AS expected_runs,
        round(run_probability, 4) AS run_probability,
        round(all_left_handed_batters_hit_probability, 4) AS all_left_handed_batters_hit_probability,
        sample_size,
        notes
      FROM predictions.recent_simulation_runs
      LIMIT 25
    `)

    return Response.json({ runs: rows })
  } catch (error) {
    return apiError(error)
  }
}

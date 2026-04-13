import { apiError, runPythonScript } from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

export async function POST(request: Request): Promise<Response> {
  try {
    const body = await request.json()
    const gameId = String(body.game_id || '')
    const plateAppearanceId = Number(body.plate_appearance_id || 0)

    if (!gameId || !plateAppearanceId) {
      return Response.json(
        { error: 'game_id and plate_appearance_id are required' },
        { status: 400 },
      )
    }

    if (body.target_id === 'pa_outcome_distribution') {
      const args = [
        '--game-id',
        gameId,
        '--plate-appearance-id',
        String(plateAppearanceId),
      ]
      if (body.model_name) {
        args.push('--model-name', String(body.model_name))
      }
      if (body.model_version) {
        args.push('--model-version', String(body.model_version))
      }
      if (body.apply_calibration) {
        args.push('--apply-calibration')
      }
      if (body.calibration_report_name) {
        args.push('--calibration-report-name', String(body.calibration_report_name))
      }

      const output = await runPythonScript('predict_pa_outcome_distribution.py', args)
      return Response.json(JSON.parse(output))
    }

    const output = await runPythonScript('predict_plate_appearance.py', [
      '--game-id',
      gameId,
      '--plate-appearance-id',
      String(plateAppearanceId),
      '--targets',
      'pa_batter_hit',
      'pa_batter_walk',
      'pa_batter_strikeout',
    ])
    return Response.json(JSON.parse(output))
  } catch (error) {
    return apiError(error)
  }
}

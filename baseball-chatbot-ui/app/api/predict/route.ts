import { apiError, runPythonScript } from '../_lib/warehouse'
import type { PredictRequest, PredictResponse, PredictErrorResponse } from '../../../lib/types/predict'

export const dynamic = 'force-dynamic'

export async function POST(request: Request): Promise<Response> {
  try {
    const body: PredictRequest = await request.json()
    const gameId = String(body.game_id || '')
    const plateAppearanceId = Number(body.plate_appearance_id || 0)

    // Validate required fields
    if (!gameId || !plateAppearanceId) {
      const error: PredictErrorResponse = {
        error: 'game_id and plate_appearance_id are required',
        code: 'MISSING_REQUIRED_FIELDS',
      }
      return Response.json(error, { status: 400 })
    }

    // Handle pa_outcome_distribution target (multiclass PA outcome)
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

      try {
        const output = await runPythonScript('predict_pa_outcome_distribution.py', args)
        const result: PredictResponse = JSON.parse(output)
        return Response.json(result)
      } catch (error) {
        // Check if error is due to missing PA
        const errorMessage = error instanceof Error ? error.message : String(error)
        if (errorMessage.includes('not found') || errorMessage.includes('Plate appearance not found')) {
          const notFoundError: PredictErrorResponse = {
            error: 'Plate appearance not found',
            details: `game_id: ${gameId}, plate_appearance_id: ${plateAppearanceId}`,
            code: 'PA_NOT_FOUND',
          }
          return Response.json(notFoundError, { status: 404 })
        }
        throw error
      }
    }

    // Handle live PA prediction
    if (body.live_game_pk && body.live_event_id) {
      const args = [
        '--game-pk',
        String(body.live_game_pk),
        '--event-id',
        String(body.live_event_id),
      ]
      if (body.model_name) {
        args.push('--model-name', String(body.model_name))
      }
      if (body.model_version) {
        args.push('--model-version', String(body.model_version))
      }
      // Default to calibrated output, allow override
      const applyCalibration = body.apply_calibration !== undefined ? body.apply_calibration : DEFAULT_APPLY_CALIBRATION
      if (applyCalibration) {
        args.push('--apply-calibration')
      }
      if (body.calibration_report_name) {
        args.push('--calibration-report-name', String(body.calibration_report_name))
      }

      try {
        const output = await runPythonScript('predict_live_pa_outcome_distribution.py', args)
        const result: PredictResponse = JSON.parse(output)
        return Response.json(result)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error)
        if (errorMessage.includes('not found') || errorMessage.includes('Plate appearance not found')) {
          const notFoundError: PredictErrorResponse = {
            error: 'Live plate appearance not found',
            details: `game_pk: ${body.live_game_pk}, event_id: ${body.live_event_id}`,
            code: 'LIVE_PA_NOT_FOUND',
          }
          return Response.json(notFoundError, { status: 404 })
        }
        throw error
      }
    }

    // Legacy binary PA prediction (backward compatibility)
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
    // Handle unsupported target error
    const errorMessage = error instanceof Error ? error.message : String(error)
    if (errorMessage.includes('unsupported') || errorMessage.includes('No registered')) {
      const unsupportedError: PredictErrorResponse = {
        error: 'Unsupported target or model',
        details: errorMessage,
        code: 'UNSUPPORTED_TARGET',
      }
      return Response.json(unsupportedError, { status: 400 })
    }
    return apiError(error)
  }
}

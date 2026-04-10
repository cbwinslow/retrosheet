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

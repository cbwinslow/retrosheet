import { apiError, queryJson, runPythonScript } from '../_lib/warehouse'

export const dynamic = 'force-dynamic'

const commands = {
  status: async () => {
    const rows = await queryJson(`
      SELECT object_name, row_count
      FROM features.temporal_production_validation_summary
      ORDER BY object_name
    `)
    return JSON.stringify(rows, null, 2)
  },
  models: async () => {
    const rows = await queryJson(`
      SELECT target_id, model_name, feature_spec->>'feature_set' AS feature_set,
             round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc
      FROM models.model_registry
      WHERE is_active
      ORDER BY target_id, model_name
    `)
    return JSON.stringify(rows, null, 2)
  },
  'analyze-pa': async () => runPythonScript('analyze_pa_models.py', []),
  'rebuild-help': async () =>
    'Run locally from repo root:\nYEARS=2000-2025 PGDATABASE=retrosheet scripts/rebuild_warehouse.sh',
  'sweep-help': async () =>
    'Example:\npython3 scripts/sweep_hyperparameters.py --target-id pa_batter_hit --feature-set advanced --sample-rate 0.05 --max-candidates 12',
}

export async function POST(request: Request) {
  try {
    const { command } = (await request.json()) as { command?: keyof typeof commands }
    if (!command || !(command in commands)) {
      return Response.json(
        {
          error: 'Command is not allow-listed.',
          allowed: Object.keys(commands),
        },
        { status: 400 },
      )
    }
    const output = await commands[command]()
    return Response.json({ command, output })
  } catch (error) {
    return apiError(error)
  }
}

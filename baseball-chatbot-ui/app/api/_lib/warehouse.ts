import { execFile } from 'node:child_process'
import path from 'node:path'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

export const repoRoot = path.resolve(process.cwd(), '..')

function psqlArgs(sql: string): string[] {
  return [
    '-h',
    process.env.PGHOST || 'localhost',
    '-p',
    process.env.PGPORT || '5432',
    '-d',
    process.env.PGDATABASE || 'retrosheet',
    '-X',
    '-A',
    '-t',
    '-v',
    'ON_ERROR_STOP=1',
    '-c',
    sql,
  ]
}

export async function queryJson<T = unknown>(sql: string): Promise<T> {
  const wrapped = `SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${sql}) result;`
  const { stdout } = await execFileAsync('psql', psqlArgs(wrapped), {
    cwd: repoRoot,
    maxBuffer: 20 * 1024 * 1024,
  })
  const text = stdout.trim() || '[]'
  return JSON.parse(text) as T
}

export async function queryOne<T = Record<string, unknown>>(sql: string): Promise<T | null> {
  const rows = await queryJson<T[]>(sql)
  return rows[0] ?? null
}

export async function runPythonScript(script: string, args: string[]): Promise<string> {
  const safeScript = path.join(repoRoot, 'scripts', script)
  const { stdout, stderr } = await execFileAsync('python3', [safeScript, ...args], {
    cwd: repoRoot,
    maxBuffer: 20 * 1024 * 1024,
  })
  return [stdout.trim(), stderr.trim()].filter(Boolean).join('\n')
}

export function apiError(error: unknown) {
  const message = error instanceof Error ? error.message : 'Unknown API error'
  return Response.json({ error: message }, { status: 500 })
}

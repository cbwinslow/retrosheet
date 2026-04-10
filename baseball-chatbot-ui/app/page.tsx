'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  BarChart3,
  Bot,
  Database,
  FileSpreadsheet,
  MessageSquare,
  Play,
  RefreshCw,
  ShieldCheck,
  TerminalSquare,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type View = 'chat' | 'simulations' | 'models' | 'workbench'

type Row = Record<string, string | number | boolean | null>

type StatusPayload = {
  summary: Row[]
  active_models: Row[]
  ingest: Row | null
}

type AnalyticsPayload = {
  overall: Row | null
  model_metrics: Row[]
  target_summary: Row[]
  batter_leaders: Row[]
  pitcher_leaders: Row[]
}

type BacktestPayload = {
  overview: Row | null
  leaderboard: Row[]
  sweep_candidates: Row[]
}

type SimulationPayload = {
  mode: string
  summary: Row | null
  run_distribution: Row[]
  recent_examples: Row[]
}

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  table?: Row[]
  tools?: string[]
}

function pct(value: unknown) {
  const num = Number(value ?? 0)
  return `${(num * 100).toFixed(1)}%`
}

function numberText(value: unknown) {
  if (value === null || value === undefined) return '...'
  if (typeof value === 'number') return value.toLocaleString()
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toLocaleString() : String(value)
}

function StatCard({
  label,
  value,
  accent,
  caption,
}: {
  label: string
  value: string
  accent: string
  caption: string
}) {
  return (
    <div className="scoreboard rounded-3xl border border-white/10 bg-white/[0.055] p-5">
      <div className="text-xs uppercase tracking-[0.22em] text-chalk/55">{label}</div>
      <div className={`mt-3 text-3xl font-black ${accent}`}>{value}</div>
      <div className="mt-2 text-sm text-chalk/55">{caption}</div>
    </div>
  )
}

function DataTable({ rows, title }: { rows: Row[]; title: string }) {
  const columns = useMemo(() => {
    const first = rows[0]
    return first ? Object.keys(first) : []
  }, [rows])

  const csv = useMemo(() => {
    if (!rows.length) return ''
    const escape = (value: unknown) => `"${String(value ?? '').replace(/"/g, '""')}"`
    return [columns.join(','), ...rows.map((row) => columns.map((column) => escape(row[column])).join(','))].join('\n')
  }, [columns, rows])

  return (
    <section className="rounded-3xl border border-white/10 bg-black/20 p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="h-5 w-5 text-emerald-300" />
          <h3 className="font-display text-xl font-bold text-chalk">{title}</h3>
        </div>
        {rows.length > 0 && (
          <a
            href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`}
            download={`${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.csv`}
            className="rounded-full border border-chalk/15 px-3 py-1 text-xs text-chalk/70 hover:bg-chalk/10"
          >
            Export CSV
          </a>
        )}
      </div>
      <div className="table-scroll max-h-[420px] overflow-auto rounded-2xl border border-white/10">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="sticky top-0 bg-[#10251d] text-xs uppercase tracking-wider text-chalk/55">
            <tr>
              {columns.map((column) => (
                <th key={column} className="whitespace-nowrap border-b border-white/10 px-3 py-2">
                  {column.replaceAll('_', ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-chalk/50">No rows returned yet.</td>
              </tr>
            )}
            {rows.map((row, index) => (
              <tr key={index} className="odd:bg-white/[0.025] hover:bg-clay/10">
                {columns.map((column) => (
                  <td key={column} className="whitespace-nowrap border-b border-white/5 px-3 py-2 text-chalk/80">
                    {numberText(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default function Home() {
  const [view, setView] = useState<View>('chat')
  const [status, setStatus] = useState<StatusPayload | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsPayload | null>(null)
  const [backtests, setBacktests] = useState<BacktestPayload | null>(null)
  const [loading, setLoading] = useState(true)

  async function refresh() {
    setLoading(true)
    const [statusRes, analyticsRes, backtestsRes] = await Promise.all([
      fetch('/api/status'),
      fetch('/api/analytics'),
      fetch('/api/backtests'),
    ])
    setStatus(await statusRes.json())
    setAnalytics(await analyticsRes.json())
    setBacktests(await backtestsRes.json())
    setLoading(false)
  }

  useEffect(() => {
    refresh().catch(() => setLoading(false))
  }, [])

  const activeModels = status?.active_models?.length ?? 0
  const warehouseRows = status?.summary?.reduce((sum, row) => sum + Number(row.row_count ?? 0), 0) ?? 0
  const bestAuc = Number(analytics?.overall?.best_roc_auc ?? 0)

  return (
    <main className="stadium-grid min-h-screen px-4 py-6 text-chalk md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="scoreboard overflow-hidden rounded-[2rem] border border-white/10 bg-[rgba(5,20,15,0.82)]">
          <div className="flex flex-col gap-6 p-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="mb-3 flex items-center gap-3 text-sm uppercase tracking-[0.3em] text-emerald-200/70">
                <ShieldCheck className="h-4 w-4" />
                Retrosheet Prediction Command Center
              </div>
              <h1 className="font-display text-4xl font-black leading-tight md:text-6xl">
                Ask the warehouse.
                <span className="block text-clay">Run the model room.</span>
              </h1>
              <p className="mt-4 max-w-3xl text-base text-chalk/65 md:text-lg">
                Chat over PostgreSQL, inspect active model registrations, run historical scenario simulations,
                export spreadsheet-like tables, and launch safe local workflow commands.
              </p>
            </div>
            <button
              onClick={refresh}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-clay px-5 py-3 font-bold text-white shadow-lg shadow-clay/20 hover:bg-[#cc7040]"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
          <div className="grid gap-3 border-t border-white/10 p-4 md:grid-cols-3">
            <StatCard label="Active Models" value={numberText(activeModels)} accent="text-emerald-300" caption="registered in models.model_registry" />
            <StatCard label="Best ROC AUC" value={bestAuc ? bestAuc.toFixed(3) : '...'} accent="text-amber-200" caption="current active model ceiling" />
            <StatCard label="Warehouse Rows" value={numberText(warehouseRows)} accent="text-sky-200" caption="validation summaries combined" />
          </div>
        </header>

        <nav className="my-6 grid gap-3 md:grid-cols-4">
          {[
            ['chat', MessageSquare, 'Chat Analyst'],
            ['simulations', Play, 'Sim Lab'],
            ['models', BarChart3, 'Models & Backtests'],
            ['workbench', TerminalSquare, 'Workbench'],
          ].map(([id, Icon, label]) => (
            <button
              key={String(id)}
              onClick={() => setView(id as View)}
              className={`rounded-2xl border px-4 py-3 text-left transition ${
                view === id
                  ? 'border-clay bg-clay/20 text-white'
                  : 'border-white/10 bg-white/[0.045] text-chalk/70 hover:bg-white/[0.08]'
              }`}
            >
              <Icon className="mb-2 h-5 w-5" />
              <span className="font-bold">{String(label)}</span>
            </button>
          ))}
        </nav>

        {view === 'chat' && <ChatPanel />}
        {view === 'simulations' && <SimulationPanel />}
        {view === 'models' && <ModelsPanel analytics={analytics} backtests={backtests} />}
        {view === 'workbench' && <WorkbenchPanel status={status} />}
      </div>
    </main>
  )
}

function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'I can query active models, top hitters, warehouse status, and half-inning scenario baselines. Try “show active models” or “simulate left-handed batters this inning.”',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!input.trim()) return
    const userMessage: ChatMessage = { role: 'user', content: input.trim() }
    setMessages((current) => [...current, userMessage])
    setInput('')
    setLoading(true)
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage.content }),
    })
    const result = await response.json()
    setMessages((current) => [
      ...current,
      {
        role: 'assistant',
        content: result.response || result.error || 'No response.',
        table: result.table,
        tools: result.tools_used,
      },
    ])
    setLoading(false)
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <div className="rounded-3xl border border-white/10 bg-black/25 p-5">
        <div className="mb-4 flex items-center gap-3">
          <Bot className="h-6 w-6 text-emerald-300" />
          <div>
            <h2 className="font-display text-2xl font-bold">Chat Analyst</h2>
            <p className="text-sm text-chalk/55">Rule-based local tools today; LLM orchestration plugs in later.</p>
          </div>
        </div>
        <div className="mb-4 h-[520px] overflow-auto rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div key={index} className={message.role === 'user' ? 'ml-auto max-w-2xl' : 'mr-auto max-w-3xl'}>
                <div className={`rounded-2xl p-4 ${message.role === 'user' ? 'bg-clay text-white' : 'bg-white/[0.07] text-chalk/80'}`}>
                  <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
                  {message.tools && <p className="mt-2 text-xs text-emerald-200/75">Tools: {message.tools.join(', ')}</p>}
                </div>
                {message.table && message.table.length > 0 && <div className="mt-3"><DataTable rows={message.table} title="Chat Result" /></div>}
              </div>
            ))}
            {loading && <div className="text-sm text-chalk/55">Thinking through the warehouse...</div>}
          </div>
        </div>
        <form onSubmit={submit} className="flex gap-3">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            className="flex-1 rounded-full border border-white/10 bg-white/[0.06] px-5 py-3 text-chalk outline-none focus:border-clay"
            placeholder="Ask about active models, top hitters, or half-inning scenarios..."
          />
          <button className="rounded-full bg-emerald-600 px-5 py-3 font-bold text-white hover:bg-emerald-500">Ask</button>
        </form>
      </div>
      <div className="space-y-4">
        <DataTable
          title="Prompt Starters"
          rows={[
            { prompt: 'show active models', tool: 'models.model_registry' },
            { prompt: 'top hitters this season', tool: 'player production' },
            { prompt: 'simulate left-handed batters this inning', tool: 'half-inning summary' },
            { prompt: 'warehouse status', tool: 'validation summaries' },
          ]}
        />
        <div className="rounded-3xl border border-white/10 bg-white/[0.045] p-5 text-sm leading-6 text-chalk/65">
          <h3 className="mb-2 font-display text-xl font-bold text-chalk">Interface Approach</h3>
          <p>
            Best path: Next.js cockpit for humans, Python scripts for heavy model work, Postgres views for
            spreadsheet exports, and a safe command workbench instead of a raw shell until auth/PTY isolation exists.
          </p>
        </div>
      </div>
    </section>
  )
}

function SimulationPanel() {
  const [season, setSeason] = useState(2025)
  const [inning, setInning] = useState(1)
  const [half, setHalf] = useState<'top' | 'bottom'>('top')
  const [leftOnly, setLeftOnly] = useState(false)
  const [result, setResult] = useState<SimulationPayload | null>(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    const response = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        season,
        inning,
        is_bottom_inning: half === 'bottom',
        left_handed_only: leftOnly,
      }),
    })
    setResult(await response.json())
    setLoading(false)
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <div className="rounded-3xl border border-white/10 bg-black/25 p-5">
        <h2 className="font-display text-2xl font-bold">Simulation Workflow</h2>
        <p className="mt-2 text-sm text-chalk/55">
          This first workflow is a historical scenario backtest distribution. Monte Carlo model simulation can build on this baseline.
        </p>
        <div className="mt-6 space-y-4">
          <label className="block text-sm text-chalk/65">
            Season endpoint
            <input type="number" value={season} onChange={(event) => setSeason(Number(event.target.value))} className="mt-2 w-full rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3" />
          </label>
          <label className="block text-sm text-chalk/65">
            Inning
            <input type="number" min={1} max={15} value={inning} onChange={(event) => setInning(Number(event.target.value))} className="mt-2 w-full rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3" />
          </label>
          <label className="block text-sm text-chalk/65">
            Half inning
            <select value={half} onChange={(event) => setHalf(event.target.value as 'top' | 'bottom')} className="mt-2 w-full rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3">
              <option value="top">Top</option>
              <option value="bottom">Bottom</option>
            </select>
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm">
            <input type="checkbox" checked={leftOnly} onChange={(event) => setLeftOnly(event.target.checked)} />
            Require at least one left-handed batter in half-inning
          </label>
          <button onClick={run} className="w-full rounded-full bg-clay px-5 py-3 font-bold text-white hover:bg-[#cc7040]">
            {loading ? 'Running...' : 'Run Historical Simulation'}
          </button>
        </div>
      </div>
      <div className="space-y-5">
        {result?.summary && (
          <div className="grid gap-3 md:grid-cols-4">
            <StatCard label="Sample" value={numberText(result.summary.historical_half_innings)} accent="text-sky-200" caption="historical half-innings" />
            <StatCard label="Expected Runs" value={numberText(result.summary.expected_runs)} accent="text-emerald-300" caption="mean runs scored" />
            <StatCard label="Run Chance" value={pct(result.summary.run_probability)} accent="text-amber-200" caption="any run scores" />
            <StatCard label="All LHB Hit" value={pct(result.summary.all_left_handed_batters_hit_probability)} accent="text-clay" caption="scenario probability" />
          </div>
        )}
        {result?.run_distribution && (
          <div className="rounded-3xl border border-white/10 bg-black/25 p-5">
            <h3 className="mb-4 font-display text-xl font-bold">Run Distribution</h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={result.run_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(246,234,214,0.12)" />
                  <XAxis dataKey="runs_scored" stroke="#9fb2aa" />
                  <YAxis stroke="#9fb2aa" />
                  <Tooltip contentStyle={{ background: '#10251d', border: '1px solid rgba(255,255,255,.15)' }} />
                  <Bar dataKey="probability" fill="#b45f32" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
        {result?.recent_examples && <DataTable rows={result.recent_examples} title="Recent Matching Half-Innings" />}
      </div>
    </section>
  )
}

function ModelsPanel({ analytics, backtests }: { analytics: AnalyticsPayload | null; backtests: BacktestPayload | null }) {
  return (
    <section className="space-y-6">
      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="Active Models" value={numberText(analytics?.overall?.total_active_models)} accent="text-emerald-300" caption="production candidates" />
        <StatCard label="Avg ROC AUC" value={numberText(analytics?.overall?.avg_roc_auc)} accent="text-amber-200" caption="across active models" />
        <StatCard label="Registered" value={numberText(backtests?.overview?.registered_models)} accent="text-sky-200" caption="all model versions" />
        <StatCard label="Sweeps" value={numberText(backtests?.overview?.sweep_candidates)} accent="text-clay" caption="grid-search candidates" />
      </div>
      {analytics?.model_metrics && <DataTable rows={analytics.model_metrics} title="Active Model Registry" />}
      {backtests?.leaderboard && <DataTable rows={backtests.leaderboard} title="Backtest Leaderboard" />}
      <div className="grid gap-6 lg:grid-cols-2">
        {analytics?.batter_leaders && <DataTable rows={analytics.batter_leaders} title="2025 Batter Production" />}
        {analytics?.pitcher_leaders && <DataTable rows={analytics.pitcher_leaders} title="2025 Pitcher Production" />}
      </div>
    </section>
  )
}

function WorkbenchPanel({ status }: { status: StatusPayload | null }) {
  const [command, setCommand] = useState('status')
  const [output, setOutput] = useState('')
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    const response = await fetch('/api/terminal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    })
    const result = await response.json()
    setOutput(result.output || result.error || '')
    setLoading(false)
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
      <div className="rounded-3xl border border-white/10 bg-black/25 p-5">
        <div className="mb-4 flex items-center gap-3">
          <TerminalSquare className="h-6 w-6 text-clay" />
          <div>
            <h2 className="font-display text-2xl font-bold">Command Workbench</h2>
            <p className="text-sm text-chalk/55">Safe allow-listed commands, not an unrestricted shell.</p>
          </div>
        </div>
        <select value={command} onChange={(event) => setCommand(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3">
          <option value="status">status</option>
          <option value="models">models</option>
          <option value="analyze-pa">analyze-pa</option>
          <option value="rebuild-help">rebuild-help</option>
          <option value="sweep-help">sweep-help</option>
        </select>
        <button onClick={run} className="mt-4 w-full rounded-full bg-emerald-600 px-5 py-3 font-bold text-white hover:bg-emerald-500">
          {loading ? 'Running...' : 'Run Command'}
        </button>
        <div className="mt-5 rounded-2xl border border-amber-200/20 bg-amber-200/10 p-4 text-sm leading-6 text-amber-100/80">
          A real embedded terminal is doable with `node-pty` + `xterm.js` + websocket auth, but this allow-list is the right first step because it is safer and enough for rebuild/sweep/backtest workflows.
        </div>
      </div>
      <div className="space-y-5">
        <pre className="min-h-[360px] overflow-auto rounded-3xl border border-white/10 bg-[#020805] p-5 font-mono text-sm leading-6 text-emerald-100">
          {output || '$ choose an allow-listed command and run it'}
        </pre>
        {status?.summary && <DataTable rows={status.summary.slice(0, 30)} title="Warehouse Validation Snapshot" />}
      </div>
    </section>
  )
}

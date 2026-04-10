'use client'

import { useState } from 'react'
import { Play, Square, RotateCcw, TrendingUp, Target, Zap, BarChart3 } from 'lucide-react'

interface SimulationParams {
  game_id?: string
  inning: number
  top_bottom: 'top' | 'bottom'
  home_team: string
  away_team: string
  current_score_home: number
  current_score_away: number
  outs: number
  runners_on_base: {
    first: boolean
    second: boolean
    third: boolean
  }
  batter_id?: string
  pitcher_id?: string
  num_simulations: number
}

interface SimulationResult {
  total_runs: number
  run_probability: number
  event_probabilities: {
    out: number
    single: number
    double: number
    triple: number
    home_run: number
    walk: number
    strikeout: number
  }
  detailed_outcomes: Array<{
    runs_scored: number
    probability: number
    most_likely_events: string[]
  }>
}

export function SimulationPlayground() {
  const [params, setParams] = useState<SimulationParams>({
    inning: 1,
    top_bottom: 'top',
    home_team: 'NYY',
    away_team: 'BOS',
    current_score_home: 0,
    current_score_away: 0,
    outs: 0,
    runners_on_base: {
      first: false,
      second: false,
      third: false
    },
    num_simulations: 1000
  })

  const [results, setResults] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runSimulation = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('/api/simulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      })

      if (!response.ok) {
        throw new Error('Simulation failed')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  const resetSimulation = () => {
    setResults(null)
    setError(null)
  }

  const updateRunners = (base: keyof SimulationParams['runners_on_base']) => {
    setParams(prev => ({
      ...prev,
      runners_on_base: {
        ...prev.runners_on_base,
        [base]: !prev.runners_on_base[base]
      }
    }))
  }

  const formatProbability = (prob: number) => `${(prob * 100).toFixed(1)}%`

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Monte Carlo Simulation Playground</h2>
        <p className="text-slate-400">Run probabilistic simulations for half-innings using our ML models</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Simulation Parameters */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <Target className="w-5 h-5" />
            <span>Simulation Parameters</span>
          </h3>

          <div className="space-y-4">
            {/* Game State */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Inning</label>
                <input
                  type="number"
                  min="1"
                  max="9"
                  value={params.inning}
                  onChange={(e) => setParams(prev => ({ ...prev, inning: parseInt(e.target.value) || 1 }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Half</label>
                <select
                  value={params.top_bottom}
                  onChange={(e) => setParams(prev => ({ ...prev, top_bottom: e.target.value as 'top' | 'bottom' }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="top">Top</option>
                  <option value="bottom">Bottom</option>
                </select>
              </div>
            </div>

            {/* Teams */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Home Team</label>
                <input
                  type="text"
                  value={params.home_team}
                  onChange={(e) => setParams(prev => ({ ...prev, home_team: e.target.value.toUpperCase() }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="NYY"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Away Team</label>
                <input
                  type="text"
                  value={params.away_team}
                  onChange={(e) => setParams(prev => ({ ...prev, away_team: e.target.value.toUpperCase() }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="BOS"
                />
              </div>
            </div>

            {/* Score */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Home Score</label>
                <input
                  type="number"
                  min="0"
                  value={params.current_score_home}
                  onChange={(e) => setParams(prev => ({ ...prev, current_score_home: parseInt(e.target.value) || 0 }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Away Score</label>
                <input
                  type="number"
                  min="0"
                  value={params.current_score_away}
                  onChange={(e) => setParams(prev => ({ ...prev, current_score_away: parseInt(e.target.value) || 0 }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Outs */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Outs</label>
              <select
                value={params.outs}
                onChange={(e) => setParams(prev => ({ ...prev, outs: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={0}>0 outs</option>
                <option value={1}>1 out</option>
                <option value={2}>2 outs</option>
              </select>
            </div>

            {/* Runners on Base */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">Runners on Base</label>
              <div className="flex justify-center space-x-8">
                {[
                  { key: 'first', label: '1st' },
                  { key: 'second', label: '2nd' },
                  { key: 'third', label: '3rd' }
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => updateRunners(key as keyof SimulationParams['runners_on_base'])}
                    className={`w-12 h-12 rounded-full border-2 transition-colors ${
                      params.runners_on_base[key as keyof SimulationParams['runners_on_base']]
                        ? 'bg-blue-600 border-blue-400 text-white'
                        : 'bg-slate-700 border-slate-600 text-slate-400 hover:border-slate-500'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Number of Simulations */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Simulations</label>
              <select
                value={params.num_simulations}
                onChange={(e) => setParams(prev => ({ ...prev, num_simulations: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={100}>100</option>
                <option value={500}>500</option>
                <option value={1000}>1,000</option>
                <option value={5000}>5,000</option>
                <option value={10000}>10,000</option>
              </select>
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-3 pt-4">
              <button
                onClick={runSimulation}
                disabled={loading}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed px-4 py-3 rounded-lg text-white font-medium transition-colors flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Running...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    <span>Run Simulation</span>
                  </>
                )}
              </button>
              <button
                onClick={resetSimulation}
                className="px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-300 hover:text-white transition-colors flex items-center space-x-2"
              >
                <RotateCcw className="w-5 h-5" />
                <span>Reset</span>
              </button>
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <BarChart3 className="w-5 h-5" />
            <span>Simulation Results</span>
          </h3>

          {error && (
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-4">
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {!results && !loading && !error && (
            <div className="text-center py-12">
              <Square className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-slate-400 mb-2">No Results Yet</h4>
              <p className="text-slate-500">Configure your simulation parameters and click "Run Simulation"</p>
            </div>
          )}

          {loading && (
            <div className="text-center py-12">
              <div className="w-12 h-12 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <h4 className="text-lg font-medium text-slate-400 mb-2">Running Simulation</h4>
              <p className="text-slate-500">Analyzing {params.num_simulations.toLocaleString()} scenarios...</p>
            </div>
          )}

          {results && (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-700 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-400 mb-1">
                    {results.total_runs.toFixed(2)}
                  </div>
                  <div className="text-sm text-slate-400">Expected Runs</div>
                </div>
                <div className="bg-slate-700 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-400 mb-1">
                    {formatProbability(results.run_probability)}
                  </div>
                  <div className="text-sm text-slate-400">Run Probability</div>
                </div>
              </div>

              {/* Event Probabilities */}
              <div>
                <h4 className="text-md font-medium text-slate-300 mb-3">Event Probabilities</h4>
                <div className="space-y-2">
                  {Object.entries(results.event_probabilities).map(([event, prob]) => (
                    <div key={event} className="flex items-center justify-between">
                      <span className="text-sm text-slate-400 capitalize">
                        {event.replace('_', ' ')}
                      </span>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${prob * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-white min-w-[4rem] text-right">
                          {formatProbability(prob)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Detailed Outcomes */}
              <div>
                <h4 className="text-md font-medium text-slate-300 mb-3">Possible Outcomes</h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {results.detailed_outcomes.slice(0, 10).map((outcome, index) => (
                    <div key={index} className="flex items-center justify-between bg-slate-700 rounded-lg p-3">
                      <div className="flex items-center space-x-3">
                        <span className="text-sm text-slate-400">
                          {outcome.runs_scored} run{outcome.runs_scored !== 1 ? 's' : ''}
                        </span>
                        <div className="text-xs text-slate-500">
                          {outcome.most_likely_events.slice(0, 2).join(', ')}
                        </div>
                      </div>
                      <span className="text-sm font-medium text-white">
                        {formatProbability(outcome.probability)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
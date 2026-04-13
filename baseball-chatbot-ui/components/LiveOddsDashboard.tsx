'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Clock, Target, Users, MapPin, RefreshCw } from 'lucide-react'

interface GameOdds {
  game_id: string
  home_team: string
  away_team: string
  home_win_prob: number
  away_win_prob: number
  over_under: number
  spread: number
  game_time: string
  status: 'scheduled' | 'in_progress' | 'completed'
  current_score?: {
    home: number
    away: number
    inning: number
    top_bottom: 'top' | 'bottom'
  }
  venue: string
  weather?: {
    temperature: number
    condition: string
  }
}

export function LiveOddsDashboard() {
  const [games, setGames] = useState<GameOdds[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'live' | 'today'>('all')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const fetchLiveOdds = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/live-odds')
      if (!response.ok) throw new Error('Failed to fetch live odds')
      const data = await response.json()
      setGames(data.games || [])
      setLastUpdate(new Date())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load odds')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLiveOdds()

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchLiveOdds, 30000)
    return () => clearInterval(interval)
  }, [])

  const filteredGames = games.filter(game => {
    if (filter === 'live') return game.status === 'in_progress'
    if (filter === 'today') return game.status !== 'completed'
    return true
  })

  const formatProbability = (prob: number) => `${(prob * 100).toFixed(1)}%`
  const formatSpread = (spread: number) => spread > 0 ? `+${spread}` : spread.toString()

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header with controls */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Live Odds Dashboard</h2>
          <p className="text-slate-400">Real-time predictions powered by 18 ML models</p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Filter buttons */}
          <div className="flex bg-slate-800 rounded-lg p-1">
            {[
              { id: 'all', label: 'All Games' },
              { id: 'live', label: 'Live' },
              { id: 'today', label: 'Today' }
            ].map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setFilter(id as typeof filter)}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  filter === id
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Refresh button */}
          <button
            onClick={fetchLiveOdds}
            disabled={loading}
            className="p-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded-lg transition-colors"
            title="Refresh odds"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Last update indicator */}
      {lastUpdate && (
        <div className="text-sm text-slate-500 flex items-center space-x-2">
          <Clock className="w-4 h-4" />
          <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {loading && games.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center space-x-3">
            <RefreshCw className="w-6 h-6 text-blue-400 animate-spin" />
            <span className="text-slate-400">Loading live odds...</span>
          </div>
        </div>
      )}

      {/* Games grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredGames.map((game) => (
          <div
            key={game.game_id}
            className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden hover:border-slate-600 transition-colors"
          >
            {/* Game header */}
            <div className="p-4 bg-gradient-to-r from-blue-600 to-purple-600">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <MapPin className="w-4 h-4 text-blue-100" />
                  <span className="text-sm text-blue-100">{game.venue}</span>
                </div>
                <div className={`px-2 py-1 rounded text-xs font-medium ${
                  game.status === 'in_progress'
                    ? 'bg-green-600 text-white'
                    : game.status === 'completed'
                    ? 'bg-gray-600 text-white'
                    : 'bg-slate-700 text-slate-300'
                }`}>
                  {game.status === 'in_progress' ? 'LIVE' : game.status.toUpperCase()}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="text-center flex-1">
                  <div className="text-white font-bold text-lg">{game.away_team}</div>
                  <div className="text-blue-100 text-sm">vs</div>
                  <div className="text-white font-bold text-lg">{game.home_team}</div>
                </div>
              </div>
            </div>

            {/* Game details */}
            <div className="p-4 space-y-4">
              {/* Current score (if live) */}
              {game.current_score && game.status === 'in_progress' && (
                <div className="bg-slate-700 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-300">Score</span>
                    <span className="text-xs text-slate-400">
                      {game.current_score.top_bottom === 'top' ? '▲' : '▼'} {game.current_score.inning}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{game.current_score.away}</div>
                      <div className="text-xs text-slate-400">{game.away_team}</div>
                    </div>
                    <div className="text-2xl font-bold text-slate-400">-</div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{game.current_score.home}</div>
                      <div className="text-xs text-slate-400">{game.home_team}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Win probabilities */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-300">Win Probability</span>
                  <Users className="w-4 h-4 text-slate-500" />
                </div>

                <div className="space-y-2">
                  {/* Away team */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">{game.away_team}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${game.away_win_prob * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-white min-w-[4rem] text-right">
                        {formatProbability(game.away_win_prob)}
                      </span>
                    </div>
                  </div>

                  {/* Home team */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">{game.home_team}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${game.home_win_prob * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-white min-w-[4rem] text-right">
                        {formatProbability(game.home_win_prob)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Betting lines */}
              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-slate-700">
                <div className="text-center">
                  <div className="text-xs text-slate-500 mb-1">Spread</div>
                  <div className="text-sm font-medium text-white">
                    {formatSpread(game.spread)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-slate-500 mb-1">O/U</div>
                  <div className="text-sm font-medium text-white">
                    {game.over_under.toFixed(1)}
                  </div>
                </div>
              </div>

              {/* Weather (if available) */}
              {game.weather && (
                <div className="flex items-center justify-between pt-3 border-t border-slate-700">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-slate-400">Weather</span>
                  </div>
                  <div className="text-sm text-slate-300">
                    {game.weather.temperature}°F • {game.weather.condition}
                  </div>
                </div>
              )}

              {/* Game time */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-700">
                <span className="text-sm text-slate-400">Start Time</span>
                <span className="text-sm text-white">{game.game_time}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {filteredGames.length === 0 && !loading && (
        <div className="text-center py-12">
          <Target className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-400 mb-2">No games found</h3>
          <p className="text-slate-500">Try changing your filter or check back later for live games.</p>
        </div>
      )}
    </div>
  )
}
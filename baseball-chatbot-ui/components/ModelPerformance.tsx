'use client'

import { Award, BarChart3, RefreshCw, Target, Zap } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

interface ModelMetrics {
  model_name: string
  model_type: string
  accuracy: number
  precision: number
  recall: number
  f1_score: number
  auc_roc?: number
  training_samples: number
  features_used: number
  last_trained: string
}

interface FeatureImportance {
  feature: string
  importance: number
  category: string
}

interface ModelPerformanceData {
  overall_metrics: {
    total_models: number
    average_accuracy: number
    best_performing_model: string
    total_predictions_today: number
  }
  model_metrics: ModelMetrics[]
  feature_importance: FeatureImportance[]
  prediction_targets: Array<{
    target: string
    models_count: number
    average_accuracy: number
  }>
}

export function ModelPerformance() {
  const [data, setData] = useState<ModelPerformanceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)

  const fetchPerformanceData = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/analytics')
      if (!response.ok) throw new Error('Failed to fetch performance data')
      const result = await response.json()
      setData(result)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load performance data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPerformanceData()
  }, [fetchPerformanceData])

  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`
  const formatNumber = (value: number) => value.toLocaleString()

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 0.8) return 'text-green-400'
    if (accuracy >= 0.7) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getModelTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'xgboost':
        return '🌳'
      case 'random_forest':
        return '🌲'
      case 'neural_network':
        return '🧠'
      case 'logistic_regression':
        return '📈'
      default:
        return '🤖'
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Model Performance Dashboard</h2>
          <p className="text-slate-400">
            Performance metrics for our 18 ML models across 9 prediction targets
          </p>
        </div>

        <button
          type="button"
          onClick={fetchPerformanceData}
          disabled={loading}
          className="p-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded-lg transition-colors"
          title="Refresh data"
        >
          <RefreshCw className={`w-5 h-5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center space-x-3">
            <RefreshCw className="w-6 h-6 text-blue-400 animate-spin" />
            <span className="text-slate-400">Loading performance data...</span>
          </div>
        </div>
      )}

      {data && (
        <>
          {/* Overall Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <BarChart3 className="w-8 h-8 text-blue-400" />
                <span className="text-sm text-slate-400">Total Models</span>
              </div>
              <div className="text-3xl font-bold text-white">
                {data.overall_metrics.total_models}
              </div>
              <div className="text-sm text-slate-500 mt-1">18 active models</div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <Target className="w-8 h-8 text-green-400" />
                <span className="text-sm text-slate-400">Avg Accuracy</span>
              </div>
              <div
                className={`text-3xl font-bold ${getAccuracyColor(data.overall_metrics.average_accuracy)}`}
              >
                {formatPercentage(data.overall_metrics.average_accuracy)}
              </div>
              <div className="text-sm text-slate-500 mt-1">Across all targets</div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <Award className="w-8 h-8 text-yellow-400" />
                <span className="text-sm text-slate-400">Best Model</span>
              </div>
              <div className="text-lg font-bold text-white mb-1">
                {data.overall_metrics.best_performing_model}
              </div>
              <div className="text-sm text-slate-500">Highest accuracy</div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <Zap className="w-8 h-8 text-purple-400" />
                <span className="text-sm text-slate-400">Daily Predictions</span>
              </div>
              <div className="text-3xl font-bold text-white">
                {formatNumber(data.overall_metrics.total_predictions_today)}
              </div>
              <div className="text-sm text-slate-500 mt-1">Real-time predictions</div>
            </div>
          </div>

          {/* Prediction Targets Overview */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Prediction Targets</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {data.prediction_targets.map((target) => (
                <div key={target.target} className="bg-slate-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-300">{target.target}</span>
                    <span className="text-xs text-slate-500">{target.models_count} models</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 bg-slate-600 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${target.average_accuracy * 100}%` }}
                      />
                    </div>
                    <span
                      className={`text-sm font-medium ${getAccuracyColor(target.average_accuracy)}`}
                    >
                      {formatPercentage(target.average_accuracy)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Individual Model Performance */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Model Performance</h3>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {data.model_metrics.map((model) => (
                  <button
                    type="button"
                    key={model.model_name}
                    className={`p-4 rounded-lg border transition-colors text-left w-full ${
                      selectedModel === model.model_name
                        ? 'bg-blue-900/20 border-blue-600'
                        : 'bg-slate-700 border-slate-600 hover:border-slate-500'
                    }`}
                    onClick={() =>
                      setSelectedModel(selectedModel === model.model_name ? null : model.model_name)
                    }
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        <span className="text-lg">{getModelTypeIcon(model.model_type)}</span>
                        <div>
                          <h4 className="text-sm font-medium text-white">{model.model_name}</h4>
                          <p className="text-xs text-slate-400">{model.model_type}</p>
                        </div>
                      </div>
                      <div className={`text-lg font-bold ${getAccuracyColor(model.accuracy)}`}>
                        {formatPercentage(model.accuracy)}
                      </div>
                    </div>

                    {selectedModel === model.model_name && (
                      <div className="mt-3 pt-3 border-t border-slate-600 space-y-2">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-slate-400">Precision:</span>
                            <span className="text-white ml-2">
                              {formatPercentage(model.precision)}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400">Recall:</span>
                            <span className="text-white ml-2">
                              {formatPercentage(model.recall)}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400">F1 Score:</span>
                            <span className="text-white ml-2">
                              {formatPercentage(model.f1_score)}
                            </span>
                          </div>
                          {model.auc_roc && (
                            <div>
                              <span className="text-slate-400">AUC-ROC:</span>
                              <span className="text-white ml-2">
                                {formatPercentage(model.auc_roc)}
                              </span>
                            </div>
                          )}
                        </div>
                        <div className="text-xs text-slate-500">
                          {formatNumber(model.training_samples)} training samples •{' '}
                          {model.features_used} features
                        </div>
                        <div className="text-xs text-slate-500">
                          Last trained: {new Date(model.last_trained).toLocaleDateString()}
                        </div>
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Feature Importance */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Top Features</h3>
              <div className="space-y-3">
                {data.feature_importance.slice(0, 15).map((feature, index) => (
                  <div key={feature.feature} className="flex items-center space-x-3">
                    <div className="w-6 text-sm font-medium text-slate-400 text-right">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-slate-300">{feature.feature}</span>
                        <span className="text-sm font-medium text-white">
                          {(feature.importance * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${feature.importance * 100}%` }}
                        />
                      </div>
                      <div className="text-xs text-slate-500 mt-1">{feature.category}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

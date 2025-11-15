/**
 * AI Cost Calculator Component
 * Interactive cost forecasting for assessments
 */

import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Calculator,
  DollarSign,
  TrendingUp,
  Info,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  BarChart3,
  FileText,
} from 'lucide-react';
import { api } from '../../services/api';

interface ForecastResult {
  estimated_cost: number;
  min_cost: number;
  max_cost: number;
  confidence_level: string;
  confidence_interval: string;
  data_source: string;
  breakdown: {
    [key: string]: {
      cost: number;
      percentage: number;
      description: string;
      unit_cost?: number;
      units?: number;
    };
  };
  parameters: any;
  similar_assessments: Array<{
    id: string;
    name: string;
    cmmc_level: number;
    control_count: number;
    total_cost: number;
    similarity: string;
  }>;
  recommendations: string[];
  forecasted_at: string;
}

export const CostCalculator: React.FC = () => {
  // Form state
  const [controlCount, setControlCount] = useState<number>(110);
  const [documentCount, setDocumentCount] = useState<number>(500);
  const [pageCount, setPageCount] = useState<number>(2500);
  const [cmmcLevel, setCmmcLevel] = useState<number>(2);
  const [useHistorical, setUseHistorical] = useState<boolean>(true);

  // Forecast mutation
  const forecastMutation = useMutation({
    mutationFn: async (params: any) => {
      const response = await api.post('/ai/forecast/assessment', params);
      return response.data;
    },
  });

  // Historical averages query
  const { data: historicalData } = useQuery({
    queryKey: ['historical-averages'],
    queryFn: async () => {
      const response = await api.get('/ai/forecast/historical-averages');
      return response.data;
    },
  });

  const handleCalculate = () => {
    forecastMutation.mutate({
      control_count: controlCount,
      document_count: documentCount > 0 ? documentCount : null,
      page_count: pageCount > 0 ? pageCount : null,
      cmmc_level: cmmcLevel,
      use_historical_data: useHistorical,
    });
  };

  const forecast: ForecastResult | undefined = forecastMutation.data;

  const getConfidenceLevelColor = (level: string): string => {
    const colors: Record<string, string> = {
      high: 'text-green-600 bg-green-100',
      medium: 'text-yellow-600 bg-yellow-100',
      low: 'text-orange-600 bg-orange-100',
    };
    return colors[level] || 'text-gray-600 bg-gray-100';
  };

  const getSimilarityColor = (similarity: string): string => {
    const colors: Record<string, string> = {
      high: 'text-green-700 bg-green-50 border-green-200',
      medium: 'text-yellow-700 bg-yellow-50 border-yellow-200',
      low: 'text-gray-700 bg-gray-50 border-gray-200',
    };
    return colors[similarity] || 'text-gray-700 bg-gray-50 border-gray-200';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Calculator className="w-8 h-8 text-blue-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Cost Calculator</h2>
          <p className="text-sm text-gray-600 mt-1">
            Estimate AI costs for your assessment based on size and complexity
          </p>
        </div>
      </div>

      {/* Historical Data Banner */}
      {historicalData && historicalData.has_data && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <BarChart3 className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-blue-900 mb-1">
                Historical Data Available
              </h3>
              <p className="text-sm text-blue-700">
                Based on {historicalData.assessment_count} completed assessments. Average
                cost: ${historicalData.averages.total_cost_per_assessment} per assessment
                (${historicalData.averages.cost_per_control}/control)
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            Assessment Parameters
          </h3>

          <div className="space-y-4">
            {/* Control Count */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of Controls
                <span className="text-red-500 ml-1">*</span>
              </label>
              <input
                type="number"
                min="1"
                max="1000"
                value={controlCount}
                onChange={(e) => setControlCount(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                CMMC Level 2 typically has 110 controls
              </p>
            </div>

            {/* Document Count */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of Documents
              </label>
              <input
                type="number"
                min="0"
                value={documentCount}
                onChange={(e) => setDocumentCount(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Evidence documents to process (leave 0 for estimate)
              </p>
            </div>

            {/* Page Count */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Total Pages
              </label>
              <input
                type="number"
                min="0"
                value={pageCount}
                onChange={(e) => setPageCount(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Total pages in all documentation (leave 0 for estimate)
              </p>
            </div>

            {/* CMMC Level */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                CMMC Level
              </label>
              <select
                value={cmmcLevel}
                onChange={(e) => setCmmcLevel(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value={1}>Level 1 (Basic)</option>
                <option value={2}>Level 2 (Advanced)</option>
                <option value={3}>Level 3 (Expert)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Higher levels have more complex requirements
              </p>
            </div>

            {/* Use Historical Data */}
            <div className="pt-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useHistorical}
                  onChange={(e) => setUseHistorical(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  Use my organization's historical data
                </span>
              </label>
              <p className="text-xs text-gray-500 mt-1 ml-6">
                {historicalData?.has_data
                  ? `Based on ${historicalData.assessment_count} assessments`
                  : 'Will use industry averages (no historical data)'}
              </p>
            </div>

            {/* Calculate Button */}
            <button
              onClick={handleCalculate}
              disabled={forecastMutation.isPending || controlCount <= 0}
              className={`w-full py-3 px-4 rounded-lg font-medium text-white flex items-center justify-center gap-2 transition-colors ${
                forecastMutation.isPending || controlCount <= 0
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              <Calculator className="w-5 h-5" />
              {forecastMutation.isPending ? 'Calculating...' : 'Calculate Cost'}
            </button>
          </div>
        </div>

        {/* Results Panel */}
        <div className="space-y-4">
          {forecast && (
            <>
              {/* Estimated Cost */}
              <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-lg p-6 text-white">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium opacity-90">
                    Estimated Total Cost
                  </span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${getConfidenceLevelColor(
                      forecast.confidence_level
                    )}`}
                  >
                    {forecast.confidence_level} confidence
                  </span>
                </div>
                <div className="text-4xl font-bold mb-2">
                  ${forecast.estimated_cost.toFixed(2)}
                </div>
                <div className="text-sm opacity-90">
                  Range: ${forecast.min_cost.toFixed(2)} - $
                  {forecast.max_cost.toFixed(2)} ({forecast.confidence_interval})
                </div>
                <div className="mt-3 pt-3 border-t border-white/20 text-xs opacity-75">
                  Based on {forecast.data_source === 'historical' ? 'your historical data' : 'industry averages'}
                </div>
              </div>

              {/* Cost Breakdown */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-600" />
                  Cost Breakdown
                </h3>
                <div className="space-y-3">
                  {Object.entries(forecast.breakdown)
                    .filter(([_, item]) => item.cost > 0)
                    .map(([key, item]) => (
                      <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-900">
                            {key.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                          </div>
                          <div className="text-xs text-gray-500">{item.description}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-bold text-gray-900">
                            ${item.cost.toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-500">
                            {item.percentage.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Recommendations */}
              {forecast.recommendations.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-yellow-900 mb-3 flex items-center gap-2">
                    <Lightbulb className="w-4 h-4" />
                    Recommendations
                  </h3>
                  <ul className="space-y-2">
                    {forecast.recommendations.map((rec, idx) => (
                      <li key={idx} className="text-sm text-yellow-800 flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Similar Assessments */}
              {forecast.similar_assessments.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-purple-600" />
                    Similar Past Assessments
                  </h3>
                  <div className="space-y-2">
                    {forecast.similar_assessments.map((assessment) => (
                      <div
                        key={assessment.id}
                        className={`p-3 border rounded-lg ${getSimilarityColor(
                          assessment.similarity
                        )}`}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <div className="font-medium text-sm">{assessment.name}</div>
                          <span className="text-xs px-2 py-1 bg-white/50 rounded">
                            {assessment.similarity} match
                          </span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span>
                            {assessment.control_count} controls · Level {assessment.cmmc_level}
                          </span>
                          <span className="font-semibold">
                            ${assessment.total_cost.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Empty State */}
          {!forecast && !forecastMutation.isPending && (
            <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
              <Calculator className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Enter Assessment Details
              </h3>
              <p className="text-gray-600 text-sm">
                Fill in the form on the left and click "Calculate Cost" to get your
                estimate
              </p>
            </div>
          )}

          {/* Error State */}
          {forecastMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                <div>
                  <h3 className="text-sm font-semibold text-red-900 mb-1">
                    Calculation Failed
                  </h3>
                  <p className="text-sm text-red-700">
                    Failed to calculate cost estimate. Please check your inputs and try
                    again.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-900">
            <p className="font-medium mb-1">How cost estimation works:</p>
            <ul className="list-disc list-inside space-y-1 text-blue-800">
              <li>Analyzes your organization's historical AI usage patterns</li>
              <li>Calculates average cost per control, document, and page</li>
              <li>Applies CMMC level complexity multipliers</li>
              <li>Provides confidence interval based on data quality</li>
              <li>Compares with similar past assessments</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CostCalculator;

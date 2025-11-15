/**
 * AI Cost Dashboard Component
 * Organization-wide AI usage and cost analytics
 */

import React, { useState } from 'react';
import { useQuery } from '@tantml:react-query';
import {
  DollarSign,
  TrendingUp,
  Calendar,
  Zap,
  BarChart3,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../services/api';

interface DailyCost {
  date: string;
  operations: number;
  tokens: number;
  cost_usd: number;
}

interface OperationCost {
  operation_type: string;
  count: number;
  tokens: number;
  cost_usd: number;
}

interface OrganizationCostData {
  organization_id: string;
  period: {
    start: string;
    end: string;
  };
  summary: {
    total_operations: number;
    total_tokens: number;
    total_cost_usd: number;
  };
  daily_breakdown: DailyCost[];
  operation_breakdown: OperationCost[];
}

export const AICostDashboard: React.FC = () => {
  const [dateRange, setDateRange] = useState(30); // Default: last 30 days

  const { data: costs, isLoading, error, refetch } = useQuery<OrganizationCostData>({
    queryKey: ['ai-costs-org', dateRange],
    queryFn: async () => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - dateRange);

      const response = await api.get('/ai/costs/organization', {
        params: {
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString(),
        },
      });
      return response.data;
    },
  });

  const formatCost = (cost: number): string => {
    if (cost < 0.01) return `$${cost.toFixed(6)}`;
    return `$${cost.toFixed(2)}`;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const getOperationColor = (opType: string): string => {
    const colors: Record<string, string> = {
      embedding: 'bg-blue-100 text-blue-800',
      analysis: 'bg-green-100 text-green-800',
      rag_query: 'bg-purple-100 text-purple-800',
      document_processing: 'bg-orange-100 text-orange-800',
    };
    return colors[opType] || 'bg-gray-100 text-gray-800';
  };

  const avgDailyCost = costs
    ? costs.summary.total_cost_usd / (costs.daily_breakdown.length || 1)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Cost Analytics</h2>
          <p className="text-sm text-gray-600 mt-1">
            Organization-wide AI usage and spending
          </p>
        </div>
        <div className="flex gap-3">
          {/* Date Range Selector */}
          <select
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>

          {/* Refresh Button */}
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="bg-white rounded-lg shadow p-12">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 rounded-lg border border-red-200 p-4">
          <p className="text-red-800">Failed to load cost data. Please try again.</p>
        </div>
      )}

      {costs && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600">Total Spent</p>
                <DollarSign className="w-5 h-5 text-green-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {formatCost(costs.summary.total_cost_usd)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {dateRange} day{dateRange > 1 ? 's' : ''}
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600">Avg. Daily Cost</p>
                <TrendingUp className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {formatCost(avgDailyCost)}
              </p>
              <p className="text-xs text-gray-500 mt-1">per day</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600">Total Operations</p>
                <Zap className="w-5 h-5 text-purple-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {formatNumber(costs.summary.total_operations)}
              </p>
              <p className="text-xs text-gray-500 mt-1">AI API calls</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600">Total Tokens</p>
                <BarChart3 className="w-5 h-5 text-orange-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {formatNumber(costs.summary.total_tokens)}
              </p>
              <p className="text-xs text-gray-500 mt-1">tokens processed</p>
            </div>
          </div>

          {/* Daily Trend Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Daily Spending Trend
            </h3>
            <div className="space-y-2">
              {costs.daily_breakdown.slice(0, 10).map((day, index) => {
                const maxCost = Math.max(
                  ...costs.daily_breakdown.map((d) => d.cost_usd)
                );
                const percentage = (day.cost_usd / maxCost) * 100;

                return (
                  <div key={index} className="flex items-center gap-4">
                    <div className="w-24 text-sm text-gray-600">
                      {new Date(day.date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                      })}
                    </div>
                    <div className="flex-1">
                      <div className="bg-gray-200 rounded-full h-6 relative overflow-hidden">
                        <div
                          className="bg-blue-600 h-full rounded-full flex items-center justify-end pr-2"
                          style={{ width: `${percentage}%` }}
                        >
                          {percentage > 20 && (
                            <span className="text-xs text-white font-medium">
                              {formatCost(day.cost_usd)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="w-32 text-right text-sm text-gray-600">
                      {formatNumber(day.operations)} ops
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Operation Breakdown */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Cost by Operation Type
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {costs.operation_breakdown.map((op, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getOperationColor(
                        op.operation_type
                      )}`}
                    >
                      {op.operation_type}
                    </span>
                    <span className="text-lg font-bold text-gray-900">
                      {formatCost(op.cost_usd)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>{formatNumber(op.count)} operations</span>
                    <span>{formatNumber(op.tokens)} tokens</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AICostDashboard;

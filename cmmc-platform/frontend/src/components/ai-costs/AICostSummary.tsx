/**
 * AI Cost Summary Component
 * Displays AI usage and costs for an assessment
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DollarSign, Zap, Clock, TrendingUp } from 'lucide-react';
import { api } from '../../services/api';

interface CostBreakdown {
  operation_type: string;
  model_name: string;
  count: number;
  tokens: number;
  cost_usd: number;
}

interface AssessmentCostData {
  assessment_id: string;
  total_operations: number;
  total_tokens: number;
  total_cost_usd: number;
  first_operation: string | null;
  last_operation: string | null;
  breakdown: CostBreakdown[];
}

interface AICostSummaryProps {
  assessmentId: string;
}

export const AICostSummary: React.FC<AICostSummaryProps> = ({ assessmentId }) => {
  const { data: costs, isLoading, error } = useQuery<AssessmentCostData>({
    queryKey: ['ai-costs', assessmentId],
    queryFn: async () => {
      const response = await api.get(`/ai/costs/assessment/${assessmentId}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-lg border border-red-200 p-4">
        <p className="text-red-800 text-sm">Failed to load AI cost data</p>
      </div>
    );
  }

  if (!costs || costs.total_operations === 0) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
        <div className="text-center">
          <DollarSign className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">No AI operations recorded yet</p>
          <p className="text-sm text-gray-500 mt-1">
            Costs will appear here after running AI analysis or document processing
          </p>
        </div>
      </div>
    );
  }

  const formatCost = (cost: number): string => {
    if (cost < 0.01) {
      return `$${cost.toFixed(6)}`; // Show more precision for very small amounts
    }
    return `$${cost.toFixed(2)}`;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const getOperationLabel = (opType: string): string => {
    const labels: Record<string, string> = {
      embedding: 'Document Embeddings',
      analysis: 'AI Control Analysis',
      rag_query: 'RAG Searches',
      document_processing: 'Document Processing',
    };
    return labels[opType] || opType;
  };

  const getOperationIcon = (opType: string): React.ReactNode => {
    const icons: Record<string, React.ReactNode> = {
      embedding: <Zap className="w-4 h-4 text-blue-500" />,
      analysis: <TrendingUp className="w-4 h-4 text-green-500" />,
      rag_query: <Clock className="w-4 h-4 text-purple-500" />,
      document_processing: <DollarSign className="w-4 h-4 text-orange-500" />,
    };
    return icons[opType] || <DollarSign className="w-4 h-4 text-gray-500" />;
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-green-600" />
          AI Usage & Costs
        </h3>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6 border-b border-gray-200">
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-1">Total Cost</p>
          <p className="text-2xl font-bold text-green-600">
            {formatCost(costs.total_cost_usd)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-1">Operations</p>
          <p className="text-2xl font-bold text-blue-600">
            {formatNumber(costs.total_operations)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-1">Tokens Used</p>
          <p className="text-2xl font-bold text-purple-600">
            {formatNumber(costs.total_tokens)}
          </p>
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="p-6">
        <h4 className="text-sm font-semibold text-gray-700 mb-4">Cost Breakdown</h4>
        <div className="space-y-3">
          {costs.breakdown.map((item, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-3 flex-1">
                {getOperationIcon(item.operation_type)}
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {getOperationLabel(item.operation_type)}
                  </p>
                  <p className="text-xs text-gray-500">{item.model_name}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900">
                  {formatCost(item.cost_usd)}
                </p>
                <p className="text-xs text-gray-500">
                  {formatNumber(item.count)} ops · {formatNumber(item.tokens)} tokens
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer with timestamps */}
      {costs.first_operation && costs.last_operation && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-600">
          <div className="flex justify-between">
            <span>
              First operation: {new Date(costs.first_operation).toLocaleString()}
            </span>
            <span>
              Last operation: {new Date(costs.last_operation).toLocaleString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default AICostSummary;

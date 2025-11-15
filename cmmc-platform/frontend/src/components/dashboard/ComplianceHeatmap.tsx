import React from 'react';
import { DomainComplianceData } from '@/types';

export interface ComplianceHeatmapProps {
  data: DomainComplianceData[];
}

export const ComplianceHeatmap: React.FC<ComplianceHeatmapProps> = ({ data }) => {
  const getColor = (complianceRate: number) => {
    if (complianceRate >= 90) return 'bg-success-500';
    if (complianceRate >= 70) return 'bg-success-400';
    if (complianceRate >= 50) return 'bg-warning-500';
    if (complianceRate >= 30) return 'bg-warning-400';
    return 'bg-danger-500';
  };

  const getTextColor = (complianceRate: number) => {
    if (complianceRate >= 90) return 'text-success-700';
    if (complianceRate >= 70) return 'text-success-600';
    if (complianceRate >= 50) return 'text-warning-700';
    if (complianceRate >= 30) return 'text-warning-600';
    return 'text-danger-700';
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {data.map((item) => (
        <div
          key={item.domain}
          className="relative overflow-hidden rounded-lg border border-gray-200 bg-white p-4 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-gray-900">{item.domain}</h4>
            <span className={`text-lg font-bold ${getTextColor(item.complianceRate)}`}>
              {Math.round(item.complianceRate)}%
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-gray-600 mb-2">
            <span>
              {item.metControls} / {item.totalControls} controls
            </span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${getColor(item.complianceRate)} transition-all duration-300`}
              style={{ width: `${item.complianceRate}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

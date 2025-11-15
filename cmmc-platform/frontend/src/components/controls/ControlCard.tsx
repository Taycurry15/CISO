import React, { useState } from 'react';
import { ControlFinding, CmmcControl, ControlStatus } from '@/types';
import { Badge } from '@/components/common/Badge';
import { ControlStatusSelector } from './ControlStatusSelector';
import { ChevronDown, ChevronUp, Shield, Sparkles } from 'lucide-react';

export interface ControlCardProps {
  control: CmmcControl;
  finding?: ControlFinding;
  onStatusChange?: (controlId: string, status: ControlStatus) => void;
}

export const ControlCard: React.FC<ControlCardProps> = ({
  control,
  finding,
  onStatusChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getStatusVariant = (status?: ControlStatus) => {
    switch (status) {
      case 'Met':
        return 'success';
      case 'Not Met':
        return 'danger';
      case 'Partially Met':
        return 'warning';
      case 'Not Applicable':
        return 'gray';
      default:
        return 'gray';
    }
  };

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <Badge variant="blue">{control.id}</Badge>
            <Badge variant="gray">{control.domain}</Badge>
            {finding?.isInherited && (
              <Badge variant="blue">
                <Shield className="w-3 h-3 mr-1" />
                Inherited
              </Badge>
            )}
          </div>
          <h3 className="text-lg font-semibold text-gray-900">{control.title}</h3>
        </div>
        {finding?.status && <Badge variant={getStatusVariant(finding.status)}>{finding.status}</Badge>}
      </div>

      <p className="text-sm text-gray-700 mb-4">{control.objective}</p>

      {finding && (
        <div className="space-y-3">
          <ControlStatusSelector
            value={finding.status}
            onChange={(status) => onStatusChange?.(control.id, status)}
          />

          {finding.implementationNarrative && (
            <div className="bg-gray-50 rounded-lg p-3">
              <h4 className="text-sm font-semibold text-gray-900 mb-1">Implementation</h4>
              <p className="text-sm text-gray-700">{finding.implementationNarrative}</p>
              {finding.aiConfidenceScore && (
                <div className="flex items-center mt-2 text-xs text-gray-500">
                  <Sparkles className="w-3 h-3 mr-1" />
                  AI Confidence: {Math.round(finding.aiConfidenceScore * 100)}%
                </div>
              )}
            </div>
          )}

          {finding.assessorNotes && (
            <div className="bg-blue-50 rounded-lg p-3">
              <h4 className="text-sm font-semibold text-gray-900 mb-1">Assessor Notes</h4>
              <p className="text-sm text-gray-700">{finding.assessorNotes}</p>
            </div>
          )}
        </div>
      )}

      {/* Expandable Details */}
      <div className="mt-4">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-4 h-4 mr-1" />
              Hide Details
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4 mr-1" />
              Show Details
            </>
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
          {control.discussion && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">Discussion</h4>
              <p className="text-sm text-gray-700">{control.discussion}</p>
            </div>
          )}

          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">Assessment Objectives</h4>
            <ul className="list-disc list-inside space-y-1">
              {control.assessmentObjectives.map((obj, idx) => (
                <li key={idx} className="text-sm text-gray-700">
                  {obj}
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <h4 className="text-xs font-semibold text-gray-900 mb-2">Examine</h4>
              <ul className="list-disc list-inside space-y-1">
                {control.examineItems.slice(0, 2).map((item, idx) => (
                  <li key={idx} className="text-xs text-gray-600">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-gray-900 mb-2">Interview</h4>
              <ul className="list-disc list-inside space-y-1">
                {control.interviewItems.slice(0, 2).map((item, idx) => (
                  <li key={idx} className="text-xs text-gray-600">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-gray-900 mb-2">Test</h4>
              <ul className="list-disc list-inside space-y-1">
                {control.testItems.slice(0, 2).map((item, idx) => (
                  <li key={idx} className="text-xs text-gray-600">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

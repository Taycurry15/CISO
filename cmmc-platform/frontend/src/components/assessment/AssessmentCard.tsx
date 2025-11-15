import React from 'react';
import { Assessment } from '@/types';
import { Badge } from '@/components/common/Badge';
import { ProgressBar } from '@/components/common/ProgressBar';
import { Calendar, User, TrendingUp } from 'lucide-react';

export interface AssessmentCardProps {
  assessment: Assessment;
  onClick?: () => void;
}

export const AssessmentCard: React.FC<AssessmentCardProps> = ({ assessment, onClick }) => {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'Completed':
        return 'success';
      case 'In Progress':
        return 'blue';
      case 'Under Review':
        return 'warning';
      case 'Draft':
        return 'gray';
      default:
        return 'gray';
    }
  };

  return (
    <div
      className="card p-6 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">{assessment.name}</h3>
          {assessment.description && (
            <p className="text-sm text-gray-600 mt-1">{assessment.description}</p>
          )}
        </div>
        <Badge variant={getStatusVariant(assessment.status)}>{assessment.status}</Badge>
      </div>

      <div className="space-y-3 mb-4">
        {assessment.targetCompletionDate && (
          <div className="flex items-center text-sm text-gray-600">
            <Calendar className="w-4 h-4 mr-2" />
            <span>
              Due: {new Date(assessment.targetCompletionDate).toLocaleDateString()}
            </span>
          </div>
        )}
        {assessment.leadAssessorId && (
          <div className="flex items-center text-sm text-gray-600">
            <User className="w-4 h-4 mr-2" />
            <span>Assessor assigned</span>
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Progress</span>
          <span className="text-sm font-semibold text-gray-900">{assessment.progress}%</span>
        </div>
        <ProgressBar
          value={assessment.progress}
          variant={assessment.progress >= 90 ? 'success' : assessment.progress >= 50 ? 'primary' : 'warning'}
          showLabel={false}
        />
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Created {new Date(assessment.createdAt).toLocaleDateString()}</span>
          <span className="flex items-center">
            <TrendingUp className="w-3 h-3 mr-1" />
            {assessment.assessmentType}
          </span>
        </div>
      </div>
    </div>
  );
};

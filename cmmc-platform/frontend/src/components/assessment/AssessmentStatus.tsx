import React from 'react';
import { AssessmentStatus as Status } from '@/types';
import { Badge } from '@/components/common/Badge';
import {
  FileText,
  Play,
  Eye,
  Wrench,
  CheckCircle,
} from 'lucide-react';

export interface AssessmentStatusProps {
  status: Status;
  showIcon?: boolean;
}

export const AssessmentStatus: React.FC<AssessmentStatusProps> = ({
  status,
  showIcon = true,
}) => {
  const statusConfig = {
    Draft: {
      variant: 'gray' as const,
      icon: FileText,
    },
    'In Progress': {
      variant: 'blue' as const,
      icon: Play,
    },
    'Under Review': {
      variant: 'warning' as const,
      icon: Eye,
    },
    Remediation: {
      variant: 'warning' as const,
      icon: Wrench,
    },
    'Final Review': {
      variant: 'blue' as const,
      icon: CheckCircle,
    },
    Completed: {
      variant: 'success' as const,
      icon: CheckCircle,
    },
  };

  const config = statusConfig[status] || statusConfig.Draft;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className="inline-flex items-center">
      {showIcon && <Icon className="w-3 h-3 mr-1" />}
      {status}
    </Badge>
  );
};

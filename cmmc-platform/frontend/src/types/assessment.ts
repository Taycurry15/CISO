export type AssessmentStatus =
  | 'Draft'
  | 'In Progress'
  | 'Under Review'
  | 'Remediation'
  | 'Final Review'
  | 'Completed';

export interface Assessment {
  id: string;
  organizationId: string;
  name: string;
  description?: string;
  assessmentType: string;
  status: AssessmentStatus;
  scope?: string;
  startDate?: string;
  targetCompletionDate?: string;
  actualCompletionDate?: string;
  leadAssessorId?: string;
  progress: number;
  createdAt: string;
  updatedAt: string;
}

export interface AssessmentStats {
  totalControls: number;
  metControls: number;
  notMetControls: number;
  partiallyMetControls: number;
  notApplicableControls: number;
  complianceRate: number;
}

export interface CreateAssessmentDto {
  name: string;
  description?: string;
  assessmentType: string;
  scope?: string;
  startDate?: string;
  targetCompletionDate?: string;
  leadAssessorId?: string;
}

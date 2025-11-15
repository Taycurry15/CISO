export interface DashboardStats {
  totalAssessments: number;
  activeAssessments: number;
  completedAssessments: number;
  overallComplianceRate: number;
  totalControls: number;
  metControls: number;
  atRiskControls: number;
  totalEvidence: number;
}

export interface DomainComplianceData {
  domain: string;
  complianceRate: number;
  metControls: number;
  totalControls: number;
}

export interface ProgressOverTimeData {
  date: string;
  complianceRate: number;
  metControls: number;
}

export interface RecentActivity {
  id: string;
  type: string;
  description: string;
  user: string;
  timestamp: string;
  assessmentId?: string;
}

export interface TimeSavingsData {
  automationHours: number;
  manualHours: number;
  percentageSaved: number;
  costSavings: number;
}

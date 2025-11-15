export type ControlStatus = 'Met' | 'Not Met' | 'Partially Met' | 'Not Applicable';
export type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Low';

export interface CmmcControl {
  id: string;
  level: number;
  domain: string;
  practiceId: string;
  title: string;
  objective: string;
  discussion?: string;
  nistControlId: string;
  assessmentObjectives: string[];
  examineItems: string[];
  interviewItems: string[];
  testItems: string[];
}

export interface ControlFinding {
  id: string;
  assessmentId: string;
  controlId: string;
  status: ControlStatus;
  implementationNarrative?: string;
  assessorNotes?: string;
  riskLevel?: RiskLevel;
  aiConfidenceScore?: number;
  aiGeneratedNarrative?: string;
  assignedTo?: string;
  reviewedBy?: string;
  reviewedAt?: string;
  isInherited: boolean;
  inheritanceSource?: string;
  inheritanceType?: string;
  evidenceIds: string[];
  createdAt: string;
  updatedAt: string;
  control?: CmmcControl;
}

export interface ControlFindingUpdate {
  status?: ControlStatus;
  implementationNarrative?: string;
  assessorNotes?: string;
  riskLevel?: RiskLevel;
  assignedTo?: string;
  isInherited?: boolean;
  inheritanceSource?: string;
  inheritanceType?: string;
}

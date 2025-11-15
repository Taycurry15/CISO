export type EvidenceType =
  | 'Policy'
  | 'Procedure'
  | 'Screenshot'
  | 'Configuration'
  | 'Log'
  | 'Report'
  | 'Other';

export interface Evidence {
  id: string;
  assessmentId: string;
  organizationId: string;
  fileName: string;
  filePath: string;
  fileSize: number;
  fileType: string;
  fileHash: string;
  evidenceType: EvidenceType;
  description?: string;
  uploadedBy: string;
  controlIds: string[];
  tags: string[];
  collectionDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface EvidenceUpload {
  file: File;
  evidenceType: EvidenceType;
  description?: string;
  controlIds?: string[];
  tags?: string[];
  collectionDate?: string;
}

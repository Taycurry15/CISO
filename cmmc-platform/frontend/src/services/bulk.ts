import { api } from './api';

export interface BulkControlUpdate {
  controlId: string;
  status?: string;
  implementationNarrative?: string;
  assessorNotes?: string;
  riskLevel?: string;
}

export interface BulkOperationResponse {
  successCount: number;
  failureCount: number;
  totalProcessed: number;
  errors: Array<{ controlId?: string; fileName?: string; error: string }>;
}

export const bulkService = {
  /**
   * Bulk update control statuses
   */
  async bulkUpdateControls(
    assessmentId: string,
    updates: BulkControlUpdate[]
  ): Promise<BulkOperationResponse> {
    const { data } = await api.post(`/api/v1/bulk/controls/update`, {
      assessment_id: assessmentId,
      updates,
    });
    return data;
  },

  /**
   * Bulk upload evidence ZIP file
   */
  async bulkUploadEvidenceZip(
    assessmentId: string,
    zipFile: File,
    evidenceType: string,
    controlIds?: string[]
  ): Promise<BulkOperationResponse> {
    const formData = new FormData();
    formData.append('zip_file', zipFile);
    formData.append('evidence_type', evidenceType);
    if (controlIds) formData.append('control_ids', JSON.stringify(controlIds));

    const { data } = await api.post(`/api/v1/bulk/evidence/upload-zip`, formData, {
      params: { assessment_id: assessmentId },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  /**
   * Import findings from Excel
   */
  async importFindingsFromExcel(
    assessmentId: string,
    excelFile: File
  ): Promise<BulkOperationResponse> {
    const formData = new FormData();
    formData.append('excel_file', excelFile);

    const { data } = await api.post(`/api/v1/bulk/findings/import`, formData, {
      params: { assessment_id: assessmentId },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  /**
   * Export findings to Excel
   */
  async exportFindingsToExcel(assessmentId: string): Promise<Blob> {
    const { data } = await api.get(`/api/v1/bulk/findings/export`, {
      params: { assessment_id: assessmentId },
      responseType: 'blob',
    });
    return data;
  },

  /**
   * Bulk assign controls to user
   */
  async bulkAssignControls(
    assessmentId: string,
    controlIds: string[],
    userId: string
  ): Promise<BulkOperationResponse> {
    const { data } = await api.post(`/api/v1/bulk/controls/assign`, {
      assessment_id: assessmentId,
      control_ids: controlIds,
      user_id: userId,
    });
    return data;
  },

  /**
   * Bulk update controls by domain
   */
  async bulkUpdateDomain(
    assessmentId: string,
    domain: string,
    updates: Partial<BulkControlUpdate>
  ): Promise<BulkOperationResponse> {
    const { data } = await api.post(`/api/v1/bulk/domain/update`, {
      assessment_id: assessmentId,
      domain,
      updates,
    });
    return data;
  },
};

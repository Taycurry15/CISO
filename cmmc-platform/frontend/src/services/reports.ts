import { api } from './api';

export const reportsService = {
  /**
   * Generate SSP (System Security Plan) report
   */
  async generateSSP(assessmentId: string): Promise<Blob> {
    const { data } = await api.post(
      `/api/v1/reports/ssp`,
      { assessment_id: assessmentId },
      { responseType: 'blob' }
    );
    return data;
  },

  /**
   * Generate POA&M (Plan of Action & Milestones) report
   */
  async generatePOAM(assessmentId: string): Promise<Blob> {
    const { data } = await api.post(
      `/api/v1/reports/poam`,
      { assessment_id: assessmentId },
      { responseType: 'blob' }
    );
    return data;
  },

  /**
   * Generate executive summary PDF
   */
  async generateExecutiveSummary(assessmentId: string): Promise<Blob> {
    const { data } = await api.post(
      `/api/v1/reports/executive-summary`,
      { assessment_id: assessmentId },
      { responseType: 'blob' }
    );
    return data;
  },

  /**
   * Generate compliance matrix
   */
  async generateComplianceMatrix(assessmentId: string, format: 'pdf' | 'excel' = 'pdf'): Promise<Blob> {
    const { data } = await api.post(
      `/api/v1/reports/compliance-matrix`,
      { assessment_id: assessmentId, format },
      { responseType: 'blob' }
    );
    return data;
  },

  /**
   * Get report generation status
   */
  async getReportStatus(reportId: string): Promise<{ status: string; progress: number; url?: string }> {
    const { data } = await api.get(`/api/v1/reports/${reportId}/status`);
    return data;
  },
};

import { api } from './api';
import { CmmcControl, ControlFinding, ControlFindingUpdate } from '@/types';

export const controlsService = {
  /**
   * Get all CMMC controls
   */
  async getCmmcControls(): Promise<CmmcControl[]> {
    const { data } = await api.get('/api/v1/controls');
    return data;
  },

  /**
   * Get a single CMMC control by ID
   */
  async getCmmcControl(id: string): Promise<CmmcControl> {
    const { data } = await api.get(`/api/v1/controls/${id}`);
    return data;
  },

  /**
   * Get control findings for an assessment
   */
  async getControlFindings(assessmentId: string): Promise<ControlFinding[]> {
    const { data } = await api.get(`/api/v1/assessments/${assessmentId}/findings`);
    return data;
  },

  /**
   * Get a single control finding
   */
  async getControlFinding(assessmentId: string, controlId: string): Promise<ControlFinding> {
    const { data } = await api.get(`/api/v1/assessments/${assessmentId}/findings/${controlId}`);
    return data;
  },

  /**
   * Update a control finding
   */
  async updateControlFinding(
    assessmentId: string,
    controlId: string,
    updates: ControlFindingUpdate
  ): Promise<ControlFinding> {
    const { data } = await api.put(
      `/api/v1/assessments/${assessmentId}/findings/${controlId}`,
      updates
    );
    return data;
  },

  /**
   * Generate AI narrative for a control
   */
  async generateAiNarrative(assessmentId: string, controlId: string): Promise<{ narrative: string; confidence: number }> {
    const { data } = await api.post(
      `/api/v1/assessments/${assessmentId}/findings/${controlId}/generate-narrative`
    );
    return data;
  },

  /**
   * Get controls by domain
   */
  async getControlsByDomain(domain: string): Promise<CmmcControl[]> {
    const { data } = await api.get(`/api/v1/controls/domain/${domain}`);
    return data;
  },
};

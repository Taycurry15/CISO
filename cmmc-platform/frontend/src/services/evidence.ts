import { api } from './api';
import { Evidence } from '@/types';

export const evidenceService = {
  /**
   * Get all evidence for an assessment
   */
  async getEvidence(assessmentId: string): Promise<Evidence[]> {
    const { data } = await api.get(`/api/v1/assessments/${assessmentId}/evidence`);
    return data;
  },

  /**
   * Get a single evidence item
   */
  async getEvidenceItem(evidenceId: string): Promise<Evidence> {
    const { data } = await api.get(`/api/v1/evidence/${evidenceId}`);
    return data;
  },

  /**
   * Upload evidence file
   */
  async uploadEvidence(
    assessmentId: string,
    file: File,
    metadata: {
      evidenceType: string;
      description?: string;
      controlIds?: string[];
      tags?: string[];
      collectionDate?: string;
    }
  ): Promise<Evidence> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('evidence_type', metadata.evidenceType);
    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.controlIds) formData.append('control_ids', JSON.stringify(metadata.controlIds));
    if (metadata.tags) formData.append('tags', JSON.stringify(metadata.tags));
    if (metadata.collectionDate) formData.append('collection_date', metadata.collectionDate);

    const { data } = await api.post(
      `/api/v1/assessments/${assessmentId}/evidence/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return data;
  },

  /**
   * Update evidence metadata
   */
  async updateEvidence(evidenceId: string, updates: Partial<Evidence>): Promise<Evidence> {
    const { data } = await api.put(`/api/v1/evidence/${evidenceId}`, updates);
    return data;
  },

  /**
   * Delete evidence
   */
  async deleteEvidence(evidenceId: string): Promise<void> {
    await api.delete(`/api/v1/evidence/${evidenceId}`);
  },

  /**
   * Link evidence to controls
   */
  async linkEvidenceToControls(evidenceId: string, controlIds: string[]): Promise<Evidence> {
    const { data } = await api.post(`/api/v1/evidence/${evidenceId}/link-controls`, {
      control_ids: controlIds,
    });
    return data;
  },

  /**
   * Download evidence file
   */
  async downloadEvidence(evidenceId: string): Promise<Blob> {
    const { data } = await api.get(`/api/v1/evidence/${evidenceId}/download`, {
      responseType: 'blob',
    });
    return data;
  },
};

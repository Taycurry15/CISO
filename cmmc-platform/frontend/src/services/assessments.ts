import { api } from './api';
import { Assessment, CreateAssessmentDto } from '@/types';

export const assessmentsService = {
  /**
   * Get all assessments for the current organization
   */
  async getAssessments(): Promise<Assessment[]> {
    const { data } = await api.get('/api/v1/assessments');
    return data;
  },

  /**
   * Get a single assessment by ID
   */
  async getAssessment(id: string): Promise<Assessment> {
    const { data } = await api.get(`/api/v1/assessments/${id}`);
    return data;
  },

  /**
   * Create a new assessment
   */
  async createAssessment(assessment: CreateAssessmentDto): Promise<Assessment> {
    const { data } = await api.post('/api/v1/assessments', assessment);
    return data;
  },

  /**
   * Update an existing assessment
   */
  async updateAssessment(id: string, updates: Partial<Assessment>): Promise<Assessment> {
    const { data } = await api.put(`/api/v1/assessments/${id}`, updates);
    return data;
  },

  /**
   * Delete an assessment
   */
  async deleteAssessment(id: string): Promise<void> {
    await api.delete(`/api/v1/assessments/${id}`);
  },

  /**
   * Get assessment statistics
   */
  async getAssessmentStats(id: string): Promise<any> {
    const { data } = await api.get(`/api/v1/assessments/${id}/stats`);
    return data;
  },

  /**
   * Update assessment status
   */
  async updateAssessmentStatus(id: string, status: string): Promise<Assessment> {
    const { data } = await api.patch(`/api/v1/assessments/${id}/status`, { status });
    return data;
  },
};

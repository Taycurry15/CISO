import { api } from './api';
import {
  DashboardStats,
  DomainComplianceData,
  ProgressOverTimeData,
  RecentActivity,
  TimeSavingsData,
} from '@/types';

export const dashboardService = {
  /**
   * Get overall dashboard statistics
   */
  async getDashboardStats(): Promise<DashboardStats> {
    const { data } = await api.get('/api/v1/dashboard/stats');
    return data;
  },

  /**
   * Get compliance data by domain
   */
  async getDomainCompliance(assessmentId?: string): Promise<DomainComplianceData[]> {
    const params = assessmentId ? { assessment_id: assessmentId } : {};
    const { data } = await api.get('/api/v1/dashboard/domain-compliance', { params });
    return data;
  },

  /**
   * Get progress over time
   */
  async getProgressOverTime(
    assessmentId?: string,
    days: number = 30
  ): Promise<ProgressOverTimeData[]> {
    const params: any = { days };
    if (assessmentId) params.assessment_id = assessmentId;
    const { data } = await api.get('/api/v1/dashboard/progress-over-time', { params });
    return data;
  },

  /**
   * Get recent activity
   */
  async getRecentActivity(limit: number = 10): Promise<RecentActivity[]> {
    const { data } = await api.get('/api/v1/dashboard/recent-activity', {
      params: { limit },
    });
    return data;
  },

  /**
   * Get time savings data
   */
  async getTimeSavings(assessmentId?: string): Promise<TimeSavingsData> {
    const params = assessmentId ? { assessment_id: assessmentId } : {};
    const { data } = await api.get('/api/v1/dashboard/time-savings', { params });
    return data;
  },

  /**
   * Export dashboard data to PDF
   */
  async exportDashboard(assessmentId?: string): Promise<Blob> {
    const params = assessmentId ? { assessment_id: assessmentId } : {};
    const { data } = await api.get('/api/v1/dashboard/export', {
      params,
      responseType: 'blob',
    });
    return data;
  },
};

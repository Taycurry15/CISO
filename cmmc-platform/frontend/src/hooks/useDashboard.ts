import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '@/services/dashboard';

export const useDashboard = (assessmentId?: string) => {
  const {
    data: stats,
    isLoading: isLoadingStats,
    error: statsError,
  } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => dashboardService.getDashboardStats(),
  });

  const {
    data: domainCompliance,
    isLoading: isLoadingDomains,
  } = useQuery({
    queryKey: ['dashboard', 'domain-compliance', assessmentId],
    queryFn: () => dashboardService.getDomainCompliance(assessmentId),
  });

  const {
    data: progressOverTime,
    isLoading: isLoadingProgress,
  } = useQuery({
    queryKey: ['dashboard', 'progress', assessmentId],
    queryFn: () => dashboardService.getProgressOverTime(assessmentId, 30),
  });

  const {
    data: recentActivity,
    isLoading: isLoadingActivity,
  } = useQuery({
    queryKey: ['dashboard', 'activity'],
    queryFn: () => dashboardService.getRecentActivity(10),
  });

  const {
    data: timeSavings,
    isLoading: isLoadingSavings,
  } = useQuery({
    queryKey: ['dashboard', 'time-savings', assessmentId],
    queryFn: () => dashboardService.getTimeSavings(assessmentId),
  });

  return {
    stats,
    domainCompliance,
    progressOverTime,
    recentActivity,
    timeSavings,
    isLoading:
      isLoadingStats ||
      isLoadingDomains ||
      isLoadingProgress ||
      isLoadingActivity ||
      isLoadingSavings,
    error: statsError,
  };
};

export const useExportDashboard = () => {
  const exportDashboard = async (assessmentId?: string) => {
    const blob = await dashboardService.exportDashboard(assessmentId);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dashboard-${assessmentId || 'all'}-${new Date().toISOString()}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return { exportDashboard };
};

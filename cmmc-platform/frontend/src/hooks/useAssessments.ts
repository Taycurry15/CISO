import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assessmentsService } from '@/services/assessments';
import { Assessment, CreateAssessmentDto } from '@/types';

export const useAssessments = () => {
  const queryClient = useQueryClient();

  // Get all assessments
  const {
    data: assessments,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['assessments'],
    queryFn: () => assessmentsService.getAssessments(),
  });

  // Create assessment mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateAssessmentDto) => assessmentsService.createAssessment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
    },
  });

  // Update assessment mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Assessment> }) =>
      assessmentsService.updateAssessment(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
    },
  });

  // Delete assessment mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => assessmentsService.deleteAssessment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
    },
  });

  return {
    assessments,
    isLoading,
    error,
    createAssessment: createMutation.mutateAsync,
    updateAssessment: updateMutation.mutateAsync,
    deleteAssessment: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

export const useAssessment = (id: string) => {
  const queryClient = useQueryClient();

  const {
    data: assessment,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['assessments', id],
    queryFn: () => assessmentsService.getAssessment(id),
    enabled: !!id,
  });

  const {
    data: stats,
    isLoading: isLoadingStats,
  } = useQuery({
    queryKey: ['assessments', id, 'stats'],
    queryFn: () => assessmentsService.getAssessmentStats(id),
    enabled: !!id,
  });

  const updateStatusMutation = useMutation({
    mutationFn: (status: string) => assessmentsService.updateAssessmentStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments', id] });
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
    },
  });

  return {
    assessment,
    stats,
    isLoading: isLoading || isLoadingStats,
    error,
    updateStatus: updateStatusMutation.mutateAsync,
    isUpdatingStatus: updateStatusMutation.isPending,
  };
};

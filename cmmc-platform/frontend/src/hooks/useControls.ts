import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { controlsService } from '@/services/controls';
import { ControlFindingUpdate } from '@/types';

export const useControls = () => {
  const {
    data: controls,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['controls'],
    queryFn: () => controlsService.getCmmcControls(),
    staleTime: 60 * 60 * 1000, // CMMC controls rarely change, cache for 1 hour
  });

  return {
    controls,
    isLoading,
    error,
  };
};

export const useControlsByDomain = (domain: string) => {
  const {
    data: controls,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['controls', 'domain', domain],
    queryFn: () => controlsService.getControlsByDomain(domain),
    enabled: !!domain,
    staleTime: 60 * 60 * 1000,
  });

  return {
    controls,
    isLoading,
    error,
  };
};

export const useControlFindings = (assessmentId: string) => {
  const queryClient = useQueryClient();

  const {
    data: findings,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['assessments', assessmentId, 'findings'],
    queryFn: () => controlsService.getControlFindings(assessmentId),
    enabled: !!assessmentId,
  });

  const updateFindingMutation = useMutation({
    mutationFn: ({ controlId, updates }: { controlId: string; updates: ControlFindingUpdate }) =>
      controlsService.updateControlFinding(assessmentId, controlId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'findings'] });
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'stats'] });
    },
  });

  const generateAiNarrativeMutation = useMutation({
    mutationFn: (controlId: string) =>
      controlsService.generateAiNarrative(assessmentId, controlId),
  });

  return {
    findings,
    isLoading,
    error,
    updateFinding: updateFindingMutation.mutateAsync,
    generateAiNarrative: generateAiNarrativeMutation.mutateAsync,
    isUpdating: updateFindingMutation.isPending,
    isGenerating: generateAiNarrativeMutation.isPending,
  };
};

export const useControlFinding = (assessmentId: string, controlId: string) => {
  const queryClient = useQueryClient();

  const {
    data: finding,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['assessments', assessmentId, 'findings', controlId],
    queryFn: () => controlsService.getControlFinding(assessmentId, controlId),
    enabled: !!assessmentId && !!controlId,
  });

  const updateMutation = useMutation({
    mutationFn: (updates: ControlFindingUpdate) =>
      controlsService.updateControlFinding(assessmentId, controlId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'findings'] });
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'findings', controlId] });
    },
  });

  return {
    finding,
    isLoading,
    error,
    update: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
  };
};

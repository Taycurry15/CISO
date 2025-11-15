import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { evidenceService } from '@/services/evidence';
import { Evidence } from '@/types';

export const useEvidence = (assessmentId: string) => {
  const queryClient = useQueryClient();

  const {
    data: evidence,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['assessments', assessmentId, 'evidence'],
    queryFn: () => evidenceService.getEvidence(assessmentId),
    enabled: !!assessmentId,
  });

  const uploadMutation = useMutation({
    mutationFn: ({
      file,
      metadata,
    }: {
      file: File;
      metadata: {
        evidenceType: string;
        description?: string;
        controlIds?: string[];
        tags?: string[];
        collectionDate?: string;
      };
    }) => evidenceService.uploadEvidence(assessmentId, file, metadata),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'evidence'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Evidence> }) =>
      evidenceService.updateEvidence(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'evidence'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => evidenceService.deleteEvidence(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'evidence'] });
    },
  });

  const linkControlsMutation = useMutation({
    mutationFn: ({ evidenceId, controlIds }: { evidenceId: string; controlIds: string[] }) =>
      evidenceService.linkEvidenceToControls(evidenceId, controlIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments', assessmentId, 'evidence'] });
    },
  });

  const downloadEvidence = async (evidenceId: string, fileName: string) => {
    const blob = await evidenceService.downloadEvidence(evidenceId);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return {
    evidence,
    isLoading,
    error,
    uploadEvidence: uploadMutation.mutateAsync,
    updateEvidence: updateMutation.mutateAsync,
    deleteEvidence: deleteMutation.mutateAsync,
    linkControls: linkControlsMutation.mutateAsync,
    downloadEvidence,
    isUploading: uploadMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

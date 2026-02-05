import { useMutation, useQuery } from '@tanstack/react-query';
import { analysisApi } from '@/services/analysis-api';
import type { BackendTaskStatus } from '@/services/backend-types';

export function useStartTraining() {
  return useMutation({
    mutationFn: ({
      fileId,
      targetColumn,
      config: extra,
    }: {
      fileId: string;
      targetColumn: string;
      config?: Record<string, unknown>;
    }) => analysisApi.startTraining(fileId, targetColumn, extra),
  });
}

export function useTaskStatus(taskId: string | null) {
  return useQuery<BackendTaskStatus | null>({
    queryKey: ['task-status', taskId],
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return 2000;
      const done = ['COMPLETED', 'FAILURE', 'ERROR'].includes(status);
      return done ? false : 2000;
    },
    queryFn: async () => {
      if (!taskId) return null;
      return analysisApi.getTaskStatus(taskId);
    },
  });
}

import { useQuery } from '@tanstack/react-query';
import { config } from '@/lib/config';
import { modelsApi } from '@/services/models-api';
import { toModel, toModelDetail } from '@/services/adapters';
import { mockModels } from '@/lib/mock-data';
import type { Model } from '@/types';

export function useModels(experimentName?: string) {
  return useQuery<Model[]>({
    queryKey: ['models', experimentName],
    queryFn: async () => {
      if (config.useMock) {
        // Mock 모드: sessionId 기반 필터링
        if (experimentName) {
          const sid = experimentName.replace('session_', '');
          return mockModels.filter((m) => m.sessionId === sid);
        }
        return mockModels;
      }
      const res = await modelsApi.listModels(experimentName);
      return res.map(toModel);
    },
  });
}

export function useModel(runId: string | null) {
  return useQuery<Model | null>({
    queryKey: ['model', runId],
    enabled: !!runId,
    queryFn: async () => {
      if (!runId) return null;
      if (config.useMock) return mockModels.find((m) => m.id === runId) ?? null;
      const res = await modelsApi.getModel(runId);
      return toModelDetail(res);
    },
  });
}

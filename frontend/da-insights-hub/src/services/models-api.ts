import { apiClient } from './api-client';
import type {
  BackendModelSummary,
  BackendModelDetail,
  BackendPredictResponse,
  BackendExplainResponse,
} from './backend-types';

export const modelsApi = {
  listModels(experimentName?: string, limit = 100): Promise<BackendModelSummary[]> {
    const params = new URLSearchParams();
    if (experimentName) params.set('experiment_name', experimentName);
    if (limit !== 100) params.set('limit', String(limit));
    const q = params.toString();
    return apiClient.get<BackendModelSummary[]>(`/models${q ? `?${q}` : ''}`);
  },

  getModel(runId: string): Promise<BackendModelDetail> {
    return apiClient.get<BackendModelDetail>(`/models/${runId}`);
  },

  predict(runId: string, data: Record<string, unknown>[]): Promise<BackendPredictResponse> {
    return apiClient.post<BackendPredictResponse>(`/models/${runId}/predict`, { data });
  },

  explain(runId: string, topN = 10): Promise<BackendExplainResponse> {
    return apiClient.get<BackendExplainResponse>(`/models/${runId}/explain?top_n=${topN}`);
  },
};

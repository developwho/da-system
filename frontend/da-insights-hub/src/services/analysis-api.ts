import { apiClient } from './api-client';
import { config } from '@/lib/config';
import type { BackendTaskStartResponse, BackendTaskStatus } from './backend-types';

export const analysisApi = {
  startTraining(
    fileId: string,
    targetColumn: string,
    extraConfig?: Record<string, unknown>,
  ): Promise<BackendTaskStartResponse> {
    return apiClient.post<BackendTaskStartResponse>('/analysis/train', {
      file_id: fileId,
      target_column: targetColumn,
      config: extraConfig,
    });
  },

  getTaskStatus(taskId: string): Promise<BackendTaskStatus> {
    return apiClient.get<BackendTaskStatus>(`/analysis/tasks/${taskId}`);
  },

  cancelTask(taskId: string): Promise<{ message: string; task_id: string }> {
    return apiClient.delete<{ message: string; task_id: string }>(`/analysis/tasks/${taskId}`);
  },

  /**
   * Subscribe to SSE log stream for a Celery task.
   * Returns an abort function to stop listening.
   */
  streamTaskLogs(
    taskId: string,
    onEvent: (data: BackendTaskStatus) => void,
    onError?: (err: unknown) => void,
  ): () => void {
    const controller = new AbortController();
    const url = `${config.apiBaseUrl}/analysis/tasks/${taskId}/logs`;

    const headers: Record<string, string> = {};
    if (config.apiKey) headers['x-api-key'] = config.apiKey;

    fetch(url, { headers, signal: controller.signal })
      .then(async (res) => {
        if (!res.ok || !res.body) {
          onError?.(new Error(`SSE failed: ${res.status}`));
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6)) as BackendTaskStatus;
                onEvent(data);
              } catch {
                // skip malformed lines
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') onError?.(err);
      });

    return () => controller.abort();
  },
};

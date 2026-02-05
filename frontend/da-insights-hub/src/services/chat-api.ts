import { apiClient } from './api-client';
import type {
  BackendCreateSessionResponse,
  BackendSendMessageResponse,
  BackendSessionDetail,
  BackendSessionList,
  BackendDeleteResponse,
} from './backend-types';

export const chatApi = {
  createSession(fileId?: string): Promise<BackendCreateSessionResponse> {
    return apiClient.post<BackendCreateSessionResponse>('/chat/sessions', {
      ...(fileId ? { file_id: fileId } : {}),
    });
  },

  getSession(sessionId: string): Promise<BackendSessionDetail> {
    return apiClient.get<BackendSessionDetail>(`/chat/sessions/${sessionId}`);
  },

  sendMessage(sessionId: string, message: string): Promise<BackendSendMessageResponse> {
    return apiClient.post<BackendSendMessageResponse>(
      `/chat/sessions/${sessionId}/messages`,
      { message, role: 'user' },
    );
  },

  listSessions(limit = 50): Promise<BackendSessionList> {
    return apiClient.get<BackendSessionList>(`/chat/sessions?limit=${limit}`);
  },

  deleteSession(sessionId: string): Promise<BackendDeleteResponse> {
    return apiClient.delete<BackendDeleteResponse>(`/chat/sessions/${sessionId}`);
  },
};

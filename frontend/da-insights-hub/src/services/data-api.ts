import { apiClient } from './api-client';
import type {
  BackendUploadResponse,
  BackendFileList,
  BackendProfileResponse,
  BackendPreviewResponse,
  BackendDeleteResponse,
} from './backend-types';

export const dataApi = {
  uploadFile(file: File): Promise<BackendUploadResponse> {
    const form = new FormData();
    form.append('file', file);
    return apiClient.postFormData<BackendUploadResponse>('/data/upload', form);
  },

  listFiles(): Promise<BackendFileList> {
    return apiClient.get<BackendFileList>('/data');
  },

  getProfile(fileId: string, targetColumn?: string): Promise<BackendProfileResponse> {
    const q = targetColumn ? `?target_column=${encodeURIComponent(targetColumn)}` : '';
    return apiClient.get<BackendProfileResponse>(`/data/${fileId}/profile${q}`);
  },

  getPreview(fileId: string, limit = 100): Promise<BackendPreviewResponse> {
    return apiClient.get<BackendPreviewResponse>(`/data/${fileId}/preview?limit=${limit}`);
  },

  deleteFile(fileId: string): Promise<BackendDeleteResponse> {
    return apiClient.delete<BackendDeleteResponse>(`/data/${fileId}`);
  },
};

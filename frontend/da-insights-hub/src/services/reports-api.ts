import { apiClient } from './api-client';
import type {
  BackendReportContent,
  BackendReportSummary,
  BackendDeleteResponse,
} from './backend-types';

export const reportsApi = {
  listReports(): Promise<BackendReportSummary[]> {
    return apiClient.get<BackendReportSummary[]>('/reports');
  },

  getMarkdownReport(sessionId: string): Promise<BackendReportContent> {
    return apiClient.get<BackendReportContent>(`/reports/${sessionId}`);
  },

  async getHtmlReport(sessionId: string): Promise<string> {
    const res = await apiClient.getRaw(`/reports/${sessionId}/html`);
    if (!res.ok) throw new Error(`Failed to fetch HTML report: ${res.statusText}`);
    return res.text();
  },

  downloadArtifacts(sessionId: string): string {
    // Returns the download URL for the browser to fetch directly
    return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/reports/${sessionId}/download`;
  },

  deleteReport(sessionId: string): Promise<BackendDeleteResponse> {
    return apiClient.delete<BackendDeleteResponse>(`/reports/${sessionId}`);
  },
};

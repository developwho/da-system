import { useQuery } from '@tanstack/react-query';
import { config } from '@/lib/config';
import { reportsApi } from '@/services/reports-api';
import { toReport } from '@/services/adapters';
import { mockReports } from '@/lib/mock-data';
import type { Report } from '@/types';

export function useReports() {
  return useQuery<Report[]>({
    queryKey: ['reports'],
    queryFn: async () => {
      if (config.useMock) return mockReports;
      const res = await reportsApi.listReports();
      return res.map(toReport);
    },
  });
}

export function useReportContent(sessionId: string | null) {
  return useQuery<string | null>({
    queryKey: ['report-content', sessionId],
    enabled: !!sessionId,
    queryFn: async () => {
      if (!sessionId) return null;
      if (config.useMock) return '# Mock Report\n\nThis is a placeholder report.';
      const res = await reportsApi.getMarkdownReport(sessionId);
      return res.content;
    },
  });
}

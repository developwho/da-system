import { useQuery } from '@tanstack/react-query';
import { config } from '@/lib/config';
import { reportsApi } from '@/services/reports-api';
import { toReport } from '@/services/adapters';
import { mockReportMarkdownBySession, mockReports } from '@/lib/mock-data';
import type { Report } from '@/types';

export function useReports() {
  return useQuery<Report[]>({
    queryKey: ['reports'],
    queryFn: async () => {
      if (config.useMock) return mockReports;
      const res = await reportsApi.listReports();
      return res.map(toReport);
    },
    retry: 2,
    refetchOnWindowFocus: true,
    refetchOnMount: 'always',
    staleTime: 30_000,
  });
}

export function useReportContent(sessionId: string | null) {
  return useQuery<string | null>({
    queryKey: ['report-content', sessionId],
    enabled: !!sessionId,
    queryFn: async () => {
      if (!sessionId) return null;
      if (config.useMock) {
        return (
          mockReportMarkdownBySession[sessionId] ??
          mockReportMarkdownBySession['session-1'] ??
          '# Report not found in mock data.'
        );
      }
      const res = await reportsApi.getMarkdownReport(sessionId);
      return res.content;
    },
  });
}

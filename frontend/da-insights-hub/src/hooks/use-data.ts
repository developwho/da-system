import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { config } from '@/lib/config';
import { dataApi } from '@/services/data-api';
import { toDataFile, dataInfoToDataFile, toDataProfile } from '@/services/adapters';
import { mockDataFiles, generateMockProfile } from '@/lib/mock-data';
import type { DataFile, DataProfile } from '@/types';

export function useFiles() {
  return useQuery<DataFile[]>({
    queryKey: ['files'],
    queryFn: async () => {
      if (config.useMock) return mockDataFiles;
      const res = await dataApi.listFiles();
      return res.files.map(dataInfoToDataFile);
    },
  });
}

export function useFileProfile(fileId: string | null) {
  return useQuery<DataProfile | null>({
    queryKey: ['file-profile', fileId],
    enabled: !!fileId,
    queryFn: async () => {
      if (!fileId) return null;
      if (config.useMock) {
        const file = mockDataFiles.find((f) => f.id === fileId);
        return file ? generateMockProfile(file) : null;
      }
      const res = await dataApi.getProfile(fileId);
      return toDataProfile(res);
    },
  });
}

export function useUploadFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const res = await dataApi.uploadFile(file);
      return toDataFile(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['files'] });
    },
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) => dataApi.deleteFile(fileId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['files'] });
    },
  });
}

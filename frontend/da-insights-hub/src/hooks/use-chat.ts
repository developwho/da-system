import { useMutation, useQuery } from '@tanstack/react-query';
import { config } from '@/lib/config';
import { chatApi } from '@/services/chat-api';
import { toChatMessage } from '@/services/adapters';
import type { ChatMessage } from '@/types';

export function useCreateSession() {
  return useMutation({
    mutationFn: (fileId?: string) => chatApi.createSession(fileId),
  });
}

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['session', sessionId],
    enabled: !!sessionId && !config.useMock,
    queryFn: async () => {
      if (!sessionId) return null;
      const res = await chatApi.getSession(sessionId);
      return {
        ...res,
        messages: res.messages.map(toChatMessage),
      };
    },
  });
}

export function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    enabled: !config.useMock,
    queryFn: () => chatApi.listSessions(50),
    refetchInterval: 30_000,
  });
}

export function useSendMessage() {
  return useMutation({
    mutationFn: async ({
      sessionId,
      message,
    }: {
      sessionId: string;
      message: string;
    }): Promise<ChatMessage> => {
      const res = await chatApi.sendMessage(sessionId, message);
      return toChatMessage(res.message);
    },
  });
}

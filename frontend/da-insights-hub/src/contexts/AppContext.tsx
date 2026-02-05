import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { AppState, ChatMessage, ProgressCard } from '@/types';

interface AppContextValue extends AppState {
  // Chat state
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  appendToMessage: (id: string, chunk: string) => void;
  clearMessages: () => void;

  // Analysis state
  setCurrentAnalysis: (analysis: ProgressCard | null) => void;

  // WebSocket state
  setWsStatus: (status: AppState['wsStatus']) => void;

  // Session state
  setActiveSession: (sessionId: string | null) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  // Core app state
  const [activeSessionId, setActiveSessionId] = useState<string | null>('session-new');
  const [wsStatus, setWsStatus] = useState<AppState['wsStatus']>('disconnected');
  const [currentAnalysis, setCurrentAnalysis] = useState<ProgressCard | null>(null);

  // Chat messages
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const updateMessage = useCallback((id: string, updates: Partial<ChatMessage>) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
    );
  }, []);

  const appendToMessage = useCallback((id: string, chunk: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === id ? { ...msg, content: (msg.content || '') + chunk } : msg
      )
    );
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const setActiveSession = useCallback((sessionId: string | null) => {
    setActiveSessionId(sessionId);
  }, []);

  const value: AppContextValue = {
    // App state
    activeSessionId,
    wsStatus,
    currentAnalysis,

    // Chat
    messages,
    addMessage,
    updateMessage,
    appendToMessage,
    clearMessages,

    // Analysis
    setCurrentAnalysis,

    // WebSocket
    setWsStatus,

    // Session
    setActiveSession,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

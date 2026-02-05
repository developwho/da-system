import { useRef, useState, useCallback, useEffect } from 'react';
import { ChatWelcome } from '@/components/chat/ChatWelcome';
import { ChatMessages } from '@/components/chat/ChatMessages';
import { ChatInput } from '@/components/chat/ChatInput';
import type { InlineProgressState } from '@/components/chat/AnalysisProgress';
import { useApp } from '@/contexts/AppContext';
import { config } from '@/lib/config';
import { mockWebSocket } from '@/lib/mock-websocket';
import { realWebSocket } from '@/lib/websocket-client';
import { chatApi } from '@/services/chat-api';
import type { ChatMessage, MessageReceivedPayload, StatusUpdatePayload, MessageCard, StepStatus, SubStep } from '@/types';

// Pick transport based on feature flag
const ws = config.useMock ? mockWebSocket : realWebSocket;

const PROGRESS_MESSAGE_ID = 'analysis-progress';

const ALL_STEPS = [
  { id: 1, name: 'ProblemDefinition' },
  { id: 2, name: 'Research' },
  { id: 3, name: 'Modeling' },
  { id: 4, name: 'Insight' },
  { id: 5, name: 'Reporting' },
] as const;

export default function ChatPage() {
  const {
    messages,
    addMessage,
    appendToMessage,
    updateMessage,
    activeSessionId,
    setActiveSession,
    setWsStatus,
  } = useApp();
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentStreamingId = useRef<string | null>(null);
  const sessionCreating = useRef(false);
  const analysisStartTime = useRef<number>(0);
  const progressMessageAdded = useRef(false);
  const accumulatedSubSteps = useRef<SubStep[]>([]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Create a real backend session if needed
  useEffect(() => {
    if (config.useMock) return;
    if (activeSessionId && activeSessionId !== 'session-new') return;
    if (sessionCreating.current) return;

    sessionCreating.current = true;
    chatApi
      .createSession()
      .then((res) => {
        setActiveSession(res.session_id);
      })
      .catch((err) => {
        console.error('Failed to create session:', err);
      })
      .finally(() => {
        sessionCreating.current = false;
      });
  }, [activeSessionId, setActiveSession]);

  // Set up WebSocket listeners
  useEffect(() => {
    if (!activeSessionId || activeSessionId === 'session-new') return;

    ws.connect(activeSessionId);

    const unsubscribe = ws.subscribe((event) => {
      switch (event.type) {
        case 'connected':
          setWsStatus('connected');
          break;

        case 'disconnected':
          setWsStatus('disconnected');
          break;

        case 'message.received': {
          const payload = event.payload as MessageReceivedPayload;

          if (currentStreamingId.current !== payload.messageId) {
            // New message - create it
            currentStreamingId.current = payload.messageId;
            setIsTyping(false);
            addMessage({
              id: payload.messageId,
              role: 'assistant',
              content: payload.chunk,
              timestamp: new Date(),
              isStreaming: true,
            });
          } else {
            // Append to existing message
            appendToMessage(payload.messageId, payload.chunk);
          }
          break;
        }
        case 'message.complete': {
          const payload = event.payload as { messageId: string };
          updateMessage(payload.messageId, { isStreaming: false });
          currentStreamingId.current = null;
          break;
        }
        case 'status.update': {
          const payload = event.payload as StatusUpdatePayload;

          // Build step states
          const steps = ALL_STEPS.map((s) => ({
            id: s.id,
            name: s.name,
            status: (s.id < payload.step
              ? 'complete'
              : s.id === payload.step
                ? payload.status
                : 'pending') as StepStatus,
          }));

          // Track start time
          if (payload.step === 1 && analysisStartTime.current === 0) {
            analysisStartTime.current = Date.now();
          }

          // Accumulate subSteps from payload
          if (payload.subSteps) {
            for (const sub of payload.subSteps) {
              const idx = accumulatedSubSteps.current.findIndex((s) => s.id === sub.id);
              if (idx >= 0) {
                accumulatedSubSteps.current[idx] = sub;
              } else {
                accumulatedSubSteps.current.push(sub);
              }
            }
          }

          // Determine overall status
          let overallStatus: 'running' | 'complete' | 'failed' = 'running';
          if (payload.status === 'complete' && payload.step >= payload.totalSteps) {
            overallStatus = 'complete';
          } else if (payload.status === 'failed') {
            overallStatus = 'failed';
          }

          const progressState: InlineProgressState = {
            steps,
            currentStep: payload.step,
            totalSteps: payload.totalSteps,
            description: payload.description || '분석 진행 중...',
            overallStatus,
            progress: payload.progress ?? 0,
            startTime: analysisStartTime.current || Date.now(),
            subSteps: [...accumulatedSubSteps.current],
          };

          const progressCard: MessageCard = {
            type: 'progress',
            data: progressState as any,
          };

          // Add or update the progress message (useRef to avoid stale closure)
          if (!progressMessageAdded.current) {
            progressMessageAdded.current = true;
            addMessage({
              id: PROGRESS_MESSAGE_ID,
              role: 'assistant',
              content: '',
              timestamp: new Date(),
              cards: [progressCard],
            });
          } else {
            updateMessage(PROGRESS_MESSAGE_ID, { cards: [progressCard] });
          }

          // Reset on completion/failure
          if (overallStatus === 'complete' || overallStatus === 'failed') {
            analysisStartTime.current = 0;
          }
          break;
        }
      }
    });

    return () => {
      unsubscribe();
      ws.disconnect();
      setWsStatus('disconnected');
      // Reset progress tracking for next session
      progressMessageAdded.current = false;
      accumulatedSubSteps.current = [];
      analysisStartTime.current = 0;
    };
  }, [activeSessionId, addMessage, appendToMessage, updateMessage, setWsStatus]);

  const handleSendMessage = useCallback(
    async (content: string, fileId?: string) => {
      // Add user message
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date(),
        attachments: fileId
          ? [{ type: 'file', fileId, fileName: 'Uploaded file' }]
          : undefined,
      };
      addMessage(userMessage);

      // Show typing indicator
      setIsTyping(true);

      // Send to WebSocket
      await ws.sendMessage(content, fileId);
    },
    [addMessage]
  );

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          {!hasMessages ? (
            <ChatWelcome onAction={handleSendMessage} />
          ) : (
            <ChatMessages messages={messages} isTyping={isTyping} />
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-border bg-background p-4">
        <div className="mx-auto max-w-3xl">
          <ChatInput onSend={handleSendMessage} disabled={isTyping} />
        </div>
      </div>
    </div>
  );
}

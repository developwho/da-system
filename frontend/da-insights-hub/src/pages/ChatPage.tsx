import { useRef, useState, useCallback, useEffect } from 'react';
import { Upload } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { ChatWelcome } from '@/components/chat/ChatWelcome';
import { ChatMessages } from '@/components/chat/ChatMessages';
import { ChatInput, validateFiles } from '@/components/chat/ChatInput';
import type { InlineProgressState } from '@/components/chat/AnalysisProgress';
import { toast } from 'sonner';
import { useApp } from '@/contexts/AppContext';
import { config } from '@/lib/config';
import { mockWebSocket } from '@/lib/mock-websocket';
import { realWebSocket } from '@/lib/websocket-client';
import { chatApi } from '@/services/chat-api';
import type { ChatMessage, MessageReceivedPayload, StatusUpdatePayload, MessageCard, StepStatus, SubStep, ReportSummaryCard, AnalysisQuestionsPayload, AnalysisPlanPayload } from '@/types';

// Pick transport based on feature flag
const ws = config.useMock ? mockWebSocket : realWebSocket;

const PROGRESS_MESSAGE_ID = 'analysis-progress';
const QUESTIONS_MESSAGE_ID = 'analysis-questions';
const PLAN_MESSAGE_ID = 'analysis-plan';

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
  const queryClient = useQueryClient();
  const [isTyping, setIsTyping] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounter = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentStreamingId = useRef<string | null>(null);
  const sessionCreating = useRef(false);
  const analysisStartTime = useRef<number>(0);
  const accumulatedSubSteps = useRef<SubStep[]>([]);
  // Keep a ref to latest messages to avoid stale closures
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Create a session if needed
  useEffect(() => {
    if (activeSessionId && activeSessionId !== 'session-new') return;

    if (config.useMock) {
      // Mock mode: assign a default session ID immediately
      setActiveSession('session-1');
      return;
    }

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

          // Accumulate subSteps from payload, injecting phase from stepName
          if (payload.subSteps) {
            for (const sub of payload.subSteps) {
              const enriched: SubStep = { ...sub, phase: sub.phase || payload.stepName };
              const idx = accumulatedSubSteps.current.findIndex((s) => s.id === enriched.id);
              if (idx >= 0) {
                accumulatedSubSteps.current[idx] = enriched;
              } else {
                accumulatedSubSteps.current.push(enriched);
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

          // Check if progress message already exists in current messages (avoids stale ref)
          const existingProgress = messagesRef.current.find(
            (m) => m.id === PROGRESS_MESSAGE_ID
          );

          if (existingProgress) {
            updateMessage(PROGRESS_MESSAGE_ID, { cards: [progressCard] });
          } else {
            // Don't create new progress for already finished analyses
            if (overallStatus !== 'complete' && overallStatus !== 'failed') {
              addMessage({
                id: PROGRESS_MESSAGE_ID,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                cards: [progressCard],
              });
            }
          }

          // Reset on completion/failure
          if (overallStatus === 'complete' || overallStatus === 'failed') {
            analysisStartTime.current = 0;
          }
          break;
        }
        case 'report.ready': {
          const payload = event.payload as { sessionId: string; title: string; preview: string };
          queryClient.invalidateQueries({ queryKey: ['reports'] });
          addMessage({
            id: `report-${payload.sessionId}`,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            cards: [{
              type: 'report-summary',
              data: {
                sessionId: payload.sessionId,
                title: payload.title,
                preview: payload.preview,
              } as ReportSummaryCard,
            }],
          });
          break;
        }
        case 'analysis.questions': {
          const payload = event.payload as AnalysisQuestionsPayload;
          setIsTyping(false);
          addMessage({
            id: QUESTIONS_MESSAGE_ID,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            cards: [{
              type: 'analysis-questions',
              data: payload,
            }],
          });
          break;
        }
        case 'analysis.plan': {
          const payload = event.payload as AnalysisPlanPayload;
          addMessage({
            id: PLAN_MESSAGE_ID,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            cards: [{
              type: 'analysis-plan',
              data: payload,
            }],
          });
          break;
        }
      }
    });

    return () => {
      unsubscribe();
      ws.disconnect();
      setWsStatus('disconnected');
      // Reset substep accumulation for next session
      accumulatedSubSteps.current = [];
      analysisStartTime.current = 0;
      // NOTE: no progressMessageAdded ref reset needed — we check messages directly
    };
  }, [activeSessionId, addMessage, appendToMessage, updateMessage, setWsStatus, queryClient]);

  const handleSubmitAnswers = useCallback(
    (answers: Record<string, string>) => {
      // Mark the questions card as submitted
      const questionsMsg = messagesRef.current.find((m) => m.id === QUESTIONS_MESSAGE_ID);
      if (questionsMsg?.cards?.[0]) {
        const updatedData = { ...(questionsMsg.cards[0].data as AnalysisQuestionsPayload), submitted: true, answers };
        updateMessage(QUESTIONS_MESSAGE_ID, {
          cards: [{ type: 'analysis-questions', data: updatedData }],
        });
      }
      // Send answers to backend/mock
      ws.sendAnalysisAnswers(answers);
    },
    [updateMessage]
  );

  const handleConfirmPlan = useCallback(() => {
    // Mark the plan card as confirmed
    const planMsg = messagesRef.current.find((m) => m.id === PLAN_MESSAGE_ID);
    if (planMsg?.cards?.[0]) {
      const updatedData = { ...(planMsg.cards[0].data as AnalysisPlanPayload), confirmed: true };
      updateMessage(PLAN_MESSAGE_ID, {
        cards: [{ type: 'analysis-plan', data: updatedData }],
      });
    }
    // Start analysis
    ws.sendAnalysisConfirm();
  }, [updateMessage]);

  const handleEditPlan = useCallback(() => {
    // Re-enable the questions card for editing
    const questionsMsg = messagesRef.current.find((m) => m.id === QUESTIONS_MESSAGE_ID);
    if (questionsMsg?.cards?.[0]) {
      const updatedData = { ...(questionsMsg.cards[0].data as AnalysisQuestionsPayload), submitted: false };
      updateMessage(QUESTIONS_MESSAGE_ID, {
        cards: [{ type: 'analysis-questions', data: updatedData }],
      });
    }
    // Remove the plan card
    const planMsg = messagesRef.current.find((m) => m.id === PLAN_MESSAGE_ID);
    if (planMsg) {
      updateMessage(PLAN_MESSAGE_ID, { cards: [] });
    }
  }, [updateMessage]);

  const handleStopGeneration = useCallback(() => {
    setIsTyping(false);
    if (currentStreamingId.current) {
      updateMessage(currentStreamingId.current, { isStreaming: false });
      currentStreamingId.current = null;
    }
    // Stop mock analysis if running
    if (config.useMock && 'stopAnalysis' in ws) {
      (ws as any).stopAnalysis();
    }
  }, [updateMessage]);

  const handleRetry = useCallback(() => {
    // Find the last user message and resend it
    const lastUserMsg = [...messagesRef.current].reverse().find((m) => m.role === 'user');
    if (lastUserMsg) {
      setIsTyping(true);
      ws.sendMessage(lastUserMsg.content);
    }
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current = 0;
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    const { valid, invalid } = validateFiles(files);
    if (invalid.length > 0) {
      toast.error(`지원하지 않는 형식: ${invalid.join(', ')}`);
    }
    if (valid.length > 0) {
      // Use the exposed method to add files
      if ((ChatInput as any)._addFiles) {
        (ChatInput as any)._addFiles(valid);
      }
    }
  }, []);

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
    <div
      className="relative flex h-full flex-col"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-4 rounded-2xl border-2 border-dashed border-primary p-12">
            <Upload className="h-12 w-12 text-primary animate-bounce" />
            <p className="text-lg font-medium text-foreground">파일을 여기에 놓으세요</p>
            <p className="text-sm text-muted-foreground">CSV, Excel 파일을 지원합니다</p>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          {!hasMessages ? (
            <ChatWelcome onAction={handleSendMessage} />
          ) : (
            <ChatMessages
              messages={messages}
              isTyping={isTyping}
              onSubmitAnswers={handleSubmitAnswers}
              onConfirmPlan={handleConfirmPlan}
              onEditPlan={handleEditPlan}
              onStopGeneration={handleStopGeneration}
              onRetry={handleRetry}
            />
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

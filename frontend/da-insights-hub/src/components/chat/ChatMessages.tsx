import { useState } from 'react';
import { User, Loader2, Square, Copy, Check, RefreshCw, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';
import { toast } from 'sonner';
import { format, formatDistanceToNow, isToday } from 'date-fns';
import { ko } from 'date-fns/locale';
import type { ChatMessage, ReportSummaryCard, AnalysisQuestionsPayload, AnalysisPlanPayload } from '@/types';
import { cn } from '@/lib/utils';
import { AnalysisProgressInline, type InlineProgressState } from './AnalysisProgress';
import { ReportCardInline } from './ReportCard';
import { AnalysisQuestionnaire } from './AnalysisQuestionnaire';
import { AnalysisPlanCard } from './AnalysisPlanCard';

interface ChatMessagesProps {
  messages: ChatMessage[];
  isTyping: boolean;
  onSubmitAnswers?: (answers: Record<string, string>) => void;
  onConfirmPlan?: () => void;
  onEditPlan?: () => void;
  onStopGeneration?: () => void;
  onRetry?: () => void;
}

export function ChatMessages({ messages, isTyping, onSubmitAnswers, onConfirmPlan, onEditPlan, onStopGeneration, onRetry }: ChatMessagesProps) {
  return (
    <div className="space-y-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onSubmitAnswers={onSubmitAnswers}
          onConfirmPlan={onConfirmPlan}
          onEditPlan={onEditPlan}
          onRetry={onRetry}
        />
      ))}

      {isTyping && <TypingIndicator onStop={onStopGeneration} />}
    </div>
  );
}

function MessageActions({ message, onRetry }: { message: ChatMessage; onRetry?: () => void }) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const isAssistant = message.role === 'assistant';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      toast.success('복사됨');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('복사에 실패했습니다');
    }
  };

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedback(type);
    toast.success(type === 'up' ? '피드백 감사합니다!' : '개선하겠습니다');
  };

  if (!message.content) return null;

  return (
    <div className={cn(
      'flex items-center gap-0.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity',
      isAssistant ? 'justify-start' : 'justify-end'
    )}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopy}>
            {copied ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3 text-muted-foreground" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom"><p>복사</p></TooltipContent>
      </Tooltip>

      {isAssistant && onRetry && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onRetry}>
              <RefreshCw className="h-3 w-3 text-muted-foreground" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom"><p>재생성</p></TooltipContent>
        </Tooltip>
      )}

      {isAssistant && (
        <>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => handleFeedback('up')}
              >
                <ThumbsUp className={cn('h-3 w-3', feedback === 'up' ? 'text-primary fill-primary' : 'text-muted-foreground')} />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom"><p>좋아요</p></TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => handleFeedback('down')}
              >
                <ThumbsDown className={cn('h-3 w-3', feedback === 'down' ? 'text-destructive fill-destructive' : 'text-muted-foreground')} />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom"><p>별로예요</p></TooltipContent>
          </Tooltip>
        </>
      )}
    </div>
  );
}

function MessageTimestamp({ timestamp, align }: { timestamp: Date; align: 'left' | 'right' }) {
  const formatted = isToday(timestamp)
    ? format(timestamp, 'a h:mm', { locale: ko })
    : formatDistanceToNow(timestamp, { addSuffix: true, locale: ko });

  return (
    <p className={cn(
      'text-[10px] text-muted-foreground/60 mt-1',
      align === 'right' ? 'text-right' : 'text-left'
    )}>
      {formatted}
    </p>
  );
}

function MessageBubble({
  message,
  onSubmitAnswers,
  onConfirmPlan,
  onEditPlan,
  onRetry,
}: {
  message: ChatMessage;
  onSubmitAnswers?: (answers: Record<string, string>) => void;
  onConfirmPlan?: () => void;
  onEditPlan?: () => void;
  onRetry?: () => void;
}) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const progressCard = message.cards?.find((c) => c.type === 'progress');
  const reportCard = message.cards?.find((c) => c.type === 'report-summary');
  const questionsCard = message.cards?.find((c) => c.type === 'analysis-questions');
  const planCard = message.cards?.find((c) => c.type === 'analysis-plan');
  const isSpecialCard = progressCard || reportCard || questionsCard || planCard;
  const hasContent = !!message.content;

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <p className="text-sm text-muted-foreground">{message.content}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'group flex gap-4 animate-fade-in',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      {isUser ? (
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-secondary text-secondary-foreground text-xs">
            <User className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      ) : (
        <img src="/icon.svg" alt="DA" className="h-8 w-8 shrink-0 rounded-full" />
      )}

      {/* Message content + actions */}
      <div className={cn(
        isSpecialCard ? 'max-w-[90%] w-full' : 'max-w-[80%]',
      )}>
        <div
          className={cn(
            'rounded-2xl px-4 py-3',
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-card border border-border text-card-foreground'
          )}
        >
          {questionsCard ? (
            <AnalysisQuestionnaire
              data={questionsCard.data as AnalysisQuestionsPayload}
              onSubmit={onSubmitAnswers || (() => {})}
            />
          ) : planCard ? (
            <AnalysisPlanCard
              data={planCard.data as AnalysisPlanPayload}
              onConfirm={onConfirmPlan || (() => {})}
              onEdit={onEditPlan || (() => {})}
            />
          ) : progressCard ? (
            <AnalysisProgressInline state={progressCard.data as InlineProgressState} />
          ) : reportCard ? (
            <ReportCardInline data={reportCard.data as ReportSummaryCard} />
          ) : (
            <>
              {isUser ? (
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              ) : (
                <MarkdownRenderer content={message.content} className="prose-sm max-w-none" />
              )}
              {message.isStreaming && (
                <span className="inline-block h-4 w-1 animate-pulse bg-current" />
              )}
            </>
          )}
        </div>

        {/* Timestamp */}
        <MessageTimestamp timestamp={message.timestamp} align={isUser ? 'right' : 'left'} />

        {/* Actions (hover) */}
        {hasContent && !isSpecialCard && !message.isStreaming && (
          <MessageActions message={message} onRetry={!isUser ? onRetry : undefined} />
        )}
      </div>
    </div>
  );
}

function TypingIndicator({ onStop }: { onStop?: () => void }) {
  return (
    <div className="flex gap-4">
      <img src="/icon.svg" alt="DA" className="h-8 w-8 shrink-0 rounded-full" />

      <div className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3">
        <img src="/icon.svg" alt="" className="h-4 w-4 rounded-full animate-pulse" />
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">DA가 응답을 생성하고 있습니다...</span>
        {onStop && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 ml-1 hover:bg-destructive/10"
            onClick={onStop}
            title="생성 중지"
          >
            <Square className="h-3 w-3 fill-current text-destructive" />
          </Button>
        )}
      </div>
    </div>
  );
}

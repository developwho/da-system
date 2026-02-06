import { Brain, User } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
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
}

export function ChatMessages({ messages, isTyping, onSubmitAnswers, onConfirmPlan, onEditPlan }: ChatMessagesProps) {
  return (
    <div className="space-y-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onSubmitAnswers={onSubmitAnswers}
          onConfirmPlan={onConfirmPlan}
          onEditPlan={onEditPlan}
        />
      ))}

      {isTyping && <TypingIndicator />}
    </div>
  );
}

function MessageBubble({
  message,
  onSubmitAnswers,
  onConfirmPlan,
  onEditPlan,
}: {
  message: ChatMessage;
  onSubmitAnswers?: (answers: Record<string, string>) => void;
  onConfirmPlan?: () => void;
  onEditPlan?: () => void;
}) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const progressCard = message.cards?.find((c) => c.type === 'progress');
  const reportCard = message.cards?.find((c) => c.type === 'report-summary');
  const questionsCard = message.cards?.find((c) => c.type === 'analysis-questions');
  const planCard = message.cards?.find((c) => c.type === 'analysis-plan');
  const isSpecialCard = progressCard || reportCard || questionsCard || planCard;

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
        'flex gap-4 animate-fade-in',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback
          className={cn(
            'text-xs',
            isUser ? 'bg-secondary text-secondary-foreground' : 'bg-primary text-primary-foreground'
          )}
        >
          {isUser ? <User className="h-4 w-4" /> : <Brain className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      {/* Message content */}
      <div
        className={cn(
          'rounded-2xl px-4 py-3',
          isSpecialCard ? 'max-w-[90%] w-full' : 'max-w-[80%]',
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
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <MessageContent content={message.content} />
            </div>
            {message.isStreaming && (
              <span className="inline-block h-4 w-1 animate-pulse bg-current" />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function MessageContent({ content }: { content: string }) {
  // Simple markdown-like rendering
  const lines = content.split('\n');

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith('## ')) {
          return (
            <h3 key={i} className="text-base font-semibold mt-4 first:mt-0">
              {line.slice(3)}
            </h3>
          );
        }
        if (line.startsWith('### ')) {
          return (
            <h4 key={i} className="text-sm font-semibold mt-3 first:mt-0">
              {line.slice(4)}
            </h4>
          );
        }

        // List items
        if (line.startsWith('- ') || line.startsWith('• ')) {
          return (
            <p key={i} className="flex gap-2 text-sm">
              <span>•</span>
              <span>{renderInlineMarkdown(line.slice(2))}</span>
            </p>
          );
        }

        // Numbered list
        const numberedMatch = line.match(/^(\d+)\.\s+/);
        if (numberedMatch) {
          return (
            <p key={i} className="flex gap-2 text-sm">
              <span className="text-muted-foreground">{numberedMatch[1]}.</span>
              <span>{renderInlineMarkdown(line.slice(numberedMatch[0].length))}</span>
            </p>
          );
        }

        // Empty line
        if (!line.trim()) {
          return <div key={i} className="h-2" />;
        }

        // Regular paragraph
        return (
          <p key={i} className="text-sm">
            {renderInlineMarkdown(line)}
          </p>
        );
      })}
    </div>
  );
}

function renderInlineMarkdown(text: string): React.ReactNode {
  // Handle **bold** text
  const parts = text.split(/(\*\*[^*]+\*\*)/g);

  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

function TypingIndicator() {
  return (
    <div className="flex gap-4">
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className="bg-primary text-primary-foreground text-xs">
          <Brain className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>

      <div className="flex items-center gap-1 rounded-2xl border border-border bg-card px-4 py-3">
        <div className="typing-indicator flex gap-1">
          <span className="h-2 w-2 rounded-full bg-muted-foreground" />
          <span className="h-2 w-2 rounded-full bg-muted-foreground" />
          <span className="h-2 w-2 rounded-full bg-muted-foreground" />
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { Plus, Trash2, MessageSquare, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import type { BackendSessionSummary } from '@/services/backend-types';

interface SessionListProps {
  sessions: BackendSessionSummary[];
  activeSessionId: string | null;
  isLoading: boolean;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
}

export function SessionList({
  sessions,
  activeSessionId,
  isLoading,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}: SessionListProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-2">
      {/* New chat button */}
      <Button
        variant="outline"
        className="w-full gap-2 justify-start"
        onClick={onNewChat}
      >
        <Plus className="h-4 w-4" />
        새 채팅
      </Button>

      {/* Session list */}
      <ScrollArea className="flex-1 max-h-[300px]">
        {isLoading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : sessions.length === 0 ? (
          <p className="px-2 py-4 text-xs text-muted-foreground text-center">
            대화 기록이 없습니다
          </p>
        ) : (
          <div className="space-y-1">
            {sessions.map((session) => {
              const isActive = session.session_id === activeSessionId;
              const isHovered = hoveredId === session.session_id;
              const timeAgo = formatDistanceToNow(
                new Date(session.updated_at || session.created_at),
                { addSuffix: true, locale: ko }
              );

              return (
                <button
                  key={session.session_id}
                  className={cn(
                    'w-full flex items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors',
                    isActive
                      ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                  )}
                  onClick={() => onSelectSession(session.session_id)}
                  onMouseEnter={() => setHoveredId(session.session_id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-xs">
                      {session.session_id.slice(0, 8)}...
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {timeAgo} · {session.message_count}개 메시지
                    </p>
                  </div>
                  {isHovered && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0 opacity-70 hover:opacity-100 hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.session_id);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

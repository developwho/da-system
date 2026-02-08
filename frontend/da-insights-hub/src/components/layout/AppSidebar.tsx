import { MessageSquare, Database, Crown, FileText, HelpCircle, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { NavLink } from '@/components/NavLink';
import { Separator } from '@/components/ui/separator';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar';
import { useApp } from '@/contexts/AppContext';
import { useSessions } from '@/hooks/use-chat';
import { chatApi } from '@/services/chat-api';
import { SessionList } from '@/components/chat/SessionList';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';

const navItems = [
  { title: '채팅', url: '/', icon: MessageSquare },
  { title: '데이터', url: '/data', icon: Database },
  { title: '모델', url: '/models', icon: Crown },
  { title: '리포트', url: '/reports', icon: FileText },
];

export function AppSidebar() {
  const { state, toggleSidebar } = useSidebar();
  const isCollapsed = state === 'collapsed';
  const location = useLocation();
  const navigate = useNavigate();
  const isChatPage = location.pathname === '/';
  const { activeSessionId, setActiveSession, clearMessages } = useApp();
  const { data: sessionsData, isLoading: isSessionsLoading } = useSessions();
  const queryClient = useQueryClient();

  const handleNewChat = () => {
    clearMessages();
    setActiveSession('session-new');
    navigate('/');
  };

  const handleSelectSession = (sessionId: string) => {
    if (sessionId === activeSessionId) return;
    clearMessages();
    setActiveSession(sessionId);
    navigate('/');
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await chatApi.deleteSession(sessionId);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      if (sessionId === activeSessionId) {
        handleNewChat();
      }
      toast.success('세션이 삭제되었습니다');
    } catch {
      toast.error('세션 삭제에 실패했습니다');
    }
  };

  return (
    <Sidebar
      className="border-r border-border bg-sidebar"
      collapsible="icon"
    >
      <SidebarHeader className="border-b border-sidebar-border p-4">
        <div className="flex items-center gap-3">
          <img src="/icon.svg" alt="DA System" className="h-8 w-8 rounded-full" />
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-sidebar-foreground">DA System</span>
              <span className="text-xs text-muted-foreground">v1.0</span>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent className="p-2">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
                    <NavLink
                      to={item.url}
                      end={item.url === '/'}
                      className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      activeClassName="bg-sidebar-accent text-foreground font-medium"
                    >
                      <item.icon className="h-5 w-5 shrink-0" />
                      {!isCollapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Session history - only on chat page and expanded sidebar */}
        {isChatPage && !isCollapsed && (
          <SidebarGroup>
            <SidebarGroupLabel className="text-xs text-muted-foreground">대화 기록</SidebarGroupLabel>
            <SidebarGroupContent>
              <SessionList
                sessions={sessionsData?.sessions ?? []}
                activeSessionId={activeSessionId}
                isLoading={isSessionsLoading}
                onSelectSession={handleSelectSession}
                onNewChat={handleNewChat}
                onDeleteSession={handleDeleteSession}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="p-2">
        <Separator className="mb-2" />

        {/* Help */}
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip="도움말"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              onClick={() => toast.info('준비 중인 기능입니다')}
            >
              <HelpCircle className="h-5 w-5 shrink-0" />
              {!isCollapsed && <span>도움말</span>}
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        {/* Sidebar toggle */}
        <Separator className="my-2" />
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip={isCollapsed ? '사이드바 펼치기' : '사이드바 접기'}
              onClick={toggleSidebar}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            >
              {isCollapsed ? (
                <ChevronsRight className="h-5 w-5 shrink-0" />
              ) : (
                <>
                  <ChevronsLeft className="h-5 w-5 shrink-0" />
                  <span>사이드바 접기</span>
                </>
              )}
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}

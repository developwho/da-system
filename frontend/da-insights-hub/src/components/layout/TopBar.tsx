import { Settings, User, Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useApp } from '@/contexts/AppContext';
import { config } from '@/lib/config';
import { useTheme } from '@/hooks/use-theme';

const statusColors: Record<string, string> = {
  connected: 'bg-green-500',
  connecting: 'bg-yellow-500',
  disconnected: 'bg-red-500',
  error: 'bg-red-500',
};

const statusLabels: Record<string, string> = {
  connected: '연결됨',
  connecting: '연결 중...',
  disconnected: '연결 안됨',
  error: '오류',
};

export function TopBar() {
  const { wsStatus } = useApp();
  const { resolved, toggle } = useTheme();

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4">
      <div className="flex items-center gap-2">
        <SidebarTrigger className="h-8 w-8" />
      </div>

      <div className="flex items-center gap-3">
        {/* Connection status */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <div className={`h-2 w-2 rounded-full ${statusColors[wsStatus] || statusColors.disconnected}`} />
          <span>{statusLabels[wsStatus] || '연결 안됨'}</span>
          {config.useMock && (
            <span className="ml-1 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium">MOCK</span>
          )}
        </div>

        {/* Dark mode toggle */}
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggle}>
          {resolved === 'dark' ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>

        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Settings className="h-4 w-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 rounded-full p-0">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                  U
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel>내 계정</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              프로필
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              설정
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

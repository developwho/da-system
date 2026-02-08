import { Link } from 'react-router-dom';
import { MessageSquare, Database, Crown, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';

const quickLinks = [
  { to: '/', label: '채팅', icon: MessageSquare },
  { to: '/data', label: '데이터', icon: Database },
  { to: '/models', label: '모델', icon: Crown },
  { to: '/reports', label: '리포트', icon: FileText },
];

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center space-y-6 px-4">
        <h1 className="text-6xl font-bold text-foreground">404</h1>
        <div>
          <p className="text-xl text-muted-foreground">
            페이지를 찾을 수 없습니다
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            요청하신 페이지가 존재하지 않거나 이동되었습니다.
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-2">
          {quickLinks.map((link) => (
            <Button key={link.to} variant="outline" asChild>
              <Link to={link.to} className="gap-2">
                <link.icon className="h-4 w-4" />
                {link.label}
              </Link>
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}

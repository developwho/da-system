import { FileUp, TrendingUp, FileText } from 'lucide-react';

interface ChatWelcomeProps {
  onAction: (content: string, fileId?: string) => void;
}

const quickActions = [
  {
    icon: TrendingUp,
    title: '에너지 가격 예측',
    description: 'AI 에이전트가 도시가스 도입 원가를 분석하고 예측합니다',
    action: '다음 달 도시가스 가격을 예측하고 싶어요',
  },
  {
    icon: FileUp,
    title: '데이터 업로드',
    description: 'CSV 또는 Excel 파일을 업로드하여 분석을 시작하세요',
    action: '데이터셋을 분석하고 싶습니다',
  },
  {
    icon: FileText,
    title: '시스템 안내',
    description: '어떤 분석이 가능한지 알아보세요',
    action: '이 시스템으로 어떤 분석을 할 수 있나요?',
  },
];

export function ChatWelcome({ onAction }: ChatWelcomeProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      {/* Header */}
      <div className="mb-10 text-center">
        <h1 className="mb-3 text-4xl font-bold text-foreground">
          DA System에 오신 것을 환영합니다
        </h1>
        <p className="text-base text-muted-foreground">
          AI 기반 데이터 분석 어시스턴트
        </p>
      </div>

      {/* Quick actions */}
      <div className="grid w-full max-w-3xl gap-4 px-4 sm:grid-cols-3">
        {quickActions.map((action) => (
          <button
            key={action.title}
            className="group flex flex-col items-center rounded-xl border border-border bg-card p-6 text-center transition-all hover:border-muted-foreground/50 hover:bg-accent"
            onClick={() => onAction(action.action)}
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <action.icon className="h-5 w-5 text-foreground" />
            </div>
            <h3 className="mb-1.5 font-semibold text-foreground">{action.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{action.description}</p>
          </button>
        ))}
      </div>

      {/* Hint */}
      <p className="mt-10 text-sm text-muted-foreground">
        파일을 드래그하거나 메시지를 입력하여 시작하세요
      </p>
    </div>
  );
}

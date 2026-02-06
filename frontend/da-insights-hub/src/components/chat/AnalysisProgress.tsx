import { CheckCircle, Loader2, Circle, XCircle, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { useEffect, useRef, useState, useMemo } from 'react';
import type { StepStatus, SubStep } from '@/types';

export interface InlineProgressStep {
  id: number;
  name: string;
  status: StepStatus;
}

export interface InlineProgressState {
  steps: InlineProgressStep[];
  currentStep: number;
  totalSteps: number;
  description: string;
  overallStatus: 'running' | 'complete' | 'failed';
  progress: number;
  startTime: number;
  subSteps?: SubStep[];
}

const STEP_LABELS: Record<string, string> = {
  ProblemDefinition: '문제 정의',
  Research: '선행연구',
  Modeling: '모델 학습',
  Insight: '인사이트',
  Reporting: '리포트',
};

function getStepLabel(name: string): string {
  return STEP_LABELS[name] || name;
}

function StepIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case 'complete':
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'running':
      return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-destructive" />;
    default:
      return <Circle className="h-5 w-5 text-muted-foreground/40" />;
  }
}

function SubStepIcon({ status }: { status: SubStep['status'] }) {
  switch (status) {
    case 'complete':
      return <span className="text-green-500 text-xs">✓</span>;
    case 'running':
      return <span className="text-primary text-xs animate-spin inline-block">⟳</span>;
    case 'failed':
      return <span className="text-destructive text-xs">✕</span>;
    default:
      return <span className="text-muted-foreground/40 text-xs">○</span>;
  }
}

function ElapsedTimer({ startTime }: { startTime: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startTime) return;
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  const display = minutes > 0 ? `${minutes}분 ${seconds}초` : `${seconds}초`;

  return (
    <span className="flex items-center gap-1 text-xs text-muted-foreground">
      <Clock className="h-3 w-3" />
      경과: {display}
    </span>
  );
}

/** Group substeps by phase, each phase gets its own collapsible section */
function PhaseGroupedSubStepsLog({ subSteps }: { subSteps: SubStep[] }) {
  // Group by phase
  const groups = useMemo(() => {
    const map = new Map<string, SubStep[]>();
    for (const sub of subSteps) {
      const phase = sub.phase || 'Unknown';
      if (!map.has(phase)) map.set(phase, []);
      map.get(phase)!.push(sub);
    }
    return map;
  }, [subSteps]);

  if (subSteps.length === 0) return null;

  return (
    <div className="mt-2 border-t border-border/50 pt-2 space-y-1">
      {Array.from(groups.entries()).map(([phase, items]) => (
        <PhaseSection key={phase} phase={phase} items={items} />
      ))}
    </div>
  );
}

function PhaseSection({ phase, items }: { phase: string; items: SubStep[] }) {
  const hasRunning = items.some((s) => s.status === 'running');
  const [isOpen, setIsOpen] = useState(hasRunning);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-open when phase becomes active, auto-close when completed
  useEffect(() => {
    if (hasRunning) setIsOpen(true);
  }, [hasRunning]);

  // Auto-scroll within this group
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      });
    }
  }, [items.length, isOpen]);

  const label = getStepLabel(phase);
  const completeCount = items.filter((s) => s.status === 'complete').length;

  return (
    <div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
      >
        {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span className={hasRunning ? 'shimmer-text font-medium' : ''}>
          {label}
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/60">
          {completeCount}/{items.length}
        </span>
      </button>
      {isOpen && (
        <div
          ref={scrollRef}
          className="mt-1 ml-3 max-h-28 overflow-y-scroll substep-log-scroll space-y-0.5 pr-1"
        >
          {items.map((sub, i) => (
            <div
              key={sub.id}
              className="flex items-start gap-1.5 text-xs animate-in fade-in duration-300"
              style={{ animationDelay: `${i * 30}ms` }}
            >
              <span className="mt-0.5 flex-shrink-0 w-3 text-center">
                <SubStepIcon status={sub.status} />
              </span>
              <span
                className={
                  sub.status === 'running'
                    ? 'text-foreground'
                    : sub.status === 'complete'
                      ? 'text-muted-foreground'
                      : sub.status === 'failed'
                        ? 'text-destructive'
                        : 'text-muted-foreground/60'
                }
              >
                {sub.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface AnalysisProgressInlineProps {
  state: InlineProgressState;
}

export function AnalysisProgressInline({ state }: AnalysisProgressInlineProps) {
  const { steps, description, overallStatus, progress, startTime, subSteps } = state;

  const overallPercentage =
    overallStatus === 'complete'
      ? 100
      : overallStatus === 'failed'
        ? progress
        : Math.max(
            0,
            Math.round(
              ((steps.filter((s) => s.status === 'complete').length +
                (progress > 0 ? progress / 100 : 0)) /
                steps.length) *
                100
            )
          );

  return (
    <div className="w-full space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className={`text-sm font-medium text-foreground ${overallStatus === 'running' ? 'shimmer-text' : ''}`}>
          {overallStatus === 'complete'
            ? '분석 완료'
            : overallStatus === 'failed'
              ? '분석 실패'
              : '데이터 분석을 진행하고 있습니다'}
        </span>
        {overallStatus === 'running' && startTime > 0 && (
          <ElapsedTimer startTime={startTime} />
        )}
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-between w-full">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center flex-1 last:flex-none">
            {/* Step circle + label */}
            <div className="flex flex-col items-center gap-1">
              <StepIcon status={step.status} />
              <span
                className={`text-[10px] leading-tight text-center whitespace-nowrap ${
                  step.status === 'running'
                    ? 'font-semibold text-primary shimmer-text'
                    : step.status === 'complete'
                      ? 'text-green-600 dark:text-green-400'
                      : step.status === 'failed'
                        ? 'text-destructive'
                        : 'text-muted-foreground'
                }`}
              >
                {getStepLabel(step.name)}
              </span>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div
                className={`flex-1 h-px mx-1.5 mt-[-14px] ${
                  step.status === 'complete'
                    ? 'bg-green-500'
                    : 'bg-muted-foreground/20'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <Progress value={overallPercentage} className="h-2" />

      {/* Description + percentage */}
      <div className="flex items-center justify-between">
        <span className={`text-xs text-muted-foreground ${overallStatus === 'running' ? 'shimmer-text' : ''}`}>
          {description}
        </span>
        <span className="text-xs font-medium text-muted-foreground">
          {overallPercentage}%
        </span>
      </div>

      {/* Phase-grouped sub-steps log */}
      {subSteps && subSteps.length > 0 && <PhaseGroupedSubStepsLog subSteps={subSteps} />}
    </div>
  );
}

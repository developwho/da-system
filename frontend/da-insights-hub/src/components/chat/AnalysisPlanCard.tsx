import { CheckCircle2, Clock, Play, Pencil, Target, BarChart3 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { AnalysisPlanPayload } from '@/types';

interface AnalysisPlanCardProps {
  data: AnalysisPlanPayload;
  onConfirm: () => void;
  onEdit: () => void;
}

const PROBLEM_TYPE_LABELS: Record<string, string> = {
  binary_classification: '이진 분류',
  multiclass_classification: '다중 분류',
  regression: '회귀',
  time_series: '시계열',
};

export function AnalysisPlanCard({ data, onConfirm, onEdit }: AnalysisPlanCardProps) {
  const { plan, confirmed } = data;

  return (
    <div className="w-full space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Target className="h-5 w-5 text-primary" />
        <span className="text-sm font-medium">분석 계획</span>
        {confirmed && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            <CheckCircle2 className="h-3 w-3 mr-0.5" />
            시작됨
          </Badge>
        )}
      </div>

      {/* Plan summary */}
      <div className="bg-muted/30 rounded-lg p-3 space-y-2 text-sm">
        <div className="flex items-start gap-2">
          <span className="text-muted-foreground shrink-0 w-16">목표:</span>
          <span>{plan.analysisGoal}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground shrink-0 w-16">타겟:</span>
          <Badge variant="outline" className="text-xs">{plan.targetColumn}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground shrink-0 w-16">유형:</span>
          <Badge variant="outline" className="text-xs">
            {PROBLEM_TYPE_LABELS[plan.problemType] || plan.problemType}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground shrink-0 w-16">지표:</span>
          <Badge variant="outline" className="text-xs">
            <BarChart3 className="h-3 w-3 mr-0.5" />
            {plan.evaluationMetric}
          </Badge>
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-1.5">
        <span className="text-xs font-medium text-muted-foreground">분석 진행 과정</span>
        {plan.steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground w-4 text-right">{i + 1}.</span>
            <span className="font-medium">{step.name}</span>
            <span className="text-muted-foreground">- {step.description}</span>
          </div>
        ))}
      </div>

      {/* Estimated time */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Clock className="h-3.5 w-3.5" />
        예상 소요 시간: {plan.estimatedDuration}
      </div>

      {/* Actions */}
      {!confirmed ? (
        <div className="flex items-center gap-2">
          <Button onClick={onConfirm} size="sm" className="flex-1">
            <Play className="h-3.5 w-3.5 mr-1" />
            분석 시작
          </Button>
          <Button onClick={onEdit} variant="outline" size="sm">
            <Pencil className="h-3.5 w-3.5 mr-1" />
            설정 수정
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
          <CheckCircle2 className="h-3.5 w-3.5" />
          분석이 시작되었습니다
        </div>
      )}
    </div>
  );
}

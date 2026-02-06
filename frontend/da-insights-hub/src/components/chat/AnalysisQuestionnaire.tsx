import { useState } from 'react';
import { ClipboardList, Database, Columns, Hash, Type, AlertTriangle, HardDrive, Star } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { AnalysisQuestionsPayload, AnalysisQuestion } from '@/types';

interface AnalysisQuestionnaireProps {
  data: AnalysisQuestionsPayload;
  onSubmit: (answers: Record<string, string>) => void;
}

function DataProfileSummary({ profile }: { profile: AnalysisQuestionsPayload['profile'] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
      <div className="flex items-center gap-1.5 text-xs">
        <Database className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">행:</span>
        <Badge variant="secondary" className="text-xs px-1.5 py-0">
          {profile.rows.toLocaleString()}
        </Badge>
      </div>
      <div className="flex items-center gap-1.5 text-xs">
        <Columns className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">열:</span>
        <Badge variant="secondary" className="text-xs px-1.5 py-0">
          {profile.columns}
        </Badge>
      </div>
      <div className="flex items-center gap-1.5 text-xs">
        <Hash className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">숫자형:</span>
        <Badge variant="secondary" className="text-xs px-1.5 py-0">
          {profile.numericColumns.length}
        </Badge>
      </div>
      <div className="flex items-center gap-1.5 text-xs">
        <Type className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">범주형:</span>
        <Badge variant="secondary" className="text-xs px-1.5 py-0">
          {profile.categoricalColumns.length}
        </Badge>
      </div>
      <div className="flex items-center gap-1.5 text-xs">
        <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">결측치:</span>
        <Badge variant={profile.missingCellsPct > 10 ? 'destructive' : 'secondary'} className="text-xs px-1.5 py-0">
          {profile.missingCellsPct.toFixed(1)}%
        </Badge>
      </div>
      <div className="flex items-center gap-1.5 text-xs">
        <HardDrive className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">메모리:</span>
        <Badge variant="secondary" className="text-xs px-1.5 py-0">
          {profile.memoryMB.toFixed(1)} MB
        </Badge>
      </div>
    </div>
  );
}

function QuestionItem({
  question,
  value,
  onChange,
  disabled,
}: {
  question: AnalysisQuestion;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm font-medium">
        {question.label}
        {question.required && <span className="text-destructive ml-0.5">*</span>}
      </Label>
      {question.description && (
        <p className="text-xs text-muted-foreground">{question.description}</p>
      )}

      {question.type === 'text' && (
        <Input
          placeholder={question.placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="text-sm h-8"
        />
      )}

      {question.type === 'select' && question.options && (
        <Select value={value} onValueChange={onChange} disabled={disabled}>
          <SelectTrigger className="text-sm h-8">
            <SelectValue placeholder={question.placeholder || '선택하세요'} />
          </SelectTrigger>
          <SelectContent>
            {question.options.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                <span className="flex items-center gap-1.5">
                  {opt.label}
                  {opt.recommended && (
                    <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                  )}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {question.type === 'radio' && question.options && (
        <RadioGroup value={value} onValueChange={onChange} disabled={disabled} className="space-y-1">
          {question.options.map((opt) => (
            <div key={opt.value} className="flex items-start gap-2">
              <RadioGroupItem value={opt.value} id={`${question.id}-${opt.value}`} className="mt-0.5" />
              <Label
                htmlFor={`${question.id}-${opt.value}`}
                className="text-sm font-normal cursor-pointer flex items-center gap-1.5"
              >
                {opt.label}
                {opt.recommended && (
                  <Badge variant="outline" className="text-[10px] px-1 py-0 border-yellow-500 text-yellow-600">
                    추천
                  </Badge>
                )}
                {opt.reason && (
                  <span className="text-xs text-muted-foreground">- {opt.reason}</span>
                )}
              </Label>
            </div>
          ))}
        </RadioGroup>
      )}
    </div>
  );
}

export function AnalysisQuestionnaire({ data, onSubmit }: AnalysisQuestionnaireProps) {
  const { profile, questions, submitted, answers: submittedAnswers } = data;

  // Initialize form state from defaults or submitted answers
  const [answers, setAnswers] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const q of questions) {
      initial[q.id] = submittedAnswers?.[q.id] || q.defaultValue || '';
    }
    return initial;
  });

  const isDisabled = !!submitted;

  const allRequiredFilled = questions
    .filter((q) => q.required)
    .every((q) => answers[q.id]?.trim());

  const handleSubmit = () => {
    if (!allRequiredFilled) return;
    onSubmit(answers);
  };

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <ClipboardList className="h-5 w-5 text-primary" />
        <span className="text-sm font-medium">분석 설정</span>
        {submitted && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">제출 완료</Badge>
        )}
      </div>

      {/* Profile summary */}
      <DataProfileSummary profile={profile} />

      {/* Questions */}
      <div className="space-y-4">
        {questions.map((q) => (
          <QuestionItem
            key={q.id}
            question={q}
            value={answers[q.id] || ''}
            onChange={(val) => setAnswers((prev) => ({ ...prev, [q.id]: val }))}
            disabled={isDisabled}
          />
        ))}
      </div>

      {/* Submit */}
      {!submitted && (
        <Button
          onClick={handleSubmit}
          disabled={!allRequiredFilled}
          className="w-full"
          size="sm"
        >
          분석 설정 완료
        </Button>
      )}
    </div>
  );
}

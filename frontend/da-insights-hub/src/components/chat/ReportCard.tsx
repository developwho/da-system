import { useState } from 'react';
import { FileText, ExternalLink, Download, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ReportSummaryCard } from '@/types';
import { config } from '@/lib/config';

interface ReportCardInlineProps {
  data: ReportSummaryCard;
}

export function ReportCardInline({ data }: ReportCardInlineProps) {
  const [expanded, setExpanded] = useState(false);
  const { sessionId, title, preview } = data;

  const previewLines = preview?.trim() || '';
  const isLong = previewLines.length > 500;
  const displayText = expanded ? previewLines : previewLines.slice(0, 500);

  const handleViewFull = () => {
    window.open(`/reports?id=${sessionId}`, '_blank');
  };

  const handleViewHtml = () => {
    const baseUrl = config.useMock ? '' : '/api/v1';
    window.open(`${baseUrl}/reports/${sessionId}/html`, '_blank');
  };

  const handleDownload = () => {
    const baseUrl = config.useMock ? '' : '/api/v1';
    window.open(`${baseUrl}/reports/${sessionId}/download`, '_blank');
  };

  return (
    <div className="w-full space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <FileText className="h-5 w-5 text-primary" />
        <span className="text-sm font-medium text-foreground">
          {title || '분석 리포트'}
        </span>
      </div>

      {/* Markdown preview */}
      {previewLines && (
        <div className="relative">
          <div
            className={`text-xs text-muted-foreground whitespace-pre-wrap font-mono bg-muted/30 rounded-lg p-3 ${
              !expanded && isLong ? 'max-h-40 overflow-hidden' : ''
            }`}
          >
            {displayText}
            {!expanded && isLong && '...'}
          </div>
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 mt-1 transition-colors"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3" /> 접기
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3" /> 더 보기
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="text-xs h-7"
          onClick={handleViewFull}
        >
          <ExternalLink className="h-3 w-3 mr-1" />
          전체 리포트 보기
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-xs h-7"
          onClick={handleViewHtml}
        >
          <FileText className="h-3 w-3 mr-1" />
          HTML로 보기
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-xs h-7"
          onClick={handleDownload}
        >
          <Download className="h-3 w-3 mr-1" />
          다운로드
        </Button>
      </div>
    </div>
  );
}

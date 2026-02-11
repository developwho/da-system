import { Fragment, useState } from 'react';
import {
  FileText,
  Download,
  ExternalLink,
  Zap,
  CheckCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useReports, useReportContent } from '@/hooks/use-reports';
import { reportsApi } from '@/services/reports-api';
import { config } from '@/lib/config';
import { Skeleton } from '@/components/ui/skeleton';
import { format, formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import type { Report } from '@/types';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

export default function ReportsPage() {
  const { data: reports = [], isLoading } = useReports();
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const {
    data: reportContent,
    isLoading: isReportLoading,
    isError: isReportError,
    refetch: refetchReportContent,
  } = useReportContent(selectedReportId);

  const handleDownload = (sessionId: string) => {
    window.open(reportsApi.downloadArtifacts(sessionId), '_blank');
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">분석 리포트</h1>
            <p className="text-sm text-muted-foreground">
              분석 결과 및 생성된 리포트
            </p>
          </div>
        </div>

        {/* Stats card */}
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard
            icon={Zap}
            title="전체 리포트"
            value={String(reports.length)}
            badge="생성됨"
            badgeVariant="default"
          />
          <StatCard
            icon={CheckCircle}
            title="최근 생성"
            value={
              reports.length > 0
                ? formatDistanceToNow(reports[0].createdAt, { addSuffix: true, locale: ko })
                : '—'
            }
            badge={reports.length > 0 ? '최신' : '없음'}
            badgeVariant={reports.length > 0 ? 'success' : 'default'}
          />
        </div>

        {/* Generated Reports Table */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-foreground">생성된 리포트</h2>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : reports.length > 0 ? (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="text-xs font-medium text-muted-foreground uppercase">리포트명</TableHead>
                    <TableHead className="text-xs font-medium text-muted-foreground uppercase">문제 유형</TableHead>
                    <TableHead className="text-xs font-medium text-muted-foreground uppercase">생성일</TableHead>
                    <TableHead className="text-xs font-medium text-muted-foreground uppercase text-right">작업</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reports.map((report: Report) => {
                    const isExpanded = selectedReportId === report.sessionId;
                    return (
                      <Fragment key={report.id}>
                        <TableRow
                          className="cursor-pointer"
                          onClick={() =>
                            setSelectedReportId((prev) =>
                              prev === report.sessionId ? null : report.sessionId
                            )
                          }
                        >
                          <TableCell>
                            <div className="flex items-center gap-3">
                              <div className="flex h-8 w-8 items-center justify-center rounded bg-red-500/10">
                                <FileText className="h-4 w-4 text-red-500" />
                              </div>
                              <span className="font-medium text-foreground">{report.title}</span>
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {report.problemType.replace('_', ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {format(report.createdAt, 'MMM dd, yyyy')}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              title="HTML 리포트 보기"
                              onClick={(e) => {
                                e.stopPropagation();
                                window.open(`${config.apiBaseUrl}/reports/${report.sessionId}/html`, '_blank');
                              }}
                            >
                              <ExternalLink className="h-4 w-4 text-muted-foreground" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              title="아티팩트 다운로드"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownload(report.sessionId);
                              }}
                            >
                              <Download className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          </TableCell>
                        </TableRow>
                        {isExpanded && (
                          <TableRow className="bg-muted/20 hover:bg-muted/20">
                            <TableCell colSpan={4} className="p-0">
                              <div className="max-h-[600px] overflow-y-auto px-4 py-4">
                                {isReportLoading ? (
                                  <div className="space-y-3 py-2">
                                    <Skeleton className="h-6 w-48" />
                                    <Skeleton className="h-4 w-full" />
                                    <Skeleton className="h-4 w-3/4" />
                                    <Skeleton className="h-4 w-full" />
                                    <Skeleton className="h-4 w-5/6" />
                                    <Skeleton className="h-6 w-36 mt-4" />
                                    <Skeleton className="h-4 w-full" />
                                    <Skeleton className="h-4 w-2/3" />
                                  </div>
                                ) : isReportError ? (
                                  <div className="space-y-2 text-sm">
                                    <p className="text-destructive">
                                      리포트 내용을 불러오지 못했습니다.
                                    </p>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        refetchReportContent();
                                      }}
                                    >
                                      다시 시도
                                    </Button>
                                  </div>
                                ) : reportContent ? (
                                  <MarkdownRenderer content={reportContent} />
                                ) : (
                                  <p className="text-sm text-muted-foreground">
                                    표시할 리포트 내용이 없습니다.
                                  </p>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          ) : (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">아직 생성된 리포트가 없습니다. 분석을 시작하여 첫 리포트를 만들어보세요.</p>
              </CardContent>
            </Card>
          )}
        </div>

      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  title,
  value,
  badge,
  badgeVariant,
}: {
  icon: React.ElementType;
  title: string;
  value: string;
  badge: string;
  badgeVariant: 'success' | 'default';
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
            <Icon className="h-5 w-5 text-foreground" />
          </div>
          <Badge
            variant="outline"
            className={
              badgeVariant === 'success'
                ? 'border-green-500/30 bg-green-500/10 text-green-500'
                : 'border-border text-muted-foreground'
            }
          >
            {badge} {badgeVariant === 'success' && '\u2191'}
          </Badge>
        </div>
        <div className="mt-4">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-3xl font-bold text-foreground">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

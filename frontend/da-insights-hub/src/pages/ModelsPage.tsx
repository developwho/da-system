import { useState } from 'react';
import { Brain, Download, Eye, MessageSquare, CheckCircle, Clock, XCircle, TrendingUp, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useModels, useModel } from '@/hooks/use-models';
import { useApp } from '@/contexts/AppContext';
import { formatDuration } from '@/lib/mock-data';
import { config } from '@/lib/config';
import type { ModelStatus, Model } from '@/types';

export default function ModelsPage() {
  const { activeSessionId } = useApp();
  // 현재 세션의 모델만 조회
  const experimentName = activeSessionId ? `session_${activeSessionId}` : undefined;
  const { data: models = [], isLoading } = useModels(experimentName);
  const [activeTab, setActiveTab] = useState('all');

  const filteredModels = models.filter((model) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'training') return model.status === 'training';
    if (activeTab === 'complete') return model.status === 'complete';
    if (activeTab === 'failed') return model.status === 'failed';
    return true;
  });

  const trainingCount = models.filter((m) => m.status === 'training').length;
  const completeCount = models.filter((m) => m.status === 'complete').length;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">모델</h1>
            <p className="text-sm text-muted-foreground">
              학습된 ML 모델을 추적하고 비교합니다
            </p>
          </div>
          <Button className="gap-2">
            <TrendingUp className="h-4 w-4" />
            새 모델 학습
          </Button>
        </div>

        {/* Stats */}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="flex items-center gap-4 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Brain className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-semibold">{models.length}</p>
                <p className="text-sm text-muted-foreground">전체 모델</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-4 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-da-warning/10">
                <Clock className="h-5 w-5 text-da-warning" />
              </div>
              <div>
                <p className="text-2xl font-semibold">{trainingCount}</p>
                <p className="text-sm text-muted-foreground">학습 중</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-4 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-da-success/10">
                <CheckCircle className="h-5 w-5 text-da-success" />
              </div>
              <div>
                <p className="text-2xl font-semibold">{completeCount}</p>
                <p className="text-sm text-muted-foreground">완료</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="all">전체</TabsTrigger>
            <TabsTrigger value="training">학습 중</TabsTrigger>
            <TabsTrigger value="complete">완료</TabsTrigger>
            <TabsTrigger value="failed">실패</TabsTrigger>
          </TabsList>

          <TabsContent value={activeTab} className="mt-4">
            {filteredModels.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {filteredModels.map((model) => (
                  <ModelCard key={model.id} model={model} />
                ))}
              </div>
            ) : (
              <EmptyState activeTab={activeTab} />
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function ModelCard({ model }: { model: Model }) {
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const { data: modelDetail, isLoading: isLoadingDetail } = useModel(
    isDetailsOpen ? model.id : null
  );

  const getStatusIcon = (status: ModelStatus) => {
    switch (status) {
      case 'training':
        return <Clock className="h-4 w-4 text-da-warning" />;
      case 'complete':
        return <CheckCircle className="h-4 w-4 text-da-success" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-destructive" />;
    }
  };

  const getStatusBadge = (status: ModelStatus) => {
    const variants: Record<ModelStatus, { variant: 'default' | 'secondary' | 'destructive'; label: string }> = {
      training: { variant: 'secondary', label: '학습 중' },
      complete: { variant: 'default', label: '완료' },
      failed: { variant: 'destructive', label: '실패' },
    };
    return <Badge variant={variants[status].variant}>{variants[status].label}</Badge>;
  };

  const handleDownload = () => {
    const downloadUrl = `${config.apiBaseUrl}/models/${model.id}/download`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${model.name}.pkl`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const trainingDuration = model.trainingCompletedAt && model.trainingStartedAt
    ? (model.trainingCompletedAt.getTime() - model.trainingStartedAt.getTime()) / 1000
    : null;

  return (
    <Card className="transition-all hover:border-primary/50">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {getStatusIcon(model.status)}
            <CardTitle className="text-base">{model.name}</CardTitle>
          </div>
          {getStatusBadge(model.status)}
        </div>
        <CardDescription>{model.datasetName}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Training progress */}
        {model.status === 'training' && model.trainingProgress !== undefined && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">{model.trainingProgress}%</span>
            </div>
            <Progress value={model.trainingProgress} className="h-2" />
          </div>
        )}

        {/* Metrics */}
        {model.status === 'complete' && (
          <div className="grid grid-cols-2 gap-3">
            {model.metrics.rocAuc != null && (
              <div>
                <p className="text-xs text-muted-foreground">ROC-AUC</p>
                <p className="text-lg font-semibold text-da-success">
                  {(model.metrics.rocAuc * 100).toFixed(1)}%
                </p>
              </div>
            )}
            {model.metrics.accuracy != null && (
              <div>
                <p className="text-xs text-muted-foreground">Accuracy</p>
                <p className="text-lg font-semibold">
                  {(model.metrics.accuracy * 100).toFixed(1)}%
                </p>
              </div>
            )}
            {model.metrics.f1Score != null && (
              <div>
                <p className="text-xs text-muted-foreground">F1 Score</p>
                <p className="text-lg font-semibold">
                  {(model.metrics.f1Score * 100).toFixed(1)}%
                </p>
              </div>
            )}
            {trainingDuration != null && (
              <div>
                <p className="text-xs text-muted-foreground">Duration</p>
                <p className="text-sm font-medium">{formatDuration(trainingDuration)}</p>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 gap-1"
            onClick={() => setIsDetailsOpen(true)}
          >
            <Eye className="h-3 w-3" />
            상세
          </Button>
          {model.status === 'complete' && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={handleDownload}
              >
                <Download className="h-3 w-3" />
              </Button>
              <Button variant="outline" size="sm" className="gap-1">
                <MessageSquare className="h-3 w-3" />
              </Button>
            </>
          )}
        </div>
      </CardContent>

      {/* Details Modal */}
      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{model.name}</DialogTitle>
            <DialogDescription>모델 상세 정보</DialogDescription>
          </DialogHeader>

          {isLoadingDetail ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : modelDetail ? (
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">모델 타입</p>
                  <p className="font-medium">{modelDetail.modelType || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">상태</p>
                  {getStatusBadge(modelDetail.status)}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">데이터셋</p>
                  <p className="font-medium">{modelDetail.datasetName}</p>
                </div>
                {trainingDuration && (
                  <div>
                    <p className="text-sm text-muted-foreground">학습 시간</p>
                    <p className="font-medium">{formatDuration(trainingDuration)}</p>
                  </div>
                )}
              </div>

              {/* Metrics */}
              {modelDetail.metrics && Object.keys(modelDetail.metrics).length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-3">성능 지표</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(modelDetail.metrics).map(([key, value]) => (
                      <div key={key} className="rounded-lg border p-3">
                        <p className="text-xs text-muted-foreground capitalize">
                          {key.replace(/([A-Z])/g, ' $1').trim()}
                        </p>
                        <p className="text-lg font-semibold">
                          {typeof value === 'number' ? (value * 100).toFixed(2) + '%' : value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Feature Importance */}
              {modelDetail.featureImportance && modelDetail.featureImportance.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-3">중요 변수 (Top 10)</h3>
                  <div className="space-y-2">
                    {modelDetail.featureImportance.slice(0, 10).map((feature) => (
                      <div key={feature.feature} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">{feature.feature}</span>
                          <span className="font-medium">{(feature.importance * 100).toFixed(1)}%</span>
                        </div>
                        <Progress value={feature.importance * 100} className="h-2" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">모델 정보를 불러올 수 없습니다.</p>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function EmptyState({ activeTab }: { activeTab: string }) {
  const messages: Record<string, { title: string; description: string }> = {
    all: { title: '모델이 없습니다', description: '첫 번째 모델을 학습해보세요' },
    training: { title: '학습 중인 모델이 없습니다', description: '새 학습을 시작해보세요' },
    complete: { title: '완료된 모델이 없습니다', description: '완료된 모델이 여기에 표시됩니다' },
    failed: { title: '실패한 모델이 없습니다', description: '실패한 학습 작업이 여기에 표시됩니다' },
  };

  const { title, description } = messages[activeTab] || messages.all;

  return (
    <Card className="border-dashed">
      <CardHeader className="items-center pb-2">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <Brain className="h-8 w-8 text-muted-foreground" />
        </div>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-center">
        <p className="mb-4 text-sm text-muted-foreground">{description}</p>
        {activeTab === 'all' && (
          <Button className="gap-2">
            <TrendingUp className="h-4 w-4" />
            새 모델 학습
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

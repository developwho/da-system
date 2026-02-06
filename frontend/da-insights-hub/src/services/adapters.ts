import type { DataFile, DataProfile, ColumnProfile, Model, ModelStatus, Report, ChatMessage, ProblemType } from '@/types';
import type {
  BackendUploadResponse,
  BackendDataInfo,
  BackendProfileResponse,
  BackendModelSummary,
  BackendModelDetail,
  BackendReportSummary,
  BackendMessage,
} from './backend-types';

// ===== Data Adapters =====

export function toDataFile(b: BackendUploadResponse): DataFile {
  const m = b.metadata ?? {};
  return {
    id: b.file_id,
    name: b.filename,
    size: b.size_bytes,
    rows: m.n_rows ?? m.rows ?? 0,
    columns: m.n_columns ?? m.columns ?? 0,
    problemType: null,
    status: 'ready',
    uploadedAt: new Date(),
  };
}

export function dataInfoToDataFile(b: BackendDataInfo): DataFile {
  const m = b.metadata ?? {};
  return {
    id: b.file_id,
    name: b.filename ?? m.filename ?? `dataset_${b.file_id.slice(0, 8)}`,
    size: b.size_bytes ?? m.size_bytes ?? m.memory_usage_bytes ?? 0,
    rows: m.n_rows ?? m.rows ?? 0,
    columns: m.n_columns ?? m.columns ?? 0,
    problemType: null,
    status: (b.validation?.is_valid === false) ? 'error' : 'ready',
    uploadedAt: b.uploaded_at ? new Date(b.uploaded_at) : new Date(),
  };
}

export function toDataProfile(b: BackendProfileResponse): DataProfile {
  const columns: ColumnProfile[] = [];

  for (const [name, stats] of Object.entries(b.profile.numerical_stats || {})) {
    columns.push({
      name,
      dtype: 'number',
      nonNull: stats.count,
      unique: 0,
      mean: stats.mean,
      std: stats.std,
      min: stats.min,
      max: stats.max,
    });
  }

  for (const [name, stats] of Object.entries(b.profile.categorical_stats || {})) {
    columns.push({
      name,
      dtype: 'category',
      nonNull: 0,
      unique: stats.unique,
      topValues: stats.top ? [{ value: String(stats.top), count: stats.frequency }] : undefined,
    });
  }

  const missingValues = Object.entries(b.profile.missing_analysis || {}).map(
    ([column, data]) => ({ column, count: data.count, percentage: data.percentage }),
  );

  return {
    fileId: b.file_id,
    basicStats: {
      rows: columns.reduce((max, c) => Math.max(max, c.nonNull), 0),
      columns: columns.length,
      memoryUsage: '—',
      duplicateRows: 0,
    },
    columns,
    missingValues,
  };
}

// ===== Model Adapters =====

function mapModelStatus(status: string): ModelStatus {
  const lower = status.toLowerCase();
  if (lower === 'finished' || lower === 'completed') return 'complete';
  if (lower === 'failed' || lower === 'error') return 'failed';
  if (lower === 'running' || lower === 'training') return 'training';
  return 'complete';
}

function mapProblemType(pt?: string): ProblemType {
  if (pt === 'regression') return 'regression';
  if (pt === 'multiclass') return 'multiclass_classification';
  return 'binary_classification';
}

export function toModel(b: BackendModelSummary): Model {
  return {
    id: b.run_id,
    name: b.best_estimator ? `${b.best_estimator} - ${b.run_id.slice(0, 8)}` : `Model ${b.run_id.slice(0, 8)}`,
    algorithm: b.best_estimator || 'Unknown',
    datasetId: '',
    datasetName: b.experiment_name || '',
    problemType: mapProblemType(b.problem_type),
    status: mapModelStatus(b.status),
    metrics: {
      rocAuc: b.metrics['roc_auc'] ?? b.metrics['roc-auc'],
      accuracy: b.metrics['accuracy'],
      f1Score: b.metrics['f1'] ?? b.metrics['f1_score'],
      precision: b.metrics['precision'],
      recall: b.metrics['recall'],
      rmse: b.metrics['rmse'],
      mae: b.metrics['mae'],
      r2: b.metrics['r2'],
    },
    trainingStartedAt: b.start_time ? new Date(b.start_time) : undefined,
    trainingCompletedAt: b.end_time ? new Date(b.end_time) : undefined,
    sessionId: '',
  };
}

export function toModelDetail(b: BackendModelDetail): Model {
  const base = toModel(b);
  return {
    ...base,
    modelType: b.best_estimator || undefined,
    hyperparameters: b.params,
    featureImportance: b.feature_importance?.map((fi) => ({
      feature: fi.feature,
      importance: fi.importance,
    })),
  };
}

// ===== Report Adapters =====

export function toReport(b: BackendReportSummary): Report {
  return {
    id: b.session_id,
    sessionId: b.session_id,
    title: `Analysis Report - ${b.session_id.slice(0, 8)}`,
    problemType: mapProblemType(b.problem_type),
    createdAt: new Date(b.timestamp),
    insights: [],
    modelId: b.model || '',
    datasetId: '',
    datasetName: '',
  };
}

// ===== Chat Adapters =====

export function toChatMessage(b: BackendMessage): ChatMessage {
  return {
    id: b.id,
    role: b.role,
    content: b.content,
    timestamp: new Date(b.timestamp),
  };
}

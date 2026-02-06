// DA System Types

// ============ Data/Files Types ============
export interface DataFile {
  id: string;
  name: string;
  size: number;
  rows: number;
  columns: number;
  problemType: ProblemType | null;
  status: FileStatus;
  uploadedAt: Date;
  profiledAt?: Date;
}

export type FileStatus = 'uploading' | 'processing' | 'ready' | 'error';
export type ProblemType = 'binary_classification' | 'multiclass_classification' | 'regression';

export interface DataProfile {
  fileId: string;
  basicStats: {
    rows: number;
    columns: number;
    memoryUsage: string;
    duplicateRows: number;
  };
  columns: ColumnProfile[];
  missingValues: { column: string; count: number; percentage: number }[];
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  nonNull: number;
  unique: number;
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
  topValues?: { value: string; count: number }[];
}

// ============ Chat Types ============
export interface ChatSession {
  id: string;
  createdAt: Date;
  messages: ChatMessage[];
  attachedFileId?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  attachments?: MessageAttachment[];
  cards?: MessageCard[];
  isStreaming?: boolean;
}

export interface MessageAttachment {
  type: 'file' | 'chart';
  fileId?: string;
  fileName?: string;
  chartData?: ChartData;
}

export interface MessageCard {
  type: 'data-profile' | 'model-result' | 'report-summary' | 'progress' | 'analysis-questions' | 'analysis-plan';
  data: DataProfileCard | ModelResultCard | ReportSummaryCard | ProgressCard | AnalysisQuestionsPayload | AnalysisPlanPayload;
}

export interface DataProfileCard {
  fileId: string;
  fileName: string;
  rows: number;
  columns: number;
  problemType: ProblemType | null;
}

export interface ModelResultCard {
  modelId: string;
  modelName: string;
  metrics: ModelMetrics;
}

export interface ReportSummaryCard {
  sessionId: string;
  title: string;
  preview: string;
  insights?: string[];
}

export interface ProgressCard {
  steps: AnalysisStep[];
  currentStep: number;
  elapsedTime: number;
  estimatedRemaining?: number;
}

export interface ChartData {
  type: 'feature-importance' | 'confusion-matrix' | 'roc-curve' | 'distribution';
  data: Record<string, unknown>;
}

// ============ Pre-Analysis Q&A Types ============
export interface QuestionOption {
  value: string;
  label: string;
  recommended?: boolean;
  reason?: string;
}

export interface AnalysisQuestion {
  id: string;
  type: 'text' | 'select' | 'radio';
  label: string;
  description?: string;
  placeholder?: string;
  options?: QuestionOption[];
  defaultValue?: string;
  required?: boolean;
}

export interface AnalysisProfileSummary {
  rows: number;
  columns: number;
  numericColumns: string[];
  categoricalColumns: string[];
  missingCellsPct: number;
  duplicateRows: number;
  memoryMB: number;
}

export interface AnalysisQuestionsPayload {
  sessionId: string;
  profile: AnalysisProfileSummary;
  questions: AnalysisQuestion[];
  submitted?: boolean;
  answers?: Record<string, string>;
}

export interface AnalysisPlanStep {
  name: string;
  description: string;
}

export interface AnalysisPlan {
  analysisGoal: string;
  targetColumn: string;
  problemType: string;
  evaluationMetric: string;
  constraints: string[];
  estimatedDuration: string;
  steps: AnalysisPlanStep[];
}

export interface AnalysisPlanPayload {
  sessionId: string;
  plan: AnalysisPlan;
  confirmed?: boolean;
}

// ============ Analysis Types ============
export interface AnalysisStep {
  id: number;
  name: string;
  status: StepStatus;
  startedAt?: Date;
  completedAt?: Date;
  details?: AnalysisStepDetails;
}

export type StepStatus = 'pending' | 'running' | 'complete' | 'failed';

export interface SubStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  timestamp?: number;
  phase?: string;  // 'ProblemDefinition' | 'Research' | 'Modeling' | 'Insight' | 'Reporting'
}

export interface AnalysisStepDetails {
  researchSources?: ResearchSource[];
  metrics?: Partial<ModelMetrics>;
  logs?: string[];
}

export interface ResearchSource {
  name: 'HuggingFace' | 'Kaggle' | 'DeepResearch';
  status: StepStatus;
  resultsCount?: number;
}

// ============ Model Types ============
export interface Model {
  id: string;
  name: string;
  algorithm: string;
  datasetId: string;
  datasetName: string;
  problemType: ProblemType;
  status: ModelStatus;
  metrics: ModelMetrics;
  trainingProgress?: number;
  trainingStartedAt?: Date;
  trainingCompletedAt?: Date;
  sessionId: string;
  modelType?: string;
  hyperparameters?: Record<string, unknown>;
  featureImportance?: FeatureImportance[];
}

export type ModelStatus = 'training' | 'complete' | 'failed';

export interface ModelMetrics {
  rocAuc?: number;
  accuracy?: number;
  f1Score?: number;
  precision?: number;
  recall?: number;
  rmse?: number;
  mae?: number;
  r2?: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

// ============ Report Types ============
export interface Report {
  id: string;
  sessionId: string;
  title: string;
  problemType: ProblemType;
  createdAt: Date;
  insights: string[];
  modelId: string;
  datasetId: string;
  datasetName: string;
}

export interface ReportContent {
  markdown: string;
  html: string;
  tableOfContents: TocItem[];
}

export interface TocItem {
  id: string;
  title: string;
  level: number;
}

// ============ WebSocket Types ============
export type WebSocketEventType =
  | 'message.received'
  | 'message.complete'
  | 'status.update'
  | 'report.ready'
  | 'analysis.questions'
  | 'analysis.plan'
  | 'error'
  | 'connected'
  | 'disconnected';

export interface WebSocketEvent {
  type: WebSocketEventType;
  payload: unknown;
}

export interface StatusUpdatePayload {
  sessionId: string;
  step: number;
  totalSteps: number;
  stepName: string;
  status: StepStatus;
  progress?: number;
  description?: string;
  details?: AnalysisStepDetails;
  subSteps?: SubStep[];
}

export interface MessageReceivedPayload {
  sessionId: string;
  messageId: string;
  chunk: string;
  isComplete: boolean;
}

// ============ App State Types ============
export interface AppState {
  activeSessionId: string | null;
  wsStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  currentAnalysis: ProgressCard | null;
}

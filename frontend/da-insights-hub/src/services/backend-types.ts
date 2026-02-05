/** Backend response types matching FastAPI JSON shapes */

// ===== Data API =====

/** Metadata returned by DataLoader._extract_metadata() */
export interface BackendMetadata {
  // Actual backend keys
  n_rows?: number;
  n_columns?: number;
  column_names?: string[];
  dtypes?: Record<string, string>;
  memory_usage_bytes?: number;
  size_bytes?: number;
  filename?: string;
  file_id?: string;
  upload_time?: string;
  has_missing_values?: boolean;
  total_missing_values?: number;
  // Legacy / upload-response aliases (kept for compatibility)
  rows?: number;
  columns?: number;
  column_types?: Record<string, string>;
  memory_usage?: number;
  file_size?: number;
}

/** Validation returned by DataValidator.validate() */
export interface BackendValidation {
  is_valid?: boolean;
  errors?: string[];
  warnings?: string[];
  suggestions?: string[];
  summary?: {
    total_rows?: number;
    total_columns?: number;
    missing_values?: number;
    duplicate_rows?: number;
    constant_columns?: number;
  };
  // Legacy upload-response aliases
  has_missing_values?: boolean;
  missing_value_counts?: Record<string, number>;
  duplicate_rows?: number;
  issues?: string[];
}

export interface BackendUploadResponse {
  file_id: string;
  filename: string;
  size_bytes: number;
  metadata: BackendMetadata;
  validation: BackendValidation;
  preview: unknown[];
}

export interface BackendDataInfo {
  file_id: string;
  filename?: string;
  size_bytes?: number;
  uploaded_at?: string;
  metadata: BackendMetadata;
  validation: BackendValidation;
}

export interface BackendFileList {
  files: BackendDataInfo[];
  count: number;
}

export interface BackendProfileResponse {
  file_id: string;
  profile: {
    numerical_stats: Record<string, {
      count: number;
      mean: number;
      std: number;
      min: number;
      q25: number;
      median: number;
      q75: number;
      max: number;
      skewness: number;
      kurtosis: number;
    }>;
    categorical_stats: Record<string, {
      unique: number;
      top: unknown;
      frequency: number;
      mode: unknown;
    }>;
    missing_analysis: Record<string, { count: number; percentage: number }>;
    correlation_matrix: Record<string, Record<string, number>>;
    distributions: Record<string, unknown>;
  };
  target_analysis: {
    column_name: string;
    unique_values: number;
    data_type: string;
    missing_count: number;
    distribution: Record<string, number>;
  } | null;
  task_detection: {
    task_type: string;
    confidence: number;
    classes: string[] | null;
    class_distribution: Record<string, number> | null;
    reasoning: string;
  } | null;
}

export interface BackendPreviewResponse {
  file_id: string;
  preview: Record<string, unknown>[];
}

// ===== Chat API =====
export interface BackendMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface BackendCreateSessionResponse {
  session_id: string;
  created_at: string;
  message: string;
}

export interface BackendSendMessageResponse {
  message: BackendMessage;
  session_id: string;
}

export interface BackendSessionDetail {
  session_id: string;
  user_id?: string;
  file_id?: string;
  messages: BackendMessage[];
  created_at: string;
  updated_at: string;
  status: string;
}

export interface BackendSessionSummary {
  session_id: string;
  user_id?: string;
  file_id?: string;
  created_at: string;
  updated_at: string;
  status: string;
  message_count: number;
}

export interface BackendSessionList {
  sessions: BackendSessionSummary[];
  count: number;
}

// ===== Models API =====
export interface BackendModelSummary {
  run_id: string;
  experiment_name?: string;
  status: string;
  start_time?: string;
  end_time?: string;
  best_estimator?: string;
  problem_type?: string;
  metrics: Record<string, number>;
}

export interface BackendModelDetail extends BackendModelSummary {
  artifact_uri?: string;
  params: Record<string, unknown>;
  tags: Record<string, string>;
  target_column?: string;
  feature_importance?: Array<{ feature: string; importance: number; ranking: number }>;
}

export interface BackendPredictResponse {
  predictions: unknown[];
  probabilities?: number[][];
  run_id: string;
  model_info: {
    best_estimator: string;
    problem_type: string;
    metrics: Record<string, number>;
  };
}

export interface BackendExplainResponse {
  run_id: string;
  feature_importance?: Array<{ feature: string; importance: number; ranking: number }>;
  shap_artifacts?: string[];
  shap_directory?: string;
  message?: string;
}

// ===== Reports API =====
export interface BackendReportContent {
  session_id: string;
  content: string;
  format: string;
  metadata: Record<string, unknown>;
}

export interface BackendReportSummary {
  session_id: string;
  timestamp: string;
  problem_type: string;
  model: string;
}

export interface BackendReportFiles {
  session_id: string;
  files: {
    markdown: string | null;
    html: string | null;
    artifacts: string | null;
    metadata: string | null;
  };
}

// ===== Analysis API =====
export interface BackendTaskStartResponse {
  status: string;
  task_id: string;
  message: string;
}

export interface BackendTaskStatus {
  task_id: string;
  status: string;
  progress: number;
  message: string;
  result?: unknown;
  error?: string;
  traceback?: string;
}

// ===== Common =====
export interface BackendDeleteResponse {
  message: string;
  [key: string]: string;
}

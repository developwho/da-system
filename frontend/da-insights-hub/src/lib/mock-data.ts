import type {
  DataFile,
  Model,
  Report,
  ChatMessage,
  AnalysisStep,
  FeatureImportance,
  DataProfile,
} from '@/types';

// ============ Sample Data Files ============
export const mockDataFiles: DataFile[] = [
  {
    id: 'file-1',
    name: 'LPG_도시가스_가격데이터_sample.csv',
    size: 8_400,
    rows: 80,
    columns: 8,
    problemType: 'regression',
    status: 'ready',
    uploadedAt: new Date('2025-10-20T09:00:00'),
    profiledAt: new Date('2025-10-20T09:00:05'),
  },
  {
    id: 'file-2',
    name: 'titanic_passengers.csv',
    size: 61_000,
    rows: 891,
    columns: 12,
    problemType: 'binary_classification',
    status: 'ready',
    uploadedAt: new Date('2024-01-14T14:20:00'),
    profiledAt: new Date('2024-01-14T14:20:30'),
  },
  {
    id: 'file-3',
    name: 'customer_churn.xlsx',
    size: 1_200_000,
    rows: 7_043,
    columns: 21,
    problemType: 'binary_classification',
    status: 'ready',
    uploadedAt: new Date('2024-01-13T09:15:00'),
    profiledAt: new Date('2024-01-13T09:16:00'),
  },
  {
    id: 'file-4',
    name: 'house_prices.csv',
    size: 460_000,
    rows: 1_460,
    columns: 81,
    problemType: 'regression',
    status: 'processing',
    uploadedAt: new Date('2024-01-16T08:00:00'),
  },
];

// ============ Sample Models ============
export const mockModels: Model[] = [
  {
    id: 'model-1',
    name: 'LightGBM - LPG/도시가스 가격 예측',
    algorithm: 'LightGBM',
    datasetId: 'file-1',
    datasetName: 'LPG_도시가스_가격데이터_sample.csv',
    problemType: 'regression',
    status: 'complete',
    metrics: {
      r2: 0.94,
      mape: 4.8,
      rmse: 1.18,
      mae: 0.82,
    },
    trainingStartedAt: new Date('2025-10-20T09:05:00'),
    trainingCompletedAt: new Date('2025-10-20T09:08:42'),
    sessionId: 'session-1',
    featureImportance: generateFeatureImportance(),
  },
  {
    id: 'model-2',
    name: 'LightGBM - Customer Churn',
    algorithm: 'LightGBM',
    datasetId: 'file-3',
    datasetName: 'customer_churn.xlsx',
    problemType: 'binary_classification',
    status: 'complete',
    metrics: {
      rocAuc: 0.9412,
      accuracy: 0.8934,
      f1Score: 0.8523,
      precision: 0.8645,
      recall: 0.8405,
    },
    trainingStartedAt: new Date('2024-01-13T09:20:00'),
    trainingCompletedAt: new Date('2024-01-13T09:28:00'),
    sessionId: 'session-2',
    featureImportance: generateFeatureImportance(),
  },
  {
    id: 'model-3',
    name: 'RandomForest - Titanic',
    algorithm: 'RandomForest',
    datasetId: 'file-2',
    datasetName: 'titanic_passengers.csv',
    problemType: 'binary_classification',
    status: 'training',
    trainingProgress: 67,
    metrics: {
      rocAuc: 0.8534,
      accuracy: 0.8123,
    },
    trainingStartedAt: new Date(),
    sessionId: 'session-3',
  },
];

// ============ Sample Reports ============
export const mockReports: Report[] = [
  {
    id: 'report-1',
    sessionId: 'session-1',
    title: 'LPG/도시가스 가격 예측 분석 리포트',
    problemType: 'regression',
    createdAt: new Date('2025-10-20T09:20:00'),
    insights: [
      'CP 가격이 전체 예측력의 38.2%를 차지하며 최대 영향 변수',
      'LightGBM 모델 R\u00B2=0.94, MAPE=4.8%로 높은 예측 정확도 달성',
      '상위 3개 변수(CP+JKM+유가)가 전체 예측력의 81.1% 설명',
    ],
    modelId: 'model-1',
    datasetId: 'file-1',
    datasetName: 'LPG_도시가스_가격데이터_sample.csv',
  },
  {
    id: 'report-2',
    sessionId: 'session-2',
    title: 'Customer Churn Prediction Report',
    problemType: 'binary_classification',
    createdAt: new Date('2024-01-13T09:30:00'),
    insights: [
      'Monthly charges and tenure are strongest churn predictors',
      'Customers with fiber optic internet show 3x higher churn rate',
      'Contract type significantly impacts customer retention',
    ],
    modelId: 'model-2',
    datasetId: 'file-3',
    datasetName: 'customer_churn.xlsx',
  },
];

export const mockReportMarkdownBySession: Record<string, string> = {
  'session-1': `# LPG/도시가스 가격 예측 분석 리포트

## 문서 정보
- **프로젝트:** LPG/도시가스 판매 단가 예측 모델 구축
- **데이터셋:** \`LPG_도시가스_가격데이터_sample.csv\` (80행, 8개 컬럼)
- **기간:** 2018년 3월 ~ 2024년 10월 (월별)
- **문제 유형:** 회귀 (타겟: \`lpg_retail_price\`, 원/kg)
- **검증 방식:** 80:20 홀드아웃
- **핵심 목표:** LPG/도시가스 판매 단가의 주요 변동 요인을 정량화하고 예측 모델 구축

## 경영진 요약

LPG/도시가스 판매 단가는 국제 CP 가격, JKM 현물가, 유가 등 복합적 요인에 의해 결정됩니다. 본 분석은 80개월 간의 월별 데이터를 활용하여 **LightGBM 기반 예측 모델**을 구축했으며, **R\u00B2=0.94, MAPE=4.8%**의 높은 예측 정확도를 달성했습니다.

### 핵심 성과
| 지표 | 값 |
|---|---:|
| R\u00B2 | 0.94 |
| MAPE | 4.8% |
| RMSE | 1.18 원/kg |
| MAE | 0.82 원/kg |

### 전략적 시사점
CP 가격(38.2%), JKM 현물가격(27.1%), 브렌트유(15.8%)가 전체 예측력의 **81.1%**를 차지하며, 이 세 지표의 모니터링만으로도 판매 단가의 방향성을 상당 부분 예측할 수 있습니다.

## 1. 비즈니스 맥락

LPG/도시가스 사업에서 **판매 단가 예측**은 다음 의사결정의 핵심 입력입니다:
- **CP 계약 타이밍** 판단 및 선제적 원가 헷지
- **재고 관리** 전략 수립 (저점 매입, 고점 방어)
- **영업 마진** 시뮬레이션 및 분기별 실적 전망
- **규제 대응** 자료 (에너지위원회 보고용 근거)

## 2. 데이터 진단

### 데이터 개요
- **관측치:** 80개월 (2018-03 ~ 2024-10)
- **변수:** 예측변수 7개 + 타겟 1개
- **결측값:** 없음 (0.0%)

### 주요 변수 설명
| 변수 | 설명 | 단위 |
|---|---|---|
| cp_price | 사우디 아람코 CP(Contract Price) | $/톤 |
| jkm_price | JKM(아시아 LNG 벤치마크) 현물가격 | $/MMBTU |
| brent_crude | 브렌트유 현물가격 | $/배럴 |
| heating_demand_idx | 난방 수요 지수 | 지수 |
| usd_krw | 원/달러 환율 | KRW/USD |
| season | 계절 (봄/여름/가을/겨울) | 범주형 |
| inventory_level | LPG 재고 수준 | 천톤 |

## 3. 모델링

### 비교 모델군
| 모델 | RMSE | MAE | R\u00B2 | MAPE |
|---|---:|---:|---:|---:|
| Linear Regression | 3.21 | 2.64 | 0.72 | 12.3% |
| RandomForest | 1.85 | 1.34 | 0.88 | 7.2% |
| XGBoost | 1.32 | 0.95 | 0.92 | 5.4% |
| **LightGBM (챔피언)** | **1.18** | **0.82** | **0.94** | **4.8%** |

### LightGBM 선정 근거
- 소규모 데이터셋(80행)에서도 과적합 없이 안정적 성능
- 범주형 변수(season) 네이티브 지원
- 학습 속도 우수 (3분 42초 내 전체 탐색 완료)
- SHAP 호환성 양호 → 해석 가능성 확보

## 4. 설명가능성 (SHAP 분석)

### 글로벌 변수 기여도
| 순위 | 변수 | SHAP 기여도 | 방향성 |
|---:|---|---:|---|
| 1 | cp_price | 38.2% | CP 상승 시 판매가 상승 |
| 2 | jkm_price | 27.1% | JKM 상승 시 판매가 상승 |
| 3 | brent_crude | 15.8% | 유가 상승 시 판매가 상승 |
| 4 | heating_demand_idx | 9.3% | 난방 수요 증가 시 판매가 상승 |
| 5 | usd_krw | 5.7% | 원화 약세 시 판매가 상승 |
| 6 | season | 3.9% | 동절기 가격 프리미엄 존재 |

### 핵심 인사이트
1. **CP + JKM + 유가 = 81.1%**: 국제 에너지 가격 3개 변수가 판매가의 대부분을 설명
2. **환율 비선형 효과**: 1,350원 이상 구간에서 SHAP 기여도가 급증 (임계효과)
3. **계절성 13.2%**: 난방 수요 지수 + 계절 변수가 동절기 가격 프리미엄을 포착
4. **CP 가격 지배적**: 사우디 아람코 CP가 단일 변수로 가장 높은 설명력 보유

## 5. 권고사항

### 즉시 실행 (높음)
1. CP 가격 및 JKM 일일 모니터링 대시보드 구축
2. 월별 모델 재학습 파이프라인 자동화
3. 환율 1,350원 돌파 시 경보 체계 연동

### 중기 과제 (중간)
1. 지정학적 이벤트(OPEC 회의, 중동 정세) 텍스트 변수 추가
2. 기상청 예보 데이터 연동으로 난방 수요 예측 정확도 향상

### 장기 과제 (낮음)
1. 주간 데이터 확보 시 시계열 모델 재구축
2. 분기별 챌린저 모델 비교 체계 도입

---

*DA System | AI 데이터 분석 자동화 에이전트 | 자동 생성 리포트*`,

  'session-2': `# Customer Churn Prediction Report

## Executive Summary
This report presents the findings from our automated machine learning analysis of customer churn patterns. Our model achieved strong predictive performance and identified key factors driving customer attrition.

## Model Performance
- **Accuracy**: 96.5%
- **ROC-AUC**: 94.8%
- **Precision**: 92.3%
- **Recall**: 89.7%
- **F1-Score**: 91.0%

## Key Findings

### Top Churn Predictors
1. **Monthly Charges** - Higher monthly charges strongly correlate with increased churn risk
2. **Contract Type** - Month-to-month contracts show 3x higher churn rates compared to long-term contracts
3. **Tenure** - Customers with less than 6 months tenure are at highest risk
4. **Internet Service Type** - Fiber optic customers exhibit elevated churn rates
5. **Customer Support Contacts** - Multiple support tickets indicate dissatisfaction

### Insights & Recommendations

#### 1. Contract Optimization
- **Finding**: Month-to-month customers churn at 42%, while 2-year contract customers churn at only 2.8%
- **Recommendation**: Implement incentive programs to encourage longer-term commitments

#### 2. Early Intervention Strategy
- **Finding**: 68% of churners leave within the first 6 months
- **Recommendation**: Deploy targeted retention campaigns for customers in months 1-6

#### 3. Pricing Strategy Review
- **Finding**: Customers paying >$80/month have 2.5x higher churn risk
- **Recommendation**: Review value proposition for high-tier plans; consider loyalty discounts

#### 4. Service Quality Enhancement
- **Finding**: Fiber optic customers report 35% more technical support issues
- **Recommendation**: Invest in fiber optic infrastructure improvements

## Business Impact
- **Potential Revenue Protection**: $2.4M annually through targeted retention
- **ROI**: Estimated 320% return on retention program investment
- **Customer Lifetime Value**: 18% increase through churn reduction

## Next Steps
1. Deploy churn prediction model to production environment
2. Integrate predictions with CRM system for automated alerting
3. Train customer success team on high-risk customer engagement protocols
4. Monitor model performance and retrain quarterly with updated data

---

*Report generated by DA System | Automated ML Analytics Platform*`,
};

// ============ Sample Chat Messages ============
export const mockWelcomeMessages: ChatMessage[] = [
  {
    id: 'welcome-1',
    role: 'assistant',
    content: `DA System에 오신 것을 환영합니다!

AI 데이터 분석 어시스턴트입니다. 다음을 도와드릴 수 있습니다:

- **데이터 업로드 및 프로파일링** (CSV, Excel)
- **문제 유형 자동 감지** 및 타겟 변수 추천
- **AutoML 모델 학습** (FLAML 기반 최적 알고리즘 탐색)
- **SHAP 기반 설명가능한 AI** 분석 리포트 생성

시작하려면 데이터 파일을 드래그앤드롭하거나 아래 빠른 작업을 선택하세요.`,
    timestamp: new Date(),
  },
];

// ============ Analysis Steps Template ============
export const analysisStepsTemplate: AnalysisStep[] = [
  { id: 1, name: 'ProblemDefinition', status: 'pending' },
  { id: 2, name: 'Research', status: 'pending' },
  { id: 3, name: 'Modeling', status: 'pending' },
  { id: 4, name: 'Insight', status: 'pending' },
  { id: 5, name: 'Reporting', status: 'pending' },
];

// ============ Mock Conversation Response Templates ============

export const MOCK_INTENT_RESPONSE = `LPG/도시가스 가격 예측은 에너지 사업에서 매우 중요한 분석 주제입니다. 판매 단가를 사전에 예측할 수 있다면 **CP 계약 타이밍 최적화**, **재고 매입 시점 결정**, **마진 시뮬레이션** 등 다양한 의사결정에 직접 활용할 수 있습니다.

정확한 예측 모델을 구축하려면 다음과 같은 데이터가 이상적입니다:

| 카테고리 | 예시 변수 |
|---|---|
| 국제 에너지 가격 | 사우디 CP, JKM LNG, 브렌트유 |
| 거시경제 지표 | 원/달러 환율 |
| 수급 지표 | LPG 재고 수준 |
| 수요 요인 | 난방 수요 지수, 계절 |

월별 시계열 데이터가 있다면 더욱 정밀한 분석이 가능합니다. 관련 데이터를 CSV 또는 Excel 파일로 업로드해주세요. 데이터를 분석한 후 최적의 예측 전략을 제안해드리겠습니다.`;

export const MOCK_DATA_ANALYSIS_RESPONSE = `데이터를 분석했습니다.

### 데이터 개요
**80개월** (2018.03 ~ 2024.10)의 LPG/도시가스 가격 시계열 데이터입니다.

| 항목 | 내용 |
|---|---|
| 관측치 | 80행 (월별) |
| 변수 | 7개 예측변수 + 1개 타겟 |
| 결측값 | 없음 |
| 타겟 후보 | \`lpg_retail_price\` (원/kg) |

### 변수 구성 분석
**국제 에너지 가격** (CP, JKM, 브렌트유), **거시경제 지표** (환율), **수급 변수** (LPG 재고), **수요 지표** (난방 수요 지수, 계절)가 포함되어 있습니다.

특히 **사우디 CP 가격**과 **JKM 현물가격**을 함께 포함한 점이 인상적입니다. 이 두 변수는 국내 LPG 판매 단가의 핵심 결정 요인으로 알려져 있습니다.

### 분석 방향
말씀하신 **LPG/도시가스 가격 예측** 목표에 맞춰 다음과 같이 진행하겠습니다:

1. **FLAML AutoML**로 LightGBM, XGBoost 등 최적 회귀 모델 탐색
2. **SHAP 분석**으로 어떤 요인이 가격을 얼마나 움직이는지 정량화
3. 경영 의사결정에 활용 가능한 **종합 리포트** 생성

아래에서 세부 분석 설정을 확인해주세요.`;

export const MOCK_DATA_ANALYSIS_COLD_RESPONSE = `업로드해주신 데이터를 분석했습니다.

### 데이터 개요
**80개월** (2018.03 ~ 2024.10)의 LPG/도시가스 가격 시계열 데이터입니다.

| 항목 | 내용 |
|---|---|
| 관측치 | 80행 (월별) |
| 변수 | 7개 예측변수 + 1개 타겟 |
| 결측값 | 없음 |
| 타겟 후보 | \`lpg_retail_price\` (원/kg) |

### 변수 구성 분석
**국제 에너지 가격** (CP, JKM, 브렌트유), **거시경제 지표** (환율), **수급 변수** (LPG 재고), **수요 지표** (난방 수요 지수, 계절)가 포함되어 있습니다.

특히 **사우디 CP 가격**과 **JKM 현물가격**을 함께 포함한 점이 인상적입니다. 이 두 변수는 국내 LPG 판매 단가의 핵심 결정 요인으로 알려져 있습니다.

### 분석 방향
데이터 특성을 고려하여 다음과 같이 진행하겠습니다:

1. **FLAML AutoML**로 LightGBM, XGBoost 등 최적 회귀 모델 탐색
2. **SHAP 분석**으로 어떤 요인이 가격을 얼마나 움직이는지 정량화
3. 경영 의사결정에 활용 가능한 **종합 리포트** 생성

아래에서 세부 분석 설정을 확인해주세요.`;

export const MOCK_GUIDE_RESPONSE = `DA System은 **AI 에이전트 기반 데이터 분석 자동화 플랫폼**입니다.

### 분석 프로세스
데이터를 업로드하면 5단계 자동 분석이 진행됩니다:

| 단계 | 내용 | 소요 시간 |
|---|---|---|
| 문제 정의 | 타겟 변수 및 평가 지표 설정 | ~2분 |
| 선행연구 | 논문·Kaggle 솔루션 자동 조사 | ~3분 |
| 모델 학습 | FLAML AutoML 최적 모델 탐색 | ~8분 |
| 인사이트 | SHAP 기반 변수 기여도 분석 | ~5분 |
| 리포트 | 경영진 요약 포함 종합 보고서 | ~2분 |

### 지원 데이터 형식
- **CSV**, **Excel** (.xlsx, .xls) 파일
- 회귀, 이진 분류, 다중 분류 문제 자동 감지

### 주요 기능
- **대화형 분석 설정** — 데이터 업로드 후 AI가 최적의 분석 설정을 제안
- **설명가능한 AI** — SHAP 분석으로 모델의 판단 근거를 정량화
- **자동 리포트** — 비즈니스 맥락을 반영한 마크다운·HTML 보고서

시작하려면 분석할 데이터 파일을 업로드하거나, 분석하고 싶은 내용을 말씀해주세요.`;

// ============ Helper Functions ============
function generateFeatureImportance(): FeatureImportance[] {
  const features: { feature: string; importance: number }[] = [
    { feature: 'cp_price', importance: 0.382 },
    { feature: 'jkm_price', importance: 0.271 },
    { feature: 'brent_crude', importance: 0.158 },
    { feature: 'heating_demand_idx', importance: 0.093 },
    { feature: 'usd_krw', importance: 0.057 },
    { feature: 'season', importance: 0.039 },
  ];

  return features;
}

export function generateMockProfile(file: DataFile): DataProfile {
  return {
    fileId: file.id,
    basicStats: {
      rows: file.rows,
      columns: file.columns,
      memoryUsage: formatBytes(file.size),
      duplicateRows: Math.floor(file.rows * 0.002),
    },
    columns: Array.from({ length: Math.min(file.columns, 10) }, (_, i) => ({
      name: `column_${i + 1}`,
      dtype: i % 3 === 0 ? 'float64' : i % 3 === 1 ? 'int64' : 'object',
      nonNull: file.rows - Math.floor(Math.random() * file.rows * 0.05),
      unique: Math.floor(Math.random() * 100) + 10,
      mean: i % 3 !== 2 ? Math.random() * 100 : undefined,
      std: i % 3 !== 2 ? Math.random() * 20 : undefined,
      min: i % 3 !== 2 ? 0 : undefined,
      max: i % 3 !== 2 ? Math.random() * 200 : undefined,
    })),
    missingValues: Array.from({ length: 5 }, (_, i) => ({
      column: `column_${i + 1}`,
      count: Math.floor(Math.random() * file.rows * 0.03),
      percentage: Math.random() * 3,
    })),
  };
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || isNaN(bytes) || bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatNumber(num: number | null | undefined): string {
  if (num == null || isNaN(num)) return '\u2014';
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
  return num.toString();
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${minutes}m ${secs}s`;
}

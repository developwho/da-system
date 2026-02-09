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
    name: 'energy_price_sample.csv',
    size: 12_800,
    rows: 94,
    columns: 12,
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
    name: 'LightGBM - 가스 도입 원가 예측',
    algorithm: 'LightGBM',
    datasetId: 'file-1',
    datasetName: 'energy_price_sample.csv',
    problemType: 'regression',
    status: 'complete',
    metrics: {
      rmse: 1.23,
      mae: 0.87,
      r2: 0.946,
    },
    trainingStartedAt: new Date('2025-10-20T09:05:00'),
    trainingCompletedAt: new Date('2025-10-20T09:18:00'),
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
    title: '국내 가스 도입 원가 예측 분석 리포트',
    problemType: 'regression',
    createdAt: new Date('2025-10-20T09:20:00'),
    insights: [
      '브렌트유 가격이 전체 예측력의 31.2%를 차지하며 최대 영향 변수',
      'LightGBM 모델 R\u00B2=0.946으로 높은 예측 정확도 달성',
      '환율(KRW/USD)이 비선형 영향을 미치며, 1,300원 이상 구간에서 가격 민감도 급증',
    ],
    modelId: 'model-1',
    datasetId: 'file-1',
    datasetName: 'energy_price_sample.csv',
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
  'session-1': `# 국내 가스 도입 원가 예측 분석 리포트

## 문서 정보
- **프로젝트:** LPG·도시가스 도입 원가 예측 모델 구축
- **데이터셋:** \`energy_price_sample.csv\` (94행, 12개 컬럼)
- **기간:** 2018년 1월 ~ 2025년 10월 (월별)
- **문제 유형:** 회귀 (타겟: \`domestic_gas_price\`, 원/MJ)
- **검증 방식:** 시계열 기반 롤링 홀드아웃
- **핵심 목표:** 가스 도입 원가의 주요 변동 요인을 정량화하고 단기 예측 모델 구축

## 경영진 요약

국내 가스 도입 원가는 국제 에너지 시장의 복합적 요인에 의해 결정됩니다. 본 분석은 94개월 간의 월별 데이터를 활용하여 **LightGBM 기반 예측 모델**을 구축했으며, **R\u00B2=0.946**의 높은 설명력을 달성했습니다.

### 핵심 성과
| 지표 | 값 |
|---|---:|
| RMSE | 1.23 원/MJ |
| MAE | 0.87 원/MJ |
| R\u00B2 | 0.946 |
| MAPE | 4.2% |

### 전략적 시사점
브렌트유 가격(31.2%)과 JKM 현물가격(24.3%)이 전체 예측력의 55%를 차지하며, 이 두 지표의 모니터링만으로도 도입 원가의 방향성을 상당 부분 예측할 수 있습니다.

## 1. 비즈니스 맥락

도시가스 및 LPG 사업에서 **도입 원가 예측**은 다음 의사결정의 핵심 입력입니다:
- **요금 조정 시기** 판단 및 선제적 원가 헷지
- **재고 관리** 전략 수립 (저점 매입, 고점 방어)
- **영업 마진** 시뮬레이션 및 분기별 실적 전망
- **규제 대응** 자료 (에너지위원회 보고용 근거)

국제 에너지 가격의 변동성이 확대되는 현 시점에서, 데이터 기반 예측 체계의 구축은 경영 안정성 확보에 필수적입니다.

## 2. 데이터 진단

### 데이터 개요
- **관측치:** 94개월 (2018-01 ~ 2025-10)
- **변수:** 예측변수 11개 + 타겟 1개
- **결측값:** 없음 (0.0%)
- **메모리:** 약 0.1 MB

### 주요 변수 설명
| 변수 | 설명 | 단위 |
|---|---|---|
| brent_oil_price | 브렌트유 현물가격 | $/배럴 |
| jkm_spot_price | JKM(아시아 LNG 벤치마크) 현물가격 | $/MMBTU |
| exchange_rate_krw | 원/달러 환율 | KRW/USD |
| ppi_index | 생산자물가지수 | 지수 |
| heating_degree_days | 난방도일 | 도일 |
| lng_import_volume | LNG 수입량 | 천톤 |
| gas_inventory | 천연가스 재고 | 백만톤 |
| power_consumption | 산업용 전력소비 | GWh |
| cpi_index | 소비자물가지수 | 지수 |
| lng_import_price | 수입 LNG 단가 | $/MMBTU |
| crude_import | 원유 수입량 | 천배럴 |

### 품질 진단
- 결측: 없음
- 이상치: 브렌트유 2020년 급락(COVID) 반영, 자연 변동으로 판단
- 시계열 정상성: ADF 검정 결과 대부분 변수 비정상 → 차분/트렌드 보정 적용

## 3. 모델링

### 비교 모델군
| 모델 | RMSE | MAE | R\u00B2 |
|---|---:|---:|---:|
| Linear Regression | 2.85 | 2.31 | 0.782 |
| RandomForest | 1.67 | 1.22 | 0.912 |
| XGBoost | 1.34 | 0.94 | 0.938 |
| **LightGBM (챔피언)** | **1.23** | **0.87** | **0.946** |

### LightGBM 선정 근거
- 소규모 데이터셋(94행)에서도 과적합 없이 안정적 성능
- 범주형 변수 네이티브 지원 (계절성 인코딩 불필요)
- 학습 속도 우수 (13분 내 전체 탐색 완료)
- SHAP 호환성 양호 → 해석 가능성 확보

## 4. 모델 성능

### 예측 vs 실제
최근 24개월(2023-11 ~ 2025-10) 홀드아웃 검증에서 평균 오차 0.87 원/MJ로, 실무 의사결정에 충분한 정확도를 확인했습니다.

### 잔차 분석
- 잔차 평균: 0.02 (편향 거의 없음)
- 잔차 표준편차: 1.21
- 자기상관: Durbin-Watson 1.87 (자기상관 미미)

## 5. 설명가능성 (SHAP 분석)

### 글로벌 변수 기여도
| 순위 | 변수 | SHAP 기여도 | 방향성 |
|---:|---|---:|---|
| 1 | brent_oil_price | 31.2% | 가격 상승 시 원가 증가 |
| 2 | jkm_spot_price | 24.3% | JKM 상승 시 원가 증가 |
| 3 | exchange_rate_krw | 11.8% | 원화 약세 시 원가 증가 |
| 4 | ppi_index | 8.9% | PPI 상승 시 원가 증가 |
| 5 | heating_degree_days | 7.4% | 한파 시 수요↑ → 원가 증가 |
| 6 | lng_import_volume | 5.8% | 수입량 증가 시 가격 압력 |
| 7 | gas_inventory | 4.2% | 재고 감소 시 원가 증가 |
| 8 | power_consumption | 3.1% | 전력 수요 간접 영향 |
| 9 | cpi_index | 1.8% | 거시 물가 연동 |
| 10 | lng_import_price | 1.2% | JKM과 높은 상관 (중복 제거) |
| 11 | crude_import | 0.3% | 원유 수입량 직접 영향 미미 |

### 핵심 인사이트
1. **브렌트유 + JKM = 55.5%**: 국제 에너지 가격이 도입 원가의 절반 이상을 설명
2. **환율 비선형 효과**: 1,300원 이상 구간에서 SHAP 기여도가 급격히 증가 (임계효과)
3. **계절성 7.4%**: 난방도일을 통해 동절기 수요 증가가 원가에 반영
4. **재고 역관계**: 재고가 5백만톤 이하로 떨어지면 가격 압력이 비례적으로 증가

## 6. 경제성 영향

### 예측 활용 시 기대효과
- **재고 매입 최적화**: 저점 예측 시 선행 구매 → 연간 약 2~3% 원가 절감
- **요금 조정 선제 대응**: 3개월 전 방향성 예측으로 규제 리스크 감소
- **마진 안정화**: 변동성 ±4.2%(MAPE) 내 예측으로 분기 실적 편차 축소

## 7. 권고사항

### 즉시 실행
1. 브렌트유·JKM 일일 모니터링 대시보드 구축
2. 월별 모델 재학습 파이프라인 자동화
3. 환율 1,300원 돌파 시 경보 체계 연동

### 중기 과제
1. 지정학적 이벤트(OPEC 회의, 중동 정세) 텍스트 변수 추가
2. 날씨 예보 데이터 연동으로 난방도일 예측 정확도 향상
3. 분기별 챌린저 모델 비교 체계 도입

## 8. 리스크 및 한계
| 리스크 | 영향 | 대응 |
|---|---|---|
| 데이터 규모 | 94개월은 통계적 검정력 한계 | 주간 데이터 확보 시 재학습 |
| 외부 충격 | COVID급 이벤트 예측 불가 | 이상치 탐지 + 수동 개입 |
| 구조 변화 | 에너지 전환 정책 변경 | 연 1회 모델 구조 재검토 |
| 다중공선성 | JKM-LNG 단가 상관 0.85 | SHAP 기반 독립 기여도 분리 |

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

export const MOCK_INTENT_RESPONSE = `도시가스 가격 예측은 에너지 사업에서 매우 중요한 분석 주제입니다. 도입 원가를 사전에 예측할 수 있다면 **재고 매입 시점 최적화**, **요금 조정 선제 대응**, **마진 시뮬레이션** 등 다양한 의사결정에 직접 활용할 수 있습니다.

정확한 예측 모델을 구축하려면 다음과 같은 데이터가 이상적입니다:

| 카테고리 | 예시 변수 |
|---|---|
| 국제 에너지 가격 | 브렌트유, JKM LNG 현물가 |
| 거시경제 지표 | 원/달러 환율, 생산자물가지수 |
| 수급 지표 | LNG 수입량, 천연가스 재고 |
| 수요 요인 | 난방도일, 산업용 전력소비량 |

월별 시계열 데이터가 있다면 더욱 정밀한 분석이 가능합니다. 관련 데이터를 CSV 또는 Excel 파일로 업로드해주세요. 데이터를 분석한 후 최적의 예측 전략을 제안해드리겠습니다.`;

export const MOCK_DATA_ANALYSIS_RESPONSE = `데이터를 분석했습니다.

### 데이터 개요
**94개월** (2018.01 ~ 2025.10)의 에너지 가격 시계열 데이터입니다.

| 항목 | 내용 |
|---|---|
| 관측치 | 94행 (월별) |
| 변수 | 11개 예측변수 + 1개 타겟 |
| 결측값 | 없음 |
| 타겟 후보 | \`domestic_gas_price\` (원/MJ) |

### 변수 구성 분석
**국제 에너지 가격** (브렌트유, JKM, LNG 수입단가), **거시경제 지표** (환율, PPI, CPI), **수급 변수** (LNG 수입량, 가스 재고), **수요 지표** (난방도일, 전력소비)가 고르게 포함되어 있어 다각적인 분석이 가능합니다.

특히 **JKM 현물가격**과 **브렌트유 가격**을 함께 포함한 점이 인상적입니다. 이 두 변수는 국내 가스 도입 원가의 핵심 결정 요인으로 알려져 있습니다.

### 분석 방향
말씀하신 **도시가스 가격 예측** 목표에 맞춰 다음과 같이 진행하겠습니다:

1. **FLAML AutoML**로 LightGBM, XGBoost 등 최적 회귀 모델 탐색
2. **SHAP 분석**으로 어떤 요인이 가격을 얼마나 움직이는지 정량화
3. 경영 의사결정에 활용 가능한 **종합 리포트** 생성

아래에서 세부 분석 설정을 확인해주세요.`;

export const MOCK_DATA_ANALYSIS_COLD_RESPONSE = `업로드해주신 데이터를 분석했습니다.

### 데이터 개요
**94개월** (2018.01 ~ 2025.10)의 에너지 가격 시계열 데이터입니다.

| 항목 | 내용 |
|---|---|
| 관측치 | 94행 (월별) |
| 변수 | 11개 예측변수 + 1개 타겟 |
| 결측값 | 없음 |
| 타겟 후보 | \`domestic_gas_price\` (원/MJ) |

### 변수 구성 분석
**국제 에너지 가격** (브렌트유, JKM, LNG 수입단가), **거시경제 지표** (환율, PPI, CPI), **수급 변수** (LNG 수입량, 가스 재고), **수요 지표** (난방도일, 전력소비)가 고르게 포함되어 있어 다각적인 분석이 가능합니다.

특히 **JKM 현물가격**과 **브렌트유 가격**을 함께 포함한 점이 인상적입니다. 이 두 변수는 국내 가스 도입 원가의 핵심 결정 요인으로 알려져 있습니다.

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
    { feature: 'brent_oil_price', importance: 0.312 },
    { feature: 'jkm_spot_price', importance: 0.243 },
    { feature: 'exchange_rate_krw', importance: 0.118 },
    { feature: 'ppi_index', importance: 0.089 },
    { feature: 'heating_degree_days', importance: 0.074 },
    { feature: 'lng_import_volume', importance: 0.058 },
    { feature: 'gas_inventory', importance: 0.042 },
    { feature: 'power_consumption', importance: 0.031 },
    { feature: 'cpi_index', importance: 0.018 },
    { feature: 'lng_import_price', importance: 0.012 },
    { feature: 'crude_import', importance: 0.003 },
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

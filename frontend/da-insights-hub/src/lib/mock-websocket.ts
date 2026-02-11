import type {
  WebSocketEvent,
  StatusUpdatePayload,
  MessageReceivedPayload,
  AnalysisStep,
  StepStatus,
  SubStep,
  AnalysisQuestionsPayload,
  AnalysisPlanPayload,
} from '@/types';
import {
  analysisStepsTemplate,
  MOCK_INTENT_RESPONSE,
  MOCK_DATA_ANALYSIS_RESPONSE,
  MOCK_DATA_ANALYSIS_COLD_RESPONSE,
  MOCK_GUIDE_RESPONSE,
} from './mock-data';

const MOCK_DESCRIPTIONS: Record<number, string> = {
  1: 'LPG/도시가스 가격 데이터를 분석하고 예측 문제를 정의하고 있습니다...',
  2: 'LPG 가격 예측 관련 논문과 Kaggle 솔루션을 조사하고 있습니다...',
  3: 'FLAML AutoML로 최적 예측 모델을 탐색하고 학습하고 있습니다...',
  4: 'SHAP 분석으로 변수별 기여도를 산출하고 인사이트를 도출하고 있습니다...',
  5: '종합 분석 리포트를 작성하고 있습니다...',
};

const MOCK_SUB_STEPS: Record<number, string[]> = {
  1: [
    '분석 목표 확인: LPG/도시가스 판매 단가 예측',
  ],
  2: [
    '병렬 선행연구 시작',
    '검색 쿼리: "LPG price forecasting CP JKM"',
    '관련 논문 3건 검색 완료',
    'Kaggle LPG 가격 솔루션 분석 완료',
    'DeepResearch 조사 시작',
    'DeepResearch: LPG/CP 가격 결정 메커니즘 분석 완료',
  ],
  3: [
    '80행 x 8열 데이터 로딩 완료',
    'FLAML AutoML 실행 중... LightGBM vs XGBoost 비교',
    '최적 모델 학습 완료 (LightGBM, R\u00B2=0.94)',
  ],
  4: [
    '학습된 LightGBM 모델 로딩 완료',
    'SHAP TreeExplainer 분석 시작',
    'SHAP 분석 완료 \u2014 cp_price(38.2%), jkm_price(27.1%) 상위 확인',
  ],
  5: [
    '마크다운 리포트 생성 중 (8개 섹션)',
  ],
};

const STEP_TO_PHASE: Record<number, string> = {
  1: 'ProblemDefinition',
  2: 'Research',
  3: 'Modeling',
  4: 'Insight',
  5: 'Reporting',
};

/** Keywords that trigger the energy domain intent response */
const ENERGY_KEYWORDS = ['에너지', '가격', '예측', '가스', '도시가스', '원가', 'lng', '브렌트', 'jkm', '전력', '전기', 'lpg', 'cp'];

type ConversationPhase = 'idle' | 'intent_shared' | 'file_uploaded' | 'analyzing' | 'complete';
type EventCallback = (event: WebSocketEvent) => void;

/**
 * MockWebSocket simulates real-time WebSocket events for development.
 * It mimics the backend's WebSocket behavior with realistic timing.
 *
 * RC12: Conversation state machine for premium multi-turn demo experience.
 */
class MockWebSocket {
  private listeners: EventCallback[] = [];
  private isRunning = false;
  private currentSessionId: string | null = null;
  private abortController: AbortController | null = null;

  /** RC12: Conversation state tracking */
  private conversationState: ConversationPhase = 'idle';
  private userIntent: string | null = null;

  subscribe(callback: EventCallback): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  private emit(event: WebSocketEvent): void {
    this.listeners.forEach((cb) => cb(event));
  }

  connect(sessionId: string): void {
    this.currentSessionId = sessionId;
    // Reset conversation state on new connection
    this.conversationState = 'idle';
    this.userIntent = null;
    setTimeout(() => {
      this.emit({ type: 'connected', payload: { sessionId } });
    }, 100);
  }

  disconnect(): void {
    this.stopAnalysis();
    this.emit({ type: 'disconnected', payload: {} });
    this.currentSessionId = null;
  }

  // Store last answers for plan building
  private lastAnswers: Record<string, string> = {};
  private lastFileId: string | null = null;

  /**
   * Simulates sending a message and receiving AI response.
   * RC12: Routes based on conversation state for multi-turn flow.
   */
  async sendMessage(content: string, fileId?: string): Promise<void> {
    if (!this.currentSessionId) return;

    if (fileId) {
      // File uploaded — always go to data analysis
      this.lastFileId = fileId;
      const hasContext = this.conversationState === 'intent_shared';
      this.conversationState = 'file_uploaded';
      await this.simulateDataAnalysis(this.currentSessionId, hasContext);
    } else if (this.conversationState === 'idle') {
      // First text message — check if it's an energy intent or guide request
      if (this.isGuideRequest(content)) {
        await this.simulateGuideResponse(this.currentSessionId);
      } else if (this.isEnergyIntent(content)) {
        this.userIntent = content;
        this.conversationState = 'intent_shared';
        await this.simulateIntentResponse(this.currentSessionId);
      } else {
        // Generic message — use default response
        await this.simulateResponse(this.currentSessionId, content);
      }
    } else if (this.conversationState === 'intent_shared') {
      // Already shared intent, waiting for file — respond with gentle nudge or default
      await this.simulateResponse(this.currentSessionId, content);
    } else {
      // Default fallback
      await this.simulateResponse(this.currentSessionId, content);
    }
  }

  /**
   * Receive analysis answers and send plan
   */
  async sendAnalysisAnswers(answers: Record<string, string>): Promise<void> {
    if (!this.currentSessionId) return;
    this.lastAnswers = answers;

    await this.delay(200);

    // Build analysis goal with conversation context
    const defaultGoal = 'LPG/도시가스 판매 단가 예측 모델 구축 및 주요 영향 요인 분석';
    const contextualGoal = this.userIntent
      ? '말씀하신 LPG/도시가스 가격 예측을 위한 최적 모델 구축 및 주요 영향 요인 정량 분석'
      : defaultGoal;

    const plan: AnalysisPlanPayload = {
      sessionId: this.currentSessionId,
      plan: {
        analysisGoal: answers.goal || contextualGoal,
        targetColumn: answers.target || 'lpg_retail_price',
        problemType: answers.problem_type || 'regression',
        evaluationMetric: answers.metric || 'rmse',
        constraints: [
          '월별 데이터 (80개월, 2018-03 ~ 2024-10)',
          '80:20 홀드아웃 검증',
        ],
        estimatedDuration: '15~20분',
        steps: [
          { name: '문제 정의', description: 'LPG 판매 단가 예측을 위한 타겟 변수 및 평가 지표 확정' },
          { name: '선행연구', description: 'LPG/에너지 가격 예측 관련 논문 및 Kaggle 솔루션 조사' },
          { name: '모델 학습', description: 'FLAML AutoML로 LightGBM/XGBoost 등 최적 모델 탐색' },
          { name: '인사이트', description: 'SHAP 기반 변수별 기여도 분석 및 비즈니스 해석' },
          { name: '리포트', description: '경영진 요약, SHAP 드라이버, 권고사항 포함 종합 보고서 생성' },
        ],
      },
    };

    this.emit({
      type: 'analysis.plan',
      payload: plan,
    });
  }

  /**
   * Confirm plan and start analysis
   */
  async sendAnalysisConfirm(): Promise<void> {
    if (!this.currentSessionId) return;
    this.conversationState = 'analyzing';
    await this.simulateAnalysis(this.currentSessionId, this.lastFileId || 'mock-file');
  }

  /** Check if user message is about energy/gas/price prediction */
  private isEnergyIntent(message: string): boolean {
    const lower = message.toLowerCase();
    return ENERGY_KEYWORDS.some((kw) => lower.includes(kw));
  }

  /** Check if user is asking about system guide */
  private isGuideRequest(message: string): boolean {
    const lower = message.toLowerCase();
    return lower.includes('시스템') || lower.includes('안내') || lower.includes('어떤 분석') || lower.includes('할 수 있');
  }

  /**
   * RC12: Simulates a domain expert response after user shares intent.
   * Rich markdown with business value + ideal data table + file upload prompt.
   */
  private async simulateIntentResponse(sessionId: string): Promise<void> {
    const messageId = `msg-intent-${Date.now()}`;
    await this.streamMessage(sessionId, messageId, MOCK_INTENT_RESPONSE, 1500);
  }

  /**
   * RC12: Simulates rich data analysis response after file upload.
   * Shows data overview, variable analysis, and analysis direction.
   * Then transitions to Q&A flow.
   */
  private async simulateDataAnalysis(sessionId: string, hasContext: boolean): Promise<void> {
    const messageId = `msg-data-${Date.now()}`;
    const responseText = hasContext ? MOCK_DATA_ANALYSIS_RESPONSE : MOCK_DATA_ANALYSIS_COLD_RESPONSE;

    await this.streamMessage(sessionId, messageId, responseText, 2000);

    // After data analysis response, transition to Q&A
    await this.delay(300);
    await this.simulateQuestions(sessionId);
  }

  /**
   * RC12: Simulates system guide response (no analysis flow).
   */
  private async simulateGuideResponse(sessionId: string): Promise<void> {
    const messageId = `msg-guide-${Date.now()}`;
    await this.streamMessage(sessionId, messageId, MOCK_GUIDE_RESPONSE, 1500);
  }

  /**
   * Simulates the Q&A flow: analysis.questions event only.
   * RC12: Intro message removed — data analysis response replaces it.
   */
  private async simulateQuestions(sessionId: string): Promise<void> {
    const questionsPayload: AnalysisQuestionsPayload = {
      sessionId,
      profile: {
        rows: 80,
        columns: 8,
        numericColumns: [
          'cp_price', 'jkm_price', 'brent_crude',
          'heating_demand_idx', 'usd_krw', 'inventory_level',
          'lpg_retail_price',
        ],
        categoricalColumns: ['season'],
        missingCellsPct: 0.0,
        duplicateRows: 0,
        memoryMB: 0.05,
      },
      questions: [
        {
          id: 'target',
          type: 'select',
          label: '타겟 변수 (예측할 컬럼)',
          description: this.userIntent
            ? '말씀하신 가격 예측 목표에 맞춰 타겟 변수를 추천합니다.'
            : '모델이 예측할 대상 컬럼을 선택하세요.',
          required: true,
          defaultValue: 'lpg_retail_price',
          options: [
            { value: 'lpg_retail_price', label: 'lpg_retail_price', recommended: true, reason: '연속형 변수, LPG 판매 단가 (원/kg)' },
            { value: 'cp_price', label: 'cp_price' },
            { value: 'jkm_price', label: 'jkm_price' },
          ],
        },
        {
          id: 'problem_type',
          type: 'radio',
          label: '문제 유형',
          description: '데이터의 특성을 분석한 결과, 회귀 분석을 추천합니다.',
          required: true,
          defaultValue: 'regression',
          options: [
            { value: 'regression', label: '회귀', recommended: true, reason: '타겟이 연속형 수치 (원/kg)' },
            { value: 'time_series', label: '시계열 예측' },
          ],
        },
        {
          id: 'metric',
          type: 'radio',
          label: '평가 지표',
          description: '모델 성능을 측정할 지표를 선택하세요.',
          required: true,
          defaultValue: 'rmse',
          options: [
            { value: 'rmse', label: 'RMSE', recommended: true, reason: '오차 크기에 민감, 이상치 탐지에 적합' },
            { value: 'mae', label: 'MAE', reason: '평균 절대 오차' },
            { value: 'r2', label: 'R\u00B2', reason: '설명력 지표' },
          ],
        },
        {
          id: 'goal',
          type: 'text',
          label: '분석 목표 (선택사항)',
          description: '분석의 비즈니스 목표를 간단히 설명해주세요.',
          placeholder: this.userIntent
            ? 'LPG/도시가스 판매 단가를 예측하여 CP 계약 타이밍 최적화에 활용'
            : 'LPG 판매 단가를 예측하여 영업 의사결정에 활용',
          required: false,
        },
      ],
    };

    this.emit({
      type: 'analysis.questions',
      payload: questionsPayload,
    });
  }

  /**
   * Simulates a simple AI response with streaming
   */
  private async simulateResponse(sessionId: string, userMessage: string): Promise<void> {
    const responses: Record<string, string> = {
      default: `데이터 분석을 도와드리겠습니다. 다음 작업을 수행할 수 있습니다:

1. **데이터 업로드** \u2014 CSV 또는 Excel 파일을 드래그앤드롭하세요
2. **업로드된 데이터 확인** \u2014 데이터 탭에서 파일을 확인할 수 있습니다
3. **모델 학습** \u2014 데이터셋을 선택하면 자동으로 ML 학습을 시작합니다
4. **리포트 확인** \u2014 생성된 분석 리포트를 확인할 수 있습니다

무엇을 도와드릴까요?`,
      features: `SHAP 변수 기여도 분석 결과입니다:

예측력 상위 5개 변수:
1. **brent_oil_price** (31.2%) \u2014 브렌트유 현물가격
2. **jkm_spot_price** (24.3%) \u2014 JKM 현물가격
3. **exchange_rate_krw** (11.8%) \u2014 원/달러 환율
4. **ppi_index** (8.9%) \u2014 생산자물가지수
5. **heating_degree_days** (7.4%) \u2014 난방도일

이 5개 변수가 전체 예측력의 83.6%를 설명합니다.`,
    };

    const responseText = userMessage.toLowerCase().includes('feature') || userMessage.includes('변수')
      ? responses.features
      : responses.default;

    const messageId = `msg-${Date.now()}`;
    await this.streamMessage(sessionId, messageId, responseText);
  }

  /**
   * Builds accumulated subSteps for a given step and progress
   */
  /** Stable timestamps for completed substeps — avoids re-render from Date.now() */
  private subStepTimestamps = new Map<string, number>();

  private buildSubSteps(stepIndex: number, progressRatio: number, completedSteps: number[]): SubStep[] {
    const allSubSteps: SubStep[] = [];

    // Add completed sub-steps from previous steps
    for (const prevStep of completedSteps) {
      const labels = MOCK_SUB_STEPS[prevStep] || [];
      const phase = STEP_TO_PHASE[prevStep] || 'Unknown';
      for (let j = 0; j < labels.length; j++) {
        const id = `sub-${prevStep}-${j}`;
        if (!this.subStepTimestamps.has(id)) {
          this.subStepTimestamps.set(id, Date.now());
        }
        allSubSteps.push({
          id,
          label: labels[j],
          status: 'complete',
          timestamp: this.subStepTimestamps.get(id)!,
          phase,
        });
      }
    }

    // Add sub-steps for the current step based on progress
    const currentStepNum = stepIndex + 1;
    const currentLabels = MOCK_SUB_STEPS[currentStepNum] || [];
    const currentPhase = STEP_TO_PHASE[currentStepNum] || 'Unknown';
    const visibleCount = Math.ceil(progressRatio * currentLabels.length);
    for (let j = 0; j < visibleCount; j++) {
      const isLast = j === visibleCount - 1 && progressRatio < 1;
      const id = `sub-${currentStepNum}-${j}`;
      if (!this.subStepTimestamps.has(id)) {
        this.subStepTimestamps.set(id, Date.now());
      }
      allSubSteps.push({
        id,
        label: currentLabels[j],
        status: isLast ? 'running' : 'complete',
        timestamp: this.subStepTimestamps.get(id)!,
        phase: currentPhase,
      });
    }

    return allSubSteps;
  }

  /**
   * Simulates the full 5-step analysis pipeline
   */
  async simulateAnalysis(sessionId: string, fileId: string): Promise<void> {
    this.isRunning = true;
    this.abortController = new AbortController();

    const steps = JSON.parse(JSON.stringify(analysisStepsTemplate)) as AnalysisStep[];
    const stepDurations = [1500, 2000, 4000, 2500, 1500]; // ms per step (총 11.5초로 압축)
    const completedStepNumbers: number[] = [];

    // Initial message
    const introMessageId = `msg-intro-${Date.now()}`;
    await this.streamMessage(
      sessionId,
      introMessageId,
      '파일을 확인했습니다. 자동 분석을 시작합니다.\n\n5단계로 진행됩니다:\n1. 문제 정의\n2. 선행연구\n3. 모델 학습\n4. 인사이트 도출\n5. 리포트 생성'
    );

    // Process each step
    for (let i = 0; i < steps.length; i++) {
      if (!this.isRunning) break;

      steps[i].status = 'running' as StepStatus;
      steps[i].startedAt = new Date();

      this.emit({
        type: 'status.update',
        payload: {
          sessionId,
          step: i + 1,
          totalSteps: 5,
          stepName: steps[i].name,
          status: 'running',
          progress: 0,
          description: MOCK_DESCRIPTIONS[i + 1] || '',
          subSteps: this.buildSubSteps(i, 0, completedStepNumbers),
        } as StatusUpdatePayload,
      });

      // Simulate progress within step
      const progressSteps = 25;
      for (let p = 1; p <= progressSteps; p++) {
        if (!this.isRunning) break;
        await this.delay(stepDurations[i] / progressSteps);

        const progressRatio = p / progressSteps;

        this.emit({
          type: 'status.update',
          payload: {
            sessionId,
            step: i + 1,
            totalSteps: 5,
            stepName: steps[i].name,
            status: 'running',
            progress: progressRatio * 100,
            description: MOCK_DESCRIPTIONS[i + 1] || '',
            details: i === 1 ? this.getResearchDetails(progressRatio) : undefined,
            subSteps: this.buildSubSteps(i, progressRatio, completedStepNumbers),
          } as StatusUpdatePayload,
        });
      }

      // Mark step complete
      steps[i].status = 'complete' as StepStatus;
      steps[i].completedAt = new Date();
      completedStepNumbers.push(i + 1);

      this.emit({
        type: 'status.update',
        payload: {
          sessionId,
          step: i + 1,
          totalSteps: 5,
          stepName: steps[i].name,
          status: 'complete',
          progress: 100,
          description: MOCK_DESCRIPTIONS[i + 1] || '',
          subSteps: this.buildSubSteps(i, 1, completedStepNumbers.slice(0, -1)),
        } as StatusUpdatePayload,
      });
    }

    if (this.isRunning) {
      // Final results message
      const resultsMessageId = `msg-results-${Date.now()}`;
      await this.streamMessage(
        sessionId,
        resultsMessageId,
        `## 분석 완료

**LightGBM** 모델이 검증 데이터에서 **R\u00B2=0.94, MAPE=4.8%**를 달성했습니다.

### 모델 성능
| 지표 | 값 |
|---|---:|
| R\u00B2 | 0.94 |
| MAPE | 4.8% |
| RMSE | 1.18 원/kg |
| MAE | 0.82 원/kg |

### SHAP 변수 기여도
| 순위 | 변수 | 기여도 |
|---:|---|---:|
| 1 | cp_price | 38.2% |
| 2 | jkm_price | 27.1% |
| 3 | brent_crude | 15.8% |
| 4 | heating_demand_idx | 9.3% |
| 5 | usd_krw | 5.7% |
| 6 | season | 3.9% |

### 주요 인사이트
- **CP + JKM + 유가 = 81.1%**: 국제 에너지 가격 3개 변수가 판매가의 대부분을 설명
- **환율 비선형 효과**: 1,350원 이상 구간에서 SHAP 기여도 급증
- **계절성 13.2%**: 난방 수요 + 계절 변수가 동절기 가격 프리미엄을 포착
- **CP 가격 지배적**: 사우디 아람코 CP가 단일 변수 최고 설명력(38.2%)`
      );

      // Emit report.ready event
      await this.delay(500);
      this.emit({
        type: 'report.ready',
        payload: {
          sessionId,
          title: 'LPG/도시가스 가격 예측 분석 리포트',
          preview: `# LPG/도시가스 가격 예측 분석 리포트\n\n## 요약\nLightGBM 모델이 R\u00B2=0.94, MAPE=4.8%의 높은 예측 정확도를 달성했습니다.\n\n## 주요 발견\n- CP(38.2%), JKM(27.1%), 유가(15.8%)가 전체 예측력의 81.1% 점유\n- 환율 1,350원 돌파 시 판매가 민감도 급증\n- 동절기 난방 수요가 가격에 13.2% 기여\n\n## 모델 성능\n- R\u00B2: 0.94\n- MAPE: 4.8%\n- RMSE: 1.18 원/kg`,
        },
      });

      this.conversationState = 'complete';
    }

    this.isRunning = false;
  }

  private getResearchDetails(progress: number) {
    return {
      researchSources: [
        {
          name: 'HuggingFace' as const,
          status: progress > 0.3 ? ('complete' as const) : ('running' as const),
          resultsCount: progress > 0.3 ? 3 : undefined,
        },
        {
          name: 'Kaggle' as const,
          status: progress > 0.6 ? ('complete' as const) : progress > 0.3 ? ('running' as const) : ('pending' as const),
          resultsCount: progress > 0.6 ? 8 : undefined,
        },
        {
          name: 'DeepResearch' as const,
          status: progress > 0.9 ? ('complete' as const) : progress > 0.6 ? ('running' as const) : ('pending' as const),
          resultsCount: progress > 0.9 ? 2 : undefined,
        },
      ],
    };
  }

  /**
   * Streams a message word by word with optional thinking delay.
   * RC12: Paragraph breaks (\n\n) get a slightly longer delay for natural pacing.
   */
  private async streamMessage(
    sessionId: string,
    messageId: string,
    text: string,
    thinkingDelay = 0,
  ): Promise<void> {
    // Temporarily enable isRunning for streaming (some callers need it)
    const wasRunning = this.isRunning;
    this.isRunning = true;

    if (thinkingDelay > 0) {
      await this.delay(thinkingDelay);
    }

    const words = text.split(' ');

    for (let i = 0; i < words.length; i++) {
      if (!this.isRunning) break;

      // Slightly longer delay after paragraph breaks
      const word = words[i];
      const isParagraphBreak = word.includes('\n\n');
      await this.delay(isParagraphBreak ? 60 + Math.random() * 20 : 25 + Math.random() * 15);

      this.emit({
        type: 'message.received',
        payload: {
          sessionId,
          messageId,
          chunk: word + (i < words.length - 1 ? ' ' : ''),
          isComplete: false,
        } as MessageReceivedPayload,
      });
    }

    this.emit({
      type: 'message.complete',
      payload: { sessionId, messageId },
    });

    // Restore previous running state
    this.isRunning = wasRunning;
  }

  stopAnalysis(): void {
    this.isRunning = false;
    this.abortController?.abort();
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

// Singleton instance
export const mockWebSocket = new MockWebSocket();

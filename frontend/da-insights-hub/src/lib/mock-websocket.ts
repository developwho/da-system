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
import { analysisStepsTemplate } from './mock-data';

const MOCK_DESCRIPTIONS: Record<number, string> = {
  1: '에너지 가격 데이터를 분석하고 예측 문제를 정의하고 있습니다...',
  2: '에너지 가격 예측 관련 논문과 Kaggle 솔루션을 조사하고 있습니다...',
  3: 'FLAML AutoML로 최적 예측 모델을 탐색하고 학습하고 있습니다...',
  4: 'SHAP 분석으로 변수별 기여도를 산출하고 인사이트를 도출하고 있습니다...',
  5: '종합 분석 리포트를 작성하고 있습니다...',
};

const MOCK_SUB_STEPS: Record<number, string[]> = {
  1: [
    '분석 목표 확인: 국내 가스 도입 원가 예측',
  ],
  2: [
    '병렬 선행연구 시작',
    '검색 쿼리: "energy price forecasting LNG"',
    '관련 논문 3건 검색 완료',
    'Kaggle 에너지 가격 솔루션 분석 완료',
    'DeepResearch 조사 시작',
    'DeepResearch: LNG 가격 결정 메커니즘 분석 완료',
  ],
  3: [
    '94행 x 12열 데이터 로딩 완료',
    'FLAML AutoML 실행 중... LightGBM vs XGBoost 비교',
    '최적 모델 학습 완료 (LightGBM, R\u00B2=0.946)',
  ],
  4: [
    '학습된 LightGBM 모델 로딩 완료',
    'SHAP TreeExplainer 분석 시작',
    'SHAP 분석 완료 \u2014 브렌트유(31.2%), JKM(24.3%) 상위 확인',
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

type EventCallback = (event: WebSocketEvent) => void;

/**
 * MockWebSocket simulates real-time WebSocket events for development.
 * It mimics the backend's WebSocket behavior with realistic timing.
 */
class MockWebSocket {
  private listeners: EventCallback[] = [];
  private isRunning = false;
  private currentSessionId: string | null = null;
  private abortController: AbortController | null = null;

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
   * Simulates sending a message and receiving AI response
   */
  async sendMessage(content: string, fileId?: string): Promise<void> {
    if (!this.currentSessionId) return;

    // If file is attached, start Q&A flow instead of immediate analysis
    if (fileId) {
      this.lastFileId = fileId;
      await this.simulateQuestions(this.currentSessionId);
    } else {
      // Simple Q&A response
      await this.simulateResponse(this.currentSessionId, content);
    }
  }

  /**
   * Receive analysis answers and send plan
   */
  async sendAnalysisAnswers(answers: Record<string, string>): Promise<void> {
    if (!this.currentSessionId) return;
    this.lastAnswers = answers;

    await this.delay(500);

    const plan: AnalysisPlanPayload = {
      sessionId: this.currentSessionId,
      plan: {
        analysisGoal: answers.goal || '국내 가스 도입 원가 예측 모델 구축 및 주요 영향 요인 분석',
        targetColumn: answers.target || 'domestic_gas_price',
        problemType: answers.problem_type || 'regression',
        evaluationMetric: answers.metric || 'rmse',
        constraints: [
          '월별 데이터 (94개월, 2018-01 ~ 2025-10)',
          '최근 2년 데이터 검증 필요',
        ],
        estimatedDuration: '15~20분',
        steps: [
          { name: '문제 정의', description: '가스 도입 원가 예측을 위한 타겟 변수 및 평가 지표 확정' },
          { name: '선행연구', description: '에너지 가격 예측 관련 논문 및 Kaggle 솔루션 조사' },
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
    await this.simulateAnalysis(this.currentSessionId, this.lastFileId || 'mock-file');
  }

  /**
   * Simulates the Q&A flow: intro message + analysis.questions event
   */
  private async simulateQuestions(sessionId: string): Promise<void> {
    // Enable streaming temporarily (streamMessage checks isRunning)
    this.isRunning = true;
    const introId = `msg-intro-${Date.now()}`;
    await this.streamMessage(
      sessionId,
      introId,
      '데이터를 확인했습니다. 최적의 분석을 위해 몇 가지 설정을 확인하겠습니다.'
    );
    this.isRunning = false;

    await this.delay(300);

    // Send analysis.questions event
    const questionsPayload: AnalysisQuestionsPayload = {
      sessionId,
      profile: {
        rows: 94,
        columns: 12,
        numericColumns: [
          'brent_oil_price', 'jkm_spot_price', 'exchange_rate_krw',
          'ppi_index', 'heating_degree_days', 'lng_import_volume',
          'gas_inventory', 'power_consumption', 'cpi_index',
          'lng_import_price', 'crude_import',
        ],
        categoricalColumns: [],
        missingCellsPct: 0.0,
        duplicateRows: 0,
        memoryMB: 0.1,
      },
      questions: [
        {
          id: 'target',
          type: 'select',
          label: '\ud0c0\uac9f \ubcc0\uc218 (\uc608\uce21\ud560 \ucee8\ub7fc)',
          description: '\ubaa8\ub378\uc774 \uc608\uce21\ud560 \ub300\uc0c1 \ucee8\ub7fc\uc744 \uc120\ud0dd\ud558\uc138\uc694.',
          required: true,
          defaultValue: 'domestic_gas_price',
          options: [
            { value: 'domestic_gas_price', label: 'domestic_gas_price', recommended: true, reason: '\uc5f0\uc18d\ud615 \ubcc0\uc218, \uad6d\ub0b4 \uac00\uc2a4 \ub3c4\uc785 \uc6d0\uac00 (\uc6d0/MJ)' },
            { value: 'brent_oil_price', label: 'brent_oil_price' },
            { value: 'jkm_spot_price', label: 'jkm_spot_price' },
          ],
        },
        {
          id: 'problem_type',
          type: 'radio',
          label: '\ubb38\uc81c \uc720\ud615',
          description: '\ub370\uc774\ud130\uc758 \ud2b9\uc131\uc744 \ubd84\uc11d\ud55c \uacb0\uacfc, \ud68c\uadc0 \ubd84\uc11d\uc744 \ucd94\ucc9c\ud569\ub2c8\ub2e4.',
          required: true,
          defaultValue: 'regression',
          options: [
            { value: 'regression', label: '\ud68c\uadc0', recommended: true, reason: '\ud0c0\uac9f\uc774 \uc5f0\uc18d\ud615 \uc218\uce58 (\uc6d0/MJ)' },
            { value: 'time_series', label: '\uc2dc\uacc4\uc5f4 \uc608\uce21' },
          ],
        },
        {
          id: 'metric',
          type: 'radio',
          label: '\ud3c9\uac00 \uc9c0\ud45c',
          description: '\ubaa8\ub378 \uc131\ub2a5\uc744 \uce21\uc815\ud560 \uc9c0\ud45c\ub97c \uc120\ud0dd\ud558\uc138\uc694.',
          required: true,
          defaultValue: 'rmse',
          options: [
            { value: 'rmse', label: 'RMSE', recommended: true, reason: '\uc624\ucc28 \ud06c\uae30\uc5d0 \ubbfc\uac10, \uc774\uc0c1\uce58 \ud0d0\uc9c0\uc5d0 \uc801\ud569' },
            { value: 'mae', label: 'MAE', reason: '\ud3c9\uade0 \uc808\ub300 \uc624\ucc28' },
            { value: 'r2', label: 'R\u00B2', reason: '\uc124\uba85\ub825 \uc9c0\ud45c' },
          ],
        },
        {
          id: 'goal',
          type: 'text',
          label: '\ubd84\uc11d \ubaa9\ud45c (\uc120\ud0dd\uc0ac\ud56d)',
          description: '\ubd84\uc11d\uc758 \ube44\uc988\ub2c8\uc2a4 \ubaa9\ud45c\ub97c \uac04\ub2e8\ud788 \uc124\uba85\ud574\uc8fc\uc138\uc694.',
          placeholder: '\ud5a5\ud6c4 \uac00\uc2a4 \ub3c4\uc785 \uc6d0\uac00\ub97c \uc608\uce21\ud558\uc5ec \uc601\uc5c5 \uc758\uc0ac\uacb0\uc815\uc5d0 \ud65c\uc6a9',
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
      default: `\ub370\uc774\ud130 \ubd84\uc11d\uc744 \ub3c4\uc640\ub4dc\ub9ac\uaca0\uc2b5\ub2c8\ub2e4. \ub2e4\uc74c \uc791\uc5c5\uc744 \uc218\ud589\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4:

1. **\ub370\uc774\ud130 \uc5c5\ub85c\ub4dc** \u2014 CSV \ub610\ub294 Excel \ud30c\uc77c\uc744 \ub4dc\ub798\uadf8\uc575\ub4dc\ub86d\ud558\uc138\uc694
2. **\uc5c5\ub85c\ub4dc\ub41c \ub370\uc774\ud130 \ud655\uc778** \u2014 \ub370\uc774\ud130 \ud0ed\uc5d0\uc11c \ud30c\uc77c\uc744 \ud655\uc778\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4
3. **\ubaa8\ub378 \ud559\uc2b5** \u2014 \ub370\uc774\ud130\uc14b\uc744 \uc120\ud0dd\ud558\uba74 \uc790\ub3d9\uc73c\ub85c ML \ud559\uc2b5\uc744 \uc2dc\uc791\ud569\ub2c8\ub2e4
4. **\ub9ac\ud3ec\ud2b8 \ud655\uc778** \u2014 \uc0dd\uc131\ub41c \ubd84\uc11d \ub9ac\ud3ec\ud2b8\ub97c \ud655\uc778\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4

\ubb34\uc5c7\uc744 \ub3c4\uc640\ub4dc\ub9b4\uae4c\uc694?`,
      features: `SHAP \ubcc0\uc218 \uae30\uc5ec\ub3c4 \ubd84\uc11d \uacb0\uacfc\uc785\ub2c8\ub2e4:

\uc608\uce21\ub825 \uc0c1\uc704 5\uac1c \ubcc0\uc218:
1. **brent_oil_price** (31.2%) \u2014 \ube0c\ub80c\ud2b8\uc720 \ud604\ubb3c\uac00\uaca9
2. **jkm_spot_price** (24.3%) \u2014 JKM \ud604\ubb3c\uac00\uaca9
3. **exchange_rate_krw** (11.8%) \u2014 \uc6d0/\ub2ec\ub7ec \ud658\uc728
4. **ppi_index** (8.9%) \u2014 \uc0dd\uc0b0\uc790\ubb3c\uac00\uc9c0\uc218
5. **heating_degree_days** (7.4%) \u2014 \ub09c\ubc29\ub3c4\uc77c

\uc774 5\uac1c \ubcc0\uc218\uac00 \uc804\uccb4 \uc608\uce21\ub825\uc758 83.6%\ub97c \uc124\uba85\ud569\ub2c8\ub2e4.`,
    };

    const responseText = userMessage.toLowerCase().includes('feature') || userMessage.includes('\ubcc0\uc218')
      ? responses.features
      : responses.default;

    const messageId = `msg-${Date.now()}`;
    const words = responseText.split(' ');

    // Stream response word by word
    for (let i = 0; i < words.length; i++) {
      await this.delay(30 + Math.random() * 20);

      this.emit({
        type: 'message.received',
        payload: {
          sessionId,
          messageId,
          chunk: words[i] + (i < words.length - 1 ? ' ' : ''),
          isComplete: false,
        } as MessageReceivedPayload,
      });
    }

    // Mark message as complete
    this.emit({
      type: 'message.complete',
      payload: { sessionId, messageId },
    });
  }

  /**
   * Builds accumulated subSteps for a given step and progress
   */
  private buildSubSteps(stepIndex: number, progressRatio: number, completedSteps: number[]): SubStep[] {
    const allSubSteps: SubStep[] = [];

    // Add completed sub-steps from previous steps
    for (const prevStep of completedSteps) {
      const labels = MOCK_SUB_STEPS[prevStep] || [];
      const phase = STEP_TO_PHASE[prevStep] || 'Unknown';
      for (let j = 0; j < labels.length; j++) {
        allSubSteps.push({
          id: `sub-${prevStep}-${j}`,
          label: labels[j],
          status: 'complete',
          timestamp: Date.now(),
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
      allSubSteps.push({
        id: `sub-${currentStepNum}-${j}`,
        label: currentLabels[j],
        status: isLast ? 'running' : 'complete',
        timestamp: Date.now(),
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
    const stepDurations = [2000, 3000, 8000, 5000, 2000]; // ms per step (모델링 8초로 캡처 여유)
    const completedStepNumbers: number[] = [];

    // Initial message
    const introMessageId = `msg-intro-${Date.now()}`;
    await this.streamMessage(
      sessionId,
      introMessageId,
      '\ud30c\uc77c\uc744 \ud655\uc778\ud588\uc2b5\ub2c8\ub2e4. \uc790\ub3d9 \ubd84\uc11d\uc744 \uc2dc\uc791\ud569\ub2c8\ub2e4.\n\n5\ub2e8\uacc4\ub85c \uc9c4\ud589\ub429\ub2c8\ub2e4:\n1. \ubb38\uc81c \uc815\uc758\n2. \uc120\ud589\uc5f0\uad6c\n3. \ubaa8\ub378 \ud559\uc2b5\n4. \uc778\uc0ac\uc774\ud2b8 \ub3c4\ucd9c\n5. \ub9ac\ud3ec\ud2b8 \uc0dd\uc131'
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
      const progressSteps = 10;
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
        `## \ubd84\uc11d \uc644\ub8cc

**LightGBM** \ubaa8\ub378\uc774 \uac80\uc99d \ub370\uc774\ud130\uc5d0\uc11c **R\u00B2=0.946**\uc744 \ub2ec\uc131\ud588\uc2b5\ub2c8\ub2e4.

### \ubaa8\ub378 \uc131\ub2a5
| \uc9c0\ud45c | \uac12 |
|---|---:|
| RMSE | 1.23 \uc6d0/MJ |
| MAE | 0.87 \uc6d0/MJ |
| R\u00B2 | 0.946 |
| MAPE | 4.2% |

### SHAP \ubcc0\uc218 \uae30\uc5ec\ub3c4
| \uc21c\uc704 | \ubcc0\uc218 | \uae30\uc5ec\ub3c4 |
|---:|---|---:|
| 1 | brent_oil_price | 31.2% |
| 2 | jkm_spot_price | 24.3% |
| 3 | exchange_rate_krw | 11.8% |
| 4 | ppi_index | 8.9% |
| 5 | heating_degree_days | 7.4% |

### \uc8fc\uc694 \uc778\uc0ac\uc774\ud2b8
- **\ube0c\ub80c\ud2b8\uc720 + JKM = 55.5%**: \uad6d\uc81c \uc5d0\ub108\uc9c0 \uac00\uaca9\uc774 \ub3c4\uc785 \uc6d0\uac00\uc758 \uc808\ubc18 \uc774\uc0c1\uc744 \uc124\uba85
- **\ud658\uc728 \ube44\uc120\ud615 \ud6a8\uacfc**: 1,300\uc6d0 \uc774\uc0c1 \uad6c\uac04\uc5d0\uc11c SHAP \uae30\uc5ec\ub3c4 \uae09\uc99d
- **\uacc4\uc808\uc131 7.4%**: \ub09c\ubc29\ub3c4\uc77c\uc744 \ud1b5\ud574 \ub3d9\uc808\uae30 \uc218\uc694 \uc99d\uac00\uac00 \uc6d0\uac00\uc5d0 \ubc18\uc601
- **\uc7ac\uace0 \uc5ed\uad00\uacc4**: \uc7ac\uace0 5\ubc31\ub9cc\ud1a4 \uc774\ud558 \uc2dc \uac00\uaca9 \uc555\ub825 \ube44\ub840\uc801 \uc99d\uac00`
      );

      // Emit report.ready event
      await this.delay(500);
      this.emit({
        type: 'report.ready',
        payload: {
          sessionId,
          title: '\uad6d\ub0b4 \uac00\uc2a4 \ub3c4\uc785 \uc6d0\uac00 \uc608\uce21 \ubd84\uc11d \ub9ac\ud3ec\ud2b8',
          preview: `# \uad6d\ub0b4 \uac00\uc2a4 \ub3c4\uc785 \uc6d0\uac00 \uc608\uce21 \ubd84\uc11d \ub9ac\ud3ec\ud2b8\n\n## \uc694\uc57d\nLightGBM \ubaa8\ub378\uc774 R\u00B2=0.946\uc758 \ub192\uc740 \uc608\uce21 \uc815\ud655\ub3c4\ub97c \ub2ec\uc131\ud588\uc2b5\ub2c8\ub2e4.\n\n## \uc8fc\uc694 \ubc1c\uacac\n- \ube0c\ub80c\ud2b8\uc720(31.2%)\uc640 JKM(24.3%)\uc774 \uc804\uccb4 \uc608\uce21\ub825\uc758 55% \uc810\uc720\n- \ud658\uc728 1,300\uc6d0 \ub3cc\ud30c \uc2dc \uc6d0\uac00 \ubbfc\uac10\ub3c4 \uae09\uc99d\n- \ub3d9\uc808\uae30 \ub09c\ubc29 \uc218\uc694\uac00 \uc6d0\uac00\uc5d0 7.4% \uae30\uc5ec\n\n## \ubaa8\ub378 \uc131\ub2a5\n- RMSE: 1.23 \uc6d0/MJ\n- MAE: 0.87 \uc6d0/MJ\n- R\u00B2: 0.946`,
        },
      });
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

  private async streamMessage(sessionId: string, messageId: string, text: string): Promise<void> {
    const words = text.split(' ');

    for (let i = 0; i < words.length; i++) {
      if (!this.isRunning) break;
      await this.delay(25 + Math.random() * 15);

      this.emit({
        type: 'message.received',
        payload: {
          sessionId,
          messageId,
          chunk: words[i] + (i < words.length - 1 ? ' ' : ''),
          isComplete: false,
        } as MessageReceivedPayload,
      });
    }

    this.emit({
      type: 'message.complete',
      payload: { sessionId, messageId },
    });
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

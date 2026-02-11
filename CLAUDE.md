# DA System - AI 데이터 분석 자동화 에이전트

**Version:** 1.0.0-rc15 | **Updated:** 2026-02-11 | **Status:** 99% Production Ready

비전문가도 고품질 데이터 분석을 수행할 수 있도록 돕는 AI 에이전트 기반 자동화 시스템.
데이터 업로드 → 문제 정의 → 선행연구 → 모델링 → 인사이트 → 리포트까지 15~30분 내 자동 완료.

---

## 빠른 시작

```bash
# 1. Redis (필수 - 세션 관리)
docker run -d -p 6379:6379 --name redis-da redis:7-alpine

# 2. 백엔드
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs

# 3. 프론트엔드
cd frontend/da-insights-hub
npm run dev
# http://localhost:8080

# 4. (선택) Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# 5. (선택) MLflow UI
mlflow ui --backend-store-uri file:./mlruns
# http://localhost:5000
```

**Feature Flag:** `.env.development`에서 `VITE_USE_MOCK=true`(Mock) / `false`(실제 API)

---

## 기술 스택

```
Frontend:  React + Vite + Tailwind + shadcn/ui + React Query
Backend:   FastAPI + Redis + Celery
ML:        FLAML + XGBoost + LightGBM + CatBoost + SHAP
Tracking:  MLflow
LLM:       Gemini Flash 3.0 (기본), OpenAI, Anthropic (fallback)
External:  HuggingFace Papers, Kaggle, Gemini DeepResearch
```

---

## 아키텍처

```
React (8080) → Vite Proxy → FastAPI (8000)
             → WebSocket   → /api/v1/chat/ws/{sessionId}

┌─────────────── FastAPI Backend ───────────────┐
│  Orchestrator Agent (워크플로우 조율)          │
│  ├── ProblemDefinition  (LLM 대화형 정의)     │
│  ├── ResearchCoordinator (병렬)               │
│  │   ├── HuggingFace Papers                   │
│  │   ├── Kaggle Solutions                     │
│  │   └── DeepResearch (Gemini)                │
│  ├── ModelingAgent      (FLAML AutoML)        │
│  ├── InsightAgent       (SHAP + LLM)         │
│  └── ReportingAgent     (MD + HTML)           │
└──────────┬────────────┬───────────────────────┘
     Redis (Session)  MLflow (Tracking)  File Storage
```

**워크플로우 상태 머신:**
`NOT_STARTED → AWAITING_INPUT → AWAITING_CONFIRMATION → RUNNING → COMPLETED/FAILED`

**분석 플로우 (rc8+):**
`파일 업로드 → 데이터 프로파일 + Q&A → 사용자 응답 → 분석 계획 확인 → Background Task 분석 시작`

---

## API 엔드포인트

| 영역 | 메서드 | 경로 | 설명 |
|------|--------|------|------|
| **Chat** | POST | `/api/v1/chat/sessions` | 세션 생성 |
| | POST | `/api/v1/chat/sessions/{id}/messages` | 메시지 전송 |
| | GET | `/api/v1/chat/sessions/{id}` | 세션 조회 |
| | DELETE | `/api/v1/chat/sessions/{id}` | 세션 삭제 |
| | GET | `/api/v1/chat/sessions` | 세션 목록 |
| | WS | `/api/v1/chat/ws/{id}` | WebSocket 실시간 |
| **Data** | POST | `/api/v1/data/upload` | 파일 업로드 |
| | GET | `/api/v1/data/{id}/profile` | 프로파일 |
| | GET | `/api/v1/data/{id}/preview` | 미리보기 |
| | GET | `/api/v1/data` | 파일 목록 |
| | DELETE | `/api/v1/data/{id}` | 삭제 |
| **Models** | GET | `/api/v1/models` | 모델 목록 |
| | GET | `/api/v1/models/{id}` | 모델 상세 |
| | POST | `/api/v1/models/{id}/predict` | 예측 |
| | GET | `/api/v1/models/{id}/explain` | SHAP 설명 |
| **Analysis** | POST | `/api/v1/analysis/train` | 학습 시작 |
| | GET | `/api/v1/analysis/tasks/{id}` | 작업 상태 |
| | GET | `/api/v1/analysis/tasks/{id}/logs` | SSE 로그 |
| **Reports** | GET | `/api/v1/reports/{id}` | Markdown |
| | GET | `/api/v1/reports/{id}/html` | HTML 대시보드 |
| | GET | `/api/v1/reports/{id}/download` | 다운로드 |

---

## 디렉토리 구조

```
D:\dasystem/
├── app/
│   ├── agents/                    # 에이전트 시스템
│   │   ├── base.py               # BaseAgent (async emit_event)
│   │   ├── orchestrator.py       # Orchestrator (상태 머신)
│   │   ├── contracts.py          # 에이전트 간 데이터 정규화
│   │   ├── problem_definition.py
│   │   ├── modeling.py
│   │   ├── insight.py
│   │   ├── reporting.py
│   │   └── research/             # 선행연구 에이전트 (3종)
│   ├── api/routes/               # FastAPI 라우트 (chat, data, models, analysis, reports)
│   ├── core/
│   │   ├── data_pipeline/        # 로더, 검증, 타입감지, 프로파일링
│   │   ├── automl/               # FLAML 래퍼
│   │   └── evaluation/           # SHAP 분석
│   ├── services/
│   │   ├── llm/                  # LLM 라우터 (Gemini/OpenAI/Anthropic)
│   │   └── external/             # HuggingFace, Kaggle, DeepResearch
│   ├── storage/                  # Redis 세션, 파일 매니저, MLflow
│   └── tasks/                    # Celery 태스크
├── frontend/da-insights-hub/
│   ├── src/
│   │   ├── components/chat/      # ChatMessages, ChatInput, AnalysisProgress (인라인)
│   │   ├── pages/                # Data, Models, Reports, Chat
│   │   ├── services/             # 5개 API 서비스 + adapters
│   │   ├── hooks/                # React Query 훅 5개 + use-theme
│   │   ├── lib/                  # config, websocket-client, mock-websocket
│   │   ├── contexts/             # AppContext (client state only)
│   │   └── types/                # TypeScript 타입 정의
│   └── vite.config.ts            # Proxy /api/v1 → localhost:8000
├── data/uploads/                 # 사용자 업로드 파일
├── outputs/                      # reports, models, research, logs
└── mlruns/                       # MLflow 추적 데이터
```

---

## 개발 시 주의사항

### 에이전트 패턴
- **emit_event는 async**: `await self.emit_event(...)` 필수 (모든 에이전트)
- **생성자**: `__init__(self, context, llm_provider=None)` (keyword arg)
- **ResearchCoordinator**: `__init__(self, context, **kwargs)` → `llm_provider=` 로 전달
- **데이터 전달**: context.data에 file_path 저장, DataFrame은 런타임 로드

### FLAML 이슈
- Object 컬럼 → `fillna('__MISSING__')` 후 LabelEncoding (`_preprocess_features()`)
- Binary target인데 multiclass 오류 → `binary_classification` 강제
- 예측 시 FLAML이 전처리한 X_test 사용
- Feature importance → MLflow artifact (`analysis/feature_importance.json`)

### Redis
- DataFrame 저장 불가 → file_path만 저장
- Atomic 업데이트: WATCH/MULTI/EXEC 패턴
- Redis 미실행 시 모든 API 500 에러

### 프론트엔드 아키텍처
- **서버 상태**: React Query (files, models, reports)
- **클라이언트 상태**: AppContext (messages, wsStatus, activeSessionId)
- **Adapters**: `src/services/adapters.ts` (snake_case → camelCase 변환)
- **WebSocket**: `realWebSocket` / `mockWebSocket` (config.useMock 토글)
- **분석 진행률**: 채팅 메시지 내 인라인 프로그레스 (`AnalysisProgressInline`)
  - `status.update` → `addMessage/updateMessage` (id=`analysis-progress`)
  - 5단계: ProblemDefinition → Research → Modeling → Insight → Reporting
- **분석 Q&A**: `analysis.questions` → `analysis.answers` → `analysis.plan` → `analysis.confirm`
- **Background Task**: 분석은 `asyncio.create_task()`로 실행 → 페이지 이동해도 분석 계속

### LLM 설정
- 기본 채팅: `CHAT_LLM_PROVIDER=gemini` (app/config.py, 환경변수 오버라이드 가능)
- Gemini 3 권장 temperature=1.0
- stream_generate에 fallback 로직 내장

### 보안
- API Key: `X-API-Key` 헤더, 미설정 시 인증 비활성화 (개발 모드)
- Path Traversal: UUID 검증 + safe path resolution
- CORS: `localhost:8080` 허용

---

## 현재 상태

### 완료된 항목
| 영역 | 상태 |
|------|------|
| Phase 1: 데이터 파이프라인 | 100% |
| Phase 2: AutoML (FLAML + MLflow + Celery) | 100% |
| Phase 3: 에이전트 시스템 (LLM + Orchestrator + Chat) | 100% |
| Phase 4: 외부 API (HuggingFace + Kaggle + DeepResearch) | 100% |
| Phase 5: SHAP + Insight + Reporting | 100% |
| 보안/안정성 패치 | 100% |
| Orchestrator 통합 (전체 워크플로우) | 100% |
| Frontend-Backend 연결 (React Query + WebSocket) | 100% |
| 한글화 + 다크모드 + 브랜딩 | 100% |
| 인라인 분석 진행률 (채팅 메시지 통합) | 100% |
| XAI 서브스텝 로그 + 프로그레스바 버그 수정 | 100% |
| Phase-based substep toggles + Shimmer UI | 100% |
| Feature importance artifacts + Report cards in chat | 100% |
| Interactive Pre-Analysis Q&A | 100% |
| Background Task Architecture + 프로덕션 품질 개선 | 100% |
| Modern AI UX (마크다운/타임스탬프/액션/세션히스토리/DnD/textarea) | 100% |
| P5 캡처용 에너지 가격 Mock 시나리오 + 커스텀 아이콘 | 100% |
| Mock 데모 시나리오 고급화 (Multi-turn 대화, 도메인 전문 응답) | 100% |
| RC13 기능적 품질 대폭 개선 (DataIntelligence, 스마트 전처리, 적응형 Q&A, 리서치 연계) | 100% |
| RC14 McKinsey-Quality HTML 리포트 템플릿 (Pretendard 타이포, KPI 카드, dotted 테이블, 인쇄용 CSS) | 100% |
| RC15 프로그레스 바 부드러운 전환 + 서브스텝 깜박임 제거 + 사이드바 정렬/원형 아이콘 | 100% |

### 미완료 / 다음 단계
| 항목 | 우선순위 |
|------|----------|
| `VITE_USE_MOCK=false` 실제 E2E 테스트 | HIGH |
| Rate Limiting (Redis 기반) | MEDIUM |
| 테스트 커버리지 80%+ (현재 ~72%) | MEDIUM |
| WebSocket 토큰별 스트리밍 고도화 | LOW |

### 알려진 이슈
- Redis 미실행 시 채팅/세션 API 전부 500 에러 → `docker start redis-da` 또는 `redis-server`
- Windows 콘솔 한글 인코딩 깨짐 (기능 무관)

---

## 버전 이력

| 버전 | 날짜 | 요약 |
|------|------|------|
| 1.0.0-rc15 | 2026-02-11 | UX 폴리시: 프로그레스 바 500ms ease-out 전환(25단계 세분화), 서브스텝 깜박임 제거(seenIds ref), 사이드바 접힘 아이콘 가운데 정렬(중첩 패딩 제거), 서비스 아이콘 원형 래퍼, 스크롤 영역 확대 |
| 1.0.0-rc14 | 2026-02-11 | McKinsey-Quality HTML 리포트 템플릿: Pretendard 타이포그래피, KPI 카드 그리드, dotted-line 테이블, 섹션 번호, SHAP figure 프레임, 우선순위별 추천 카드, A4 인쇄용 CSS, HTML 보기 버튼 추가 |
| 1.0.0-rc13 | 2026-02-10 | 기능적 품질 대폭 개선: DataIntelligence 레이어, 7단계 스마트 전처리, 적응형 Q&A/메트릭, LLM 리서치 쿼리, 리서치→모델링 연계, Cohen's d 에러 분석, SHAP HTML 임베드, 리포트 품질 강화 |
| 1.0.0-rc12 | 2026-02-08 | Mock 데모 시나리오 고급화: Multi-turn 대화 상태 머신, 도메인 전문 응답, 리치 데이터 분석, 시스템 안내, 웰컴 카드 리뉴얼 |
| 1.0.0-rc11 | 2026-02-08 | P5 캡처용 에너지 가격 Mock 시나리오 (더미 CSV, mock-data/websocket 전면 교체, 커스텀 Brain 아이콘, CAPTURE_MODE, Mock 세션 버그 수정) |
| 1.0.0-rc10 | 2026-02-06 | Modern AI UX: Rich Markdown, 메시지 액션/타임스탬프, 세션 히스토리, DnD, auto-resize textarea, 404 한글화, 비기능 버튼 정리 |
| 1.0.0-rc9 | 2026-02-06 | Background Task 분석, 리포트 저장/표시 수정, 중복 프로그레스 제거, NaN 전처리 개선, debug.log 제거 |
| 1.0.0-rc8 | 2026-02-06 | Interactive Pre-Analysis Q&A (파일→질문→계획→확인→분석) |
| 1.0.0-rc7 | 2026-02-06 | Phase-based substep toggles, Shimmer UI, Feature importance artifacts, Report cards |
| 1.0.0-rc6 | 2026-02-05 | 프로그레스바 중복 버그 수정(useRef), XAI 서브스텝 로그, 실제 에이전트 이벤트 매핑 |
| 1.0.0-rc5 | 2026-02-05 | 인라인 진행률 (채팅 메시지 통합), emit_event async 전환, 재연결 플래시 수정 |
| 1.0.0-rc4 | 2026-02-05 | 한글화, 다크모드, 브랜딩, API Key 개발모드 |
| 1.0.0-rc3 | 2026-02-05 | Frontend-Backend 연결, React Query, WebSocket |
| 1.0.0-rc2 | 2026-02-05 | 에이전트 계약 정규화 |
| 1.0.0-rc1 | 2026-02-04 | Orchestrator 통합 완료, ModelingAgent 추가 |
| 1.0.0-beta | 2026-02-04 | 보안/안정성 패치 |
| 0.1~0.4 | 2026-02-04 | Phase 1~4 순차 구현 |

---

## 라이선스

MIT License

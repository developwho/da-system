"""
Chat API 라우트
대화형 인터페이스 - 사용자와 에이전트 간 실시간 대화
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from typing import List, Optional
import asyncio
import json
import os
import time
from pydantic import BaseModel, UUID4
import uuid
from datetime import datetime
from uuid import UUID
from starlette.concurrency import run_in_threadpool

from app.utils.logger import get_logger
from app.storage.session_store import SessionStore, get_session_store
from app.agents import (
    AgentContext,
    OrchestratorAgent
)
from app.services.llm import llm_router, LLMMessage, LLMProvider
from app.api.deps import require_api_key, require_ws_api_key
from app.config import settings

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = get_logger(__name__)

# Session별 실행 중인 분석 태스크 추적
_analysis_tasks: dict[str, asyncio.Task] = {}

# 세션 스토어는 요청 시점에 초기화 (Redis 의존성 지연)
session_store: SessionStore | None = None

# DA System 시스템 프롬프트
DA_SYSTEM_PROMPT = (
    "당신은 DA System의 AI 데이터 분석 어시스턴트입니다. "
    "사용자가 데이터를 업로드하면 자동으로 분석 목표를 파악하고, "
    "모델을 학습·최적화하여, "
    "SHAP 기반 인사이트와 비즈니스 리포트를 생성합니다.\n\n"
    "주요 역할:\n"
    "- 데이터 분석 목표 및 타겟 변수 파악을 위한 대화\n"
    "- 분석 결과 설명 및 비즈니스 인사이트 제공\n"
    "- 모델 성능 해석 및 개선 방향 제안\n\n"
    "항상 한국어로 친절하고 전문적으로 답변하세요. "
    "데이터가 아직 업로드되지 않았다면 데이터 업로드를 안내하세요."
)


def _get_chat_provider() -> LLMProvider:
    """설정에서 채팅용 LLM provider를 가져옴"""
    provider_map = {
        "gemini": LLMProvider.GEMINI,
        "openai": LLMProvider.OPENAI,
        "anthropic": LLMProvider.ANTHROPIC,
    }
    return provider_map.get(settings.CHAT_LLM_PROVIDER, LLMProvider.GEMINI)


# Pydantic 스키마
class CreateSessionRequest(BaseModel):
    """세션 생성 요청"""
    user_id: Optional[str] = None
    file_id: Optional[str] = None  # 분석할 데이터 파일 ID


class CreateSessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    created_at: str
    message: str


class SendMessageRequest(BaseModel):
    """메시지 전송 요청"""
    message: str
    role: str = "user"


class Message(BaseModel):
    """메시지"""
    id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str


class SendMessageResponse(BaseModel):
    """메시지 전송 응답"""
    message: Message
    session_id: str


class SessionDetail(BaseModel):
    """세션 상세 정보"""
    session_id: str
    user_id: Optional[str]
    file_id: Optional[str]
    messages: List[Message]
    created_at: str
    updated_at: str
    status: str  # "active", "completed", "failed"


def _normalize_session(session_data: dict) -> dict:
    """SessionStore 스키마와 Chat 스키마 간 호환성 보장.

    SessionStore는 'history'를 사용하지만 chat.py는 'messages'를 사용.
    이 함수가 두 스키마를 브리지한다.
    읽을 때: history → messages, 쓸 때: messages → history (sync)
    """
    if "messages" not in session_data:
        session_data["messages"] = session_data.get("history", [])
    # history도 동기화 (update_session 시 SessionStore가 history를 사용할 수 있으므로)
    session_data["history"] = session_data["messages"]
    return session_data


def _build_message(role: str, content: str, message_id: Optional[str] = None) -> dict:
    """메시지 생성 헬퍼"""
    return {
        "id": message_id or str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }


def _messages_to_llm(
    messages: List[dict],
    max_history: int = 20,
    system_prompt: Optional[str] = None,
) -> List[LLMMessage]:
    """세션 메시지를 LLM 입력 형식으로 변환"""
    llm_messages: List[LLMMessage] = []
    if system_prompt:
        llm_messages.append(LLMMessage(role="system", content=system_prompt))
    for msg in messages[-max_history:]:
        role = msg.get("role", "user")
        if role not in {"user", "assistant", "system"}:
            role = "user"
        llm_messages.append(LLMMessage(role=role, content=msg.get("content", "")))
    return llm_messages


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    새 채팅 세션 생성

    - 사용자와 에이전트 간 대화 세션 시작
    - 세션 ID 반환
    """
    try:
        # 세션 ID 생성
        session_id = str(uuid.uuid4())

        # Context 초기화
        context = {}

        # file_id가 있으면 file_path를 context에 추가
        if request.file_id:
            try:
                from app.storage.file_manager import FileManager
                file_path = FileManager.get_file_path(request.file_id)
                context["file_id"] = request.file_id
                context["file_path"] = file_path
                logger.info("file_attached_to_session", session_id=session_id, file_id=request.file_id)
            except FileNotFoundError:
                logger.warning("file_not_found", file_id=request.file_id)
                raise HTTPException(status_code=404, detail=f"File not found: {request.file_id}")

        # Redis에 세션 생성 (SessionStore의 자체 스키마 사용)
        global session_store
        session_store = session_store or get_session_store()
        session_data = await run_in_threadpool(
            session_store.create_session, session_id, context
        )

        # chat 전용 필드 추가 (messages, user_id, file_id, status)
        chat_fields = {
            "user_id": request.user_id,
            "file_id": request.file_id,
            "messages": [],
            "status": "active",
        }
        await run_in_threadpool(
            session_store.update_session, session_id, chat_fields
        )

        logger.info("session_created", session_id=session_id, user_id=request.user_id)

        return CreateSessionResponse(
            session_id=session_id,
            created_at=session_data["created_at"],
            message="Session created successfully"
        )

    except Exception as e:
        logger.error("session_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: UUID4, request: SendMessageRequest):
    """
    메시지 전송

    - 사용자 메시지를 에이전트에게 전달
    - 에이전트 응답 반환
    """
    try:
        # 세션 조회
        session_id_str = str(session_id)
        global session_store
        session_store = session_store or get_session_store()
        session_data = await run_in_threadpool(session_store.get_session, session_id_str)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        _normalize_session(session_data)

        # 사용자 메시지 추가
        user_message = _build_message(request.role, request.message)
        session_data["messages"].append(user_message)

        # TODO: 에이전트 처리 (Phase 3B에서 완전 구현)
        # 현재는 간단한 응답만 반환
        assistant_message = _build_message(
            "assistant",
            f"메시지를 받았습니다: '{request.message}'. 에이전트 처리가 곧 구현됩니다."
        )
        session_data["messages"].append(assistant_message)

        # 세션 업데이트
        session_data["updated_at"] = datetime.now().isoformat()
        await run_in_threadpool(session_store.update_session, session_id_str, session_data)

        logger.info("message_sent", session_id=session_id, message_length=len(request.message))

        return SendMessageResponse(
            message=Message(**assistant_message),
            session_id=session_id_str
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("message_sending_failed", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: UUID4):
    """
    세션 조회

    - 세션 정보 및 대화 기록 조회
    """
    try:
        global session_store
        session_store = session_store or get_session_store()
        session_data = await run_in_threadpool(session_store.get_session, str(session_id))
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        _normalize_session(session_data)

        # 메시지 변환 (id 누락 시 보정)
        normalized_messages = []
        updated = False
        for msg in session_data.get("messages", []):
            if "id" not in msg:
                msg = dict(msg)
                msg["id"] = str(uuid.uuid4())
                updated = True
            normalized_messages.append(msg)

        if updated:
            session_data["messages"] = normalized_messages
            session_data["updated_at"] = datetime.now().isoformat()
            await run_in_threadpool(session_store.update_session, str(session_id), session_data)

        messages = [Message(**msg) for msg in normalized_messages]

        return SessionDetail(
            session_id=session_data["session_id"],
            user_id=session_data.get("user_id"),
            file_id=session_data.get("file_id"),
            messages=messages,
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            status=session_data.get("status", "active")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("session_retrieval_failed", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID4):
    """
    세션 삭제

    - 세션 및 관련 데이터 삭제
    """
    try:
        global session_store
        session_store = session_store or get_session_store()
        await run_in_threadpool(session_store.delete_session, str(session_id))
        logger.info("session_deleted", session_id=session_id)
        return {"message": "Session deleted successfully", "session_id": session_id}

    except Exception as e:
        logger.error("session_deletion_failed", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/sessions")
async def list_sessions(user_id: Optional[str] = None, limit: int = 50):
    """
    세션 목록 조회

    - 사용자별 세션 목록 (선택적)
    - 최근 순으로 정렬
    """
    try:
        global session_store
        session_store = session_store or get_session_store()

        session_ids = await run_in_threadpool(session_store.list_sessions, "*", max(limit, 100))

        async def fetch_session(sid: str):
            try:
                return await run_in_threadpool(session_store.get_session, sid)
            except Exception:
                return None

        sessions_raw = await asyncio.gather(*(fetch_session(sid) for sid in session_ids))
        sessions_filtered = []
        for session in sessions_raw:
            if not session:
                continue
            if user_id and session.get("user_id") != user_id:
                continue
            sessions_filtered.append(session)

        def _parse_ts(value: str) -> datetime:
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return datetime.min

        sessions_filtered.sort(
            key=lambda s: _parse_ts(s.get("updated_at", "")),
            reverse=True
        )
        sessions_filtered = sessions_filtered[:limit]

        sessions_summary = []
        for session in sessions_filtered:
            sessions_summary.append({
                "session_id": session.get("session_id"),
                "user_id": session.get("user_id"),
                "file_id": session.get("file_id"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "status": session.get("status", "active"),
                "message_count": len(session.get("messages", [])),
            })

        logger.info("sessions_listed", user_id=user_id, count=len(sessions_summary))
        return {"sessions": sessions_summary, "count": len(sessions_summary)}

    except Exception as e:
        logger.error("session_listing_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


# WebSocket 연결 관리자
class ConnectionManager:
    """WebSocket 연결 관리"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """연결 추가"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("websocket_connected", session_id=session_id)

    def disconnect(self, session_id: str):
        """연결 제거"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info("websocket_disconnected", session_id=session_id)

    def is_connected(self, session_id: str) -> bool:
        """연결 상태 확인"""
        return session_id in self.active_connections

    async def send_message(self, session_id: str, message: dict):
        """메시지 전송 (연결 끊김 시 조용히 무시)"""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_json(message)
            except Exception:
                # WebSocket이 끊어진 경우 → 무시 (분석은 계속 진행)
                pass


manager = ConnectionManager()

PHASE_STATUS_MAP = {
    "problem_definition": (1, "ProblemDefinition"),
    "research": (2, "Research"),
    "modeling": (3, "Modeling"),
    "insight": (4, "Insight"),
    "reporting": (5, "Reporting"),
}

PHASE_DESCRIPTIONS = {
    "problem_definition": "데이터를 분석하고 문제를 정의하고 있습니다...",
    "research": "관련 논문과 Kaggle 솔루션을 조사하고 있습니다...",
    "modeling": "최적의 모델을 탐색하고 학습하고 있습니다...",
    "insight": "모델 결과를 분석하고 인사이트를 도출하고 있습니다...",
    "reporting": "종합 분석 리포트를 작성하고 있습니다...",
}

# 실제 에이전트가 emit하는 이벤트 → 한국어 기본 설명 매핑
# 동적 데이터는 _build_sub_step_label()에서 event data를 이용해 보강
SUB_STEP_DESCRIPTIONS: dict[str, str] = {
    # ProblemDefinition (problem_definition.py)
    "agent_question": "분석 목표 확인 중",
    # Research (research/coordinator.py, papers_agent.py, solutions_agent.py, deep_research_agent.py)
    "parallel_research_started": "병렬 선행연구 시작",
    "query_extracted": "검색 쿼리 추출 완료",
    "query_generated": "검색 쿼리 생성 완료",
    "papers_found": "관련 논문 검색 완료",
    "insights_generated": "Kaggle 인사이트 생성 완료",
    "research_started": "DeepResearch 조사 시작",
    "research_completed": "DeepResearch 조사 완료",
    # Modeling (modeling.py)
    "data_loading": "데이터 로딩 중",
    "training_started": "모델 학습 시작",
    "training_completed": "모델 학습 완료",
    # Insight (insight.py)
    "data_loaded": "분석 데이터 로딩 완료",
    "shap_analysis_started": "SHAP 분석 시작",
    "shap_analysis_completed": "SHAP 분석 완료",
}


def _build_sub_step_label(event_type: str, event_data: dict) -> str:
    """이벤트 타입과 데이터에서 동적 서브스텝 라벨 생성"""
    base = SUB_STEP_DESCRIPTIONS.get(event_type, event_type)
    details: list[str] = []

    if event_type == "training_started":
        if pt := event_data.get("problem_type"):
            details.append(pt.replace("_", " "))
        if n := event_data.get("samples"):
            details.append(f"{n}개 샘플")
        if f := event_data.get("features"):
            details.append(f"{f}개 피처")
    elif event_type == "training_completed":
        if est := event_data.get("best_estimator"):
            details.append(est)
    elif event_type == "papers_found":
        if cnt := event_data.get("count"):
            details.append(f"{cnt}건")
    elif event_type == "insights_generated":
        if comp := event_data.get("competition"):
            details.append(comp)
        if cnt := event_data.get("kernels_count"):
            details.append(f"커널 {cnt}건")
    elif event_type == "research_completed":
        if cnt := event_data.get("findings_count"):
            details.append(f"발견 {cnt}건")
    elif event_type == "data_loaded":
        if tr := event_data.get("train_samples"):
            details.append(f"학습 {tr}")
        if te := event_data.get("test_samples"):
            details.append(f"테스트 {te}")
    elif event_type == "shap_analysis_completed":
        if cnt := event_data.get("top_features_count"):
            details.append(f"상위 {cnt}개 피처")

    if details:
        return f"{base} ({', '.join(details)})"
    return base


def _sanitize_for_json(value, path=""):
    """Non-serializable 값 제거 (module-level)"""
    drop = object()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value, []
    if isinstance(value, dict):
        cleaned = {}
        removed = []
        for key, item in value.items():
            sanitized, removed_child = _sanitize_for_json(
                item,
                f"{path}.{key}" if path else str(key),
            )
            if sanitized is not drop:
                cleaned[key] = sanitized
            else:
                removed.append(f"{path}.{key}" if path else str(key))
            removed.extend(removed_child)
        return cleaned, removed
    if isinstance(value, list):
        cleaned_list = []
        removed = []
        for idx, item in enumerate(value):
            sanitized, removed_child = _sanitize_for_json(
                item,
                f"{path}[{idx}]",
            )
            if sanitized is not drop:
                cleaned_list.append(sanitized)
            else:
                removed.append(f"{path}[{idx}]")
            removed.extend(removed_child)
        return cleaned_list, removed
    return drop, [path]


def _to_native_types(obj):
    """numpy/pandas 타입을 native Python 타입으로 재귀 변환 (JSON 직렬화 보장)"""
    import numpy as np

    if isinstance(obj, dict):
        return {str(k): _to_native_types(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native_types(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.str_,)):
        return str(obj)
    return obj


def _get_metric_options(problem_type: str) -> list:
    """문제 유형별 평가 지표 옵션 반환"""
    if problem_type in ("binary_classification",):
        return [
            {"value": "roc_auc", "label": "ROC-AUC", "recommended": True, "reason": "불균형 이진 분류에 최적"},
            {"value": "f1", "label": "F1 Score", "reason": "정밀도/재현율 조화 평균"},
            {"value": "accuracy", "label": "Accuracy", "reason": "단순 정확도"},
        ]
    elif problem_type in ("multiclass_classification",):
        return [
            {"value": "f1_macro", "label": "F1 Macro", "recommended": True, "reason": "클래스별 균형 평가"},
            {"value": "accuracy", "label": "Accuracy", "reason": "단순 정확도"},
            {"value": "log_loss", "label": "Log Loss", "reason": "확률 기반 손실"},
        ]
    elif problem_type in ("regression",):
        return [
            {"value": "rmse", "label": "RMSE", "recommended": True, "reason": "평균 제곱근 오차"},
            {"value": "mae", "label": "MAE", "reason": "평균 절대 오차"},
            {"value": "r2", "label": "R²", "reason": "결정계수"},
        ]
    else:
        return [
            {"value": "accuracy", "label": "Accuracy", "recommended": True},
        ]


async def _build_analysis_questions(session_context: dict) -> dict:
    """DataProfiler + TypeDetector 실행 → 프로필 요약 + 질문 구성"""
    file_path = session_context.get("file_path")
    if not file_path:
        raise ValueError("No file_path in session context")

    from app.core.data_pipeline.loader import DataLoader
    from app.core.data_pipeline.profiler import DataProfiler
    from app.core.data_pipeline.type_detector import TypeDetector

    df, _ = await run_in_threadpool(DataLoader.load_file, file_path)

    profiler = DataProfiler()
    profile = await run_in_threadpool(profiler.profile, df)

    detector = TypeDetector()
    detection = await run_in_threadpool(detector.detect, df)

    # Build profile summary
    overview = profile.get("overview", profile.get("basic_info", {}))
    variables = profile.get("variables", profile.get("column_types", {}))

    def is_numeric(info):
        vt = info.get("variable_type") or info.get("type")
        if vt == "numeric":
            return True
        dtype_name = str(info.get("type", ""))
        return dtype_name.startswith(("int", "float", "uint"))

    def is_categorical(info):
        vt = info.get("variable_type") or info.get("type")
        return vt in ("categorical", "object") or str(info.get("type", "")) in ("object", "category", "bool")

    numeric_cols = [c for c, info in variables.items() if is_numeric(info)]
    categorical_cols = [c for c, info in variables.items() if is_categorical(info)]

    rows = overview.get("n_observations", overview.get("rows", 0))
    cols = overview.get("n_variables", overview.get("columns", 0))
    memory_bytes = overview.get("memory_size", overview.get("memory_usage", 0))
    if isinstance(memory_bytes, str):
        memory_bytes = 0
    memory_mb = memory_bytes / (1024 * 1024) if memory_bytes > 1024 else memory_bytes

    # Missing cells
    missing_info = profile.get("missing", {})
    total_cells = rows * cols if rows and cols else 1
    missing_cells = missing_info.get("total_missing", 0) if isinstance(missing_info, dict) else 0
    if missing_cells == 0:
        # Fallback: sum from variables
        for info in variables.values():
            missing_cells += info.get("missing", info.get("n_missing", 0))
    missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0

    duplicate_rows = overview.get("n_duplicates", overview.get("duplicate_rows", 0))

    profile_summary = {
        "rows": rows,
        "columns": cols,
        "numericColumns": numeric_cols[:20],
        "categoricalColumns": categorical_cols[:20],
        "missingCellsPct": round(missing_pct, 1),
        "duplicateRows": duplicate_rows,
        "memoryMB": round(memory_mb, 1),
    }

    # Build target options from columns
    recommended_target = detection.get("recommended_target")
    problem_type = detection.get("problem_type") or detection.get("task_type") or "unknown"

    all_columns = list(df.columns)
    target_options = []
    for col in all_columns[:30]:
        opt = {"value": col, "label": col}
        if col == recommended_target:
            opt["recommended"] = True
            unique_count = df[col].nunique()
            opt["reason"] = f"고유값 {unique_count}개, 분류 대상으로 적합" if unique_count <= 20 else f"고유값 {unique_count}개"
        target_options.append(opt)

    # Problem type options
    problem_type_options = [
        {"value": "binary_classification", "label": "이진 분류"},
        {"value": "multiclass_classification", "label": "다중 분류"},
        {"value": "regression", "label": "회귀"},
    ]
    for opt in problem_type_options:
        if opt["value"] == problem_type:
            opt["recommended"] = True
            confidence = detection.get("confidence", 0)
            try:
                opt["reason"] = f"자동 감지 신뢰도 {float(confidence):.0%}"
            except (TypeError, ValueError):
                pass

    metric_options = _get_metric_options(problem_type)

    questions = [
        {
            "id": "target",
            "type": "select",
            "label": "타겟 변수 (예측할 컬럼)",
            "description": "모델이 예측할 대상 컬럼을 선택하세요.",
            "required": True,
            "defaultValue": recommended_target or "",
            "options": target_options,
        },
        {
            "id": "problem_type",
            "type": "radio",
            "label": "문제 유형",
            "description": "데이터 특성을 분석한 결과를 바탕으로 추천합니다.",
            "required": True,
            "defaultValue": problem_type,
            "options": problem_type_options,
        },
        {
            "id": "metric",
            "type": "radio",
            "label": "평가 지표",
            "description": "모델 성능을 측정할 지표를 선택하세요.",
            "required": True,
            "defaultValue": metric_options[0]["value"] if metric_options else "accuracy",
            "options": metric_options,
        },
        {
            "id": "goal",
            "type": "text",
            "label": "분석 목표 (선택사항)",
            "description": "분석의 비즈니스 목표를 간단히 설명해주세요.",
            "placeholder": "예: 고위험 고객 식별, 매출 예측 등",
            "required": False,
        },
    ]

    return _to_native_types({
        "profile": profile_summary,
        "questions": questions,
        "_detection": detection,  # internal: keep for plan building
    })


def _build_analysis_plan(answers: dict, session_context: dict) -> dict:
    """사용자 응답 → 분석 계획 요약"""
    problem_type = answers.get("problem_type", "binary_classification")
    target = answers.get("target", "target")
    metric = answers.get("metric", "accuracy")
    goal = answers.get("goal", "데이터 분석 및 예측 모델 구축")
    if not goal.strip():
        goal = "데이터 분석 및 예측 모델 구축"

    type_labels = {
        "binary_classification": "이진 분류",
        "multiclass_classification": "다중 분류",
        "regression": "회귀",
    }

    return {
        "analysisGoal": goal,
        "targetColumn": target,
        "problemType": problem_type,
        "evaluationMetric": metric,
        "constraints": [],
        "estimatedDuration": "15~30분",
        "steps": [
            {"name": "문제 정의", "description": "분석 목표 및 타겟 확인"},
            {"name": "선행연구", "description": "관련 논문/Kaggle 솔루션 조사"},
            {"name": "모델 학습", "description": "AutoML(FLAML)로 최적 모델 탐색"},
            {"name": "인사이트", "description": "SHAP 기반 모델 해석"},
            {"name": "리포트", "description": "종합 분석 보고서 생성"},
        ],
    }


def _create_event_handler(session_id: str, accumulated_sub_steps: list, current_phase: dict, sub_step_counter_ref: list):
    """이벤트 핸들러 팩토리 — Orchestrator 이벤트를 WebSocket status.update로 변환"""

    async def _send_status(payload: dict):
        payload["subSteps"] = list(accumulated_sub_steps)
        await manager.send_message(session_id, {
            "type": "status.update",
            "payload": payload,
        })

    def handler(event: dict):
        event_type = event.get("type", "")
        event_data = event.get("data", {})

        if event_type == "phase_change":
            phase = event_data.get("phase")
            if phase in PHASE_STATUS_MAP:
                for s in accumulated_sub_steps:
                    if s["status"] == "running":
                        s["status"] = "complete"
                step, step_name = PHASE_STATUS_MAP[phase]
                current_phase["step"] = step
                current_phase["step_name"] = step_name
                current_phase["phase"] = phase
                return _send_status({
                    "sessionId": session_id,
                    "step": step,
                    "totalSteps": 5,
                    "stepName": step_name,
                    "status": "running",
                    "progress": 0,
                    "description": PHASE_DESCRIPTIONS.get(phase, ""),
                })
        elif event_type in SUB_STEP_DESCRIPTIONS:
            for s in accumulated_sub_steps:
                if s["status"] == "running":
                    s["status"] = "complete"
            label = _build_sub_step_label(event_type, event_data)
            sub_step_counter_ref[0] += 1
            accumulated_sub_steps.append({
                "id": f"sub-{sub_step_counter_ref[0]}",
                "label": label,
                "status": "running",
                "timestamp": int(time.time() * 1000),
            })
            if current_phase["step"] > 0:
                return _send_status({
                    "sessionId": session_id,
                    "step": current_phase["step"],
                    "totalSteps": 5,
                    "stepName": current_phase["step_name"],
                    "status": "running",
                    "progress": 0,
                    "description": PHASE_DESCRIPTIONS.get(current_phase["phase"], ""),
                })
        return None

    return handler, _send_status


async def _run_analysis_background(
    session_id: str,
    session_data: dict,
    session_context: dict,
):
    """WebSocket과 독립적으로 분석 실행. 결과는 Redis에 저장."""
    accumulated_sub_steps: list[dict] = []
    sub_step_counter_ref = [0]
    current_phase: dict = {"step": 0, "step_name": "", "phase": ""}

    event_handler, send_status = _create_event_handler(
        session_id, accumulated_sub_steps, current_phase, sub_step_counter_ref
    )

    global session_store
    session_store = session_store or get_session_store()

    try:
        agent_context = AgentContext(
            session_id=session_id,
            user_id=session_data.get("user_id"),
            data=session_context,
            history=session_data.get("messages", []),
            event_handler=event_handler,
        )
        agent = OrchestratorAgent(agent_context, llm_provider=None)
        result = await agent.execute()
        session_context.update(agent_context.data)

        confirm_msg_id = str(uuid.uuid4())

        if result.success:
            for s in accumulated_sub_steps:
                if s["status"] == "running":
                    s["status"] = "complete"
            accumulated_sub_steps.append({
                "id": "sub-final",
                "label": "전체 분석 파이프라인 완료",
                "status": "complete",
                "timestamp": int(time.time() * 1000),
            })
            session_context["analysis_state"] = "COMPLETED"
            await send_status({
                "sessionId": session_id,
                "step": 5,
                "totalSteps": 5,
                "stepName": "Reporting",
                "status": "complete",
                "progress": 100,
                "description": "분석이 완료되었습니다! 리포트 페이지에서 결과를 확인하세요.",
            })

            # report.ready event
            try:
                report_data = session_context.get("report", {})
                report_md_path = report_data.get("markdown_report") if isinstance(report_data, dict) else None
                report_preview = ""
                if report_md_path and os.path.exists(report_md_path):
                    with open(report_md_path, "r", encoding="utf-8") as rf:
                        report_preview = rf.read()[:2000]
                await manager.send_message(session_id, {
                    "type": "report.ready",
                    "payload": {
                        "sessionId": session_id,
                        "title": f"분석 리포트 - {session_id[:8]}",
                        "preview": report_preview,
                    }
                })
            except Exception as rpt_err:
                logger.warning("report_ready_event_failed", error=str(rpt_err))

            done_text = "전체 분석 워크플로우가 완료되었습니다. 리포트를 확인해주세요."
        else:
            for s in accumulated_sub_steps:
                if s["status"] == "running":
                    s["status"] = "failed"
            session_context["analysis_state"] = "FAILED"
            session_context["analysis_error"] = result.error
            await send_status({
                "sessionId": session_id,
                "step": 5,
                "totalSteps": 5,
                "stepName": "Reporting",
                "status": "failed",
                "progress": 100,
                "description": f"분석에 실패했습니다: {result.error}",
            })
            done_text = f"분석 워크플로우에 실패했습니다: {result.error}"

        # Send result message (if WebSocket connected)
        if manager.is_connected(session_id):
            for i in range(0, len(done_text), 200):
                await manager.send_message(session_id, {
                    "type": "message.received",
                    "payload": {
                        "sessionId": session_id,
                        "messageId": confirm_msg_id,
                        "chunk": done_text[i:i + 200],
                        "isComplete": False,
                    }
                })
            await manager.send_message(session_id, {
                "type": "message.complete",
                "payload": {"sessionId": session_id, "messageId": confirm_msg_id},
            })

        done_msg = _build_message("assistant", done_text, message_id=confirm_msg_id)
        session_data["messages"].append(done_msg)

    except asyncio.CancelledError:
        session_context["analysis_state"] = "CANCELLED"
        logger.warning("analysis_cancelled", session_id=session_id)
    except Exception as exc:
        session_context["analysis_state"] = "FAILED"
        session_context["analysis_error"] = str(exc)
        logger.error("analysis_background_error", error=str(exc), session_id=session_id)
    finally:
        # Persist to Redis
        try:
            sanitized_ctx, _ = _sanitize_for_json(_to_native_types(session_context))
            session_data["context"] = sanitized_ctx
            session_data["updated_at"] = datetime.now().isoformat()
            await run_in_threadpool(session_store.update_session, session_id, session_data)
        except Exception as save_err:
            logger.error("analysis_save_failed", error=str(save_err), session_id=session_id)
        _analysis_tasks.pop(session_id, None)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket 엔드포인트

    - 실시간 양방향 통신
    - 에이전트 이벤트 스트리밍
    """
    if not await require_ws_api_key(websocket):
        return

    try:
        session_id = str(UUID(session_id))
    except ValueError:
        await websocket.close(code=1008)
        return

    await manager.connect(session_id, websocket)

    try:
        # 세션 조회
        global session_store
        session_store = session_store or get_session_store()
        session_data = await run_in_threadpool(session_store.get_session, session_id)
        if not session_data:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found"
            })
            await websocket.close()
            return
        _normalize_session(session_data)

        # 환영 메시지
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connected"
        })

        # 세션 상태 복구 (재연결 시)
        session_context = session_data.get("context", {}) or {}
        analysis_state = session_context.get("analysis_state")
        if analysis_state == "COMPLETED":
            logger.info("session_state_restored", session_id=session_id, state="COMPLETED")
        elif analysis_state == "RUNNING":
            if session_id in _analysis_tasks and not _analysis_tasks[session_id].done():
                # 분석이 아직 실행 중 → 실패가 아님
                logger.info("analysis_still_running", session_id=session_id)
            else:
                # 태스크가 없거나 완료됨 → Redis 상태 불일치 → FAILED로 처리
                session_context["analysis_state"] = "FAILED"
                await websocket.send_json({
                    "type": "status.update",
                    "payload": {
                        "sessionId": session_id,
                        "step": 0,
                        "totalSteps": 5,
                        "stepName": "Analysis",
                        "status": "failed",
                        "progress": 0,
                        "description": "연결이 끊어져 분석이 중단되었습니다.",
                    }
                })
                logger.warning("session_state_reset", session_id=session_id, state="RUNNING->FAILED")
        elif analysis_state == "FAILED":
            logger.info("session_state_restored", session_id=session_id, state="FAILED")

        # 메시지 수신 대기
        while True:
            data = await websocket.receive_json()

            # 메시지 타입별 처리
            if data.get("type") == "message":
                user_message = data.get("content", "")
                message_file_id = data.get("file_id")

                # 사용자 메시지 저장
                user_message_obj = _build_message("user", user_message)
                session_data["messages"].append(user_message_obj)

                # ProblemDefinition/Orchestrator 연결 (데이터가 있을 때)
                session_context = session_data.get("context", {}) or {}
                session_context["last_user_message"] = user_message
                assistant_content = None

                assistant_message_id = str(uuid.uuid4())
                if message_file_id:
                    try:
                        from app.storage.file_manager import FileManager
                        file_path = FileManager.get_file_path(message_file_id)
                        session_context["file_id"] = message_file_id
                        session_context["file_path"] = file_path
                        session_data["file_id"] = message_file_id
                    except FileNotFoundError:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"File not found: {message_file_id}"
                        })

                if not session_context.get("file_id") and session_data.get("file_id"):
                    session_context["file_id"] = session_data.get("file_id")
                    try:
                        from app.storage.file_manager import FileManager
                        session_context["file_path"] = FileManager.get_file_path(session_context["file_id"])
                    except FileNotFoundError:
                        pass

                has_file_context = bool(session_context.get("file_id") or session_context.get("file_path"))

                # 분석 상태 확인
                analysis_state = session_context.get("analysis_state", "NOT_STARTED")

                # 분석 트리거 조건
                should_run_analysis = False
                if has_file_context:
                    # 새 파일 첨부 OR 명시적 분석 시작 요청
                    is_new_file_attached = bool(message_file_id)
                    is_explicit_request = any(
                        keyword in user_message.lower()
                        for keyword in ["분석 시작", "분석해", "analyze", "analysis"]
                    )
                    # 분석이 아직 실행되지 않았거나 실패했을 경우에만 실행
                    is_analysis_not_done = analysis_state in ["NOT_STARTED", "FAILED"]

                    should_run_analysis = (
                        is_new_file_attached or
                        (is_explicit_request and is_analysis_not_done)
                    )

                if should_run_analysis:
                    # Instead of starting analysis immediately, enter Q&A flow
                    try:
                        qa_result = await _build_analysis_questions(session_context)
                        session_context["analysis_state"] = "AWAITING_INPUT"
                        session_context["_qa_detection"] = qa_result.get("_detection", {})

                        # Send intro message
                        intro_text = "데이터를 확인했습니다. 최적의 분석을 위해 몇 가지 설정을 확인하겠습니다."
                        for i in range(0, len(intro_text), 200):
                            await websocket.send_json({
                                "type": "message.received",
                                "payload": {
                                    "sessionId": session_id,
                                    "messageId": assistant_message_id,
                                    "chunk": intro_text[i:i + 200],
                                    "isComplete": False,
                                }
                            })
                        await websocket.send_json({
                            "type": "message.complete",
                            "payload": {"sessionId": session_id, "messageId": assistant_message_id},
                        })

                        # Save assistant message
                        intro_msg = _build_message("assistant", intro_text, message_id=assistant_message_id)
                        session_data["messages"].append(intro_msg)

                        # Send analysis.questions event
                        await websocket.send_json({
                            "type": "analysis.questions",
                            "payload": {
                                "sessionId": session_id,
                                "profile": qa_result["profile"],
                                "questions": qa_result["questions"],
                            },
                        })

                        sanitized_ctx, _ = _sanitize_for_json(_to_native_types(session_context))
                        session_data["context"] = sanitized_ctx
                        session_data["updated_at"] = datetime.now().isoformat()
                        await run_in_threadpool(session_store.update_session, session_id, session_data)

                        # Skip the rest of the message handling (LLM response, etc.)
                        continue
                    except Exception as qa_err:
                        logger.error("analysis_questions_failed", error=str(qa_err), session_id=session_id)
                        # Fall through to regular analysis if Q&A fails
                        pass

                # Legacy path: direct analysis (fallback if Q&A didn't redirect via continue)
                if should_run_analysis and session_context.get("analysis_state") != "AWAITING_INPUT":
                    session_context["analysis_state"] = "RUNNING"
                    session_data["context"] = session_context
                    task = asyncio.create_task(
                        _run_analysis_background(session_id, session_data, session_context)
                    )
                    _analysis_tasks[session_id] = task
                    assistant_content = "분석을 시작합니다. 잠시만 기다려주세요."

                streamed_chunks = False

                if assistant_content is None:
                    chat_provider = _get_chat_provider()
                    llm_messages = _messages_to_llm(
                        session_data.get("messages", []),
                        system_prompt=DA_SYSTEM_PROMPT,
                    )
                    chunks: List[str] = []
                    try:
                        async for chunk in llm_router.stream_generate(
                            llm_messages,
                            provider=chat_provider,
                            use_fallback=True,
                        ):
                            if not chunk:
                                continue
                            chunks.append(chunk)
                            streamed_chunks = True
                            await websocket.send_json({
                                "type": "message.received",
                                "payload": {
                                    "sessionId": session_id,
                                    "messageId": assistant_message_id,
                                    "chunk": chunk,
                                    "isComplete": False
                                }
                            })
                        assistant_content = "".join(chunks).strip()
                    except Exception as exc:
                        logger.error("llm_stream_failed", error=str(exc), session_id=session_id)
                        assistant_content = f"응답 생성 실패: {exc}"

                if assistant_content is None:
                    assistant_content = "응답을 생성하지 못했습니다."

                assistant_message_obj = _build_message(
                    "assistant",
                    assistant_content,
                    message_id=assistant_message_id
                )

                # 청크가 없었던 경우(에이전트 결과 등)에도 프로토콜 유지
                if assistant_content and not streamed_chunks:
                    for i in range(0, len(assistant_content), 200):
                        await websocket.send_json({
                            "type": "message.received",
                            "payload": {
                                "sessionId": session_id,
                                "messageId": assistant_message_id,
                                "chunk": assistant_content[i:i + 200],
                                "isComplete": False
                            }
                        })

                await websocket.send_json({
                    "type": "message.complete",
                    "payload": {
                        "sessionId": session_id,
                        "messageId": assistant_message_obj["id"]
                    }
                })

                session_data["messages"].append(assistant_message_obj)

                sanitized_context, _ = _sanitize_for_json(_to_native_types(session_context))
                session_data["context"] = sanitized_context

                # 세션 업데이트
                session_data["updated_at"] = datetime.now().isoformat()
                await run_in_threadpool(session_store.update_session, session_id, session_data)

            elif data.get("type") == "analysis.answers":
                # User submitted Q&A answers → build plan and send
                answers = data.get("answers", {})
                session_context = session_data.get("context", {}) or {}
                session_context["user_answers"] = answers

                plan = _build_analysis_plan(answers, session_context)
                session_context["analysis_state"] = "AWAITING_CONFIRMATION"
                session_context["analysis_plan"] = plan
                session_data["context"] = session_context
                session_data["updated_at"] = datetime.now().isoformat()
                await run_in_threadpool(session_store.update_session, session_id, session_data)

                await websocket.send_json({
                    "type": "analysis.plan",
                    "payload": {
                        "sessionId": session_id,
                        "plan": plan,
                    },
                })

            elif data.get("type") == "analysis.confirm":
                # User confirmed plan → inject user_defined_problem and run as background task
                session_context = session_data.get("context", {}) or {}
                answers = session_context.get("user_answers", {})
                plan = session_context.get("analysis_plan", {})

                # Inject user_defined_problem for ProblemDefinitionAgent bypass
                session_context["user_defined_problem"] = {
                    "analysis_goal": plan.get("analysisGoal", "데이터 분석 및 예측 모델 구축"),
                    "target_column": answers.get("target", "target"),
                    "problem_type": answers.get("problem_type", "binary_classification"),
                    "evaluation_metric": answers.get("metric", "accuracy"),
                    "constraints": plan.get("constraints", []),
                }
                session_context["analysis_state"] = "RUNNING"
                session_data["context"] = session_context

                # Save initial state before launching background task
                sanitized_ctx, _ = _sanitize_for_json(_to_native_types(session_context))
                session_data["context"] = sanitized_ctx
                session_data["updated_at"] = datetime.now().isoformat()
                await run_in_threadpool(session_store.update_session, session_id, session_data)

                # Launch analysis as background task
                task = asyncio.create_task(
                    _run_analysis_background(session_id, session_data, session_context)
                )
                _analysis_tasks[session_id] = task

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info("websocket_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("websocket_error", error=str(e), session_id=session_id)
        manager.disconnect(session_id)

"""에이전트 베이스 클래스"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
import structlog

from app.services.llm import llm_router, LLMMessage, LLMProvider

logger = structlog.get_logger()


class AgentState(str, Enum):
    """에이전트 상태"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AgentContext:
    """에이전트 컨텍스트"""
    session_id: str
    user_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    event_handler: Optional[Callable[[Dict[str, Any]], Any]] = None


@dataclass
class AgentResult:
    """에이전트 실행 결과"""
    success: bool
    state: AgentState
    data: Dict[str, Any]
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    에이전트 베이스 클래스

    모든 에이전트는 이 클래스를 상속받아 구현합니다.
    """

    def __init__(
        self,
        context: AgentContext,
        llm_provider: Optional[LLMProvider] = None,
        temperature: float = 0.7
    ):
        self.context = context
        self.llm_provider = llm_provider
        self.temperature = temperature
        self.state = AgentState.IDLE
        self.logger = logger.bind(
            agent=self.__class__.__name__,
            session_id=context.session_id
        )
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    @abstractmethod
    async def run(self) -> AgentResult:
        """에이전트 실행 (하위 클래스에서 구현)"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """에이전트 이름"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """에이전트 설명"""
        pass

    async def execute(self) -> AgentResult:
        """
        에이전트 실행 (공통 로직 포함)

        Returns:
            AgentResult: 실행 결과
        """
        self.start_time = datetime.now()
        self.state = AgentState.RUNNING

        self.logger.info(
            "agent_started",
            agent=self.name,
            session_id=self.context.session_id
        )

        try:
            result = await self.run()
            self.state = AgentState.SUCCESS if result.success else AgentState.FAILED
            self.end_time = datetime.now()

            self.logger.info(
                "agent_completed",
                agent=self.name,
                state=self.state,
                duration=(self.end_time - self.start_time).total_seconds()
            )

            # 히스토리에 기록
            self.context.history.append({
                "agent": self.name,
                "state": self.state,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "result": result.data,
            })

            return result

        except Exception as e:
            self.state = AgentState.FAILED
            self.end_time = datetime.now()

            self.logger.error(
                "agent_failed",
                agent=self.name,
                error=str(e),
                duration=(self.end_time - self.start_time).total_seconds()
            )

            return AgentResult(
                success=False,
                state=AgentState.FAILED,
                data={},
                error=str(e)
            )

    async def llm_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        LLM 텍스트 생성

        Args:
            messages: 메시지 목록
            temperature: 온도 (기본값: self.temperature)
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터

        Returns:
            LLMResponse
        """
        temp = temperature if temperature is not None else self.temperature

        response = await llm_router.generate(
            messages=messages,
            provider=self.llm_provider,
            temperature=temp,
            max_tokens=max_tokens,
            **kwargs
        )

        # LLM 호출 로깅
        self.logger.info(
            "llm_generated",
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.usage.get("prompt_tokens", 0) if response.usage else 0,
            completion_tokens=response.usage.get("completion_tokens", 0) if response.usage else 0
        )

        return response

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        간단 텍스트 생성 헬퍼

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            temperature: 온도
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터
        """
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=prompt))
        return await self.llm_generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    async def llm_stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        LLM 스트리밍 생성

        Args:
            messages: 메시지 목록
            temperature: 온도
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터

        Yields:
            str: 생성된 텍스트 청크
        """
        temp = temperature if temperature is not None else self.temperature

        async for chunk in llm_router.stream_generate(
            messages=messages,
            provider=self.llm_provider,
            temperature=temp,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk

    def update_context(self, key: str, value: Any):
        """컨텍스트 데이터 업데이트"""
        self.context.data[key] = value
        self.logger.debug("context_updated", key=key)

    def get_context(self, key: str, default: Any = None) -> Any:
        """컨텍스트 데이터 조회"""
        return self.context.data.get(key, default)

    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """이벤트 발행 (나중에 WebSocket/SSE로 전송 가능)"""
        event = {
            "type": event_type,
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.logger.info("event_emitted", event_data=event)
        if self.context.event_handler:
            try:
                result = self.context.event_handler(event)
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                self.logger.warning("event_handler_failed", error=str(exc))
        return event

"""LLM 클라이언트 베이스 클래스"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from app.config import settings


class LLMProvider(str, Enum):
    """LLM 제공자"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


@dataclass
class LLMResponse:
    """LLM 응답"""
    content: str
    provider: LLMProvider
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


@dataclass
class LLMMessage:
    """LLM 메시지"""
    role: str  # "system", "user", "assistant"
    content: str


class BaseLLMClient(ABC):
    """LLM 클라이언트 베이스 클래스"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.provider = self._get_provider()

    @abstractmethod
    def _get_provider(self) -> LLMProvider:
        """제공자 반환"""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """텍스트 생성"""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """스트리밍 생성"""
        pass

    def format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """메시지를 표준 포맷으로 변환"""
        for msg in messages:
            if msg.content and len(msg.content) > settings.LLM_MAX_MESSAGE_LENGTH:
                raise ValueError("LLM message too long")
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    @staticmethod
    def clamp_temperature(value: float) -> float:
        """Temperature 범위 제한"""
        return max(0.0, min(1.0, value))

    @staticmethod
    def clamp_max_tokens(value: Optional[int]) -> Optional[int]:
        """max_tokens 범위 제한"""
        if value is None:
            return None
        return max(1, min(settings.LLM_MAX_TOKENS, value))

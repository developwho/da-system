"""LLM 라우터 - 통합 LLM 클라이언트"""
from typing import List, Optional, Dict
import asyncio
from app.config import settings
from app.utils.logger import get_logger
from .base import BaseLLMClient, LLMResponse, LLMMessage, LLMProvider
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient

# Gemini 클라이언트는 선택적으로 로딩
try:
    from .gemini_client import GeminiClient
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    GeminiClient = None


class LLMRouter:
    """
    통합 LLM 라우터
    - 여러 LLM 제공자를 관리
    - Fallback 지원
    - 로드 밸런싱
    """

    def __init__(self):
        self.clients: Dict[LLMProvider, BaseLLMClient] = {}
        self.default_provider = LLMProvider.OPENAI
        self._initialize_clients()

    def _initialize_clients(self):
        """사용 가능한 LLM 클라이언트 초기화"""
        # OpenAI
        if settings.OPENAI_API_KEY:
            self.clients[LLMProvider.OPENAI] = OpenAIClient(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL
            )

        # Anthropic
        if settings.ANTHROPIC_API_KEY:
            self.clients[LLMProvider.ANTHROPIC] = AnthropicClient(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.ANTHROPIC_MODEL
            )

        # Gemini (선택적)
        if settings.GOOGLE_API_KEY and GEMINI_AVAILABLE and GeminiClient:
            try:
                self.clients[LLMProvider.GEMINI] = GeminiClient(
                    api_key=settings.GOOGLE_API_KEY,
                    model=settings.GEMINI_MODEL
                )
            except Exception:
                pass  # Gemini 초기화 실패 시 무시

        # 기본 제공자 설정
        if LLMProvider.OPENAI in self.clients:
            self.default_provider = LLMProvider.OPENAI
        elif LLMProvider.ANTHROPIC in self.clients:
            self.default_provider = LLMProvider.ANTHROPIC
        elif LLMProvider.GEMINI in self.clients:
            self.default_provider = LLMProvider.GEMINI
        else:
            raise ValueError("No LLM API keys configured")

    def get_client(self, provider: Optional[LLMProvider] = None) -> BaseLLMClient:
        """LLM 클라이언트 가져오기"""
        provider = provider or self.default_provider

        if provider not in self.clients:
            raise ValueError(f"Provider {provider} not available")

        return self.clients[provider]

    async def generate(
        self,
        messages: List[LLMMessage],
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_fallback: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        텍스트 생성 (Fallback 지원)

        Args:
            messages: 메시지 목록
            provider: 사용할 제공자 (None이면 기본값)
            temperature: 온도 (0.0-1.0)
            max_tokens: 최대 토큰 수
            use_fallback: 실패 시 다른 제공자로 fallback 여부
            **kwargs: 추가 파라미터
        """
        provider = provider or self.default_provider

        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            try:
                return await self._generate_with_timeout(
                    provider, messages, temperature, max_tokens, **kwargs
                )
            except Exception as e:
                if attempt >= settings.LLM_MAX_RETRIES:
                    break
                await asyncio.sleep(0.5 * (2 ** attempt))

        try:
            raise Exception("Primary provider failed after retries")
        except Exception as e:
            if not use_fallback:
                raise

            # Fallback: 다른 제공자 시도
            for fallback_provider in self.clients.keys():
                if fallback_provider == provider:
                    continue

                try:
                    return await self._generate_with_timeout(
                        fallback_provider, messages, temperature, max_tokens, **kwargs
                    )
                except Exception as fallback_error:
                    get_logger(__name__).warning(
                        "llm_fallback_failed",
                        provider=fallback_provider,
                        error=str(fallback_error)
                    )
                    continue

            # 모든 제공자 실패
            raise Exception(f"All LLM providers failed. Last error: {e}")

    async def _generate_with_timeout(
        self,
        provider: LLMProvider,
        messages: List[LLMMessage],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> LLMResponse:
        client = self.get_client(provider)
        return await asyncio.wait_for(
            client.generate(messages, temperature, max_tokens, **kwargs),
            timeout=settings.LLM_TIMEOUT_SECONDS
        )

    async def stream_generate(
        self,
        messages: List[LLMMessage],
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_fallback: bool = True,
        **kwargs
    ):
        """스트리밍 생성 (Fallback 지원)"""
        provider = provider or self.default_provider
        logger = get_logger(__name__)

        # 1차 시도: 기본 provider
        try:
            client = self.get_client(provider)
            async for chunk in client.stream_generate(messages, temperature, max_tokens, **kwargs):
                yield chunk
            return
        except Exception as e:
            logger.warning("stream_generate_primary_failed", provider=provider.value, error=str(e))
            if not use_fallback:
                raise

        # 2차 시도: fallback providers
        for fallback_provider in self.clients.keys():
            if fallback_provider == provider:
                continue
            try:
                logger.info("stream_generate_fallback", provider=fallback_provider.value)
                client = self.get_client(fallback_provider)
                async for chunk in client.stream_generate(messages, temperature, max_tokens, **kwargs):
                    yield chunk
                return
            except Exception as fallback_error:
                logger.warning(
                    "stream_generate_fallback_failed",
                    provider=fallback_provider.value,
                    error=str(fallback_error)
                )
                continue

        raise Exception(f"All LLM providers failed for stream_generate")

    def list_available_providers(self) -> List[LLMProvider]:
        """사용 가능한 제공자 목록"""
        return list(self.clients.keys())


# 글로벌 인스턴스
llm_router = LLMRouter()

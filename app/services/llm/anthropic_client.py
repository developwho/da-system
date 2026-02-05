"""Anthropic 클라이언트"""
from typing import List, Optional
from anthropic import AsyncAnthropic
from .base import BaseLLMClient, LLMResponse, LLMMessage, LLMProvider
from app.config import settings


class AnthropicClient(BaseLLMClient):
    """Anthropic API 클라이언트"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(api_key, model)
        self.client = AsyncAnthropic(api_key=api_key)

    def _get_provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC

    def _extract_system_message(self, messages: List[LLMMessage]) -> tuple[Optional[str], List[LLMMessage]]:
        """시스템 메시지 분리 (Anthropic은 system을 별도 파라미터로 받음)"""
        system_message = None
        other_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                other_messages.append(msg)

        return system_message, other_messages

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        **kwargs
    ) -> LLMResponse:
        """텍스트 생성"""
        system_message, other_messages = self._extract_system_message(messages)
        formatted_messages = self.format_messages(other_messages)
        temperature = self.clamp_temperature(temperature)
        max_tokens = self.clamp_max_tokens(max_tokens) or settings.LLM_MAX_TOKENS

        params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": settings.LLM_TIMEOUT_SECONDS,
            **kwargs
        }

        if system_message:
            params["system"] = system_message

        response = await self.client.messages.create(**params)

        return LLMResponse(
            content=response.content[0].text,
            provider=self.provider,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
            raw_response=response,
        )

    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        **kwargs
    ):
        """스트리밍 생성"""
        system_message, other_messages = self._extract_system_message(messages)
        formatted_messages = self.format_messages(other_messages)
        temperature = self.clamp_temperature(temperature)
        max_tokens = self.clamp_max_tokens(max_tokens) or settings.LLM_MAX_TOKENS

        params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": settings.LLM_TIMEOUT_SECONDS,
            **kwargs
        }

        if system_message:
            params["system"] = system_message

        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text

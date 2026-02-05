"""OpenAI 클라이언트"""
from typing import List, Optional
from openai import AsyncOpenAI
from .base import BaseLLMClient, LLMResponse, LLMMessage, LLMProvider
from app.config import settings


class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)

    def _get_provider(self) -> LLMProvider:
        return LLMProvider.OPENAI

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """텍스트 생성"""
        formatted_messages = self.format_messages(messages)
        temperature = self.clamp_temperature(temperature)
        max_tokens = self.clamp_max_tokens(max_tokens)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            **kwargs
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.provider,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
            raw_response=response,
        )

    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """스트리밍 생성"""
        formatted_messages = self.format_messages(messages)
        temperature = self.clamp_temperature(temperature)
        max_tokens = self.clamp_max_tokens(max_tokens)

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            **kwargs
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

"""Google Gemini 클라이언트"""
from typing import List, Optional
from google import genai
from google.genai import types
from .base import BaseLLMClient, LLMResponse, LLMMessage, LLMProvider
from app.config import settings


class GeminiClient(BaseLLMClient):
    """Google Gemini API 클라이언트"""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        super().__init__(api_key, model)
        self.client = genai.Client(api_key=api_key)
        self.async_client = self.client.aio

    def _get_provider(self) -> LLMProvider:
        return LLMProvider.GEMINI

    def _convert_to_gemini_format(self, messages: List[LLMMessage]) -> tuple[Optional[str], List[types.Content]]:
        """Gemini 포맷으로 변환 (system은 별도, user/model 교대)"""
        system_instruction = None
        contents: List[types.Content] = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.content)]
                    )
                )

        if not contents:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text="")])]

        return system_instruction, contents

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """텍스트 생성"""
        _ = self.format_messages(messages)
        system_instruction, contents = self._convert_to_gemini_format(messages)
        temperature = self.clamp_temperature(temperature)
        max_tokens = self.clamp_max_tokens(max_tokens)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction
        )

        response = await self.async_client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config
        )

        # 토큰 사용량 (Gemini는 제공하지 않으므로 추정)
        usage = {
            "prompt_tokens": 0,  # Gemini API는 토큰 사용량 미제공
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        return LLMResponse(
            content=response.text,
            provider=self.provider,
            model=self.model,
            usage=usage,
            finish_reason=None,
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
        _ = self.format_messages(messages)
        system_instruction, contents = self._convert_to_gemini_format(messages)
        temperature = self.clamp_temperature(temperature)
        max_tokens = self.clamp_max_tokens(max_tokens)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction
        )

        stream = await self.async_client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config
        )

        async for chunk in stream:
            if chunk.text:
                yield chunk.text

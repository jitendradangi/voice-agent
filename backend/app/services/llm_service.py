from typing import Any

from app.services.llm.base import BaseLLMService


class LLMService:
    def __init__(self, provider: BaseLLMService):
        self.provider = provider

    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        return await self.provider.generate_response(
            messages,
            tools,
        )


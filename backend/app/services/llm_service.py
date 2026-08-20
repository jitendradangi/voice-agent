from typing import Protocol


class LLMService(Protocol):

    async def generate_response(
        self,
        messages: list[dict[str, str]]
    ) -> str:
        ...
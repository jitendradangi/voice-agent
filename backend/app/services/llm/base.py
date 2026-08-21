from abc import ABC, abstractmethod
from typing import Any


class BaseLLMService(ABC):

    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        pass

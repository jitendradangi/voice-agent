from abc import ABC, abstractmethod


class BaseLLMService(ABC):

    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict[str, str]]
    ) -> str:
        pass
from app.services.llm.base import BaseLLMService


class MockLLMService(BaseLLMService):

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        tools=None,
    ) -> str:
        return "This is a mock response from the LLM service."

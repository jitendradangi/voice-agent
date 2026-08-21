from app.services.llm.base import BaseLLMService


class MockLLMService(BaseLLMService):

    async def generate_response(
        self,
        messages: list[dict[str, str]]
    ) -> str:
        user_message = messages[-1]["content"]

        return f"Mock response for: {user_message}"
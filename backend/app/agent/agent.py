from app.services.llm_service import LLMService
from app.agent.prompts import SYSTEM_PROMPT


class Agent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def run(
        self,
        message: str,
        history: list[dict[str, str]] | None = None
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        if history:
            messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        return await self.llm_service.generate_response(messages)
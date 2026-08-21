from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agent.agent import Agent
from app.services.llm_service import LLMService
from app.services.llm.mock import MockLLMService
from app.schemas.agent import AgentResponse


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(AgentResponse):
    pass


def get_llm_service() -> LLMService:
    return LLMService(
        provider=MockLLMService()
    )


def get_agent(
    llm_service: LLMService = Depends(get_llm_service)
) -> Agent:
    return Agent(llm_service)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: Agent = Depends(get_agent)
):
    response = await agent.run(
        request.message,
        [message.model_dump() for message in request.history]
    )

    return ChatResponse(
        response=response
    )
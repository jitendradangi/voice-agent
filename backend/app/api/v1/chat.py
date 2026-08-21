from fastapi import APIRouter, Depends
from pydantic import BaseModel

from datetime import date

from app.database.dependencies import get_db
from app.tools.attendance_tools import get_my_attendance

from app.agent.agent import Agent
from app.services.llm_service import LLMService
from app.services.llm.gemini import GeminiLLMService
from app.schemas.agent import AgentResponse
from app.core.user_context import UserContext


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
        provider=GeminiLLMService()
    )


def get_agent(
    llm_service: LLMService = Depends(get_llm_service),
    db=Depends(get_db),
) -> Agent:
    # TODO: Replace with proper authentication/authorization
    # This is a temporary demo configuration for development
    user_context = UserContext(
        enroll_id=1,
        name="Demo User",
    )

    return Agent(
        llm_service=llm_service,
        db=db,
        user_context=user_context,
    )


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

@router.get("/test-attendance/{enroll_id}")
def test_attendance(
    enroll_id: int,
    target_date: date,
    db=Depends(get_db),
):
    # TODO: Remove this test endpoint in production
    # This is a temporary endpoint for development/testing
    result = get_my_attendance(
        db=db,
        enroll_id=enroll_id,
        target_date=target_date,
    )
    return result
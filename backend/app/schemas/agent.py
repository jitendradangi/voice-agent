from pydantic import BaseModel
from typing import Any


class AgentResponse(BaseModel):
    response: str
    tool_used: bool = False
    tool_name: str | None = None
    metadata: dict[str, Any] | None = None
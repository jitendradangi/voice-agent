from datetime import date
import logging
from typing import Any

from app.core.user_context import UserContext
from app.services.llm_service import LLMService
from app.agent.prompts import SYSTEM_PROMPT
from app.tools.registry import tool_registry
from app.tools.base import tool_error

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, llm_service: LLMService, db: Any, user_context: UserContext):
        self.llm_service = llm_service
        self.db = db
        self.user_context = user_context

    async def run(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None
    ) -> str:
        today = date.today().isoformat()

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    f"{SYSTEM_PROMPT}\n\n"
                    f"Today's date is {today}.\n"
                    f"When the user says 'today', use {today}.\n"
                    f"When the user says 'yesterday', use the previous date."
                ),
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

        max_turns = 5
        for turn in range(max_turns):
            response = await self.llm_service.generate_response(
                messages,
                tools=[
                    {
                        "function_declarations": tool_registry.get_all_schemas()
                    }
                ]
            )

            function_call = None
            if hasattr(response, "candidates") and response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_call = part.function_call
                        break

            if not function_call:
                return response.text or ""

            tool_name = function_call.name
            tool_args = dict(function_call.args)

            # Validate tool is registered before execution
            if not tool_registry.validate_tool_name(tool_name):
                logger.warning("Attempted to execute unregistered tool: %s", tool_name)
                tool_result = tool_error(f"Tool '{tool_name}' is not available.")
            else:
                # Inject enroll_id if tool requires it
                if tool_registry.requires_enroll_id(tool_name):
                    tool_args["enroll_id"] = self.user_context.enroll_id

                logger.info("Executing tool '%s' with args: %s", tool_name, tool_args)

                tool_function = tool_registry.get_function(tool_name)

                if not tool_function:
                    tool_result = tool_error(f"Tool '{tool_name}' is not available.")
                else:
                    try:
                        tool_result = tool_function(
                            db=self.db,
                            **tool_args,
                        )
                    except Exception as e:
                        logger.error("Error executing tool '%s': %s", tool_name, e)
                        tool_result = tool_error(str(e))

                logger.info("Tool '%s' result: %s", tool_name, tool_result)

            # Record model turn with function call
            messages.append({
                "role": "assistant",
                "function_call": {
                    "name": tool_name,
                    "args": tool_args,
                },
                "raw_content": response.candidates[0].content if hasattr(response, "candidates") else None
            })

            # Record tool result turn to feed back to LLM
            messages.append({
                "role": "tool",
                "name": tool_name,
                "content": tool_result,
            })

        return getattr(response, "text", "") or "Max iteration turns reached."
  
      
import logging
from typing import Any
import google.genai as genai
from google.genai import types

from app.core.config import settings
from app.services.llm.base import BaseLLMService

logger = logging.getLogger(__name__)


class GeminiLLMService(BaseLLMService):
    def __init__(self):
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not configured in settings.")
        self.client = genai.Client(api_key=api_key)

    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        system_instruction = None
        contents = []

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "system":
                if content:
                    system_instruction = str(content)

            elif role == "user":
                if "parts" in message and message["parts"]:
                    contents.append(types.Content(role="user", parts=message["parts"]))
                elif content is not None:
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=str(content))]))

            elif role in ("assistant", "model"):
                if "raw_content" in message and message["raw_content"]:
                    contents.append(message["raw_content"])
                elif "function_call" in message:
                    fc = message["function_call"]
                    contents.append(
                        types.Content(
                            role="model",
                            parts=[types.Part.from_function_call(name=fc["name"], args=fc["args"])]
                        )
                    )
                elif "parts" in message and message["parts"]:
                    contents.append(types.Content(role="model", parts=message["parts"]))
                elif content is not None:
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=str(content))]))

            elif role in ("tool", "function"):
                name = message.get("name", "")
                tool_result = message.get("content", {})
                response_dict = tool_result if isinstance(tool_result, dict) else {"result": tool_result}
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(name=name, response=response_dict)]
                    )
                )

        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="")]))

        tool_config = None
        formatted_tools = []
        if tools:
            for t in tools:
                if isinstance(t, dict) and "function_declarations" in t:
                    formatted_tools.append(types.Tool(function_declarations=t["function_declarations"]))
                elif isinstance(t, types.Tool):
                    formatted_tools.append(t)
                else:
                    formatted_tools.append(types.Tool(function_declarations=[t]))

            tool_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=formatted_tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        elif system_instruction:
            tool_config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=tool_config
            )
            return response
        except Exception as e:
            logger.error("Gemini API call failed: %s", e)
            raise

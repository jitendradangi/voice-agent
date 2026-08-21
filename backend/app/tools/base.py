from typing import Any


def tool_success(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
    }


def tool_error(message: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": message,
    }
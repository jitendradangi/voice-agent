"""
Central tool registry for managing application tools.

This module provides a clean, LLM-provider-independent registry system for tools.
It separates tool implementation from schema definitions and provides validation
to ensure only registered tools can be executed.
"""
from dataclasses import dataclass
from typing import Callable, Any
from app.tools.attendance_tools import (
    get_my_attendance,
    get_attendance_summary,
    get_attendance_logs,
    get_attendance_status,
)
from app.tools.tool_schemas import (
    GET_MY_ATTENDANCE_SCHEMA,
    GET_ATTENDANCE_SUMMARY_SCHEMA,
    GET_ATTENDANCE_LOGS_SCHEMA,
    GET_ATTENDANCE_STATUS_SCHEMA,
)


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    function: Callable
    schema: dict[str, Any]
    requires_enroll_id: bool = False
    description: str = ""


class ToolRegistry:
    """Central registry for all available tools with validation and security."""
    
    def __init__(self):
        self._tools: dict[str, ToolMetadata] = {}
    
    def register(
        self,
        name: str,
        function: Callable,
        schema: dict[str, Any],
        requires_enroll_id: bool = False,
        description: str = ""
    ) -> None:
        """Register a tool with its metadata."""
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        
        self._tools[name] = ToolMetadata(
            name=name,
            function=function,
            schema=schema,
            requires_enroll_id=requires_enroll_id,
            description=description
        )
    
    def get_tool(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name."""
        return self._tools.get(name)
    
    def get_function(self, name: str) -> Callable | None:
        """Get tool function by name."""
        metadata = self.get_tool(name)
        return metadata.function if metadata else None
    
    def get_schema(self, name: str) -> dict[str, Any] | None:
        """Get tool schema by name."""
        metadata = self.get_tool(name)
        return metadata.schema if metadata else None
    
    def is_registered(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def requires_enroll_id(self, name: str) -> bool:
        """Check if a tool requires enroll_id injection."""
        metadata = self.get_tool(name)
        return metadata.requires_enroll_id if metadata else False
    
    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Get all tool schemas for LLM function declarations."""
        return [metadata.schema for metadata in self._tools.values()]
    
    def get_all_tool_names(self) -> list[str]:
        """Get all registered tool names."""
        return list(self._tools.keys())
    
    def validate_tool_name(self, name: str) -> bool:
        """Validate that a tool name is registered and safe to execute."""
        return self.is_registered(name)


# Global tool registry instance
tool_registry = ToolRegistry()

# Register attendance tools
tool_registry.register(
    name="get_my_attendance",
    function=get_my_attendance,
    schema=GET_MY_ATTENDANCE_SCHEMA,
    requires_enroll_id=True,
    description="Get attendance details for a specific date"
)

tool_registry.register(
    name="get_attendance_summary",
    function=get_attendance_summary,
    schema=GET_ATTENDANCE_SUMMARY_SCHEMA,
    requires_enroll_id=True,
    description="Get attendance summary for a date range"
)

tool_registry.register(
    name="get_attendance_logs",
    function=get_attendance_logs,
    schema=GET_ATTENDANCE_LOGS_SCHEMA,
    requires_enroll_id=True,
    description="Get raw attendance logs for a specific date"
)

tool_registry.register(
    name="get_attendance_status",
    function=get_attendance_status,
    schema=GET_ATTENDANCE_STATUS_SCHEMA,
    requires_enroll_id=True,
    description="Get concise current attendance status"
)

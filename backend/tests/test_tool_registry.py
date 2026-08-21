"""
Tests for the enhanced tool registry system.
"""
import pytest
from app.tools.registry import ToolRegistry, ToolMetadata, tool_registry
from app.tools.attendance_tools import (
    get_my_attendance,
    get_attendance_summary,
    get_attendance_logs,
    get_attendance_status,
)


class TestToolRegistry:
    """Tests for the ToolRegistry class."""

    def test_tool_registry_initialization(self):
        """Test that ToolRegistry initializes correctly."""
        registry = ToolRegistry()
        assert registry is not None
        assert isinstance(registry._tools, dict)
        assert len(registry._tools) == 0

    def test_register_tool(self):
        """Test registering a new tool."""
        registry = ToolRegistry()
        
        def dummy_tool(db, arg1):
            return {"success": True, "data": {"arg1": arg1}}
        
        schema = {
            "name": "dummy_tool",
            "description": "A dummy tool for testing",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"}
                },
                "required": ["arg1"]
            }
        }
        
        registry.register(
            name="dummy_tool",
            function=dummy_tool,
            schema=schema,
            requires_enroll_id=False,
            description="Test tool"
        )
        
        assert registry.is_registered("dummy_tool")
        assert registry.get_function("dummy_tool") == dummy_tool
        assert registry.get_schema("dummy_tool") == schema
        assert registry.requires_enroll_id("dummy_tool") is False

    def test_register_duplicate_tool_raises_error(self):
        """Test that registering a duplicate tool raises an error."""
        registry = ToolRegistry()
        
        def dummy_tool(db, arg1):
            return {"success": True}
        
        schema = {"name": "dummy_tool", "description": "Test", "parameters": {}}
        
        registry.register("dummy_tool", dummy_tool, schema)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register("dummy_tool", dummy_tool, schema)

    def test_get_tool_metadata(self):
        """Test getting tool metadata."""
        registry = ToolRegistry()
        
        def dummy_tool(db, arg1):
            return {"success": True}
        
        schema = {"name": "dummy_tool", "description": "Test", "parameters": {}}
        
        registry.register(
            name="dummy_tool",
            function=dummy_tool,
            schema=schema,
            requires_enroll_id=True,
            description="Test description"
        )
        
        metadata = registry.get_tool("dummy_tool")
        
        assert metadata is not None
        assert metadata.name == "dummy_tool"
        assert metadata.function == dummy_tool
        assert metadata.schema == schema
        assert metadata.requires_enroll_id is True
        assert metadata.description == "Test description"

    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist."""
        registry = ToolRegistry()
        
        assert registry.get_tool("nonexistent") is None
        assert registry.get_function("nonexistent") is None
        assert registry.get_schema("nonexistent") is None
        assert registry.is_registered("nonexistent") is False

    def test_validate_tool_name(self):
        """Test tool name validation."""
        registry = ToolRegistry()
        
        def dummy_tool(db, arg1):
            return {"success": True}
        
        schema = {"name": "dummy_tool", "description": "Test", "parameters": {}}
        
        registry.register("dummy_tool", dummy_tool, schema)
        
        assert registry.validate_tool_name("dummy_tool") is True
        assert registry.validate_tool_name("nonexistent") is False

    def test_requires_enroll_id(self):
        """Test requires_enroll_id functionality."""
        registry = ToolRegistry()
        
        def tool_with_enroll(db, enroll_id, arg1):
            return {"success": True}
        
        def tool_without_enroll(db, arg1):
            return {"success": True}
        
        schema1 = {"name": "tool1", "description": "Test", "parameters": {}}
        schema2 = {"name": "tool2", "description": "Test", "parameters": {}}
        
        registry.register("tool_with_enroll", tool_with_enroll, schema1, requires_enroll_id=True)
        registry.register("tool_without_enroll", tool_without_enroll, schema2, requires_enroll_id=False)
        
        assert registry.requires_enroll_id("tool_with_enroll") is True
        assert registry.requires_enroll_id("tool_without_enroll") is False
        assert registry.requires_enroll_id("nonexistent") is False

    def test_get_all_schemas(self):
        """Test getting all tool schemas."""
        registry = ToolRegistry()
        
        def tool1(db, arg1):
            return {"success": True}
        
        def tool2(db, arg2):
            return {"success": True}
        
        schema1 = {"name": "tool1", "description": "Test 1", "parameters": {}}
        schema2 = {"name": "tool2", "description": "Test 2", "parameters": {}}
        
        registry.register("tool1", tool1, schema1)
        registry.register("tool2", tool2, schema2)
        
        all_schemas = registry.get_all_schemas()
        
        assert len(all_schemas) == 2
        assert schema1 in all_schemas
        assert schema2 in all_schemas

    def test_get_all_tool_names(self):
        """Test getting all registered tool names."""
        registry = ToolRegistry()
        
        def tool1(db, arg1):
            return {"success": True}
        
        def tool2(db, arg2):
            return {"success": True}
        
        schema1 = {"name": "tool1", "description": "Test 1", "parameters": {}}
        schema2 = {"name": "tool2", "description": "Test 2", "parameters": {}}
        
        registry.register("tool1", tool1, schema1)
        registry.register("tool2", tool2, schema2)
        
        tool_names = registry.get_all_tool_names()
        
        assert len(tool_names) == 2
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    def test_tool_metadata_dataclass(self):
        """Test ToolMetadata dataclass."""
        def dummy_func():
            pass
        
        schema = {"name": "test", "description": "Test", "parameters": {}}
        
        metadata = ToolMetadata(
            name="test_tool",
            function=dummy_func,
            schema=schema,
            requires_enroll_id=True,
            description="Test tool metadata"
        )
        
        assert metadata.name == "test_tool"
        assert metadata.function == dummy_func
        assert metadata.schema == schema
        assert metadata.requires_enroll_id is True
        assert metadata.description == "Test tool metadata"


class TestGlobalToolRegistry:
    """Tests for the global tool_registry instance."""

    def test_global_registry_exists(self):
        """Test that the global tool_registry exists."""
        assert tool_registry is not None
        assert isinstance(tool_registry, ToolRegistry)

    def test_attendance_tools_registered(self):
        """Test that all attendance tools are registered."""
        expected_tools = [
            "get_my_attendance",
            "get_attendance_summary",
            "get_attendance_logs",
            "get_attendance_status"
        ]
        
        for tool_name in expected_tools:
            assert tool_registry.is_registered(tool_name)
            assert tool_registry.validate_tool_name(tool_name)

    def test_attendance_tools_require_enroll_id(self):
        """Test that all attendance tools require enroll_id."""
        attendance_tools = [
            "get_my_attendance",
            "get_attendance_summary",
            "get_attendance_logs",
            "get_attendance_status"
        ]
        
        for tool_name in attendance_tools:
            assert tool_registry.requires_enroll_id(tool_name) is True

    def test_attendance_tools_have_schemas(self):
        """Test that all attendance tools have schemas."""
        attendance_tools = [
            "get_my_attendance",
            "get_attendance_summary",
            "get_attendance_logs",
            "get_attendance_status"
        ]
        
        for tool_name in attendance_tools:
            schema = tool_registry.get_schema(tool_name)
            assert schema is not None
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema

    def test_attendance_tools_have_functions(self):
        """Test that all attendance tools have registered functions."""
        attendance_tools = [
            "get_my_attendance",
            "get_attendance_summary",
            "get_attendance_logs",
            "get_attendance_status"
        ]
        
        for tool_name in attendance_tools:
            func = tool_registry.get_function(tool_name)
            assert func is not None
            assert callable(func)

    def test_get_all_schemas_returns_all_attendance_schemas(self):
        """Test that get_all_schemas returns all attendance tool schemas."""
        all_schemas = tool_registry.get_all_schemas()
        
        assert len(all_schemas) == 4
        
        schema_names = [schema["name"] for schema in all_schemas]
        expected_names = [
            "get_my_attendance",
            "get_attendance_summary",
            "get_attendance_logs",
            "get_attendance_status"
        ]
        
        for name in expected_names:
            assert name in schema_names


class TestToolRegistrySecurity:
    """Tests for tool registry security features."""

    def test_unregistered_tool_validation(self):
        """Test that unregistered tools fail validation."""
        assert tool_registry.validate_tool_name("malicious_tool") is False
        assert tool_registry.validate_tool_name("eval") is False
        assert tool_registry.validate_tool_name("exec") is False
        assert tool_registry.validate_tool_name("__import__") is False

    def test_registered_tool_validation(self):
        """Test that registered tools pass validation."""
        assert tool_registry.validate_tool_name("get_my_attendance") is True
        assert tool_registry.validate_tool_name("get_attendance_summary") is True
        assert tool_registry.validate_tool_name("get_attendance_logs") is True
        assert tool_registry.validate_tool_name("get_attendance_status") is True

    def test_cannot_execute_arbitrary_functions(self):
        """Test that arbitrary function names cannot be executed."""
        registry = ToolRegistry()
        
        # Try to get dangerous function names
        dangerous_names = ["eval", "exec", "compile", "__import__", "open"]
        
        for name in dangerous_names:
            assert registry.get_function(name) is None
            assert registry.validate_tool_name(name) is False

    def test_tool_registration_prevents_overwrites(self):
        """Test that tools cannot be overwritten once registered."""
        registry = ToolRegistry()
        
        def original_tool(db, arg1):
            return {"success": True, "original": True}
        
        def malicious_tool(db, arg1):
            return {"success": True, "malicious": True}
        
        schema = {"name": "secure_tool", "description": "Test", "parameters": {}}
        
        registry.register("secure_tool", original_tool, schema)
        
        # Attempt to overwrite should fail
        with pytest.raises(ValueError):
            registry.register("secure_tool", malicious_tool, schema)
        
        # Original function should still be there
        assert registry.get_function("secure_tool") == original_tool

    def test_enroll_id_security_enforcement(self):
        """Test that enroll_id requirement is properly enforced."""
        registry = ToolRegistry()
        
        def secure_tool(db, enroll_id, data):
            return {"success": True, "enroll_id": enroll_id}
        
        def public_tool(db, data):
            return {"success": True}
        
        schema1 = {"name": "secure_tool", "description": "Test", "parameters": {}}
        schema2 = {"name": "public_tool", "description": "Test", "parameters": {}}
        
        registry.register("secure_tool", secure_tool, schema1, requires_enroll_id=True)
        registry.register("public_tool", public_tool, schema2, requires_enroll_id=False)
        
        # Verify the requirements are set correctly
        assert registry.requires_enroll_id("secure_tool") is True
        assert registry.requires_enroll_id("public_tool") is False


class TestToolRegistryExtensibility:
    """Tests for tool registry extensibility."""

    def test_easy_to_add_new_tool(self):
        """Test that adding a new tool is straightforward."""
        registry = ToolRegistry()
        
        def new_application_tool(db, user_id, action):
            return {"success": True, "action": action}
        
        new_schema = {
            "name": "new_application_tool",
            "description": "A new application-specific tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "action": {"type": "string"}
                },
                "required": ["user_id", "action"]
            }
        }
        
        # Should be able to register without any issues
        registry.register(
            name="new_application_tool",
            function=new_application_tool,
            schema=new_schema,
            requires_enroll_id=False,
            description="New tool for testing extensibility"
        )
        
        assert registry.is_registered("new_application_tool")
        assert registry.get_function("new_application_tool") == new_application_tool

    def test_multiple_application_domains(self):
        """Test that tools from different application domains can coexist."""
        registry = ToolRegistry()
        
        def hr_tool(db, employee_id):
            return {"success": True, "domain": "hr"}
        
        def finance_tool(db, budget_id):
            return {"success": True, "domain": "finance"}
        
        def it_tool(db, ticket_id):
            return {"success": True, "domain": "it"}
        
        hr_schema = {"name": "hr_tool", "description": "HR tool", "parameters": {}}
        finance_schema = {"name": "finance_tool", "description": "Finance tool", "parameters": {}}
        it_schema = {"name": "it_tool", "description": "IT tool", "parameters": {}}
        
        registry.register("hr_tool", hr_tool, hr_schema)
        registry.register("finance_tool", finance_tool, finance_schema)
        registry.register("it_tool", it_tool, it_schema)
        
        assert len(registry.get_all_tool_names()) == 3
        assert registry.is_registered("hr_tool")
        assert registry.is_registered("finance_tool")
        assert registry.is_registered("it_tool")
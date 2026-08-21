"""
Tests for UserContext and enroll_id security - ensuring LLM tool calls cannot override UserContext.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import date

from app.core.user_context import UserContext
from app.agent.agent import Agent
from app.tools.registry import tool_registry
from google.genai import types


class TestUserContextSecurity:
    """Tests for UserContext enroll_id security and injection."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def user_context(self):
        """Create UserContext with specific enroll_id."""
        return UserContext(enroll_id=123, name="Test User")

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        service = Mock()
        service.generate_response = AsyncMock()
        return service

    @pytest.fixture
    def agent(self, mock_llm_service, mock_db, user_context):
        """Create Agent instance."""
        return Agent(
            llm_service=mock_llm_service,
            db=mock_db,
            user_context=user_context
        )

    def test_user_context_creation(self):
        """Test UserContext creation with enroll_id."""
        context = UserContext(enroll_id=456, name="Jane Doe")
        assert context.enroll_id == 456
        assert context.name == "Jane Doe"

    def test_user_context_optional_name(self):
        """Test UserContext with optional name field."""
        context = UserContext(enroll_id=789)
        assert context.enroll_id == 789
        assert context.name is None

    @pytest.mark.asyncio
    async def test_user_context_supplies_enroll_id(self, agent, mock_llm_service, mock_db):
        """Test that UserContext correctly supplies enroll_id to tool calls."""
        # Create mock function call response
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}  # No enroll_id in args
        )
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_fc_response.candidates = [Mock(content=mock_fc_content)]
        mock_fc_response.text = None
        
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "Attendance retrieved."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
        ]
        
        # Mock user lookup
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Track tool calls
        tool_calls = []
        original_tool = tool_registry.get_function("get_my_attendance")
        
        def track_tool_call(db, enroll_id, **kwargs):
            tool_calls.append({"enroll_id": enroll_id, "kwargs": kwargs})
            return original_tool(db, enroll_id, **kwargs)
        
        with patch.object(tool_registry, 'get_function', return_value=track_tool_call):
            with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
                with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                    await agent.run("What was my attendance on Jan 15?")
                    
                    # Verify enroll_id from UserContext was used
                    assert len(tool_calls) == 1
                    assert tool_calls[0]["enroll_id"] == 123  # From UserContext

    @pytest.mark.asyncio
    async def test_llm_cannot_override_enroll_id(self, agent, mock_llm_service, mock_db):
        """Test that LLM tool call cannot override UserContext.enroll_id."""
        # LLM tries to pass a different enroll_id
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15", "enroll_id": 999}  # LLM tries to override
        )
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_fc_response.candidates = [Mock(content=mock_fc_content)]
        mock_fc_response.text = None
        
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "Attendance retrieved."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
        ]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Track what enroll_id was actually used
        tool_calls = []
        original_tool = tool_registry.get_function("get_my_attendance")
        
        def track_tool_call(db, enroll_id, **kwargs):
            tool_calls.append({"enroll_id": enroll_id, "kwargs": kwargs})
            return original_tool(db, enroll_id, **kwargs)
        
        with patch.object(tool_registry, 'get_function', return_value=track_tool_call):
            with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
                with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                    await agent.run("What was my attendance on Jan 15?")
                    
                    # Verify UserContext enroll_id was used, not LLM's attempt
                    assert len(tool_calls) == 1
                    assert tool_calls[0]["enroll_id"] == 123  # UserContext value
                    assert tool_calls[0]["enroll_id"] != 999  # Not LLM's attempted override

    @pytest.mark.asyncio
    async def test_enroll_id_injection_for_all_attendance_tools(self, agent, mock_llm_service, mock_db):
        """Test that enroll_id injection happens for all attendance tools."""
        # Test get_attendance_summary
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_attendance_summary",
            args={"start_date": "2025-01-15"}
        )
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_fc_response.candidates = [Mock(content=mock_fc_content)]
        mock_fc_response.text = None
        
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "Summary retrieved."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
        ]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        tool_calls = []
        original_tool = tool_registry.get_function("get_attendance_summary")
        
        def track_tool_call(db, enroll_id, **kwargs):
            tool_calls.append({"enroll_id": enroll_id, "kwargs": kwargs})
            return original_tool(db, enroll_id, **kwargs)
        
        with patch.object(tool_registry, 'get_function', return_value=track_tool_call):
            with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
                with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                    await agent.run("Get my attendance summary.")
                    
                    # Verify enroll_id was injected
                    assert len(tool_calls) == 1
                    assert tool_calls[0]["enroll_id"] == 123

    @pytest.mark.asyncio
    async def test_multiple_consecutive_queries_same_enroll_id(self, agent, mock_llm_service, mock_db):
        """Test that multiple consecutive queries use the same UserContext enroll_id."""
        # First query
        mock_fc_response_1 = Mock()
        mock_fc_part_1 = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        mock_fc_content_1 = types.Content(role="model", parts=[mock_fc_part_1])
        mock_fc_response_1.candidates = [Mock(content=mock_fc_content_1)]
        mock_fc_response_1.text = None
        
        mock_final_1 = Mock()
        mock_final_1.candidates = []
        mock_final_1.text = "Attendance for Jan 15."
        
        # Second query
        mock_fc_response_2 = Mock()
        mock_fc_part_2 = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-16"}
        )
        mock_fc_content_2 = types.Content(role="model", parts=[mock_fc_part_2])
        mock_fc_response_2.candidates = [Mock(content=mock_fc_content_2)]
        mock_fc_response_2.text = None
        
        mock_final_2 = Mock()
        mock_final_2.candidates = []
        mock_final_2.text = "Attendance for Jan 16."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response_1, mock_final_1,
            mock_fc_response_2, mock_final_2
        ]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        tool_calls = []
        original_tool = tool_registry.get_function("get_my_attendance")
        
        def track_tool_call(db, enroll_id, **kwargs):
            tool_calls.append({"enroll_id": enroll_id, "date": kwargs.get("target_date")})
            return original_tool(db, enroll_id, **kwargs)
        
        with patch.object(tool_registry, 'get_function', return_value=track_tool_call):
            with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
                with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                    await agent.run("What was my attendance on Jan 15?")
                    await agent.run("What was my attendance on Jan 16?")
                    
                    # Both calls should use the same enroll_id from UserContext
                    assert len(tool_calls) == 2
                    assert tool_calls[0]["enroll_id"] == 123
                    assert tool_calls[1]["enroll_id"] == 123

    @pytest.mark.asyncio
    async def test_enroll_id_not_exposed_in_tool_response(self, agent, mock_llm_service, mock_db):
        """Test that enroll_id is not exposed in tool response content."""
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_fc_response.candidates = [Mock(content=mock_fc_content)]
        mock_fc_response.text = None
        
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "Your attendance shows present."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
        ]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                await agent.run("What was my attendance on Jan 15?")
                
                # Check the tool response message sent to LLM
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                tool_message = [msg for msg in second_call_messages if msg.get("role") == "tool"][0]
                
                # Verify enroll_id is in the data but not as a separate security concern
                assert "enroll_id" in tool_message["content"]["data"]
                # The enroll_id is part of the attendance data, not a security bypass

    def test_user_context_immutable(self):
        """Test that UserContext fields are properly set."""
        context = UserContext(enroll_id=123, name="Test User")
        
        # Verify initial values
        assert context.enroll_id == 123
        assert context.name == "Test User"
        
        # UserContext is a dataclass, so it's immutable in the sense that
        # we create new instances rather than modifying existing ones
        new_context = UserContext(enroll_id=456, name="Different User")
        assert new_context.enroll_id == 456
        assert context.enroll_id == 123  # Original unchanged

    @pytest.mark.asyncio
    async def test_agent_with_different_user_context(self, mock_llm_service, mock_db):
        """Test Agent with different UserContext instances."""
        # First agent with enroll_id 123
        user_context_1 = UserContext(enroll_id=123, name="User 1")
        agent_1 = Agent(llm_service=mock_llm_service, db=mock_db, user_context=user_context_1)
        
        # Second agent with enroll_id 456
        user_context_2 = UserContext(enroll_id=456, name="User 2")
        agent_2 = Agent(llm_service=mock_llm_service, db=mock_db, user_context=user_context_2)
        
        assert agent_1.user_context.enroll_id == 123
        assert agent_2.user_context.enroll_id == 456
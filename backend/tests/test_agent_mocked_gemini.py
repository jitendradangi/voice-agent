"""
Tests for Agent with mocked Gemini responses - no real API calls.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.agent.agent import Agent
from app.core.user_context import UserContext
from app.tools.registry import tool_registry
from google.genai import types


class TestAgentMockedGemini:
    """Tests for Agent with fully mocked Gemini responses."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def user_context(self):
        """UserContext for testing."""
        return UserContext(enroll_id=123, name="Test User")

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        service = Mock()
        service.generate_response = AsyncMock()
        return service

    @pytest.fixture
    def agent(self, mock_llm_service, mock_db, user_context):
        """Agent instance with mocked dependencies."""
        return Agent(
            llm_service=mock_llm_service,
            db=mock_db,
            user_context=user_context
        )

    def create_mock_function_call_response(self, tool_name, args):
        """Helper to create a mock Gemini function call response."""
        mock_response = Mock()
        mock_fc_part = types.Part.from_function_call(name=tool_name, args=args)
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_response.candidates = [Mock(content=mock_fc_content)]
        mock_response.text = None
        return mock_response

    def create_mock_text_response(self, text):
        """Helper to create a mock Gemini text response."""
        mock_response = Mock()
        mock_response.candidates = []
        mock_response.text = text
        return mock_response

    @pytest.mark.asyncio
    async def test_agent_processes_mocked_function_call_and_final_response(self, agent, mock_llm_service, mock_db):
        """Test Agent correctly processes mocked Gemini function call and mocked final response."""
        # Create mocked function call response
        function_call_response = self.create_mock_function_call_response(
            tool_name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        
        # Create mocked final response
        final_response = self.create_mock_text_response(
            "You were present on January 15, 2025, from 9:00 AM to 6:00 PM."
        )
        
        mock_llm_service.generate_response.side_effect = [
            function_call_response,
            final_response
        ]
        
        # Mock database and attendance service
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', 
                      return_value={"status": "Present", "in_time": "09:00", "out_time": "18:00"}):
                result = await agent.run("What was my attendance on January 15th?")
                
                # Verify final response is returned
                assert result == "You were present on January 15, 2025, from 9:00 AM to 6:00 PM."
                
                # Verify two LLM calls were made
                assert mock_llm_service.generate_response.call_count == 2
                
                # Verify first call included tools
                first_call_kwargs = mock_llm_service.generate_response.call_args_list[0][1]
                assert 'tools' in first_call_kwargs

    @pytest.mark.asyncio
    async def test_agent_with_multiple_tool_calls(self, agent, mock_llm_service, mock_db):
        """Test Agent processes multiple consecutive tool calls."""
        # First function call
        fc1 = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-15"}
        )
        
        # Second function call (LLM asks for another date)
        fc2 = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-16"}
        )
        
        # Final response
        final = self.create_mock_text_response("You were present on both days.")
        
        mock_llm_service.generate_response.side_effect = [fc1, final]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                result = await agent.run("What was my attendance this week?")
                
                assert result == "You were present on both days."

    @pytest.mark.asyncio
    async def test_agent_with_direct_text_response(self, agent, mock_llm_service):
        """Test Agent when Gemini returns text without function call."""
        # Mock response without function call
        text_response = self.create_mock_text_response("Hello! How can I help you today?")
        
        mock_llm_service.generate_response.return_value = text_response
        
        result = await agent.run("Hello")
        
        assert result == "Hello! How can I help you today?"
        assert mock_llm_service.generate_response.call_count == 1

    @pytest.mark.asyncio
    async def test_agent_preserves_conversation_context(self, agent, mock_llm_service, mock_db):
        """Test Agent preserves conversation context across tool calls."""
        fc = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-15"}
        )
        
        final = self.create_mock_text_response("Based on your attendance...")
        
        mock_llm_service.generate_response.side_effect = [fc, final]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                result = await agent.run("What was my attendance on Jan 15?")
                
                # Verify second call includes conversation history
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                
                # Should have system, user, assistant (with function call), tool
                roles = [msg.get("role") for msg in second_call_messages]
                assert "system" in roles
                assert "user" in roles
                assert "assistant" in roles
                assert "tool" in roles

    @pytest.mark.asyncio
    async def test_agent_handles_mocked_tool_error(self, agent, mock_llm_service, mock_db):
        """Test Agent handles tool errors gracefully with mocked responses."""
        fc = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "invalid-date"}
        )
        
        final = self.create_mock_text_response("Please use YYYY-MM-DD format for dates.")
        
        mock_llm_service.generate_response.side_effect = [fc, final]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = await agent.run("What was my attendance on invalid-date?")
        
        assert result == "Please use YYYY-MM-DD format for dates."
        assert mock_llm_service.generate_response.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_with_unknown_tool_mocked(self, agent, mock_llm_service):
        """Test Agent handles unknown tool with mocked responses."""
        fc = self.create_mock_function_call_response(
            "unknown_tool",
            {"some_arg": "value"}
        )
        
        final = self.create_mock_text_response("That tool is not available.")
        
        mock_llm_service.generate_response.side_effect = [fc, final]
        
        result = await agent.run("Use unknown tool")
        
        assert result == "That tool is not available."
        assert mock_llm_service.generate_response.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_conversation_history_with_mocked_responses(self, agent, mock_llm_service):
        """Test Agent respects conversation history with mocked responses."""
        text_response = self.create_mock_text_response("I remember our previous conversation.")
        
        mock_llm_service.generate_response.return_value = text_response
        
        history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"}
        ]
        
        result = await agent.run("Second message", history=history)
        
        assert result == "I remember our previous conversation."
        
        # Verify history was included
        call_messages = mock_llm_service.generate_response.call_args[0][0]
        assert len(call_messages) == 4  # system + 2 history + 1 new

    @pytest.mark.asyncio
    async def test_agent_max_iterations_with_mocked_responses(self, agent, mock_llm_service, mock_db):
        """Test Agent stops after max iterations with mocked responses."""
        # Create a response that always requests function calls
        fc = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-15"}
        )
        
        mock_llm_service.generate_response.return_value = fc
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                result = await agent.run("Test message")
                
                assert "Max iteration turns reached" in result
                assert mock_llm_service.generate_response.call_count == 5

    @pytest.mark.asyncio
    async def test_agent_gemini_sdk_compatibility(self, agent, mock_llm_service, mock_db):
        """Test that Agent's message format is compatible with Gemini SDK."""
        fc = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-15"}
        )
        
        final = self.create_mock_text_response("Response")
        
        mock_llm_service.generate_response.side_effect = [fc, final]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                await agent.run("Test")
                
                # Verify the messages sent to LLM service follow expected format
                first_call_messages = mock_llm_service.generate_response.call_args_list[0][0][0]
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                
                # First call should have system and user messages
                assert any(msg.get("role") == "system" for msg in first_call_messages)
                assert any(msg.get("role") == "user" for msg in first_call_messages)
                
                # Second call should have tool response
                assert any(msg.get("role") == "tool" for msg in second_call_messages)

    @pytest.mark.asyncio
    async def test_agent_with_complex_mocked_scenario(self, agent, mock_llm_service, mock_db):
        """Test Agent with a complex mocked scenario."""
        # User asks about attendance for multiple dates
        fc1 = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-15"}
        )
        
        # After getting first result, LLM asks for another date
        fc2 = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-16"}
        )
        
        # Final comprehensive response
        final = self.create_mock_text_response(
            "On January 15th you were present from 9 AM to 6 PM. "
            "On January 16th you were late, arriving at 10:45 AM."
        )
        
        mock_llm_service.generate_response.side_effect = [fc1, fc2, final]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock different attendance results
        def mock_calculate_attendance(logs, target_date):
            if target_date.day == 15:
                return {"status": "Present", "in_time": "09:00", "out_time": "18:00"}
            else:
                return {"status": "Late", "in_time": "10:45", "out_time": "18:00"}
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', side_effect=mock_calculate_attendance):
                result = await agent.run("What was my attendance on Jan 15 and 16?")
                
                assert "January 15th" in result
                assert "January 16th" in result
                assert mock_llm_service.generate_response.call_count == 3

    @pytest.mark.asyncio
    async def test_agent_tool_response_format_in_mocked_flow(self, agent, mock_llm_service, mock_db):
        """Test that tool responses maintain correct format in mocked flow."""
        fc = self.create_mock_function_call_response(
            "get_my_attendance",
            {"target_date": "2025-01-15"}
        )
        
        final = self.create_mock_text_response("Attendance retrieved successfully.")
        
        mock_llm_service.generate_response.side_effect = [fc, final]
        
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                await agent.run("What was my attendance on Jan 15?")
                
                # Check the tool response message
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                tool_message = [msg for msg in second_call_messages if msg.get("role") == "tool"][0]
                
                # Verify tool response format
                assert "success" in tool_message["content"]
                assert "data" in tool_message["content"]
                assert tool_message["content"]["success"] is True
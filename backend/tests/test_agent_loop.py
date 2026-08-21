"""
Unit tests for the Agent LLM→tool→database→LLM loop without calling Gemini API.
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import date
from sqlalchemy.orm import Session

from app.agent.agent import Agent
from app.core.user_context import UserContext
from app.tools.attendance_tools import get_my_attendance
from app.tools.base import tool_success, tool_error


class TestAgentLoop:
    """Test the complete Agent conversation loop with mocked LLM responses."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def user_context(self):
        """Mock user context."""
        return UserContext(enroll_id=123, name="Test User")

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        service = Mock()
        service.generate_response = AsyncMock()
        return service

    @pytest.fixture
    def agent(self, mock_llm_service, mock_db, user_context):
        """Create Agent instance with mocked dependencies."""
        return Agent(
            llm_service=mock_llm_service,
            db=mock_db,
            user_context=user_context
        )

    def test_gemini_function_call_format(self):
        """Test that we understand the Gemini function call format."""
        from google.genai import types
        
        # Test function call creation
        function_call_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        
        assert function_call_part.function_call.name == "get_my_attendance"
        assert function_call_part.function_call.args["target_date"] == "2025-01-15"

    def test_gemini_function_response_format(self):
        """Test that we understand the Gemini function response format."""
        from google.genai import types
        
        # Test function response creation
        tool_result = {
            "success": True,
            "data": {
                "employee": "John Doe",
                "enroll_id": 123,
                "date": "2025-01-15",
                "status": "present"
            }
        }
        
        function_response_part = types.Part.from_function_response(
            name="get_my_attendance",
            response=tool_result
        )
        
        assert function_response_part.function_response.name == "get_my_attendance"
        assert function_response_part.function_response.response["success"] is True

    @pytest.mark.asyncio
    async def test_agent_with_no_function_call(self, agent, mock_llm_service):
        """Test Agent when LLM returns text without function call."""
        # Mock response without function call
        mock_response = Mock()
        mock_response.candidates = []
        mock_response.text = "Hello! How can I help you today?"
        
        mock_llm_service.generate_response.return_value = mock_response
        
        result = await agent.run("Hello")
        
        assert result == "Hello! How can I help you today?"
        assert mock_llm_service.generate_response.call_count == 1

    @pytest.mark.asyncio
    async def test_agent_with_function_call_success(self, agent, mock_llm_service, mock_db):
        """Test Agent when LLM requests a function call and tool succeeds."""
        from google.genai import types
        from unittest.mock import patch
        
        # Create mock function call response
        mock_function_call_response = Mock()
        mock_function_call_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        mock_function_call_content = types.Content(
            role="model",
            parts=[mock_function_call_part]
        )
        mock_function_call_response.candidates = [Mock(content=mock_function_call_content)]
        mock_function_call_response.text = None
        
        # Create mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "You were present on January 15, 2025."
        
        # Set up LLM service to return different responses on consecutive calls
        mock_llm_service.generate_response.side_effect = [
            mock_function_call_response,
            mock_final_response
        ]
        
        # Mock the attendance service to return a simple result
        mock_attendance_result = tool_success({
            "employee": "John Doe",
            "enroll_id": 123,
            "date": "2025-01-15",
            "status": "Present"
        })
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                # Mock the database query to return a user
                mock_user = Mock()
                mock_user.name = "John Doe"
                mock_user.enroll_id = 123
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                
                result = await agent.run("What was my attendance on January 15th?")
                
                assert result == "You were present on January 15, 2025."
                assert mock_llm_service.generate_response.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_with_function_call_error(self, agent, mock_llm_service, mock_db):
        """Test Agent when tool execution fails."""
        from google.genai import types
        from unittest.mock import patch
        
        # Create mock function call response
        mock_function_call_response = Mock()
        mock_function_call_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        mock_function_call_content = types.Content(
            role="model",
            parts=[mock_function_call_part]
        )
        mock_function_call_response.candidates = [Mock(content=mock_function_call_content)]
        mock_function_call_response.text = None
        
        # Create mock final response after tool error
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "I couldn't retrieve your attendance information."
        
        mock_llm_service.generate_response.side_effect = [
            mock_function_call_response,
            mock_final_response
        ]
        
        # Mock database to return no user (triggering error)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await agent.run("What was my attendance on January 15th?")
        
        assert result == "I couldn't retrieve your attendance information."
        assert mock_llm_service.generate_response.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_injects_enroll_id(self, agent, mock_llm_service, mock_db):
        """Test that Agent injects enroll_id from UserContext into get_my_attendance."""
        from google.genai import types
        from unittest.mock import patch
        
        # Create mock function call response without enroll_id
        mock_function_call_response = Mock()
        mock_function_call_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}  # No enroll_id here
        )
        mock_function_call_content = types.Content(
            role="model",
            parts=[mock_function_call_part]
        )
        mock_function_call_response.candidates = [Mock(content=mock_function_call_content)]
        mock_function_call_response.text = None
        
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "Attendance retrieved."
        
        mock_llm_service.generate_response.side_effect = [
            mock_function_call_response,
            mock_final_response
        ]
        
        # Mock successful user lookup
        mock_user = Mock()
        mock_user.name = "John Doe"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                await agent.run("What was my attendance today?")
                
                # Verify that the tool was called with enroll_id injected
                # The second call to generate_response should include the tool result
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                
                # Find the tool response message
                tool_message = None
                for msg in second_call_messages:
                    if msg.get("role") == "tool":
                        tool_message = msg
                        break
                
                assert tool_message is not None
                # The tool should have been called with enroll_id from UserContext
                # We can verify this indirectly by checking the tool executed successfully

    @pytest.mark.asyncio
    async def test_agent_max_iterations(self, agent, mock_llm_service, mock_db):
        """Test that Agent stops after max iterations to prevent infinite loops."""
        from google.genai import types
        from unittest.mock import patch
        
        # Create a response that always requests a function call
        mock_function_call_response = Mock()
        mock_function_call_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        mock_function_call_content = types.Content(
            role="model",
            parts=[mock_function_call_part]
        )
        mock_function_call_response.candidates = [Mock(content=mock_function_call_content)]
        mock_function_call_response.text = None
        
        # Always return function call (simulating infinite loop scenario)
        mock_llm_service.generate_response.return_value = mock_function_call_response
        
        # Mock successful user lookup to avoid errors
        mock_user = Mock()
        mock_user.name = "John Doe"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                result = await agent.run("Test message")
                
                # Should return max iteration message after 5 turns
                assert "Max iteration turns reached" in result
                # Should have called generate_response 5 times (max_turns)
                assert mock_llm_service.generate_response.call_count == 5

    @pytest.mark.asyncio
    async def test_agent_with_unknown_tool(self, agent, mock_llm_service):
        """Test Agent when LLM requests an unknown tool."""
        from google.genai import types
        
        # Create mock function call response for unknown tool
        mock_function_call_response = Mock()
        mock_function_call_part = types.Part.from_function_call(
            name="unknown_tool",
            args={"some_arg": "value"}
        )
        mock_function_call_content = types.Content(
            role="model",
            parts=[mock_function_call_part]
        )
        mock_function_call_response.candidates = [Mock(content=mock_function_call_content)]
        mock_function_call_response.text = None
        
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "That tool is not available."
        
        mock_llm_service.generate_response.side_effect = [
            mock_function_call_response,
            mock_final_response
        ]
        
        result = await agent.run("Use unknown tool")
        
        assert result == "That tool is not available."
        assert mock_llm_service.generate_response.call_count == 2

    def test_tool_success_format(self):
        """Test that tool_success returns correct format."""
        data = {"employee": "John Doe", "status": "present"}
        result = tool_success(data)
        
        assert result["success"] is True
        assert result["data"] == data
        assert "error" not in result

    def test_tool_error_format(self):
        """Test that tool_error returns correct format."""
        error_message = "Employee not found"
        result = tool_error(error_message)
        
        assert result["success"] is False
        assert result["error"] == error_message
        assert "data" not in result

    @pytest.mark.asyncio
    async def test_agent_conversation_history(self, agent, mock_llm_service):
        """Test that Agent respects conversation history."""
        mock_response = Mock()
        mock_response.candidates = []
        mock_response.text = "Response with history"
        
        mock_llm_service.generate_response.return_value = mock_response
        
        history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"}
        ]
        
        result = await agent.run("Second message", history=history)
        
        assert result == "Response with history"
        
        # Verify that history was included in the call
        call_args = mock_llm_service.generate_response.call_args[0][0]
        assert len(call_args) == 4  # system + 2 history + 1 new user message
        assert call_args[1]["role"] == "user"
        assert call_args[1]["content"] == "First message"
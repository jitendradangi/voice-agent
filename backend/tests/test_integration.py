"""
Integration tests for the complete LLM→tool→database→LLM loop.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import date
from sqlalchemy.orm import Session

from app.agent.agent import Agent
from app.core.user_context import UserContext
from app.tools.attendance_tools import get_my_attendance
from app.tools.base import tool_success, tool_error
from app.tools.registry import tool_registry
from google.genai import types


class TestIntegrationLoop:
    """Integration tests for the complete conversation loop."""

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

    @pytest.mark.asyncio
    async def test_complete_attendance_query_loop(self, agent, mock_llm_service, mock_db):
        """Test complete loop: user query → function call → tool execution → final response."""
        # Create mock function call response
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_fc_response.candidates = [Mock(content=mock_fc_content)]
        mock_fc_response.text = None
        
        # Create mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "You were present on January 15, 2025, from 9:00 AM to 6:00 PM."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
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
                
                assert result == "You were present on January 15, 2025, from 9:00 AM to 6:00 PM."
                assert mock_llm_service.generate_response.call_count == 2
                
                # Verify first call included tools
                first_call_tools = mock_llm_service.generate_response.call_args_list[0][1].get('tools')
                assert first_call_tools is not None
                
                # Verify second call included function response
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                tool_message = None
                for msg in second_call_messages:
                    if msg.get("role") == "tool":
                        tool_message = msg
                        break
                
                assert tool_message is not None
                assert tool_message["name"] == "get_my_attendance"
                assert tool_message["content"]["success"] is True

    @pytest.mark.asyncio
    async def test_error_handling_in_loop(self, agent, mock_llm_service, mock_db):
        """Test that errors in tool execution are handled gracefully."""
        # Create mock function call response
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "invalid-date"}
        )
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_fc_response.candidates = [Mock(content=mock_fc_content)]
        mock_fc_response.text = None
        
        # Create mock final response after error
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "I couldn't process that date. Please use YYYY-MM-DD format."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
        ]
        
        # Mock database to return user (tool will fail on date parsing)
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = await agent.run("What was my attendance on invalid-date?")
        
        assert result == "I couldn't process that date. Please use YYYY-MM-DD format."
        assert mock_llm_service.generate_response.call_count == 2

    @pytest.mark.asyncio
    async def test_user_not_found_error(self, agent, mock_llm_service, mock_db):
        """Test handling when user is not found in database."""
        # Create mock function call response
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}
        )
        mock_fc_content = types.Content(role="model", parts=[mock_fc_part])
        mock_fc_response.candidates = [Mock(content=mock_fc_content)]
        mock_fc_response.text = None
        
        # Create mock final response after error
        mock_final_response = Mock()
        mock_final_response.candidates = []
        mock_final_response.text = "I couldn't find your employee record."
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
        ]
        
        # Mock database to return no user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await agent.run("What was my attendance on January 15th?")
        
        assert result == "I couldn't find your employee record."
        assert mock_llm_service.generate_response.call_count == 2

    @pytest.mark.asyncio
    async def test_enroll_id_injection(self, agent, mock_llm_service, mock_db):
        """Test that enroll_id is automatically injected for get_my_attendance."""
        # Create mock function call response WITHOUT enroll_id
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15"}  # No enroll_id
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
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                # Spy on the actual tool call to verify enroll_id was injected
                original_tool = tool_registry.get_function("get_my_attendance")
                tool_calls = []
                
                def spy_tool(db, enroll_id, **kwargs):
                    tool_calls.append({"enroll_id": enroll_id, "kwargs": kwargs})
                    return original_tool(db, enroll_id, **kwargs)
                
                with patch.object(tool_registry, 'get_function', return_value=spy_tool):
                    await agent.run("What was my attendance today?")
                    
                    # Verify enroll_id was injected from UserContext
                    assert len(tool_calls) == 1
                    assert tool_calls[0]["enroll_id"] == 123

    @pytest.mark.asyncio
    async def test_preservation_of_function_call_context(self, agent, mock_llm_service, mock_db):
        """Test that raw Gemini Content objects are preserved for function call context."""
        # Create mock function call response
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
        mock_final_response.text = "Response."
        
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
                await agent.run("Test")
                
                # Verify that raw_content was preserved in the assistant message
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                assistant_message = None
                for msg in second_call_messages:
                    if msg.get("role") == "assistant":
                        assistant_message = msg
                        break
                
                assert assistant_message is not None
                assert "raw_content" in assistant_message
                assert assistant_message["raw_content"] is not None
                assert assistant_message["raw_content"].role == "model"

    @pytest.mark.asyncio
    async def test_gemini_conversation_format(self, agent, mock_llm_service, mock_db):
        """Test that the conversation format matches Gemini SDK expectations."""
        # Create mock function call response
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
        mock_final_response.text = "Response."
        
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
                await agent.run("Test")
                
                # Verify the second call has proper conversation structure
                second_call_messages = mock_llm_service.generate_response.call_args_list[1][0][0]
                
                # Should have: system, user, assistant (with function call), tool (with response)
                roles = [msg.get("role") for msg in second_call_messages]
                assert "system" in roles
                assert "user" in roles
                assert "assistant" in roles
                assert "tool" in roles
                
                # Verify tool message has correct structure
                tool_message = [msg for msg in second_call_messages if msg.get("role") == "tool"][0]
                assert "name" in tool_message
                assert "content" in tool_message
                assert isinstance(tool_message["content"], dict)
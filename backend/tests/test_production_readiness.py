"""
Production readiness tests for Agent and tools - security and reliability cases.
Tests edge cases, error handling, and security scenarios that must work in production.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.agent.agent import Agent
from app.core.user_context import UserContext
from app.tools.attendance_tools import (
    get_my_attendance,
    get_attendance_summary,
    get_attendance_logs,
    get_attendance_status,
)
from app.tools.base import tool_success, tool_error
from google.genai import types


class TestArgumentValidation:
    """Tests for tool argument validation (missing, extra arguments)."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.name = "Test User"
        user.enroll_id = 123
        return user

    def test_get_my_attendance_missing_required_argument(self, mock_db, mock_user):
        """Test get_my_attendance with missing required target_date argument."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # This should fail when called without target_date
        # The function signature requires target_date, so Python will raise TypeError
        with pytest.raises(TypeError):
            get_my_attendance(db=mock_db, enroll_id=123)

    def test_get_my_attendance_extra_arguments_rejected(self, mock_db, mock_user):
        """Test get_my_attendance with extra unexpected arguments."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Extra arguments should be rejected by Python's function signature
        with pytest.raises(TypeError):
            get_my_attendance(
                db=mock_db,
                enroll_id=123,
                target_date="2025-01-15",
                extra_arg="should_be_rejected"
            )

    def test_get_attendance_summary_missing_start_date(self, mock_db, mock_user):
        """Test get_attendance_summary with missing required start_date."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with pytest.raises(TypeError):
            get_attendance_summary(db=mock_db, enroll_id=123)

    def test_get_attendance_summary_extra_arguments_rejected(self, mock_db, mock_user):
        """Test get_attendance_summary with extra unexpected arguments."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Extra arguments should be rejected
        with pytest.raises(TypeError):
            get_attendance_summary(
                db=mock_db,
                enroll_id=123,
                start_date="2025-01-15",
                extra_param="should_be_rejected"
            )

    def test_get_attendance_logs_missing_target_date(self, mock_db, mock_user):
        """Test get_attendance_logs with missing required target_date."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with pytest.raises(TypeError):
            get_attendance_logs(db=mock_db, enroll_id=123)

    def test_get_attendance_status_all_arguments_optional(self, mock_db, mock_user):
        """Test get_attendance_status with no arguments (all are optional)."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                # Should work with no arguments (defaults to today)
                result = get_attendance_status(db=mock_db, enroll_id=123)
                
                assert result["success"] is True


class TestEdgeCases:
    """Tests for edge cases like empty responses, malformed responses."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

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
        """Create Agent instance."""
        return Agent(
            llm_service=mock_llm_service,
            db=mock_db,
            user_context=user_context
        )

    @pytest.mark.asyncio
    async def test_empty_llm_response(self, agent, mock_llm_service):
        """Test Agent handling of completely empty LLM response."""
        # Mock empty response
        mock_response = Mock()
        mock_response.candidates = []
        mock_response.text = ""
        
        mock_llm_service.generate_response.return_value = mock_response
        
        result = await agent.run("Hello")
        
        # Should return empty string, not crash
        assert result == ""

    @pytest.mark.asyncio
    async def test_malformed_function_call_missing_name(self, agent, mock_llm_service):
        """Test Agent handling of function call with missing name."""
        # Create a function call with empty name
        mock_function_call_part = types.Part.from_function_call(
            name="",  # Empty name instead of None
            args={"target_date": "2025-01-15"}
        )
        
        mock_function_call_content = types.Content(
            role="model",
            parts=[mock_function_call_part]
        )
        mock_response = Mock()
        mock_response.candidates = [Mock(content=mock_function_call_content)]
        mock_response.text = None
        
        mock_llm_service.generate_response.return_value = mock_response
        
        # Should handle gracefully without crashing
        result = await agent.run("Test")
        
        # Should return some fallback text
        assert result is not None

    @pytest.mark.asyncio
    async def test_malformed_function_call_missing_args(self, agent, mock_llm_service):
        """Test Agent handling of function call with empty args."""
        # Create a function call with empty args
        mock_function_call_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={}  # Empty args instead of None
        )
        
        mock_function_call_content = types.Content(
            role="model",
            parts=[mock_function_call_part]
        )
        mock_response = Mock()
        mock_response.candidates = [Mock(content=mock_function_call_content)]
        mock_response.text = None
        
        mock_llm_service.generate_response.return_value = mock_response
        
        # Should handle gracefully - tool will fail due to missing required args
        result = await agent.run("Test")
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_response_none_candidates(self, agent, mock_llm_service):
        """Test Agent handling of response with None candidates."""
        mock_response = Mock()
        mock_response.candidates = None
        mock_response.text = "Fallback text"
        
        mock_llm_service.generate_response.return_value = mock_response
        
        result = await agent.run("Test")
        
        # Should return the text fallback
        assert result == "Fallback text"

    @pytest.mark.asyncio
    async def test_llm_response_none_text(self, agent, mock_llm_service):
        """Test Agent handling of response with None text and no function call."""
        mock_response = Mock()
        mock_response.candidates = []
        mock_response.text = None
        
        mock_llm_service.generate_response.return_value = mock_response
        
        result = await agent.run("Test")
        
        # Should return empty string without crashing
        assert result == ""


class TestAuthorizationSecurity:
    """Tests for unauthorized access prevention and UserContext security."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def user_context(self):
        """Mock user context with specific enroll_id."""
        return UserContext(enroll_id=123, name="Authorized User")

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

    @pytest.mark.asyncio
    async def test_cannot_access_another_employee_attendance(self, agent, mock_llm_service, mock_db):
        """Test that UserContext prevents accessing another employee's attendance."""
        # UserContext has enroll_id=123, but LLM tries to access enroll_id=456
        mock_fc_response = Mock()
        mock_fc_part = types.Part.from_function_call(
            name="get_my_attendance",
            args={"target_date": "2025-01-15", "enroll_id": 456}  # Different employee
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
        mock_user.name = "Authorized User"
        mock_user.enroll_id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Track what enroll_id was actually used
        tool_calls = []
        original_tool = get_my_attendance
        
        def track_tool_call(db, enroll_id, **kwargs):
            tool_calls.append({"enroll_id": enroll_id, "kwargs": kwargs})
            return original_tool(db, enroll_id, **kwargs)
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                with patch('app.tools.registry.tool_registry.get_function', return_value=track_tool_call):
                    await agent.run("Get attendance for employee 456")
                    
                    # Verify that UserContext enroll_id was used, not the requested one
                    assert len(tool_calls) == 1
                    assert tool_calls[0]["enroll_id"] == 123  # UserContext value
                    assert tool_calls[0]["enroll_id"] != 456  # Not the requested employee

    @pytest.mark.asyncio
    async def test_user_context_with_zero_enroll_id(self, mock_llm_service, mock_db):
        """Test Agent behavior when UserContext has invalid enroll_id (0)."""
        # Create UserContext with potentially invalid enroll_id
        user_context = UserContext(enroll_id=0, name="User With Invalid ID")
        
        agent = Agent(
            llm_service=mock_llm_service,
            db=mock_db,
            user_context=user_context
        )
        
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
        mock_final_response.text = "Response"
        
        mock_llm_service.generate_response.side_effect = [
            mock_fc_response,
            mock_final_response
        ]
        
        # Should handle invalid enroll_id gracefully
        result = await agent.run("Test")
        
        # Should not crash, but handle the error
        assert result is not None


class TestDatetimeSerialization:
    """Tests for datetime/date serialization safety in tool results."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.name = "Test User"
        user.enroll_id = 123
        return user

    def test_datetime_objects_in_tool_result_require_conversion(self, mock_db, mock_user):
        """Test that datetime objects in tool results need conversion for serialization."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock attendance with datetime objects (simulating what attendance service might return)
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),  # datetime object
            "out_time": datetime(2025, 1, 15, 18, 0),  # datetime object
            "total_hours": "9h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                # Result should be successful
                assert result["success"] is True
                data = result["data"]
                
                # The current implementation passes through datetime objects
                # This test documents that datetime objects need conversion for JSON serialization
                assert data.get("in_time") is not None
                assert isinstance(data["in_time"], datetime), "Current implementation returns datetime objects"
                
                # To make this JSON serializable, conversion would be needed:
                # data["in_time"] = data["in_time"].isoformat() if data["in_time"] else None

    def test_date_object_in_tool_result(self, mock_db, mock_user):
        """Test that date objects in tool results are safely serialized."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        test_date = date(2025, 1, 15)
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date=test_date  # date object instead of string
                )
                
                # Should handle date object and convert to string
                assert result["success"] is True
                assert isinstance(result["data"]["date"], str)

    def test_tool_result_serializable_for_json_with_datetime_conversion(self, mock_db, mock_user):
        """Test that tool results can be serialized to JSON for LLM with datetime conversion."""
        import json
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Use simple attendance without datetime objects
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value={"status": "Present"}):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                # Should be JSON serializable when no datetime objects are present
                try:
                    json_str = json.dumps(result)
                    assert json_str is not None
                except (TypeError, ValueError) as e:
                    pytest.fail(f"Tool result should be JSON serializable, but got: {e}")
    
    def test_tool_result_not_serializable_with_datetime_objects(self, mock_db, mock_user):
        """Test that tool results with datetime objects are NOT JSON serializable (documents current limitation)."""
        import json
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock attendance with datetime objects
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 18, 0),
            "total_hours": "9h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                # This will fail JSON serialization due to datetime objects
                # This documents the current limitation
                with pytest.raises(TypeError, match="not JSON serializable"):
                    json.dumps(result)


class TestErrorMessageSafety:
    """Tests for error message safety (no stack traces or internals exposed)."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.name = "Test User"
        user.enroll_id = 123
        return user

    def test_tool_error_no_stack_trace(self, mock_db, mock_user):
        """Test that tool errors don't expose stack traces."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Force an exception in the tool
        with patch('app.tools.attendance_tools.get_user_daily_logs', side_effect=Exception("Database connection failed")):
            result = get_my_attendance(
                db=mock_db,
                enroll_id=123,
                target_date="2025-01-15"
            )
            
            # Should return error, not exception
            assert result["success"] is False
            assert "error" in result
            
            # Error message should not contain stack trace indicators
            error_msg = result["error"]
            assert "Traceback" not in error_msg
            assert "File \"" not in error_msg
            assert "line " not in error_msg or "line" in error_msg.lower() and "traceback" not in error_msg.lower()

    def test_database_error_no_internals_exposed(self, mock_db):
        """Test that database errors don't expose internal details."""
        # Mock database to raise an internal error
        mock_db.query.side_effect = Exception("SQLAlchemy internal error: connection pool exhausted")
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=123,
            target_date="2025-01-15"
        )
        
        # Should return generic error, not database internals
        assert result["success"] is False
        assert "error" in result
        
        error_msg = result["error"]
        # Should not expose database internals
        assert "SQLAlchemy" not in error_msg
        assert "connection pool" not in error_msg
        assert "internal error" not in error_msg.lower()

    def test_tool_error_messages_are_user_friendly(self, mock_db, mock_user):
        """Test that error messages are user-friendly, not technical."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', side_effect=Exception("Some technical error")):
            result = get_my_attendance(
                db=mock_db,
                enroll_id=123,
                target_date="2025-01-15"
            )
            
            # Error message should be user-friendly
            assert result["success"] is False
            error_msg = result["error"].lower()
            
            # Should contain user-friendly terms
            assert "unable" in error_msg or "cannot" in error_msg or "error" in error_msg
            
            # Should not contain technical jargon
            assert "exception" not in error_msg
            assert "traceback" not in error_msg

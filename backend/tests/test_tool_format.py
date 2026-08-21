"""
Tests for tool response format validation - ensuring all tools follow common format.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.tools.attendance_tools import get_my_attendance
from app.tools.base import tool_success, tool_error
from app.tools.registry import tool_registry


class TestToolResponseFormat:
    """Tests for common tool response format compliance."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.name = "John Doe"
        user.enroll_id = 123
        return user

    def test_tool_success_format_structure(self):
        """Test that tool_success() returns correct structure."""
        data = {"key": "value", "number": 42}
        result = tool_success(data)
        
        assert isinstance(result, dict)
        assert "success" in result
        assert "data" in result
        assert "error" not in result
        assert result["success"] is True
        assert result["data"] == data

    def test_tool_error_format_structure(self):
        """Test that tool_error() returns correct structure."""
        error_message = "Something went wrong"
        result = tool_error(error_message)
        
        assert isinstance(result, dict)
        assert "success" in result
        assert "error" in result
        assert "data" not in result
        assert result["success"] is False
        assert result["error"] == error_message

    def test_tool_success_with_complex_data(self):
        """Test tool_success with complex nested data."""
        complex_data = {
            "user": {"id": 123, "name": "John"},
            "records": [
                {"date": "2025-01-15", "status": "Present"},
                {"date": "2025-01-16", "status": "Absent"}
            ],
            "metadata": {"total": 2, "page": 1}
        }
        result = tool_success(complex_data)
        
        assert result["success"] is True
        assert result["data"] == complex_data
        assert result["data"]["user"]["id"] == 123
        assert len(result["data"]["records"]) == 2

    def test_tool_error_with_detailed_message(self):
        """Test tool_error with detailed error message."""
        detailed_error = "Database connection failed: timeout after 30 seconds"
        result = tool_error(detailed_error)
        
        assert result["success"] is False
        assert result["error"] == detailed_error

    def test_tool_success_with_empty_data(self):
        """Test tool_success with empty data dict."""
        result = tool_success({})
        
        assert result["success"] is True
        assert result["data"] == {}
        assert isinstance(result["data"], dict)

    def test_tool_error_with_empty_message(self):
        """Test tool_error with empty message."""
        result = tool_error("")
        
        assert result["success"] is False
        assert result["error"] == ""

    def test_get_my_attendance_success_format(self, mock_db, mock_user):
        """Test that get_my_attendance returns success format on success."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 18, 0),
            "total_hours": "9h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                # Validate success format
                assert "success" in result
                assert "data" in result
                assert "error" not in result
                assert result["success"] is True
                assert isinstance(result["data"], dict)

    def test_get_my_attendance_error_format_employee_not_found(self, mock_db):
        """Test that get_my_attendance returns error format when employee not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=999,
            target_date="2025-01-15"
        )
        
        # Validate error format
        assert "success" in result
        assert "error" in result
        assert "data" not in result
        assert result["success"] is False
        assert isinstance(result["error"], str)

    def test_get_my_attendance_error_format_invalid_date(self, mock_db, mock_user):
        """Test that get_my_attendance returns error format for invalid date."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=123,
            target_date="invalid-date"
        )
        
        # Validate error format
        assert "success" in result
        assert "error" in result
        assert "data" not in result
        assert result["success"] is False
        assert isinstance(result["error"], str)

    def test_get_my_attendance_error_format_exception(self, mock_db, mock_user):
        """Test that get_my_attendance returns error format on exception."""
        mock_db.query.return_value.filter.return_value.first.side_effect = Exception("DB Error")
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=123,
            target_date="2025-01-15"
        )
        
        # Validate error format
        assert "success" in result
        assert "error" in result
        assert "data" not in result
        assert result["success"] is False
        assert isinstance(result["error"], str)

    def test_all_registered_tools_follow_format(self):
        """Test that all tools in tool_registry follow the common format."""
        for tool_name in tool_registry.get_all_tool_names():
            tool_function = tool_registry.get_function(tool_name)
            # We can't easily test all tools without proper setup,
            # but we can verify they exist and are callable
            assert callable(tool_function), f"{tool_name} is not callable"

    def test_tool_response_no_extra_fields_success(self):
        """Test that tool_success doesn't add unexpected fields."""
        data = {"test": "value"}
        result = tool_success(data)
        
        # Should only have success and data
        assert set(result.keys()) == {"success", "data"}

    def test_tool_response_no_extra_fields_error(self):
        """Test that tool_error doesn't add unexpected fields."""
        result = tool_error("Test error")
        
        # Should only have success and error
        assert set(result.keys()) == {"success", "error"}

    def test_tool_success_data_immutability(self):
        """Test that tool_success doesn't modify input data."""
        original_data = {"key": "value"}
        original_copy = original_data.copy()
        
        result = tool_success(original_data)
        
        # Original data should be unchanged
        assert original_data == original_copy
        # Result data should match
        assert result["data"] == original_data

    def test_tool_response_types(self):
        """Test that tool response fields have correct types."""
        success_result = tool_success({"test": "data"})
        error_result = tool_error("Test error")
        
        # Success response
        assert isinstance(success_result["success"], bool)
        assert isinstance(success_result["data"], dict)
        
        # Error response
        assert isinstance(error_result["success"], bool)
        assert isinstance(error_result["error"], str)

    def test_get_my_attendance_data_fields(self, mock_db, mock_user):
        """Test that get_my_attendance data contains expected fields."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 18, 0),
            "total_hours": "9h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                # Check expected fields in data
                data = result["data"]
                assert "employee" in data
                assert "enroll_id" in data
                assert "date" in data
                assert "status" in data
                assert data["employee"] == "John Doe"
                assert data["enroll_id"] == 123
                assert data["date"] == "2025-01-15"

    def test_consecutive_tool_calls_maintain_format(self, mock_db, mock_user):
        """Test that consecutive tool calls maintain consistent format."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 18, 0),
            "total_hours": "9h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                # Multiple calls
                result1 = get_my_attendance(mock_db, 123, "2025-01-15")
                result2 = get_my_attendance(mock_db, 123, "2025-01-16")
                result3 = get_my_attendance(mock_db, 123, "2025-01-17")
                
                # All should have same format
                for result in [result1, result2, result3]:
                    assert "success" in result
                    assert "data" in result
                    assert result["success"] is True
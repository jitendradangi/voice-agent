"""
Comprehensive tests for get_my_attendance() tool without consuming Gemini API quota.
"""
import pytest
from datetime import date, datetime, time, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.tools.attendance_tools import get_my_attendance
from app.tools.base import tool_success, tool_error
from app.models.attendance import AttendanceLog


class TestGetMyAttendance:
    """Comprehensive tests for get_my_attendance() tool."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.name = "John Doe"
        user.enroll_id = 123
        return user

    def test_valid_employee(self, mock_db, mock_user):
        """Test get_my_attendance() with a valid employee."""
        from app.services.attendance_service import get_user_daily_logs, calculate_attendance
        
        # Mock database to return user
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock attendance service
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
                
                assert result["success"] is True
                assert result["data"]["employee"] == "John Doe"
                assert result["data"]["enroll_id"] == 123
                assert result["data"]["date"] == "2025-01-15"
                assert result["data"]["status"] == "Present"

    def test_employee_not_found(self, mock_db):
        """Test get_my_attendance() when employee is not found."""
        # Mock database to return None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=999,
            target_date="2025-01-15"
        )
        
        assert result["success"] is False
        assert "Employee not found" in result["error"]

    def test_invalid_date_format(self, mock_db, mock_user):
        """Test get_my_attendance() with invalid date format."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=123,
            target_date="invalid-date"
        )
        
        assert result["success"] is False
        assert "Invalid date format" in result["error"]

    def test_invalid_date_format_wrong_format(self, mock_db, mock_user):
        """Test get_my_attendance() with wrong date format."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=123,
            target_date="15-01-2025"  # DD-MM-YYYY instead of YYYY-MM-DD
        )
        
        assert result["success"] is False
        assert "Invalid date format" in result["error"]

    def test_attendance_with_no_logs(self, mock_db, mock_user):
        """Test attendance calculation when user has no logs for the day."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Absent",
            "in_time": None,
            "out_time": None,
            "total_hours": "0h 0m",
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
                
                assert result["success"] is True
                assert result["data"]["status"] == "Absent"
                assert result["data"]["in_time"] is None
                assert result["data"]["out_time"] is None

    def test_attendance_with_in_only(self, mock_db, mock_user):
        """Test attendance when user has only IN log (still working)."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Working",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": None,
            "total_hours": "4h 30m",
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
                
                assert result["success"] is True
                assert result["data"]["status"] == "Working"
                assert result["data"]["in_time"] is not None
                assert result["data"]["out_time"] is None

    def test_attendance_with_in_out(self, mock_db, mock_user):
        """Test attendance with complete IN → OUT session."""
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
                
                assert result["success"] is True
                assert result["data"]["status"] == "Present"
                assert result["data"]["in_time"] is not None
                assert result["data"]["out_time"] is not None
                assert result["data"]["total_hours"] == "9h 0m"

    def test_working_status_for_today(self, mock_db, mock_user):
        """Test Working status for today's open IN session."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock today's date
        today = date.today()
        
        mock_logs = []
        mock_attendance = {
            "status": "Working",
            "in_time": datetime.combine(today, time(9, 0)),
            "out_time": None,
            "total_hours": "3h 45m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date=today.isoformat()
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Working"
                assert result["data"]["out_time"] is None

    def test_late_attendance(self, mock_db, mock_user):
        """Test late attendance detection."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Late",
            "in_time": datetime(2025, 1, 15, 10, 45),  # After 10:30 threshold
            "out_time": datetime(2025, 1, 15, 18, 0),
            "total_hours": "7h 15m",
            "is_late": True,
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
                
                assert result["success"] is True
                assert result["data"]["status"] == "Late"
                assert result["data"]["is_late"] is True

    def test_overtime(self, mock_db, mock_user):
        """Test overtime detection (>9 hours)."""
        mock_db.query.return_value.filter.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 19, 30),
            "total_hours": "10h 30m",
            "is_late": False,
            "is_overtime": True,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                assert result["success"] is True
                assert result["data"]["is_overtime"] is True
                assert result["data"]["total_hours"] == "10h 30m"

    def test_early_out(self, mock_db, mock_user):
        """Test early-out detection (<8 hours)."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_logs = []
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 15, 30),
            "total_hours": "6h 30m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": True
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                assert result["success"] is True
                assert result["data"]["is_early_out"] is True
                assert result["data"]["total_hours"] == "6h 30m"

    def test_weekly_holiday_sunday(self, mock_db, mock_user):
        """Test weekly holiday detection for Sunday."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Sunday 2025-01-19
        mock_logs = []
        mock_attendance = {
            "status": "Holiday",
            "in_time": None,
            "out_time": None,
            "total_hours": "0h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-19"  # Sunday
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Holiday"

    def test_weekly_holiday_second_saturday(self, mock_db, mock_user):
        """Test weekly holiday detection for 2nd Saturday."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # 2nd Saturday 2025-01-11
        mock_logs = []
        mock_attendance = {
            "status": "Holiday",
            "in_time": None,
            "out_time": None,
            "total_hours": "0h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-11"  # 2nd Saturday
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Holiday"

    def test_weekly_holiday_fourth_saturday(self, mock_db, mock_user):
        """Test weekly holiday detection for 4th Saturday."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # 4th Saturday 2025-01-25
        mock_logs = []
        mock_attendance = {
            "status": "Holiday",
            "in_time": None,
            "out_time": None,
            "total_hours": "0h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_my_attendance(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-25"  # 4th Saturday
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Holiday"

    def test_date_object_input(self, mock_db, mock_user):
        """Test get_my_attendance() with date object instead of string."""
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
                    target_date=date(2025, 1, 15)  # date object
                )
                
                assert result["success"] is True
                assert result["data"]["date"] == "2025-01-15"

    def test_database_exception_handling(self, mock_db, mock_user):
        """Test that database exceptions are handled gracefully."""
        mock_db.query.return_value.filter.return_value.first.side_effect = Exception("Database connection failed")
        
        result = get_my_attendance(
            db=mock_db,
            enroll_id=123,
            target_date="2025-01-15"
        )
        
        assert result["success"] is False
        assert "Unable to retrieve attendance" in result["error"]

    def test_tool_exception_handling(self, mock_db, mock_user):
        """Test that tool execution exceptions are handled gracefully."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', side_effect=Exception("Service error")):
            result = get_my_attendance(
                db=mock_db,
                enroll_id=123,
                target_date="2025-01-15"
            )
            
            assert result["success"] is False
            assert "Unable to retrieve attendance" in result["error"]
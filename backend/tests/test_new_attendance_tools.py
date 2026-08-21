"""
Unit tests for new attendance tools: get_attendance_summary, get_attendance_logs, get_attendance_status.
"""
import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.tools.attendance_tools import (
    get_attendance_summary,
    get_attendance_logs,
    get_attendance_status,
)
from app.tools.base import tool_success, tool_error


class TestGetAttendanceSummary:
    """Tests for get_attendance_summary tool."""

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

    def test_single_day_summary(self, mock_db, mock_user):
        """Test get_attendance_summary for a single day."""
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
                result = get_attendance_summary(
                    db=mock_db,
                    enroll_id=123,
                    start_date="2025-01-15"
                )
                
                assert result["success"] is True
                assert result["data"]["employee"] == "John Doe"
                assert result["data"]["enroll_id"] == 123
                assert result["data"]["start_date"] == "2025-01-15"
                assert result["data"]["end_date"] == "2025-01-15"
                assert result["data"]["total_days"] == 1
                assert result["data"]["present_days"] == 1

    def test_date_range_summary(self, mock_db, mock_user):
        """Test get_attendance_summary for a date range."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock different attendance for different days
        def mock_calculate_attendance(logs, target_date):
            if target_date.day == 15:
                return {"status": "Present", "total_hours": "9h 0m"}
            elif target_date.day == 16:
                return {"status": "Absent", "total_hours": "0h 0m"}
            elif target_date.day == 17:
                return {"status": "Late", "total_hours": "8h 30m"}
            return {"status": "Absent", "total_hours": "0h 0m"}
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', side_effect=mock_calculate_attendance):
                result = get_attendance_summary(
                    db=mock_db,
                    enroll_id=123,
                    start_date="2025-01-15",
                    end_date="2025-01-17"
                )
                
                assert result["success"] is True
                assert result["data"]["total_days"] == 3
                assert result["data"]["present_days"] == 2  # Present + Late
                assert result["data"]["absent_days"] == 1
                assert result["data"]["late_days"] == 1

    def test_summary_with_holidays(self, mock_db, mock_user):
        """Test get_attendance_summary with holidays."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        def mock_calculate_attendance(logs, target_date):
            if target_date.day == 19:  # Sunday
                return {"status": "Holiday", "total_hours": "0h 0m"}
            return {"status": "Present", "total_hours": "9h 0m"}
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', side_effect=mock_calculate_attendance):
                result = get_attendance_summary(
                    db=mock_db,
                    enroll_id=123,
                    start_date="2025-01-18",
                    end_date="2025-01-19"
                )
                
                assert result["success"] is True
                assert result["data"]["holiday_days"] == 1
                assert result["data"]["present_days"] == 1

    def test_summary_employee_not_found(self, mock_db):
        """Test get_attendance_summary when employee not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = get_attendance_summary(
            db=mock_db,
            enroll_id=999,
            start_date="2025-01-15"
        )
        
        assert result["success"] is False
        assert "Employee not found" in result["error"]

    def test_summary_invalid_date_format(self, mock_db, mock_user):
        """Test get_attendance_summary with invalid date format."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_attendance_summary(
            db=mock_db,
            enroll_id=123,
            start_date="invalid-date"
        )
        
        assert result["success"] is False
        assert "Invalid date format" in result["error"]

    def test_summary_with_working_status(self, mock_db, mock_user):
        """Test get_attendance_summary with working status."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_attendance = {
            "status": "Working",
            "total_hours": "4h 30m"
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_attendance_summary(
                    db=mock_db,
                    enroll_id=123,
                    start_date="2025-01-15"
                )
                
                assert result["success"] is True
                assert result["data"]["working_days"] == 1
                assert result["data"]["present_days"] == 1  # Working counts as present


class TestGetAttendanceLogs:
    """Tests for get_attendance_logs tool."""

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

    @pytest.fixture
    def mock_logs(self):
        """Mock attendance logs."""
        logs = []
        for i in range(3):
            log = Mock()
            log.timestamp = datetime(2025, 1, 15, 9 + i, 0)
            log.in_out_state = "IN" if i % 2 == 0 else "OUT"
            log.device_name = f"Device_{i}"
            log.direction = "IN" if i % 2 == 0 else "OUT"
            logs.append(log)
        return logs

    def test_get_logs_success(self, mock_db, mock_user, mock_logs):
        """Test get_attendance_logs successfully returns logs."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            result = get_attendance_logs(
                db=mock_db,
                enroll_id=123,
                target_date="2025-01-15"
            )
            
            assert result["success"] is True
            assert result["data"]["employee"] == "John Doe"
            assert result["data"]["enroll_id"] == 123
            assert result["data"]["date"] == "2025-01-15"
            assert result["data"]["total_logs"] == 3
            assert len(result["data"]["logs"]) == 3

    def test_get_logs_empty(self, mock_db, mock_user):
        """Test get_attendance_logs with no logs."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            result = get_attendance_logs(
                db=mock_db,
                enroll_id=123,
                target_date="2025-01-15"
            )
            
            assert result["success"] is True
            assert result["data"]["total_logs"] == 0
            assert result["data"]["logs"] == []

    def test_get_logs_employee_not_found(self, mock_db):
        """Test get_attendance_logs when employee not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = get_attendance_logs(
            db=mock_db,
            enroll_id=999,
            target_date="2025-01-15"
        )
        
        assert result["success"] is False
        assert "Employee not found" in result["error"]

    def test_get_logs_invalid_date_format(self, mock_db, mock_user):
        """Test get_attendance_logs with invalid date format."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_attendance_logs(
            db=mock_db,
            enroll_id=123,
            target_date="invalid-date"
        )
        
        assert result["success"] is False
        assert "Invalid date format" in result["error"]

    def test_get_logs_formatting(self, mock_db, mock_user, mock_logs):
        """Test that logs are properly formatted."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=mock_logs):
            result = get_attendance_logs(
                db=mock_db,
                enroll_id=123,
                target_date="2025-01-15"
            )
            
            assert result["success"] is True
            logs = result["data"]["logs"]
            
            # Check that each log has expected fields
            for log in logs:
                assert "timestamp" in log
                assert "in_out_state" in log
                assert "device_name" in log
                assert "direction" in log


class TestGetAttendanceStatus:
    """Tests for get_attendance_status tool."""

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

    def test_get_status_with_date(self, mock_db, mock_user):
        """Test get_attendance_status with specific date."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 18, 0),
            "is_late": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_attendance_status(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Present"
                assert result["data"]["date"] == "2025-01-15"
                assert result["data"]["in_time"] == "2025-01-15T09:00:00"
                assert result["data"]["out_time"] == "2025-01-15T18:00:00"
                assert result["data"]["is_late"] is False

    def test_get_status_default_today(self, mock_db, mock_user):
        """Test get_attendance_status defaults to today when no date provided."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_attendance = {
            "status": "Working",
            "in_time": datetime.now().replace(hour=9, minute=0),
            "out_time": None,
            "is_late": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_attendance_status(
                    db=mock_db,
                    enroll_id=123
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Working"
                assert result["data"]["date"] == date.today().isoformat()

    def test_get_status_late(self, mock_db, mock_user):
        """Test get_attendance_status with late arrival."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_attendance = {
            "status": "Late",
            "in_time": datetime(2025, 1, 15, 10, 45),
            "out_time": datetime(2025, 1, 15, 18, 0),
            "is_late": True
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_attendance_status(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Late"
                assert result["data"]["is_late"] is True

    def test_get_status_absent(self, mock_db, mock_user):
        """Test get_attendance_status with absent status."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_attendance = {
            "status": "Absent",
            "in_time": None,
            "out_time": None,
            "is_late": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_attendance_status(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Absent"
                assert result["data"]["in_time"] is None
                assert result["data"]["out_time"] is None

    def test_get_status_holiday(self, mock_db, mock_user):
        """Test get_attendance_status with holiday status."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_attendance = {
            "status": "Holiday",
            "in_time": None,
            "out_time": None,
            "is_late": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_attendance_status(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-19"  # Sunday
                )
                
                assert result["success"] is True
                assert result["data"]["status"] == "Holiday"

    def test_get_status_employee_not_found(self, mock_db):
        """Test get_attendance_status when employee not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = get_attendance_status(
            db=mock_db,
            enroll_id=999,
            target_date="2025-01-15"
        )
        
        assert result["success"] is False
        assert "Employee not found" in result["error"]

    def test_get_status_invalid_date_format(self, mock_db, mock_user):
        """Test get_attendance_status with invalid date format."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_attendance_status(
            db=mock_db,
            enroll_id=123,
            target_date="invalid-date"
        )
        
        assert result["success"] is False
        assert "Invalid date format" in result["error"]

    def test_get_status_concise_output(self, mock_db, mock_user):
        """Test that get_attendance_status returns concise information."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        mock_attendance = {
            "status": "Present",
            "in_time": datetime(2025, 1, 15, 9, 0),
            "out_time": datetime(2025, 1, 15, 18, 0),
            "is_late": False
        }
        
        with patch('app.tools.attendance_tools.get_user_daily_logs', return_value=[]):
            with patch('app.tools.attendance_tools.calculate_attendance', return_value=mock_attendance):
                result = get_attendance_status(
                    db=mock_db,
                    enroll_id=123,
                    target_date="2025-01-15"
                )
                
                assert result["success"] is True
                data = result["data"]
                
                # Should have concise fields
                assert "status" in data
                assert "in_time" in data
                assert "out_time" in data
                assert "is_late" in data
                
                # Should not have verbose fields
                assert "total_hours" not in data
                assert "is_overtime" not in data
                assert "is_early_out" not in data
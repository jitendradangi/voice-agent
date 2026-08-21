from datetime import date, datetime, timedelta
import logging

from sqlalchemy.orm import Session
from app.tools.base import tool_success, tool_error

from app.models.user import User
from app.models.attendance import AttendanceLog
from app.services.attendance_service import (
    get_user_daily_logs,
    calculate_attendance,
)

logger = logging.getLogger(__name__)


def get_my_attendance(
    db: Session,
    enroll_id: int,
    target_date: date | str,
) -> dict:

    try:
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)

        user = (
            db.query(User)
            .filter(User.enroll_id == enroll_id)
            .first()
        )

        if not user:
            return tool_error("Employee not found.")

        logs = get_user_daily_logs(
            db=db,
            enroll_id=enroll_id,
            target_date=target_date,
        )

        attendance = calculate_attendance(
            logs=logs,
            target_date=target_date,
        )

        return tool_success({
            "employee": user.name,
            "enroll_id": user.enroll_id,
            "date": target_date.isoformat(),
            **attendance,
        })

    except ValueError:
        return tool_error(
            "Invalid date format. Use YYYY-MM-DD."
        )

    except Exception:
        logger.exception(
            "Failed to fetch attendance for enroll_id=%s",
            enroll_id,
        )

        return tool_error(
            "Unable to retrieve attendance right now."
        )


def get_attendance_summary(
    db: Session,
    enroll_id: int,
    start_date: date | str,
    end_date: date | str | None = None,
) -> dict:
    """
    Get attendance summary for a date range.
    If end_date is not provided, returns summary for start_date only.
    """
    try:
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        
        if end_date is not None and isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        
        # If only start_date provided, use it as end_date too (single day)
        if end_date is None:
            end_date = start_date
        
        user = (
            db.query(User)
            .filter(User.enroll_id == enroll_id)
            .first()
        )

        if not user:
            return tool_error("Employee not found.")

        # Calculate summary for the date range
        current_date = start_date
        summary_data = {
            "employee": user.name,
            "enroll_id": user.enroll_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_days": 0,
            "present_days": 0,
            "absent_days": 0,
            "late_days": 0,
            "holiday_days": 0,
            "working_days": 0,
            "total_hours": "0h 0m",
        }

        total_seconds = 0

        while current_date <= end_date:
            logs = get_user_daily_logs(
                db=db,
                enroll_id=enroll_id,
                target_date=current_date,
            )

            attendance = calculate_attendance(
                logs=logs,
                target_date=current_date,
            )

            summary_data["total_days"] += 1

            status = attendance.get("status", "Absent")
            
            if status == "Present":
                summary_data["present_days"] += 1
            elif status == "Absent":
                summary_data["absent_days"] += 1
            elif status == "Late":
                summary_data["late_days"] += 1
                summary_data["present_days"] += 1  # Late is still present
            elif status == "Holiday":
                summary_data["holiday_days"] += 1
            elif status == "Working":
                summary_data["working_days"] += 1
                summary_data["present_days"] += 1  # Working is still present

            # Add hours (parse "Xh Ym" format)
            total_hours_str = attendance.get("total_hours", "0h 0m")
            if "h" in total_hours_str:
                hours_part = total_hours_str.split("h")[0].strip()
                try:
                    total_seconds += int(hours_part) * 3600
                except ValueError:
                    pass

            current_date += timedelta(days=1)  # Add one day

        # Format total hours
        total_hours = total_seconds // 3600
        total_minutes = (total_seconds % 3600) // 60
        summary_data["total_hours"] = f"{total_hours}h {total_minutes}m"

        return tool_success(summary_data)

    except ValueError:
        return tool_error(
            "Invalid date format. Use YYYY-MM-DD."
        )

    except Exception:
        logger.exception(
            "Failed to fetch attendance summary for enroll_id=%s",
            enroll_id,
        )

        return tool_error(
            "Unable to retrieve attendance summary right now."
        )


def get_attendance_logs(
    db: Session,
    enroll_id: int,
    target_date: date | str,
) -> dict:
    """
    Get raw IN/OUT attendance logs for a specific date.
    Returns the actual attendance events for the authenticated user.
    """
    try:
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)

        user = (
            db.query(User)
            .filter(User.enroll_id == enroll_id)
            .first()
        )

        if not user:
            return tool_error("Employee not found.")

        logs = get_user_daily_logs(
            db=db,
            enroll_id=enroll_id,
            target_date=target_date,
        )

        # Format logs for user-friendly output
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "in_out_state": log.in_out_state,
                "device_name": getattr(log, 'device_name', None),
                "direction": getattr(log, 'direction', None),
            })

        return tool_success({
            "employee": user.name,
            "enroll_id": user.enroll_id,
            "date": target_date.isoformat(),
            "total_logs": len(formatted_logs),
            "logs": formatted_logs,
        })

    except ValueError:
        return tool_error(
            "Invalid date format. Use YYYY-MM-DD."
        )

    except Exception:
        logger.exception(
            "Failed to fetch attendance logs for enroll_id=%s",
            enroll_id,
        )

        return tool_error(
            "Unable to retrieve attendance logs right now."
        )


def get_attendance_status(
    db: Session,
    enroll_id: int,
    target_date: date | str | None = None,
) -> dict:
    """
    Get concise current attendance status.
    If target_date is not provided, uses today's date.
    Returns status like Present, Working, Absent, Late, or Holiday.
    """
    try:
        # Use today if no date provided
        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)

        user = (
            db.query(User)
            .filter(User.enroll_id == enroll_id)
            .first()
        )

        if not user:
            return tool_error("Employee not found.")

        logs = get_user_daily_logs(
            db=db,
            enroll_id=enroll_id,
            target_date=target_date,
        )

        attendance = calculate_attendance(
            logs=logs,
            target_date=target_date,
        )

        # Return concise status information
        return tool_success({
            "employee": user.name,
            "enroll_id": user.enroll_id,
            "date": target_date.isoformat(),
            "status": attendance.get("status", "Unknown"),
            "in_time": attendance.get("in_time").isoformat() if attendance.get("in_time") else None,
            "out_time": attendance.get("out_time").isoformat() if attendance.get("out_time") else None,
            "is_late": attendance.get("is_late", False),
        })

    except ValueError:
        return tool_error(
            "Invalid date format. Use YYYY-MM-DD."
        )

    except Exception:
        logger.exception(
            "Failed to fetch attendance status for enroll_id=%s",
            enroll_id,
        )

        return tool_error(
            "Unable to retrieve attendance status right now."
        )
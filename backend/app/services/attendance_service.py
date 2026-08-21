from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceLog

IST = timezone(timedelta(hours=5, minutes=30))

LATE_THRESHOLD = time(10, 30)




def get_user_daily_logs(
    db: Session,
    enroll_id: int,
    target_date: date
) -> list[AttendanceLog]:

    start_of_day = datetime.combine(
        target_date,
        time.min
    )

    end_of_day = datetime.combine(
        target_date,
        time.max
    )

    return (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.enroll_id == enroll_id,
            AttendanceLog.timestamp >= start_of_day,
            AttendanceLog.timestamp <= end_of_day
        )
        .order_by(AttendanceLog.timestamp)
        .all()
    )

def format_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return f"{hours}h {minutes}m"

def is_weekly_off(target_date: date) -> bool:
    # Sunday
    if target_date.weekday() == 6:
        return True

    # 2nd and 4th Saturday
    if target_date.weekday() == 5:
        saturday_count = 0
        current = date(
            target_date.year,
            target_date.month,
            1
        )

        while current <= target_date:
            if current.weekday() == 5:
                saturday_count += 1

            current += timedelta(days=1)

        return saturday_count in (2, 4)

    return False

def calculate_attendance(
    logs: list[AttendanceLog],
    target_date: date
) -> dict:

    if is_weekly_off(target_date):
        return {
            "status": "Holiday",
            "in_time": None,
            "out_time": None,
            "total_hours": "0h 0m",
            "is_late": False,
            "is_overtime": False,
            "is_early_out": False,
        }

    sorted_logs = sorted(
        logs,
        key=lambda log: log.timestamp
    )

    in_time = None
    out_time = None
    total_seconds = 0

    # First IN
    for log in sorted_logs:
        if log.in_out_state == "IN":
            in_time = log.timestamp
            break

    # Calculate IN → OUT sessions
    current_in = None
    last_out = None

    for log in sorted_logs:

        if log.in_out_state == "IN":

            if current_in is None:
                current_in = log.timestamp

        elif log.in_out_state == "OUT":

            if current_in is not None:
                total_seconds += (
                    log.timestamp - current_in
                ).total_seconds()

                current_in = None

            last_out = log.timestamp

    # Still working today
    if (
        current_in is not None
        and target_date == datetime.now(IST).date()
    ):
        now = datetime.now(IST).replace(tzinfo=None)

        duration = (
            now - current_in
        ).total_seconds()

        if duration > 0:
            total_seconds += duration

    # Status
    if not in_time:
        status = "Absent"
    elif (
        sorted_logs
        and sorted_logs[-1].in_out_state == "IN"
        and target_date == datetime.now(IST).date()
    ):
        status = "Working"
        out_time = None
    else:
        out_time = last_out

        if in_time.time() > LATE_THRESHOLD:
            status = "Late"
        else:
            status = "Present"

    total_hours = format_duration(
        timedelta(seconds=total_seconds)
    )

    total_hours_float = total_seconds / 3600

    is_late = (
        in_time is not None
        and in_time.time() > LATE_THRESHOLD
    )

    is_overtime = total_hours_float > 9

    is_early_out = (
        status not in ("Absent", "Working")
        and total_hours_float < 8
    )

    return {
        "status": status,
        "in_time": in_time,
        "out_time": out_time,
        "total_hours": total_hours,
        "is_late": is_late,
        "is_overtime": is_overtime,
        "is_early_out": is_early_out,
    }
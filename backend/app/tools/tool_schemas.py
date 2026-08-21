"""
Tool schemas for LLM function declarations.
This module contains schema definitions that are independent of any LLM provider.
Each schema defines the interface for a tool that can be called by the LLM.
"""

# Attendance tool schemas
GET_MY_ATTENDANCE_SCHEMA = {
    "name": "get_my_attendance",
    "description": (
        "Get the current user's attendance for a specific date. "
        "The date must be provided in YYYY-MM-DD format. "
        "Use today's date from the system context when the user says "
        "'today', and calculate the previous calendar date when the "
        "user says 'yesterday'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format"
            }
        },
        "required": ["target_date"]
    }
}

GET_ATTENDANCE_SUMMARY_SCHEMA = {
    "name": "get_attendance_summary",
    "description": (
        "Get a summary of attendance for a date range. "
        "Returns total days, present days, absent days, late days, holiday days, "
        "working days, and total hours worked. "
        "If only start_date is provided, returns summary for that single day. "
        "Dates must be in YYYY-MM-DD format."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format"
            },
            "end_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format (optional, defaults to start_date)"
            }
        },
        "required": ["start_date"]
    }
}

GET_ATTENDANCE_LOGS_SCHEMA = {
    "name": "get_attendance_logs",
    "description": (
        "Get the raw IN/OUT attendance log events for a specific date. "
        "Returns detailed information about each attendance event including timestamps, "
        "IN/OUT state, device name, and direction. "
        "Date must be in YYYY-MM-DD format."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format"
            }
        },
        "required": ["target_date"]
    }
}

GET_ATTENDANCE_STATUS_SCHEMA = {
    "name": "get_attendance_status",
    "description": (
        "Get a concise current attendance status. "
        "Returns the current status such as Present, Working, Absent, Late, or Holiday. "
        "If no date is provided, uses today's date. "
        "Also includes check-in time, check-out time, and whether the arrival was late."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format (optional, defaults to today)"
            }
        },
        "required": []
    }
}

# Dictionary of all tool schemas for easy access
ALL_TOOL_SCHEMAS = {
    "get_my_attendance": GET_MY_ATTENDANCE_SCHEMA,
    "get_attendance_summary": GET_ATTENDANCE_SUMMARY_SCHEMA,
    "get_attendance_logs": GET_ATTENDANCE_LOGS_SCHEMA,
    "get_attendance_status": GET_ATTENDANCE_STATUS_SCHEMA,
}

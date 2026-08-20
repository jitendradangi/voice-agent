# Voice Agent Tools

## 1. get_my_attendance

Purpose:
Get attendance information for the logged-in employee.

Input:
- user_id
- date or date range

Output:
- employee name
- date
- status
- check-in time
- check-out time


## 2. get_attendance_summary

Purpose:
Get attendance statistics for an employee.

Input:
- user_id
- start_date
- end_date

Output:
- present count
- absent count
- late count


## 3. get_absent_employees

Purpose:
Get employees who were absent on a particular date.

Input:
- date

Output:
- list of absent employees


## 4. get_leave_requests

Purpose:
Get leave requests for an employee.

Input:
- user_id
- status (optional)

Output:
- leave type
- start date
- end date
- reason
- status


## 5. get_my_tasks

Purpose:
Get tasks assigned to the logged-in employee.

Input:
- user_id
- status (optional)

Output:
- task title
- project
- status
- priority
- due date


## 6. get_projects

Purpose:
Get projects, optionally filtered by status.

Input:
- status (optional)

Output:
- project name
- status
- start date
- deadline
- manager


## 7. get_pending_leave_requests

Purpose:
Get pending leave requests for admin.

Input:
- optional date range

Output:
- employee
- leave type
- start date
- end date
- status
# Attendance Business Rules

## Late

An employee is considered late if the first IN time is after 10:30 AM.

## Absent

If an employee has no attendance entry for the day,
the status is Absent.

## Working

If the employee's latest attendance event is IN and the date
is today, the employee is considered Working.

## Present

If the employee has an IN entry and is not currently Working,
the employee is considered Present unless another status applies.

## Holiday

The following are treated as holidays:

- Republic Day
- Independence Day
- Gandhi Jayanti
- New Year
- Christmas
- Holi
- Rakshabandhan
- Dussehra
- Diwali - Dhanteras
- Diwali (Lakshmi Puja)
- Diwali - Govardhan Puja

Weekly offs:

- Every Sunday
- 2nd Saturday
- 4th Saturday

## Working Hours

Working duration is calculated from valid IN/OUT pairs.

If an employee is currently checked in today,
the duration continues until the current time.

## Overtime

More than 9 working hours is considered overtime.

## Early Out

Less than 8 working hours is considered early out,
unless the employee is Absent or currently Working.
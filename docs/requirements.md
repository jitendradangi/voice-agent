# Voice Agent Requirements

## Project Goal

Build a reusable AI Voice Agent that can interact with the existing
Attendance Portal database through application-specific tools.

The Voice Agent will be developed as a separate backend/project.

## MVP

The agent should:

1. Accept user voice input.
2. Convert speech to text.
3. Understand the user's request.
4. Select the appropriate tool.
5. Retrieve information from the Attendance Portal MySQL database.
6. Generate a natural-language response.
7. Convert the response to speech.
8. Maintain conversation context.

## Users

### Employee

- View own attendance
- View attendance summary
- View leave requests
- View assigned tasks
- View projects

### Admin

- View attendance summary
- View absent employees
- View pending leave requests
- View projects

## Database

The existing Attendance Portal MySQL database will be used as
the data source for the demo.

The Voice Agent will not create a duplicate database.

## Architecture Principle

The Agent Core must remain reusable.

Application-specific database logic will be implemented through
tools and services.

If another application is integrated later, the application-specific
tools/data-access layer can be replaced without rebuilding the
entire Agent Core.
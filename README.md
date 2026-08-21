# Voice Agent - Attendance Query System

A voice-enabled AI agent for querying attendance data from the Attendance Portal system. The system uses Google's Gemini AI to understand natural language queries and retrieve attendance information through a secure, well-architected API.

## Overview

This project provides a conversational interface for employees to query their attendance data using natural language. The system integrates with an existing Attendance Portal MySQL database and uses Google's Gemini AI for intelligent query understanding and response generation.

## Architecture

The system follows a clean layered architecture:

```
API Layer (FastAPI)
    ↓
Agent Layer (Conversation orchestration)
    ↓
LLM Service Abstraction (Provider-agnostic interface)
    ↓
Gemini LLM Service (Google Gemini implementation)
    ↓
Tool Registry (Centralized tool management)
    ↓
Application Tools (Attendance functions)
    ↓
Attendance Service (Business logic)
    ↓
Attendance Portal MySQL (Data layer)
```

### Key Components

- **API Layer**: FastAPI-based REST API for chat interactions
- **Agent**: Orchestrates conversation flow between user and LLM
- **LLM Service**: Abstraction layer supporting multiple LLM providers
- **Tool Registry**: Secure, centralized tool management with validation
- **Attendance Tools**: Domain-specific tools for attendance queries
- **Attendance Service**: Business logic for attendance calculations

## Features

### Current Capabilities

- **Natural Language Queries**: Ask questions about attendance in plain English
- **Multiple Query Types**:
  - Daily attendance details
  - Attendance summaries for date ranges
  - Raw attendance logs (IN/OUT events)
  - Current attendance status
- **Intelligent Date Handling**: Understands "today", "yesterday", and date ranges
- **Security**: Enforces user context and prevents unauthorized data access
- **Error Handling**: Graceful error handling with user-friendly messages
- **Comprehensive Testing**: 133+ tests covering security, reliability, and edge cases

### Supported Queries

- "What was my attendance today?"
- "Show me my attendance for this week"
- "Get my attendance logs for January 15th"
- "What's my current attendance status?"
- "How many hours did I work last week?"

## Installation

### Prerequisites

- Python 3.14+
- MySQL database (Attendance Portal)
- Google Gemini API key

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd voice-agent/backend
```

2. **Create virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database connection**:
```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/attendance_portal
GEMINI_API_KEY=your_gemini_api_key_here
```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/attendance_portal

# LLM Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: STT/TTS (future features)
STT_API_KEY=
TTS_API_KEY=

# Application Settings
APP_NAME=Voice AI Agent
APP_ENV=development
DEBUG=True
```

## Usage

### Running the Server

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### Chat Endpoint
```bash
POST /api/v1/chat
Content-Type: application/json

{
  "message": "What was my attendance today?",
  "history": []
}
```

#### Test Attendance Endpoint (Development Only)
```bash
GET /api/v1/chat/test-attendance/{enroll_id}?target_date=2025-01-15
```

### Example Usage

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "What was my attendance on January 15th?",
        "history": []
    }
)

print(response.json())
```

## Testing

### Running Tests

```bash
cd backend
pytest tests/ -v
```

### Test Coverage

The project includes comprehensive test coverage:

- **133 tests** covering all aspects of the system
- **Security tests**: Tool validation, enroll_id enforcement, authorization
- **Reliability tests**: Error handling, edge cases, malformed data
- **Integration tests**: End-to-end conversation flows
- **Production readiness tests**: Serialization, error message safety

### Test Categories

- `test_agent_loop.py`: Agent conversation logic
- `test_agent_mocked_gemini.py`: Agent with mocked Gemini responses
- `test_attendance_tool.py`: Individual attendance tool tests
- `test_integration.py`: End-to-end integration tests
- `test_new_attendance_tools.py`: Additional attendance tools
- `test_tool_format.py`: Tool response format validation
- `test_tool_registry.py`: Tool registry and security
- `test_user_context.py`: UserContext security and enrollment injection
- `test_production_readiness.py`: Production edge cases and security

## Project Structure

```
voice-agent/
├── backend/
│   ├── app/
│   │   ├── agent/              # Agent and conversation logic
│   │   │   ├── agent.py
│   │   │   └── prompts.py
│   │   ├── api/                # FastAPI endpoints
│   │   │   └── v1/
│   │   │       └── chat.py
│   │   ├── core/               # Core configuration and utilities
│   │   │   ├── config.py
│   │   │   └── user_context.py
│   │   ├── database/           # Database connection and models
│   │   │   ├── connection.py
│   │   │   ├── dependencies.py
│   │   │   └── models/
│   │   ├── services/           # Business logic services
│   │   │   ├── attendance_service.py
│   │   │   ├── llm_service.py
│   │   │   └── llm/
│   │   │       ├── base.py
│   │   │       ├── gemini.py
│   │   │       └── mock.py
│   │   ├── tools/              # Tool registry and implementations
│   │   │   ├── attendance_tools.py
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   └── tool_schemas.py
│   │   ├── schemas/            # Pydantic schemas
│   │   │   └── agent.py
│   │   └── main.py             # FastAPI application entry point
│   ├── tests/                  # Comprehensive test suite
│   │   ├── test_agent_loop.py
│   │   ├── test_agent_mocked_gemini.py
│   │   ├── test_attendance_tool.py
│   │   ├── test_integration.py
│   │   ├── test_new_attendance_tools.py
│   │   ├── test_production_readiness.py
│   │   ├── test_tool_format.py
│   │   ├── test_tool_registry.py
│   │   └── test_user_context.py
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

## Development Guidelines

### Adding New Tools

1. **Implement the tool function** in `app/tools/`:
```python
def my_new_tool(db: Session, enroll_id: int, param: str) -> dict:
    # Tool implementation
    return tool_success({"result": "data"})
```

2. **Define the schema** in `app/tools/tool_schemas.py`:
```python
MY_NEW_TOOL_SCHEMA = {
    "name": "my_new_tool",
    "description": "Tool description",
    "parameters": {
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        },
        "required": ["param"]
    }
}
```

3. **Register the tool** in `app/tools/registry.py`:
```python
tool_registry.register(
    name="my_new_tool",
    function=my_new_tool,
    schema=MY_NEW_TOOL_SCHEMA,
    requires_enroll_id=True,
    description="Tool description"
)
```

4. **Add tests** for the new tool

### Code Quality Standards

- **Type Hints**: All functions must have proper type hints
- **Error Handling**: Use `tool_success()` and `tool_error()` for consistent responses
- **Logging**: Use Python logging instead of print statements
- **Security**: Never expose stack traces or database internals
- **Testing**: Write comprehensive tests for all new features

## Security Considerations

### Implemented Security Measures

- **Tool Registry Validation**: Only registered tools can be executed
- **UserContext Enforcement**: LLM cannot override enroll_id
- **No Arbitrary Execution**: Prevents execution of arbitrary Python functions
- **Error Message Safety**: No stack traces or internals exposed to users
- **API Key Management**: Keys stored in environment variables
- **Input Validation**: All tool inputs are validated

### Security Best Practices

- Never commit API keys or secrets to version control
- Use environment variables for all sensitive configuration
- Implement proper authentication/authorization for production
- Regular security audits of dependencies
- Monitor and log suspicious activity

## Known Limitations

### Current Limitations

1. **Authentication**: Uses hardcoded UserContext for demo purposes
2. **Datetime Serialization**: Tool results with datetime objects aren't JSON serializable
3. **Single LLM Provider**: Currently only supports Google Gemini
4. **Synchronous Database**: Database operations are synchronous
5. **Test Endpoints**: Development endpoints should be removed in production

### Planned Improvements

- Implement proper authentication/authorization system
- Add datetime-to-string conversion for JSON compatibility
- Support multiple LLM providers (OpenAI, Anthropic, etc.)
- Implement async database operations
- Add comprehensive monitoring and logging

## API Documentation

Once the server is running, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Troubleshooting

### Common Issues

**Database Connection Failed**:
- Verify DATABASE_URL in `.env`
- Check MySQL server is running
- Ensure database credentials are correct

**Gemini API Errors**:
- Verify GEMINI_API_KEY is set correctly
- Check API key has appropriate permissions
- Ensure you have API quota available

**Import Errors**:
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Check Python version compatibility

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Specify your license here]

## Contact

For questions or support, please contact [your contact information].

---

**Note**: This project is currently in active development. Some features are still being refined for production use.

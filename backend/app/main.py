from fastapi import FastAPI
from app.api.v1.chat import router as chat_router

from app.core.config import settings
from sqlalchemy import text
from app.database.connection import engine


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.DEBUG
)

app.include_router(
    chat_router,
    prefix="/api/v1"
)


@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} Backend is running",
        "environment": settings.APP_ENV
    }

@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "Attendance Portal MySQL"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
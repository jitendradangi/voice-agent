from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from app.database.connection import Base


class AttendanceLog(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    enroll_id = Column(Integer, index=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    event_code = Column(Integer)
    verification_mode = Column(Integer)
    in_out_state = Column(String(10))
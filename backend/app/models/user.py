from sqlalchemy import Column, Integer, String, Date, DateTime

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    enroll_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    dob = Column(Date, nullable=True)
    position = Column(String(255), nullable=True)
    photo_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=True)
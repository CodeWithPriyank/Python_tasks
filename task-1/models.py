from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.sql import func
from database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False, index=True)
    short_code = Column(String(8), unique=True, nullable=False, index=True)
    custom_alias = Column(String(50), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import validators


class URLCreate(BaseModel):
    url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not validators.url(v):
            raise ValueError("Invalid URL format")
        return v

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) < 3 or len(v) > 50:
                raise ValueError("Custom alias must be 3-50 characters")
            if not v.isalnum():
                raise ValueError("Custom alias must be alphanumeric")
        return v


class URLResponse(BaseModel):
    short_url: str
    original_url: str
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


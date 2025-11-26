import string
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import engine, get_db, Base
from models import URL
from schemas import URLCreate, URLResponse

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7


def generate_short_code(length: int = CODE_LENGTH) -> str:
    """Generate a random short code of specified length (6-8 chars)."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def get_unique_code(db: Session, max_attempts: int = 10) -> str:
    """Generate a unique short code, handling collisions."""
    for _ in range(max_attempts):
        code = generate_short_code()
        if not db.query(URL).filter(URL.short_code == code).first():
            return code
    raise HTTPException(status_code=500, detail="Failed to generate unique code")


@app.post("/shorten", response_model=URLResponse)
def shorten_url(url_data: URLCreate, request: Request, db: Session = Depends(get_db)):
    """
    Create a shortened URL.
    
    - Optionally specify a custom_alias
    - Optionally specify an expires_at datetime
    - Avoids duplicates for the same URL (returns existing if found)
    """
    # Check for existing URL (avoid duplicates)
    existing = db.query(URL).filter(
        URL.original_url == url_data.url,
        or_(URL.expires_at.is_(None), URL.expires_at > datetime.now(timezone.utc))
    ).first()
    
    if existing and not url_data.custom_alias:
        base_url = str(request.base_url).rstrip("/")
        return URLResponse(
            short_url=f"{base_url}/{existing.short_code}",
            original_url=existing.original_url,
            expires_at=existing.expires_at
        )
    
    # Check if custom alias already exists
    if url_data.custom_alias:
        alias_exists = db.query(URL).filter(
            or_(URL.custom_alias == url_data.custom_alias, 
                URL.short_code == url_data.custom_alias)
        ).first()
        if alias_exists:
            raise HTTPException(status_code=400, detail="Custom alias already in use")
    
    # Generate unique short code
    short_code = get_unique_code(db)
    
    # Create new URL entry
    db_url = URL(
        original_url=url_data.url,
        short_code=short_code,
        custom_alias=url_data.custom_alias,
        expires_at=url_data.expires_at
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    
    base_url = str(request.base_url).rstrip("/")
    
    return URLResponse(
        short_url=f"{base_url}/{db_url.short_code}",
        original_url=db_url.original_url,
        expires_at=db_url.expires_at
    )


@app.get("/{code}")
def redirect_to_url(code: str, db: Session = Depends(get_db)):
    """
    Redirect to the original URL using the short code or custom alias.
    """
    # Look up by short_code or custom_alias
    url_entry = db.query(URL).filter(
        or_(URL.short_code == code, URL.custom_alias == code)
    ).first()
    
    if not url_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # Check expiration
    if url_entry.expires_at:
        now = datetime.now(timezone.utc)
        expires = url_entry.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=410, detail="URL has expired")
    
    return RedirectResponse(url=url_entry.original_url, status_code=307)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


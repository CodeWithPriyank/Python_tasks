# URL Shortener API

A simple URL shortener built with FastAPI and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

API available at `http://localhost:8000`

## Endpoints

### POST /shorten
Create a shortened URL.

**Request Body:**
```json
{
  "url": "https://example.com/very/long/url",
  "custom_alias": "mylink",      // optional
  "expires_at": "2025-12-31T23:59:59"  // optional
}
```

**Response:**
```json
{
  "short_url": "http://localhost:8000/abc1234",
  "original_url": "https://example.com/very/long/url",
  "expires_at": null
}
```

### GET /{code}
Redirects to the original URL.

## Features
- 7-character random codes (alphanumeric)
- Custom aliases support
- URL expiration
- Collision handling
- Duplicate URL detection
- URL validation

## API Docs
Visit `http://localhost:8000/docs` for interactive Swagger documentation.


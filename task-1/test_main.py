import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

from database import Base, get_db
from main import app

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_url_shortener.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestShortenURL:
    def test_shorten_valid_url(self):
        response = client.post("/shorten", json={"url": "https://www.google.com"})
        assert response.status_code == 200
        data = response.json()
        assert "short_url" in data
        assert data["original_url"] == "https://www.google.com"

    def test_shorten_with_custom_alias(self):
        response = client.post("/shorten", json={
            "url": "https://www.github.com",
            "custom_alias": "github"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == "https://www.github.com"

    def test_shorten_with_expiration(self):
        future_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        response = client.post("/shorten", json={
            "url": "https://www.example.com",
            "expires_at": future_date
        })
        assert response.status_code == 200
        assert response.json()["expires_at"] is not None

    def test_shorten_invalid_url(self):
        response = client.post("/shorten", json={"url": "not-a-valid-url"})
        assert response.status_code == 422

    def test_duplicate_custom_alias(self):
        client.post("/shorten", json={
            "url": "https://www.test1.com",
            "custom_alias": "myalias"
        })
        response = client.post("/shorten", json={
            "url": "https://www.test2.com",
            "custom_alias": "myalias"
        })
        assert response.status_code == 400

    def test_custom_alias_too_short(self):
        response = client.post("/shorten", json={
            "url": "https://www.example.com",
            "custom_alias": "ab"
        })
        assert response.status_code == 422


class TestRedirect:
    def test_redirect_valid_code(self):
        # Create a shortened URL first
        create_response = client.post("/shorten", json={"url": "https://www.python.org"})
        short_url = create_response.json()["short_url"]
        code = short_url.split("/")[-1]
        
        # Test redirect (don't follow redirects)
        response = client.get(f"/{code}", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "https://www.python.org"

    def test_redirect_custom_alias(self):
        client.post("/shorten", json={
            "url": "https://www.fastapi.tiangolo.com",
            "custom_alias": "fastapi"
        })
        response = client.get("/fastapi", follow_redirects=False)
        assert response.status_code == 307

    def test_redirect_not_found(self):
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_redirect_expired_url(self):
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        create_response = client.post("/shorten", json={
            "url": "https://www.expired.com",
            "expires_at": past_date
        })
        short_url = create_response.json()["short_url"]
        code = short_url.split("/")[-1]
        
        response = client.get(f"/{code}")
        assert response.status_code == 410


class TestStats:
    def test_get_stats(self):
        # Create URL
        create_response = client.post("/shorten", json={"url": "https://www.stats-test.com"})
        code = create_response.json()["short_url"].split("/")[-1]
        
        # Access it a few times
        client.get(f"/{code}", follow_redirects=False)
        client.get(f"/{code}", follow_redirects=False)
        
        # Check stats
        stats_response = client.get(f"/stats/{code}")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["redirect_count"] == 2
        assert stats["created_at"] is not None
        assert stats["last_accessed_at"] is not None

    def test_stats_not_found(self):
        response = client.get("/stats/nonexistent")
        assert response.status_code == 404


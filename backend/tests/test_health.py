from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_health_endpoint_returns_expected_contract():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "trailmate-ai-api"

def test_root_points_to_api_docs_and_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"
    assert response.json()["health"] == "/health"

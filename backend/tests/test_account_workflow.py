import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app

@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    import app.main as main
    original_env = main.APP_ENV
    main.APP_ENV = "test"
    with TestClient(app) as test_client:
        yield test_client
    main.APP_ENV = original_env
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register_and_verify(client):
    result = client.post("/api/v1/auth/register", json={
        "full_name": "Trail Tester", "username": "TrailTester", "email": "TRAIL@example.com",
        "password": "TrailPass123", "confirm_password": "TrailPass123", "consent": True,
    })
    assert result.status_code == 201, result.text
    code = result.json()["development_verification_code"]
    verified = client.post("/api/v1/auth/verify-email", json={"email": "trail@example.com", "code": code})
    assert verified.status_code == 200, verified.text


def test_registration_verification_signin_profile_persists(client):
    register_and_verify(client)
    signed_in = client.post("/api/v1/auth/sign-in", json={"identifier": "trailtester", "password": "TrailPass123"})
    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json()["user"]["email_verified"] is True
    saved = client.put("/api/v1/profile", json={
        "preferred_language": "English", "city": "Mangaluru", "region": "Karnataka",
        "travel_interests": ["Trekking", "Camping"], "preferred_budget": "moderate",
        "preferred_duration_days": 3, "onboarding_complete": True,
    })
    assert saved.status_code == 200, saved.text
    assert saved.json()["onboarding_complete"] is True
    assert client.get("/api/v1/profile").json()["city"] == "Mangaluru"
    assert client.get("/api/v1/dashboard").json()["onboarding_complete"] is True


def test_duplicate_normalized_email_and_username_rejected(client):
    register_and_verify(client)
    duplicate_email = client.post("/api/v1/auth/register", json={
        "full_name": "Another Person", "username": "anotheruser", "email": "trail@example.com",
        "password": "OtherPass123", "confirm_password": "OtherPass123", "consent": True,
    })
    assert duplicate_email.status_code == 409
    duplicate_username = client.post("/api/v1/auth/register", json={
        "full_name": "Another Person", "username": "TRAILTESTER", "email": "other@example.com",
        "password": "OtherPass123", "confirm_password": "OtherPass123", "consent": True,
    })
    assert duplicate_username.status_code == 409


def test_profile_and_dashboard_require_authentication(client):
    assert client.get("/api/v1/profile").status_code == 401
    assert client.put("/api/v1/profile", json={}).status_code == 401
    assert client.get("/api/v1/dashboard").status_code == 401


def test_signin_requires_verified_email_and_rejects_wrong_password(client):
    result = client.post("/api/v1/auth/register", json={
        "full_name": "Unverified User", "username": "unverified", "email": "u@example.com",
        "password": "StrongPass123", "confirm_password": "StrongPass123", "consent": True,
    })
    assert result.status_code == 201
    assert client.post("/api/v1/auth/sign-in", json={"identifier": "u@example.com", "password": "StrongPass123"}).status_code == 403
    code = result.json()["development_verification_code"]
    client.post("/api/v1/auth/verify-email", json={"email": "u@example.com", "code": code})
    assert client.post("/api/v1/auth/sign-in", json={"identifier": "u@example.com", "password": "WrongPass123"}).status_code == 401


def test_bad_verification_code_is_rejected(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Code User", "username": "codeuser", "email": "code@example.com",
        "password": "StrongPass123", "confirm_password": "StrongPass123", "consent": True,
    })
    response = client.post("/api/v1/auth/verify-email", json={"email": "code@example.com", "code": "000000"})
    assert response.status_code == 400


def test_registration_validates_consent_and_password_match(client):
    payload = {"full_name":"Invalid User", "username":"invaliduser", "email":"invalid@example.com",
               "password":"StrongPass123", "confirm_password":"NotSame123", "consent":True}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 422
    payload["confirm_password"] = payload["password"]
    payload["consent"] = False
    assert client.post("/api/v1/auth/register", json=payload).status_code == 422


def test_signout_invalidates_session(client):
    register_and_verify(client)
    assert client.post("/api/v1/auth/sign-in", json={"identifier":"trail@example.com", "password":"TrailPass123"}).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/sign-out").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_password_reset_changes_password_and_invalidates_sessions(client):
    register_and_verify(client)
    signed_in = client.post("/api/v1/auth/sign-in", json={"identifier": "trail@example.com", "password": "TrailPass123"})
    assert signed_in.status_code == 200
    reset_request = client.post("/api/v1/auth/password-reset/request", json={"email": "TRAIL@example.com"})
    assert reset_request.status_code == 200
    code = reset_request.json()["development_reset_code"]
    verified = client.post("/api/v1/auth/password-reset/verify", json={"email": "trail@example.com", "code": code})
    assert verified.status_code == 200
    token = verified.json()["reset_token"]
    completed = client.post("/api/v1/auth/password-reset/complete", json={
        "reset_token": token, "password": "NewTrailPass456", "confirm_password": "NewTrailPass456"
    })
    assert completed.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/sign-in", json={"identifier": "trail@example.com", "password": "TrailPass123"}).status_code == 401
    assert client.post("/api/v1/auth/sign-in", json={"identifier": "trail@example.com", "password": "NewTrailPass456"}).status_code == 200
    replay = client.post("/api/v1/auth/password-reset/complete", json={
        "reset_token": token, "password": "OtherTrailPass789", "confirm_password": "OtherTrailPass789"
    })
    assert replay.status_code == 400


def test_password_reset_rejects_invalid_code_and_password_mismatch(client):
    register_and_verify(client)
    response = client.post("/api/v1/auth/password-reset/request", json={"email": "trail@example.com"})
    assert response.status_code == 200
    invalid = client.post("/api/v1/auth/password-reset/verify", json={"email": "trail@example.com", "code": "000000"})
    assert invalid.status_code == 400
    code = response.json()["development_reset_code"]
    verified = client.post("/api/v1/auth/password-reset/verify", json={"email": "trail@example.com", "code": code})
    assert verified.status_code == 200
    mismatch = client.post("/api/v1/auth/password-reset/complete", json={
        "reset_token": verified.json()["reset_token"], "password": "NewTrailPass456", "confirm_password": "MismatchPass789"
    })
    assert mismatch.status_code == 422


def test_password_reset_request_does_not_disclose_unknown_email(client):
    response = client.post("/api/v1/auth/password-reset/request", json={"email": "missing@example.com"})
    assert response.status_code == 200
    assert "development_reset_code" not in response.json()
    assert response.json()["message"] == "If the account exists, a password-reset code has been issued."


def authenticated_client(client):
    register_and_verify(client)
    result = client.post("/api/v1/auth/sign-in", json={"identifier":"trail@example.com","password":"TrailPass123"})
    assert result.status_code == 200
    return client


def test_destination_catalog_is_seeded_and_public(client):
    response = client.get("/api/v1/destinations")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 5
    assert all(item["simulated"] for item in body["items"])
    assert "simulated demonstration data" in body["data_notice"].lower()


def test_trip_creation_budget_validation_and_owner_persistence(client):
    authenticated_client(client)
    destinations = client.get("/api/v1/destinations").json()["items"]
    destination = destinations[0]
    payload = {"title":"Western Ghats Weekend","start_location":"Mangaluru","destination_id":destination["id"],
               "travel_date":"2026-12-20","travellers":2,"budget":10000,"transport_cost":500,"food_cost":400,"stay_cost":1000}
    created = client.post("/api/v1/trips", json=payload)
    assert created.status_code == 201, created.text
    trip = created.json()
    assert trip["estimated_total"] == (destination["estimated_cost"] + 500 + 400 + 1000) * 2
    assert client.get("/api/v1/trips").json()["items"][0]["id"] == trip["id"]
    payload["budget"] = 1
    assert client.post("/api/v1/trips", json=payload).status_code == 422


def test_disruption_recovery_is_persisted_and_owner_scoped(client):
    authenticated_client(client)
    destination = client.get("/api/v1/destinations").json()["items"][0]
    created = client.post("/api/v1/trips", json={"title":"Recovery test trip","start_location":"Mangaluru",
        "destination_id":destination["id"],"travel_date":"2026-12-20","travellers":1,"budget":10000,
        "transport_cost":500,"food_cost":300,"stay_cost":0})
    assert created.status_code == 201, created.text
    trip_id = created.json()["id"]
    recovery = client.post(f"/api/v1/trips/{trip_id}/recover", json={"disruption_type":"transport_cancellation",
        "description":"Scheduled bus service cancelled in simulation","transport_priority":"balanced"})
    assert recovery.status_code == 200, recovery.text
    result = recovery.json()
    assert result["simulated"] is True
    assert result["affected_segments"]
    assert result["revised_itinerary"]
    assert "simulation" in result["notice"].lower()
    history = client.get(f"/api/v1/trips/{trip_id}/recovery-history")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1


def test_trip_endpoints_require_authentication(client):
    assert client.get("/api/v1/trips").status_code == 401
    assert client.post("/api/v1/trips", json={}).status_code == 401


def test_recovery_requires_explicit_acceptance_and_persists_selected_option(client):
    authenticated_client(client)
    destination = client.get("/api/v1/destinations").json()["items"][0]
    created = client.post("/api/v1/trips", json={"title":"Accept recovery test","start_location":"Mangaluru",
        "destination_id":destination["id"],"travel_date":"2026-12-20","travellers":1,"budget":10000,
        "transport_cost":500,"food_cost":300,"stay_cost":0})
    assert created.status_code == 201, created.text
    trip_id = created.json()["id"]
    original_titles = [segment["title"] for segment in created.json()["itinerary"]]
    preview = client.post(f"/api/v1/trips/{trip_id}/recover", json={"disruption_type":"transport_cancellation",
        "description":"Scheduled bus cancelled in a controlled simulation","transport_priority":"balanced"})
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert len(body["alternatives"]) >= 2
    assert body["accepted"] is False
    assert [segment["title"] for segment in client.get(f"/api/v1/trips/{trip_id}").json()["itinerary"]] == original_titles
    feasible_index = next(i for i, option in enumerate(body["alternatives"]) if option["feasible"])
    accepted = client.post(f"/api/v1/trips/{trip_id}/recovery-events/{body['event_id']}/accept", json={"alternative_index":feasible_index})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted"] is True
    updated = client.get(f"/api/v1/trips/{trip_id}").json()
    assert updated["status"] == "recovered"
    assert updated["itinerary"] == accepted.json()["revised_itinerary"]
    replay = client.post(f"/api/v1/trips/{trip_id}/recovery-events/{body['event_id']}/accept", json={"alternative_index":feasible_index})
    assert replay.status_code == 409


def test_dynamic_place_search_validates_short_query(client):
    response = client.get("/api/v1/places/search?q=a")
    assert response.status_code == 422


def test_map_selected_coordinates_persist_with_trip(client):
    authenticated_client(client)
    destination = client.get("/api/v1/destinations").json()["items"][0]
    created = client.post("/api/v1/trips", json={"title":"Map stop persistence","start_location":"Mangaluru",
        "destination_id":destination["id"],"travel_date":"2026-12-20","travellers":1,"budget":10000,
        "transport_cost":500,"food_cost":300,"stay_cost":0,
        "route_points":[{"name":"Custom viewpoint","lat":13.12345,"lng":75.54321,"source":"OpenStreetMap Nominatim"}]})
    assert created.status_code == 201, created.text
    body = client.get(f"/api/v1/trips/{created.json()['id']}").json()
    assert body["route_points"][0]["name"] == "Custom viewpoint"
    assert body["route_points"][0]["lat"] == 13.12345
    assert body["route_points"][0]["lng"] == 75.54321


def test_dynamic_place_search_normalizes_provider_results(client, monkeypatch):
    import app.main as main
    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return [{"place_id": 12, "name": "Mysuru Palace", "display_name": "Mysuru Palace, Mysuru, Karnataka",
                     "lat": "12.3051", "lon": "76.6551", "type": "attraction"}]
    class FakeClient:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, *args, **kwargs):
            return FakeResponse()
    monkeypatch.setattr(main.httpx, "Client", FakeClient)
    main._PLACE_CACHE.clear()
    response = client.get("/api/v1/places/search?q=Mysuru%20Palace")
    assert response.status_code == 200, response.text
    place = response.json()["items"][0]
    assert place["name"] == "Mysuru Palace"
    assert place["lat"] == 12.3051
    assert place["lng"] == 76.6551
    assert place["verified_tourism_data"] is False


def test_dynamic_map_place_can_be_primary_destination_without_fake_cost(client):
    authenticated_client(client)
    response = client.post("/api/v1/trips", json={"title":"Dynamic destination trip","start_location":"Mangaluru",
        "travel_date":"2026-12-20","travellers":2,"budget":10000,"transport_cost":500,"food_cost":300,"stay_cost":0,
        "destination_place":{"name":"Uncatalogued viewpoint","lat":13.1234,"lng":75.4321,"source":"OpenStreetMap Nominatim"}})
    assert response.status_code == 201, response.text
    trip = response.json()
    assert trip["destination"]["name"] == "Uncatalogued viewpoint"
    assert trip["destination"]["estimated_cost"] is None
    assert trip["cost_estimate_complete"] is False
    assert trip["destination_point"]["lat"] == 13.1234
    assert "costs unknown" in trip["destination"]["source_label"].lower()
    assert "estimated_total" in trip  # known-cost subtotal only; UI flags incomplete estimate


def test_live_trip_start_and_segment_progress_are_persisted(client):
    authenticated_client(client)
    destination = client.get("/api/v1/destinations").json()["items"][0]
    created = client.post("/api/v1/trips", json={"title":"Live progress test","start_location":"Mangaluru",
        "destination_id":destination["id"],"travel_date":"2026-12-20","travellers":1,"budget":10000,
        "transport_cost":500,"food_cost":300,"stay_cost":0})
    trip_id = created.json()["id"]
    started = client.post(f"/api/v1/trips/{trip_id}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "active"
    updated = client.patch(f"/api/v1/trips/{trip_id}/segments/2", json={"status":"completed"})
    assert updated.status_code == 200
    assert next(segment for segment in updated.json()["itinerary"] if segment["order"] == 2)["status"] == "completed"
    assert client.patch(f"/api/v1/trips/{trip_id}/segments/999", json={"status":"completed"}).status_code == 404

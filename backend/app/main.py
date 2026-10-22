"""TRAILMATE AI API: database-backed registration, verification, sessions and profile."""
import json
import os
import re
import secrets
import time
import threading
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import httpx
from .db import get_db
from .models import PasswordResetChallenge, Profile, User, UserSession, VerificationChallenge
from .schemas import (PasswordResetCompleteRequest, PasswordResetRequest, ProfileUpdate, RegisterRequest,
                      ResetCodeVerifyRequest, SignInRequest, UserResponse, VerifyRequest)
from .security import hash_secret, token_hash, verify_secret

APP_ENV = os.getenv("APP_ENV", "development").lower()
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
COOKIE_NAME = "trailmate_session"
SESSION_DAYS = 7

app = FastAPI(title="TRAILMATE AI API", description="Travel intelligence and recovery platform", version="0.2.0")


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required")
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash(token)))
    if not session or aware(session.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired; sign in again")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session is invalid")
    return user


def profile_payload(user: User) -> dict:
    profile = user.profile
    return {
        "id": user.id, "full_name": user.full_name, "username": user.username,
        "email": user.email, "email_verified": user.email_verified,
        "onboarding_complete": bool(profile and profile.onboarding_complete),
    }


@app.get("/", tags=["system"])
def root():
    return {"service": "TRAILMATE AI API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "trailmate-ai-api", "environment": APP_ENV}


@app.post("/api/v1/auth/register", status_code=201, tags=["auth"])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if APP_ENV not in {"development", "test"}:
        raise HTTPException(status_code=503, detail="Email verification provider is not configured")
    username = payload.username.lower()
    email = payload.email.lower()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=409, detail="Username is already in use")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(full_name=payload.full_name, username=username, email=email,
                password_hash=hash_secret(payload.password), consent=payload.consent, email_verified=False)
    db.add(user)
    db.flush()
    profile = Profile(user_id=user.id)
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = VerificationChallenge(user_id=user.id, code_hash=hash_secret(code),
                                      expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    db.add_all([profile, challenge])
    db.commit()
    # Explicit development-only delivery channel; never returned outside development/test.
    return {"message": "Account created. Verify your email to continue.", "email": email,
            "development_verification_code": code if APP_ENV in {"development", "test"} else None,
            "delivery_mode": "development-only"}


@app.post("/api/v1/auth/verify-email", tags=["auth"])
def verify_email(payload: VerifyRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    challenge = db.scalar(select(VerificationChallenge).where(
        VerificationChallenge.user_id == user.id, VerificationChallenge.used.is_(False)
    ).order_by(VerificationChallenge.id.desc()))
    if not challenge or challenge.attempts >= 5 or aware(challenge.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    challenge.attempts += 1
    if not verify_secret(payload.code, challenge.code_hash):
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    challenge.used = True
    user.email_verified = True
    db.commit()
    return {"message": "Email verified. You can now sign in."}


@app.post("/api/v1/auth/password-reset/request", tags=["auth"])
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    # Same public response whether the account exists or not, to reduce account enumeration.
    response = {"message": "If the account exists, a password-reset code has been issued.", "delivery_mode": "development-only"}
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not user.email_verified:
        return response
    now = datetime.now(timezone.utc)
    latest = db.scalar(select(PasswordResetChallenge).where(
        PasswordResetChallenge.user_id == user.id
    ).order_by(PasswordResetChallenge.id.desc()))
    if latest and aware(latest.created_at) > now - timedelta(seconds=60) and not latest.used:
        # Do not disclose cooldown/account existence. Do not create another challenge.
        return response
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(PasswordResetChallenge(user_id=user.id, code_hash=hash_secret(code),
        expires_at=now + timedelta(minutes=10)))
    db.commit()
    if APP_ENV in {"development", "test"}:
        response["development_reset_code"] = code
    return response


@app.post("/api/v1/auth/password-reset/verify", tags=["auth"])
def verify_password_reset_code(payload: ResetCodeVerifyRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    now = datetime.now(timezone.utc)
    challenge = db.scalar(select(PasswordResetChallenge).where(
        PasswordResetChallenge.user_id == user.id if user else False,
        PasswordResetChallenge.used.is_(False)
    ).order_by(PasswordResetChallenge.id.desc())) if user else None
    if not challenge or challenge.attempts >= 5 or aware(challenge.expires_at) <= now or not verify_secret(payload.code, challenge.code_hash):
        if challenge and challenge.attempts < 5 and aware(challenge.expires_at) > now:
            challenge.attempts += 1
            db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    challenge.attempts += 1
    raw_token = secrets.token_urlsafe(32)
    challenge.reset_token_hash = token_hash(raw_token)
    challenge.expires_at = now + timedelta(minutes=10)
    db.commit()
    return {"message": "Reset code verified. Choose a new password.", "reset_token": raw_token}


@app.post("/api/v1/auth/password-reset/complete", tags=["auth"])
def complete_password_reset(payload: PasswordResetCompleteRequest, response: Response, db: Session = Depends(get_db)):
    challenge = db.scalar(select(PasswordResetChallenge).where(
        PasswordResetChallenge.reset_token_hash == token_hash(payload.reset_token),
        PasswordResetChallenge.used.is_(False)
    ))
    if not challenge or aware(challenge.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset authorization is invalid or expired")
    user = db.get(User, challenge.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Reset authorization is invalid or expired")
    user.password_hash = hash_secret(payload.password)
    challenge.used = True
    challenge.reset_token_hash = None
    # Password change invalidates every existing browser session for this account.
    db.query(UserSession).filter(UserSession.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)
    return {"message": "Password updated. Sign in with your new password."}


@app.post("/api/v1/auth/sign-in", tags=["auth"])
def sign_in(payload: SignInRequest, response: Response, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip().lower()
    user = db.scalar(select(User).where((User.username == identifier) | (User.email == identifier)))
    if not user or not verify_secret(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Verify your email before signing in")
    raw_token = secrets.token_urlsafe(32)
    db.add(UserSession(token_hash=token_hash(raw_token), user_id=user.id,
                       expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)))
    db.commit()
    response.set_cookie(COOKIE_NAME, raw_token, httponly=True, secure=COOKIE_SECURE,
                        samesite=COOKIE_SAMESITE, max_age=SESSION_DAYS * 86400, path="/")
    return {"message": "Signed in", "user": profile_payload(user)}


@app.post("/api/v1/auth/sign-out", tags=["auth"])
def sign_out(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash(token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)
    return {"message": "Signed out"}


@app.get("/api/v1/auth/me", response_model=UserResponse, tags=["auth"])
def me(user: User = Depends(current_user)):
    return profile_payload(user)


@app.get("/api/v1/profile", tags=["profile"])
def get_profile(user: User = Depends(current_user)):
    profile = user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"preferred_language": profile.preferred_language, "city": profile.city, "region": profile.region,
            "travel_interests": json.loads(profile.travel_interests), "preferred_budget": profile.preferred_budget,
            "preferred_duration_days": profile.preferred_duration_days, "onboarding_complete": profile.onboarding_complete}


@app.put("/api/v1/profile", tags=["profile"])
def update_profile(payload: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = user.profile
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
    profile.preferred_language = payload.preferred_language
    profile.city = payload.city
    profile.region = payload.region
    profile.travel_interests = json.dumps(payload.travel_interests)
    profile.preferred_budget = payload.preferred_budget
    profile.preferred_duration_days = payload.preferred_duration_days
    profile.onboarding_complete = payload.onboarding_complete
    db.commit()
    db.refresh(profile)
    return {"preferred_language": profile.preferred_language, "city": profile.city, "region": profile.region,
            "travel_interests": json.loads(profile.travel_interests), "preferred_budget": profile.preferred_budget,
            "preferred_duration_days": profile.preferred_duration_days, "onboarding_complete": profile.onboarding_complete}


@app.get("/api/v1/dashboard", tags=["customer"])
def dashboard(user: User = Depends(current_user)):
    profile = user.profile
    return {"welcome": user.full_name, "username": user.username,
            "onboarding_complete": bool(profile and profile.onboarding_complete),
            "upcoming_trips": [], "saved_places": [], "recommended_destinations": [],
            "notice": "Your trip and destination data will appear here as you create and save them."}

# ---- Dynamic place discovery (Nominatim / OpenStreetMap) ----
_PLACE_CACHE: dict[str, tuple[float, list[dict]]] = {}
_PLACE_CACHE_TTL = 300
_PLACE_CACHE_LIMIT = 256
_PLACE_REQUEST_LOCK = threading.Lock()
_PLACE_LAST_REQUEST_AT = 0.0


@app.get("/api/v1/places/search", tags=["places"])
def search_places(q: str = Query(min_length=2, max_length=120), limit: int = Query(default=6, ge=1, le=8)):
    """Search real geographic places. Results are geocoding results, not verified tourism listings."""
    query = " ".join(q.split())
    cache_key = f"{query.casefold()}:{limit}"
    now = time.monotonic()
    cached = _PLACE_CACHE.get(cache_key)
    if cached and now - cached[0] < _PLACE_CACHE_TTL:
        return {"items": cached[1], "source": "OpenStreetMap Nominatim", "cached": True,
                "notice": "Geocoding results identify places; opening hours, access, prices and live conditions are not verified."}
    try:
        # Nominatim's public endpoint asks applications to stay at or below one request per second.
        global _PLACE_LAST_REQUEST_AT
        with _PLACE_REQUEST_LOCK:
            wait = 1.05 - (time.monotonic() - _PLACE_LAST_REQUEST_AT)
            if wait > 0:
                time.sleep(wait)
            with httpx.Client(timeout=5.0, headers={"User-Agent": "TRAILMATE-AI/0.3 (travel-planning prototype)"}) as client:
                response = client.get("https://nominatim.openstreetmap.org/search", params={
                    "q": query, "format": "jsonv2", "addressdetails": 1, "limit": limit,
                })
                response.raise_for_status()
                payload = response.json()
            _PLACE_LAST_REQUEST_AT = time.monotonic()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=502, detail="Place search is temporarily unavailable. Try again shortly or choose a curated destination.")
    items = []
    for item in payload:
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            items.append({
                "id": str(item.get("place_id", f"{lat}:{lon}")),
                "name": str(item.get("name") or item.get("display_name", "Place").split(",")[0])[:160],
                "display_name": str(item.get("display_name", ""))[:400],
                "lat": lat, "lng": lon,
                "category": str(item.get("type") or item.get("class") or "place")[:60],
                "source": "OpenStreetMap Nominatim",
                "verified_tourism_data": False,
            })
        except (KeyError, TypeError, ValueError):
            continue
    if len(_PLACE_CACHE) >= _PLACE_CACHE_LIMIT:
        oldest = min(_PLACE_CACHE, key=lambda key: _PLACE_CACHE[key][0])
        _PLACE_CACHE.pop(oldest, None)
    _PLACE_CACHE[cache_key] = (now, items)
    return {"items": items, "source": "OpenStreetMap Nominatim", "cached": False,
            "notice": "Geocoding results identify places; opening hours, access, prices and live conditions are not verified."}


# ---- Travel MVP: destinations, persistent trips, deterministic budget and recovery ----
from pydantic import BaseModel, Field, model_validator
from .models import Destination, Trip, RecoveryEvent

DEMO_DESTINATIONS = [
    {"slug":"jog-falls","name":"Jog Falls","district":"Shivamogga","category":"Waterfall","description":"A major waterfall viewpoint in the Western Ghats region. Check local access and weather information before travelling.","estimated_cost":500,"duration_hours":4,"difficulty":"Easy"},
    {"slug":"kudremukh","name":"Kudremukh","district":"Chikkamagaluru","category":"Trekking","description":"Mountain landscapes and trekking opportunities. Permits and access rules must be checked with the relevant authority.","estimated_cost":1200,"duration_hours":8,"difficulty":"Challenging"},
    {"slug":"agumbe","name":"Agumbe","district":"Shivamogga","category":"Nature","description":"Rainforest scenery and sunset viewpoints. Conditions and access can change with weather.","estimated_cost":700,"duration_hours":4,"difficulty":"Moderate"},
    {"slug":"mulki","name":"Mulki Coast","district":"Dakshina Kannada","category":"Coastal","description":"Coastal activities and local food discovery. Activity availability is not verified by this demo.","estimated_cost":900,"duration_hours":5,"difficulty":"Easy"},
    {"slug":"chikmagalur","name":"Chikkamagaluru Coffee Country","district":"Chikkamagaluru","category":"Sightseeing","description":"Coffee-growing landscapes and regional sightseeing. Listing costs are simulated demonstration estimates.","estimated_cost":1000,"duration_hours":6,"difficulty":"Easy"},
    {"slug":"ananthapura","name":"Ananthapura Lake Temple","district":"Kasaragod","category":"Culture","description":"A lakeside temple destination in northern Kerala, included as a regional demonstration listing.","estimated_cost":400,"duration_hours":2,"difficulty":"Easy"},
]

class RoutePoint(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    source: str = Field(default="OpenStreetMap Nominatim", max_length=100)

class TripCreate(BaseModel):
    route_stops: list[str] = Field(default_factory=list, max_length=12)
    route_points: list[RoutePoint] = Field(default_factory=list, max_length=12)
    destination_place: RoutePoint | None = None
    title: str = Field(min_length=3, max_length=160)
    start_location: str = Field(min_length=2, max_length=160)
    destination_id: int | None = Field(default=None, ge=1)
    travel_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    travellers: int = Field(default=1, ge=1, le=20)
    budget: int = Field(ge=1, le=10_000_000)
    transport_cost: int = Field(default=500, ge=0, le=1_000_000)
    food_cost: int = Field(default=500, ge=0, le=1_000_000)
    stay_cost: int = Field(default=0, ge=0, le=1_000_000)

    @model_validator(mode="after")
    def require_destination(self):
        if self.destination_place is None and self.destination_id is None:
            raise ValueError("Choose a curated destination or select a place from map search")
        if self.destination_place is not None and self.destination_id is not None:
            raise ValueError("Choose either a curated destination or a map-search destination, not both")
        return self

class RecoveryRequest(BaseModel):
    disruption_type: str = Field(pattern=r"^(transport_cancellation|route_closure|activity_unavailable|accommodation_unavailable)$")
    description: str = Field(min_length=5, max_length=500)
    transport_priority: str = Field(default="balanced", pattern=r"^(lowest_cost|fastest|balanced)$")


def destination_json(d: Destination) -> dict:
    cost_unknown = "costs unknown" in (d.source_label or "").lower()
    return {"id":d.id,"slug":d.slug,"name":d.name,"district":d.district,"category":d.category,
            "description":d.description,"estimated_cost":None if cost_unknown else d.estimated_cost,"duration_hours":d.duration_hours,
            "difficulty":d.difficulty,"source_label":d.source_label,"simulated":bool(d.is_published)}

def trip_json(t: Trip) -> dict:
    return {"id":t.id,"title":t.title,"start_location":t.start_location,"destination":destination_json(t.destination),
            "destination_id":t.destination_id,"travel_date":t.travel_date,"travellers":t.travellers,"budget":t.budget,
            "transport_cost":t.transport_cost,"food_cost":t.food_cost,"stay_cost":t.stay_cost,
            "estimated_total":sum(max(0, int(segment.get("estimated_cost", 0))) for segment in json.loads(t.itinerary_json)),
            "cost_estimate_complete":not any(segment.get("cost_status")=="unknown" for segment in json.loads(t.itinerary_json)),
            "destination_point":next(({"id":f"destination:{t.id}","name":segment["title"],"display_name":segment["title"],"lat":segment["lat"],"lng":segment["lng"],"category":"trip destination","source":segment.get("source","OpenStreetMap Nominatim")} for segment in json.loads(t.itinerary_json) if segment.get("type")=="activity" and isinstance(segment.get("lat"),(int,float)) and isinstance(segment.get("lng"),(int,float))),None),
            "status":t.status,"itinerary":json.loads(t.itinerary_json),"route_stops":[s["title"] for s in json.loads(t.itinerary_json) if s.get("type")=="stop"],
            "route_points":[{"id":f"saved:{s['title']}:{s['lat']}:{s['lng']}","name":s["title"],"display_name":s["title"],"lat":s["lat"],"lng":s["lng"],"category":"saved stop","source":s.get("source","OpenStreetMap Nominatim")} for s in json.loads(t.itinerary_json) if s.get("type")=="stop" and isinstance(s.get("lat"),(int,float)) and isinstance(s.get("lng"),(int,float))],"created_at":t.created_at.isoformat()}

def seed_destinations(db: Session):
    if db.scalar(select(Destination.id).limit(1)) is None:
        for item in DEMO_DESTINATIONS:
            db.add(Destination(**item, source_label="Simulated demonstration data", is_published=True))
        db.commit()

@app.get("/api/v1/destinations", tags=["travel"])
def list_destinations(q: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    seed_destinations(db)
    stmt = select(Destination).where(Destination.is_published.is_(True))
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where((Destination.name.ilike(term)) | (Destination.district.ilike(term)) | (Destination.category.ilike(term)))
    if category and category != "All":
        stmt = stmt.where(Destination.category == category)
    return {"items":[destination_json(d) for d in db.scalars(stmt.order_by(Destination.name)).all()],
            "data_notice":"Destination listings and costs are simulated demonstration data; verify access and costs with authoritative sources."}

@app.get("/api/v1/trips", tags=["travel"])
def list_trips(user: User = Depends(current_user), db: Session = Depends(get_db)):
    seed_destinations(db)
    trips = db.scalars(select(Trip).where(Trip.user_id == user.id).order_by(Trip.id.desc())).all()
    return {"items":[trip_json(t) for t in trips]}

@app.post("/api/v1/trips", status_code=201, tags=["travel"])
def create_trip(payload: TripCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    seed_destinations(db)
    destination_is_dynamic = payload.destination_place is not None
    if destination_is_dynamic:
        point = payload.destination_place
        slug_base = re.sub(r"[^a-z0-9]+", "-", point.name.lower()).strip("-")[:70] or "place"
        slug = f"map-{slug_base}-{int(abs(point.lat)*100000)}-{int(abs(point.lng)*100000)}-{user.id}"
        destination = Destination(slug=slug, name=point.name, district="Location from map search", category="Map search",
            description=f"Geocoded location: {point.lat:.5f}, {point.lng:.5f}. Tourism details and costs have not been verified.",
            estimated_cost=0, duration_hours=3, difficulty="Unknown",
            source_label="OpenStreetMap geocoding; costs unknown", is_published=False)
        db.add(destination)
        db.flush()
    else:
        destination = db.get(Destination, payload.destination_id)
        if not destination or not destination.is_published:
            raise HTTPException(status_code=404, detail="Destination not found")
    estimated = (payload.transport_cost + payload.food_cost + payload.stay_cost + destination.estimated_cost) * payload.travellers
    if not destination_is_dynamic and estimated > payload.budget:
        raise HTTPException(status_code=422, detail=f"Estimated total is ₹{estimated}, above your total group budget of ₹{payload.budget}.")
    itinerary = [
        {"order":1,"type":"transport","title":f"Travel from {payload.start_location}","status":"planned","estimated_cost":payload.transport_cost*payload.travellers,"duration_hours":3,"simulated":True},
        {"order":2,"type":"activity","title":f"Visit {destination.name}","status":"planned","estimated_cost":destination.estimated_cost*payload.travellers,"duration_hours":destination.duration_hours,"simulated":not destination_is_dynamic,
         **({"cost_status":"unknown","lat":payload.destination_place.lat,"lng":payload.destination_place.lng,"source":payload.destination_place.source,"reason":"Destination selected from geocoding search. Destination-specific costs are unknown and excluded from this subtotal."} if destination_is_dynamic else {})},
        {"order":3,"type":"food","title":"Meals and refreshments","status":"planned","estimated_cost":payload.food_cost*payload.travellers,"duration_hours":2,"simulated":True},
    ]
    if payload.stay_cost:
        itinerary.append({"order":len(itinerary)+1,"type":"accommodation","title":"Accommodation","status":"planned","estimated_cost":payload.stay_cost*payload.travellers,"duration_hours":12,"simulated":True})
    # Optional map-selected stops are persisted in the existing itinerary JSON field.
    # The final destination remains the canonical destination relation for compatibility.
    seen = set()
    for stop_name in payload.route_stops:
        clean_name = stop_name.strip()[:160]
        if clean_name and clean_name.casefold() not in seen and clean_name.casefold() != destination.name.casefold():
            seen.add(clean_name.casefold())
            itinerary.append({"order":len(itinerary)+1,"type":"stop","title":clean_name,"status":"planned","estimated_cost":0,"duration_hours":1,"simulated":True,"reason":"Added from the interactive map; stop cost is not included unless entered separately."})
    for point in payload.route_points:
        clean_name = point.name.strip()[:160]
        if clean_name and clean_name.casefold() not in seen and clean_name.casefold() != destination.name.casefold():
            seen.add(clean_name.casefold())
            itinerary.append({"order":len(itinerary)+1,"type":"stop","title":clean_name,"status":"planned",
                "estimated_cost":0,"duration_hours":1,"simulated":False,"lat":point.lat,"lng":point.lng,
                "source":point.source,"reason":"Location selected from dynamic place search. Destination costs and access are not verified."})
    trip = Trip(user_id=user.id,title=payload.title,start_location=payload.start_location,destination_id=destination.id,
        travel_date=payload.travel_date,travellers=payload.travellers,budget=payload.budget,
        transport_cost=payload.transport_cost,food_cost=payload.food_cost,stay_cost=payload.stay_cost,
        itinerary_json=json.dumps(itinerary))
    db.add(trip); db.commit(); db.refresh(trip)
    return trip_json(trip)

@app.get("/api/v1/trips/{trip_id}", tags=["travel"])
def get_trip(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    if not trip: raise HTTPException(status_code=404, detail="Trip not found")
    return trip_json(trip)

class TripSegmentStatusRequest(BaseModel):
    status: str = Field(pattern=r"^(planned|in_progress|completed|skipped)$")


@app.post("/api/v1/trips/{trip_id}/start", tags=["travel"])
def start_trip(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status == "completed":
        raise HTTPException(status_code=409, detail="This trip is already completed")
    trip.status = "active"
    db.commit()
    db.refresh(trip)
    return trip_json(trip)


@app.patch("/api/v1/trips/{trip_id}/segments/{segment_order}", tags=["travel"])
def update_trip_segment(trip_id: int, segment_order: int, payload: TripSegmentStatusRequest,
                        user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    itinerary = json.loads(trip.itinerary_json)
    segment = next((item for item in itinerary if item.get("order") == segment_order), None)
    if segment is None:
        raise HTTPException(status_code=404, detail="Itinerary segment not found")
    segment["status"] = payload.status
    trip.itinerary_json = json.dumps(itinerary)
    meaningful = [item for item in itinerary if item.get("type") in {"activity", "stop"}]
    if meaningful and all(item.get("status") in {"completed", "skipped"} for item in meaningful):
        trip.status = "completed"
    elif any(item.get("status") == "in_progress" for item in itinerary) or payload.status in {"in_progress", "completed"}:
        trip.status = "active"
    elif trip.status != "recovered":
        trip.status = "planned"
    db.commit()
    db.refresh(trip)
    return trip_json(trip)


@app.post("/api/v1/trips/{trip_id}/recover", tags=["travel"])
def recover_trip(trip_id: int, payload: RecoveryRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Analyse a disruption and save a recovery proposal without mutating the active itinerary."""
    trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    original = json.loads(trip.itinerary_json)
    affected: list[str] = []
    alternatives: list[dict] = []
    base_total = sum(max(0, int(s.get("estimated_cost", 0))) for s in original)
    # The current prototype uses explicitly simulated transport options; no live provider is queried here.
    if payload.disruption_type == "transport_cancellation":
        segment = next((s for s in original if s.get("type") == "transport"), None)
        if segment:
            affected = [segment.get("title", "Transport segment")]
            original_cost = int(segment.get("estimated_cost", trip.transport_cost * trip.travellers))
            options = [
                ("Local bus combination", max(150, int(trip.transport_cost * .65)) * trip.travellers, 5.0,
                 "Lower estimated cost; longer journey. Simulated option, not a live timetable."),
                ("Shared taxi", int(trip.transport_cost * 1.35) * trip.travellers, 2.0,
                 "Shorter estimated journey; higher cost. Simulated option, not a live offer."),
                ("Re-plan transport later", original_cost, 3.5,
                 "Preserves the transport budget estimate but requires the traveller to confirm a real service."),
            ]
            for name, cost, hours, rationale in options:
                candidate = [dict(s) for s in original]
                target = next((s for s in candidate if s.get("type") == "transport"), None)
                if target:
                    target.update({"title": name, "status": "proposed", "estimated_cost": cost,
                                   "duration_hours": hours, "reason": rationale})
                total = sum(max(0, int(s.get("estimated_cost", 0))) for s in candidate)
                alternatives.append({"name": name, "itinerary": candidate, "estimated_total": total,
                    "additional_cost": total - base_total, "estimated_extra_hours": hours - float(segment.get("duration_hours", 3)),
                    "feasible": total <= trip.budget, "constraint_results": {"within_budget": total <= trip.budget},
                    "rationale": rationale, "simulated": True})
    elif payload.disruption_type == "route_closure":
        affected = [s.get("title", "") for s in original if s.get("type") in {"transport", "activity", "stop"}]
        transport = next((s for s in original if s.get("type") == "transport"), None)
        detour = [dict(s) for s in original]
        if transport:
            target = next(s for s in detour if s.get("type") == "transport")
            target.update({"title": "Detour via an alternate route", "status": "proposed",
                           "duration_hours": float(target.get("duration_hours", 3)) + 2,
                           "reason": "Two-hour detour assumption for a simulated closure; route feasibility is not verified live."})
        alternatives.append({"name": "Take a detour", "itinerary": detour, "estimated_total": base_total,
            "additional_cost": 0, "estimated_extra_hours": 2, "feasible": True,
            "constraint_results": {"within_budget": base_total <= trip.budget},
            "rationale": "Keeps the original stops but adds an assumed two hours. Actual road access is not checked.", "simulated": True})
        reordered = [dict(s) for s in original]
        activities = [s for s in reordered if s.get("type") in {"activity", "stop"}]
        if activities:
            target = activities[0]
            target.update({"title": f"Reschedule: {target.get('title','activity')}", "status": "rescheduled",
                           "reason": "Move this stop later and confirm current access before travelling."})
        alternatives.append({"name": "Reorder remaining stops", "itinerary": reordered, "estimated_total": base_total,
            "additional_cost": 0, "estimated_extra_hours": 0, "feasible": True,
            "constraint_results": {"within_budget": base_total <= trip.budget},
            "rationale": "Preserves the existing cost estimate, but actual route and time-window feasibility require live data.", "simulated": True})
    elif payload.disruption_type == "activity_unavailable":
        affected = [s.get("title", "") for s in original if s.get("type") in {"activity", "stop"}]
        alternates = db.scalars(select(Destination).where(Destination.id != trip.destination_id, Destination.is_published.is_(True)).order_by(Destination.estimated_cost)).all()
        for destination in alternates[:4]:
            candidate = [dict(s) for s in original]
            target = next((s for s in candidate if s.get("type") in {"activity", "stop"}), None)
            if not target:
                break
            target.update({"title": f"Alternative visit: {destination.name}", "status": "proposed",
                "estimated_cost": destination.estimated_cost * trip.travellers,
                "reason": "Alternative from curated demo catalogue; availability, distance and opening hours are not live-verified."})
            total = sum(max(0, int(s.get("estimated_cost", 0))) for s in candidate)
            alternatives.append({"name": f"Visit {destination.name}", "itinerary": candidate, "estimated_total": total,
                "additional_cost": total - base_total, "estimated_extra_hours": 0,
                "feasible": total <= trip.budget, "constraint_results": {"within_budget": total <= trip.budget},
                "rationale": f"Uses {destination.name} from the curated catalogue. Verify access, distance and hours before travel.", "simulated": True})
        skipped = [dict(s) for s in original]
        target = next((s for s in skipped if s.get("type") in {"activity", "stop"}), None)
        if target:
            target.update({"status": "skipped", "estimated_cost": 0, "reason": "Activity skipped in this simulated recovery option."})
            total = sum(max(0, int(s.get("estimated_cost", 0))) for s in skipped)
            alternatives.append({"name": "Skip unavailable activity", "itinerary": skipped, "estimated_total": total,
                "additional_cost": total - base_total, "estimated_extra_hours": 0,
                "feasible": total <= trip.budget, "constraint_results": {"within_budget": total <= trip.budget},
                "rationale": "Removes the unavailable activity from the plan; confirm the remaining schedule manually.", "simulated": True})
    else:
        affected = [s.get("title", "") for s in original if s.get("type") == "accommodation"]
        stays = [s for s in original if s.get("type") == "accommodation"]
        if stays:
            for label, multiplier, rationale in [
                ("Alternative stay at similar estimated cost", 1.0, "Keeps the existing estimate; no property availability is verified."),
                ("Lower-cost stay estimate", 0.75, "Reduces the estimate by 25%; this is a simulation, not a real offer."),
            ]:
                candidate = [dict(s) for s in original]
                target = next(s for s in candidate if s.get("type") == "accommodation")
                target.update({"title": label, "status": "proposed", "estimated_cost": int(target.get("estimated_cost", 0) * multiplier), "reason": rationale})
                total = sum(max(0, int(s.get("estimated_cost", 0))) for s in candidate)
                alternatives.append({"name": label, "itinerary": candidate, "estimated_total": total,
                    "additional_cost": total - base_total, "estimated_extra_hours": 0,
                    "feasible": total <= trip.budget, "constraint_results": {"within_budget": total <= trip.budget},
                    "rationale": rationale, "simulated": True})
        else:
            alternatives.append({"name": "No accommodation segment", "itinerary": original, "estimated_total": base_total,
                "additional_cost": 0, "estimated_extra_hours": 0, "feasible": False,
                "constraint_results": {"within_budget": base_total <= trip.budget},
                "rationale": "This trip has no accommodation segment to replace. Edit the trip or select another disruption.", "simulated": True})
    cost_complete = not any(segment.get("cost_status") == "unknown" for segment in original)
    if not cost_complete:
        for item in alternatives:
            item["feasible"] = False
            item["constraint_results"]["budget_verification_complete"] = False
            item["rationale"] += " Budget feasibility cannot be confirmed because at least one saved itinerary cost is unknown; add a verified estimate before accepting this recovery plan."
    else:
        for item in alternatives:
            item["constraint_results"]["budget_verification_complete"] = True
    feasible = [item for item in alternatives if item["feasible"]]
    # Rank by feasibility first, then lower additional cost and less schedule impact.
    alternatives.sort(key=lambda item: (not item["feasible"], max(0, item["additional_cost"]), item["estimated_extra_hours"]))
    explanation = (f"Generated {len(alternatives)} candidate recovery option(s); {len(feasible)} meet the saved group budget. "
                   "Review the trade-offs and accept an option to update the trip. All options in this workflow are simulated, not live offers.")
    event = RecoveryEvent(trip_id=trip.id, user_id=user.id, disruption_type=payload.disruption_type,
        description=payload.description, original_plan_json=json.dumps(original),
        revised_plan_json=json.dumps({"accepted": False, "alternatives": alternatives}), explanation=explanation, simulated=True)
    db.add(event)
    db.commit()
    db.refresh(event)
    recommended = next((item for item in alternatives if item["feasible"]), alternatives[0] if alternatives else None)
    return {"event_id": event.id, "trip_id": trip.id, "simulated": True, "accepted": False,
        "disruption_type": payload.disruption_type, "description": payload.description,
        "affected_segments": affected, "original_itinerary": original,
        "alternatives": alternatives, "recommended_alternative": recommended["name"] if recommended else None,
        "revised_itinerary": recommended["itinerary"] if recommended else original,
        "estimated_total": recommended["estimated_total"] if recommended else base_total,
        "original_estimated_total": base_total, "cost_estimate_complete": cost_complete,
        "within_budget": bool(recommended and recommended["feasible"]), "explanation": explanation,
        "notice": "Simulation only. No live transport, route, activity or accommodation data was checked. The saved trip has not changed until you accept an alternative."}


class RecoveryAcceptRequest(BaseModel):
    alternative_index: int = Field(ge=0, le=20)


@app.post("/api/v1/trips/{trip_id}/recovery-events/{event_id}/accept", tags=["travel"])
def accept_recovery(trip_id: int, event_id: int, payload: RecoveryAcceptRequest,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    event = db.scalar(select(RecoveryEvent).where(RecoveryEvent.id == event_id,
        RecoveryEvent.trip_id == trip_id, RecoveryEvent.user_id == user.id))
    if not trip or not event:
        raise HTTPException(status_code=404, detail="Trip or recovery proposal not found")
    try:
        stored = json.loads(event.revised_plan_json)
    except ValueError:
        stored = None
    if not isinstance(stored, dict) or stored.get("accepted"):
        raise HTTPException(status_code=409, detail="This recovery proposal has already been accepted or is no longer pending")
    alternatives = stored.get("alternatives", [])
    if payload.alternative_index >= len(alternatives):
        raise HTTPException(status_code=404, detail="Recovery alternative not found")
    chosen = alternatives[payload.alternative_index]
    if not chosen.get("feasible"):
        raise HTTPException(status_code=422, detail="This alternative violates a hard budget constraint and cannot be accepted")
    # Re-read current itinerary to avoid applying a stale proposal over a trip changed after preview.
    current = json.loads(trip.itinerary_json)
    if current != json.loads(event.original_plan_json):
        raise HTTPException(status_code=409, detail="The trip changed after this proposal was generated. Generate a fresh recovery plan.")
    revised = chosen["itinerary"]
    trip.itinerary_json = json.dumps(revised)
    trip.status = "recovered"
    event.revised_plan_json = json.dumps(revised)
    event.explanation = f"Accepted alternative: {chosen['name']}. {chosen['rationale']}"
    db.commit()
    return {"event_id": event.id, "trip_id": trip.id, "accepted": True,
        "selected_alternative": chosen["name"], "revised_itinerary": revised,
        "estimated_total": chosen["estimated_total"], "within_budget": chosen["feasible"],
        "explanation": event.explanation, "notice": "The selected simulated recovery plan has been saved. Verify live conditions before travel."}

@app.get("/api/v1/trips/{trip_id}/recovery-history", tags=["travel"])
def recovery_history(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    if not trip: raise HTTPException(status_code=404, detail="Trip not found")
    events = db.scalars(select(RecoveryEvent).where(RecoveryEvent.trip_id == trip.id, RecoveryEvent.user_id == user.id).order_by(RecoveryEvent.id.desc())).all()
    return {"items":[{"id":e.id,"disruption_type":e.disruption_type,"description":e.description,"explanation":e.explanation,"simulated":e.simulated,"status":"pending" if isinstance(json.loads(e.revised_plan_json), dict) else "accepted","created_at":e.created_at.isoformat()} for e in events]}

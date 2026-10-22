"""Persistent account, session, verification, and profile models."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    profile: Mapped["Profile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class VerificationChallenge(Base):
    __tablename__ = "verification_challenges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(256))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    preferred_language: Mapped[str] = mapped_column(String(30), default="English")
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    travel_interests: Mapped[str] = mapped_column(Text, default="[]")
    preferred_budget: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preferred_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    user: Mapped[User] = relationship(back_populates="profile")


class PasswordResetChallenge(Base):
    __tablename__ = "password_reset_challenges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(256))
    reset_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Destination(Base):
    __tablename__ = "destinations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    district: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text)
    estimated_cost: Mapped[int] = mapped_column(Integer, default=0)
    duration_hours: Mapped[int] = mapped_column(Integer, default=3)
    difficulty: Mapped[str] = mapped_column(String(30), default="Easy")
    source_label: Mapped[str] = mapped_column(String(120), default="Simulated demonstration data")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    start_location: Mapped[str] = mapped_column(String(160))
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id"))
    travel_date: Mapped[str] = mapped_column(String(10))
    travellers: Mapped[int] = mapped_column(Integer, default=1)
    budget: Mapped[int] = mapped_column(Integer)
    transport_cost: Mapped[int] = mapped_column(Integer, default=0)
    food_cost: Mapped[int] = mapped_column(Integer, default=0)
    stay_cost: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="planned")
    itinerary_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    destination: Mapped[Destination] = relationship()


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    disruption_type: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text)
    original_plan_json: Mapped[str] = mapped_column(Text)
    revised_plan_json: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

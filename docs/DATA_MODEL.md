# Data Model — Initial Design

This is a proposed relational model, not a claim that all tables exist in code. Implement only the tables required by the active vertical slice, with Alembic migrations.

## Identity and access

- `users`: id, normalized email (unique), username (unique), password hash, account status, email verification timestamp, created/updated timestamps.
- `roles`, `permissions`, `user_roles`: role-based access with assignment restricted to authorized administrators.
- `sessions`: hashed session identifier/token, user id, expiry, revoked timestamp, created timestamp.
- `email_challenges`: user/email, challenge purpose, securely hashed OTP, expiry, attempt count, consumed timestamp, resend-after timestamp.
- `user_profiles`: user id, full/display name, image reference, language, optional contact fields, travel preferences, profile-completion state, privacy settings.

## Regional catalogue

- `regions`: name, code, parent region id.
- `destinations`: slug, name, description, region/district, category, safe-to-publish coordinates, visit duration, cost range, access/safety/entry notes, publication state, creator/editor ids.
- `places`: destination association, category and access/sensitivity metadata for lesser-known places.
- `trekking_routes`: destination, trailhead, distance/duration/elevation when supported, difficulty, seasonal/access/permit notes, source and verification metadata.
- `accommodations`, `restaurants`, `transport_options`, `local_contacts`: structured listings, external links, price/operating details where verified, source and verification state.
- `data_sources`: source identifier/URL, retrieval time, last verification, confidence/status, simulated flag.
- `content_revisions`, `content_reports`: review history and reports.

## Trips and recovery

- `trips`: owner, name, dates, traveller count, budget type/amount, preferences, status.
- `itinerary_versions`: trip, version number, source version, explanation, created by, created time.
- `trip_segments`: itinerary version, sequence, type, origin/destination, planned times, cost (nullable), dependency references, status, source.
- `disruption_events`: trip, type, source class (`simulated`, `user_reported`, `provider_confirmed`), affected item, event details, timestamps.
- `recovery_plans`: disruption, baseline itinerary version, proposed version, constraints snapshot, rationale, status.
- `expense_items`: itinerary version, category, amount nullable, currency, source, estimated/live/simulated flag, assumptions.
- `audit_logs`: actor, action, target type/id, safe metadata, timestamp.

## Progress and community

- `xp_transactions`: user, event/idempotency key (unique), signed amount, rule, reason, related entity, timestamp; append-only except explicit reversal entries.
- `traveller_levels`, `xp_rules`, `badge_definitions`, `user_badges`.
- `achievements`, `achievement_media`, `community_posts`, `likes`, `content_reports` with ownership and visibility rules.

## Integrity rules

- Unique normalized email and username; foreign keys for ownership and relationships.
- Private trips and profile fields are guarded by ownership/authorization checks, not just frontend visibility.
- Published discovery queries exclude drafts and archived content.
- Missing price/availability is `NULL`/unknown, never silently zero/available.
- XP event idempotency keys prevent duplicate rewards.
- Each revised itinerary is a new version; the original is preserved.
- Avoid publishing exact coordinates for sensitive ecological/restricted locations.

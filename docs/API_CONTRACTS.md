# API Contract Direction

All business endpoints will be versioned under `/api/v1`. Implemented endpoints currently include health checks, account registration/email verification/sign-in/sign-out/session inspection, profile read/update, dashboard retrieval, and password reset.

## Planned route groups

- `/auth`: register, verify email, sign in, sign out, session inspection, password-reset request, reset-code verification, and password reset completion.

## Password reset endpoints

- `POST /api/v1/auth/password-reset/request` accepts `{ "email": "..." }`. It returns a generic message regardless of whether the account exists. In `development`/`test`, a reset code is included for local testing only; no real email is sent.
- `POST /api/v1/auth/password-reset/verify` accepts email and a six-digit code. A valid code returns a short-lived, single-use reset token. Invalid/expired codes fail with HTTP 400; attempts are limited to five.
- `POST /api/v1/auth/password-reset/complete` accepts reset token, password, and confirmation. It validates password policy, consumes the authorization, updates the password hash, and invalidates all existing sessions.
- Challenges expire after 10 minutes. New challenges are subject to a 60-second cooldown. Production email delivery is not implemented; production account reset codes are not returned to clients.
- `/profile`: read/update profile and complete onboarding.
- `/destinations`, `/places`, `/trekking`: published discovery, search/filter/pagination, detail pages and saved places.
- `/accommodations`, `/restaurants`, `/transport`, `/contacts`: verified listing discovery.
- `/trips`: create/read/update owned trips and itinerary versions.
- `/planner`: validate preferences and generate feasible candidate itineraries.
- `/expenses`: deterministic budget estimate and option comparison.
- `/disruptions`, `/recovery`: create/ingest disruption events, analyse affected segments, evaluate alternatives, save a reviewed recovery version.
- `/gamification`, `/leaderboard`, `/achievements`, `/community`: eligible progression and moderated content.
- `/admin`: role-protected content, review, user/role, configuration, and audit operations.

## Contract rules

- Use Pydantic request/response schemas rather than returning ORM objects directly.
- Return standard HTTP status codes and a consistent safe error envelope.
- Paginate list endpoints and validate filters server-side.
- Require authentication and ownership checks on private resources.
- Enforce admin/operator permissions in backend dependencies/service policies.
- Avoid leaking internal exceptions, password/reset state, secrets, or private contact data.
- Keep source/provenance/simulation metadata in responses when relevant.

Detailed schemas should be committed alongside each implemented vertical slice, then reflected in FastAPI's OpenAPI output.

## Travel MVP endpoints (v1)

- `GET /api/v1/destinations?q=&category=` — public search; returned seeded entries identify themselves as simulated.
- `GET /api/v1/trips` — authenticated user's saved trips only.
- `POST /api/v1/trips` — create an itinerary; validates destination, travellers, group budget and estimated costs.
- `GET /api/v1/trips/{trip_id}` — retrieve an owned trip.
- `POST /api/v1/trips/{trip_id}/recover` — run a controlled, simulated disruption recovery. Valid types: `transport_cancellation`, `route_closure`, `activity_unavailable`, `accommodation_unavailable`.
- `GET /api/v1/trips/{trip_id}/recovery-history` — view recovery events for an owned trip.

The travel catalogue, costs, and recovery alternatives are demo-only and must not be represented as live verified information.
